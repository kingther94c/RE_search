"""地址 -> 一份完整的 landed 分析报告(估值 + 尽调),中文为主,详略分层。

    python deliverables/build_landed_full_report.py "19 CARDIFF GROVE" --type Terrace
    python deliverables/build_landed_full_report.py "385 LOYANG RISE" --area 1645.8

把两条本来分开的链子接成一个入口:
  - `researcher.landed.dd.run(address)`      -> 地理编码、MP2025 地块/分区/邻地、学校/MRT、水浸
  - `researcher.engine.value_landed`       -> 引擎 LV1 的公允价、区间、可比、买卖指导

接缝上有三件事必须做对,否则整份报告是错的:

1. **地址的路名 != URA 的街道**(EXP-0018)。URA 的 landed `street` 是**发展项目登记的街道**,
   所以 CARDIFF GROVE 的房子在 URA 里挂在 ALNWICK ROAD 名下。用 `street_alias.resolve` 解析;
   解不出来就**拒答**,不猜(GY-0006:最近质心会把 19 Cardiff Grove 配到另一个屋苑的 Chuan Drive)。
2. **地块面积**是估值最敏感的输入。MP2025 的地块只是**指示性**分区宗地,不是地籍丘块;
   `--area`(来自地契/IS 的实测)永远优先,用 MP2025 时必须在报告里标明。
3. **详略分层**:结论 -> 关键数据 -> 证据 -> 局限与方法。用 <details> 折叠,默认只展开前两层。

术语按行业习惯保留英文(land psf / conformal / DD / GPR ...)。
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deliverables.report_out import write_report                      # noqa: E402
from researcher.engine.value_landed import (NOISE_FLOOR, LandedSpec,  # noqa: E402
                                              value_landed)
from researcher import tax as costs_mod                      # noqa: E402
from researcher.landed import dd as dd_mod                            # noqa: E402
from researcher.landed import street_alias                            # noqa: E402
from researcher.landed.comps import street_comps                      # noqa: E402


# ------------------------------------------------------- 深度尽调提示(由事实推导)
# 这一层此前是**手写**的(researcher/landed/<slug>_dd.json 的 dd3_alerts)。手写的问题不是
# 质量,是**会漏**:漏掉的那条不会留下任何痕迹。所以凡是能从事实+规则推出来的,这里自动推;
# 剩下真正需要判断的(archetype / verdict / highlights),由 --digest 挂载,没有就明说没有。
_UNIVERSAL = [
    ("BCA 批准的建筑与结构图纸", True,
     "<b>你买不到</b> —— BCA 的 Plan Purchase 只受理注册业主本人、其公司职员、MCST 主席,"
     "或持<b>业主签字授权</b>+业主房产税单的获授权人。拿不到就无法把「实际建成」和「批准图则」"
     "对照,违建与其整改责任在成交后属于你。"),
    ("法定地块面积、地契起算日、他项权利", False,
     "本链条给的是 MP2025 的<b>指示性</b>宗地与街道级 tenure,<b>都不是法律事实</b>。"
     "业主、抵押、地役权、法定面积、Certified Plan —— 需 INLIS(DD-2,约 S$16)。"),
    ("这块地会不会积水?", False,
     "PUB 名单是<b>按名称</b>匹配的全国清单(23.3 ha / 全国约 73,000 ha,0.032%),"
     "「不在名单上」对<b>单一地块</b>几乎没有证据力。隔壁路淹不会命中你。属实地问题(DD-3)。"),
]


def _alerts_zh(g: dict) -> list[tuple[str, bool, str]]:
    """(标题, 是否受制于卖家, 为什么) —— 普适项 + 从本地址事实推出的项。"""
    out = list(_UNIVERSAL)
    d, v = g["dd"], g["val"]
    # F12(2026-07-21 评审):每个敏感邻地各占一条、三行说明逐字重复 —— 159 Chun Tin 渲染成
    # 重复墙。合并为一条,并带上地块**面积**与 GPR:「先识别再评级」是这条链自己的规矩
    # (14.5 sqm 的 UTILITY 是电箱不是变电站),此前面积恰恰被丢掉了。
    nb_hits = []
    for nb in (d.get("neighbours") or []):
        z, m = (nb.get("zone") or ""), nb.get("metres") or 9e9
        if z in dd_mod.TRANSECT_ZONES and m <= dd_mod.TRANSECT_WITHIN_M:
            area = nb.get("area_sqm")
            gpr = nb.get("gpr")
            nb_hits.append(f"<b>{_esc(z)}</b> @ {m:.0f}m"
                           f"{'(' + format(area, ',.0f') + ' sqm' + (' · GPR ' + _esc(gpr) if gpr else '') + ')' if area else ''}"
                           f"{' · 方位 ' + str(int(nb['bearing_deg'])) + '°' if nb.get('bearing_deg') is not None else ''}")
    if nb_hits:
        out.append(("邻近敏感用地(合并核查):" + ";".join(nb_hits),
                    False,
                    "分区<b>标签</b>不等于地上<b>今天</b>在做什么 —— 标签本身误导过人。先读"
                    "<b>面积</b>(小地块多为电箱/设施,不是厂站),再走剖面(只说明「隔着什么」,"
                    "不代表已经到达),最后按时段实地看:经营内容、噪音/气味、车流。属实地问题(DD-3)。"))
    sch = (d.get("schools_primary") or [])
    ring = [s for s in sch if s["km"] <= 1.2]
    if ring:
        out.append((f"{_esc(ring[0]['name'])} 的 1km 学区身份({ring[0]['km']}km,本报告为直线估计)",
                    False,
                    "官方口径是 OneMap <b>SchoolQuery</b>(量的是<b>校地边界</b>到住址),"
                    "我们的直线距离量到<b>校点</b>,是<b>保守的高估</b> —— 说「在圈内」安全,"
                    "贴近 1km 线时<b>未定</b>。且学区不是永久属性,报名当年要重新核。"))
    if v and (g["land_area"] or 0) >= 8000:
        out.append(("大地块的估值仅供指示", False,
                    "≥8k sqft 的地块上,尺寸曲线的证据最薄、拟合最不可靠(EXP-0011);"
                    "点估值只作指示,须逐案人工复核(可比逐笔核 + IS 佐证)后才可引用。"))
    if g["resolve"]["basis"] == "alias":
        out.append((f"本路({_esc(g['dd']['street'])})自己的成交分布", False,
                    f"URA 把本路的 caveat 归在「{_esc(g['resolve']['ura_street'])}」桶里,桶内混着"
                    f"同屋苑其它路 —— 议价门槛因此在本报告中<b>被抑制</b>。要门槛,得用 "
                    f"Investment Suite 拉本路自己的分布(操作命令见估值节折叠)。"))
    lh = d.get("landed_housing_area") or {}
    if (lh.get("classification") or "").upper().startswith("GOOD CLASS"):
        out.append((f"GCBA 身份与本宗地的适用规则({_esc(lh.get('name') or 'GCBA')})", False,
                    "本址在 Good Class Bungalow Area 内 —— 买家池(实质 SC-only 高净值现金盘)、"
                    "细分下限(1,400 sqm)、层高基调(2 层)都自成制度。本宗地按 GCB 还是按普通"
                    "detached 定价、能否按 GCB 规则重建,须 QP + GCB 专营中介逐项核;"
                    "上文估值未区分街内 GCBA 段与非 GCBA 段的成交。"))
    if v:
        out.append(("建筑状况 condition —— bundle 价里最大的未观测项", False,
                    "引擎是 condition-blind 的。实测(Cardiff Grove,同期同尺寸):原装 "
                    "$1,767-1,946/psf、翻建 $2,327-2,848/psf —— <b>同一条路上价差 60%</b>。"
                    "现场定原装/翻新/翻建与 GFA,否则这份估值的最大不确定性没有被消除。"))
    return out


# ------------------------------------------------- F1:判断层 alerts 与自动 alerts 合并
# 第一版只渲染了 digest 的 verdict/archetype/highlights,把 8 条 authored `dd3_alerts`
# **静默丢弃** —— 丢掉的里面有 archetype 指名的头号风险("Defects and build quality",
# turnkey 原型特有,自动规则永远推不出来)。合并原则:
#   - 同主题时**用人写的**(它是为这个地址写的,更具体),自动版让位;
#   - 人写独有的照登(标「人写」);自动独有的照登(标「工具推导」);
#   - 与本报告现状**冲突**的人写条目(digest 写于引擎接入之前,其「刻意不给估值」一条
#     已被第 1 节推翻)不删也不照登 —— 显式标注「已被本报告取代」,读者能看见判断的时间线。
_SUPERSEDED_ITEMS = {
    # authored item 的英文开头 -> 取代说明
    "Fair value": "该条写于估值引擎接入之前,当时「不给估值」是对的立场;本报告第 1 节"
                  "现已给出引擎 LV1 的估值 —— 此条保留存档,按已取代读。",
}
_MATCH_RULES = [
    # (authored item(en) 里的关键词, 自动标题里的关键词) —— 命中即视为同主题
    ("BCA", "BCA"),
    ("Legal land area", "法定地块面积"),
    ("pond", "积水"),
    ("SchoolQuery", "1km 学区"),
]


def _merged_alerts(g: dict) -> list[dict]:
    """[{title, gated, why, src('tool'|'authored'|'superseded'), meta, sup}] 顺序 =
    自动清单为骨架(同主题处换成人写版),其后接人写独有项,最后是已取代项。"""
    autos = [{"title": t, "gated": gd, "why": w, "src": "tool", "meta": "", "sup": ""}
             for t, gd, w in _alerts_zh(g)]
    authored = list(((g.get("digest") or {}).get("dd3_alerts")) or [])

    def _match(a_en: str, auto_title: str) -> bool:
        low = a_en.lower()
        for k_en, k_auto in _MATCH_RULES:
            if k_en.lower() in low and k_auto in auto_title:
                return True
        if "用地在" in auto_title:                       # 邻地分区项:按 zone 名对上
            zone = auto_title.split(" 用地在")[0].strip()
            if zone and zone.lower() in low:
                return True
        return False

    def _entry(a: dict, src: str, sup: str = "") -> dict:
        meta = " · ".join(x for x in (
            f"谁:{a['who_zh']}" if a.get("who_zh") else "",
            f"何时:{a['when_zh']}" if a.get("when_zh") else "",
            f"费用:{a['cost']}" if a.get("cost") else "") if x)
        return {"title": a.get("item_zh") or a.get("item") or "",
                "gated": bool(a.get("seller_gated")),
                "why": a.get("why_zh") or a.get("why") or "",
                "src": src, "meta": meta, "sup": sup}

    out, used = [], set()
    for auto in autos:
        hit = next((i for i, a in enumerate(authored) if i not in used
                    and not any(a.get("item", "").startswith(k) for k in _SUPERSEDED_ITEMS)
                    and _match(a.get("item", ""), auto["title"])), None)
        if hit is None:
            out.append(auto)
        else:
            used.add(hit)
            out.append(_entry(authored[hit], "authored"))
    for i, a in enumerate(authored):
        if i in used:
            continue
        sup = next((v for k, v in _SUPERSEDED_ITEMS.items()
                    if a.get("item", "").startswith(k)), "")
        out.append(_entry(a, "superseded" if sup else "authored", sup))
    return out


# --------------------------------------------------------------- 中文叙述层
# 引擎(value_landed)返回的是英文散文。这里**不改引擎**(它的字符串有回归测试、也被别的
# 调用方依赖),而是用它返回的**结构化字段**重新渲染中文,并把引擎原文折叠在旁边备查 ——
# 报告是渲染,不是翻译:所有判断仍然来自引擎的字段,中文只是它的表达。
_COND_ZH = {
    "rebuilt": "你报告本房已<b>翻建 rebuilt</b>:可比池是 condition-blind 的混合体,翻建房通常"
               "成交在估值<b>之上</b> —— 把这个点当作<b>地板</b>读。幅度<b>未量化</b>"
               "(尚无经过验证的 condition 效应,L2e backlog)。",
    "renovated": "你报告本房<b>翻新过 renovated</b>:大概率略高于 condition-blind 的估值;"
                 "幅度<b>未量化</b>(L2e backlog)。",
    "original": "你报告本房为<b>原装 original</b>:池子里混着翻建/翻新的可比,会把 condition-blind "
                "的估值<b>拉高</b>,所以这个点对原装房可能是<b>天花板</b>。幅度<b>未量化</b>"
                "(L2e backlog)。",
}
_COND_NONE_ZH = ("<b>未提供 condition,引擎也不会去猜。</b>区间本身已经含了"
                 "<b>平均意义上的</b> condition 无知(它是在 condition-blind 的残差上校准的),"
                 "因此不会再为此加宽。请现场确认 —— 这是 bundle 价格里最大的未观测驱动因素。")


# ------------------------------------------------- F3:方法分歧与置信度的中文叙述
_READ_NAMES = {"LC2_street_grid": "街道网格 LC2", "LA1_pooled": "池化锚 LA1",
               "LB4_spatial_knn": "空间 kNN LB4"}


def _reads_zh(v: dict) -> str:
    """独立方法读数 + 分歧,放在**明面**(此前折叠在证据层)。这个信息决定读者该多信这个点:
    实测 14 Seletar Green Walk 分歧 17%,离 hard-case 抑制线 18% 只差 1pp —— 读者有权知道
    自己站在线边,而不是只看到一个没有解释的「置信度 63」。"""
    reads = {k: x for k, x in v["independent_reads_land_psf"].items() if x}
    if len(reads) < 2:
        return ""
    sp = v["method_disagreement"].get("spread_rel")
    line = " · ".join(f"{_READ_NAMES.get(k, k)} {x:,.0f}" for k, x in reads.items())
    txt = f"<p class=note><b>独立方法读数(land psf):</b>{line}"
    if sp is not None:
        txt += f" —— 分歧 <b>{sp*100:.0f}%</b>(hard-case 抑制阈值 18%)"
        if sp >= 0.10:
            vals = sorted(reads.values())
            med = vals[len(vals) // 2]
            outk, outv = max(reads.items(), key=lambda kv: abs(kv[1] - med))
            if outk == "LA1_pooled":
                txt += ";分歧主要来自池化锚 —— 它跨街取样,在已重估的微观市场会系统性偏低"
            else:
                txt += (f";分歧主要来自{_READ_NAMES.get(outk, outk)}"
                        f"(偏离中位读数 {abs(outv/med-1)*100:.0f}%)")
        # F15(2026-07-21 评审):10 Namly 分歧 20% 已**越过** 18% 的抑制线,此前仍写
        # 「已接近」—— 与同页的 hard-case 事实矛盾。
        if v["method_disagreement"].get("hard_case"):
            txt += ";<b>已越过抑制线(hard case)</b>,出价前先用 Investment Suite 佐证"
        elif sp >= 0.14:
            txt += ";<b>已接近抑制线</b>,出价前先用 Investment Suite 佐证"
    return txt + "。</p>"


def _conf_zh(v: dict) -> str:
    """置信度的构成,由结构化字段生成(引擎的英文 confidence_label 折叠备查)。"""
    fv, md = v["fair_value"], v["method_disagreement"]
    n, sp = fv["n_street_comps"], md.get("spread_rel")
    ptype = v["subject"]["property_type"]
    floor = NOISE_FLOOR.get(ptype, 0.06)
    depth = ("同街证据深" if n >= 8 else "同街证据中等" if n >= 3 else
             "同街证据薄" if n >= 1 else "无同街证据,点来自 pooled 兜底")
    drag = (f",但方法分歧 {sp*100:.0f}% 把它拉低了" if sp and sp > 0.06 else "")
    return (f"<p class=note><b>置信度 {fv['confidence']}/100 的构成:</b>{depth}(n={n}){drag};"
            f"无论证据多深,精度都受 <b>~{floor*100:.0f}%/笔</b>({ptype})的捆绑噪声下界约束"
            f"(EXP-0010,同地块重复成交实测)。</p>")


def _suppress_reason_zh(v: dict, area: float, basis: str = "direct") -> str:
    """抑制原因用**结构化字段**重建,不解析引擎的英文串。"""
    md, fv = v["method_disagreement"], v["fair_value"]
    if basis == "alias":
        # 报告层自己加的一道闸,引擎没有(引擎不知道街道是别名解析来的)。
        # EXP-0019(L2f)量化了这道闸:混路本身不必然错置门槛 —— 关键是**少数份额**。
        # 当真实路只占母路桶一小部分时(Cardiff Grove 占 ALNWICK 桶 4%),桶的分位数被
        # 多数派主导,把门槛推离本路 15.8%;而同屋苑同量级的路(Loyang Rise/View)偏差 <4%。
        # 点估值可以留(引擎在整桶上验证过),但**议价门槛不能**在少数份额的路上直接用。
        return ("URA 街道是<b>别名解析</b>来的 —— 本路的成交只占母路桶一小部分,桶的 p25/p75 "
                "被桶里的多数派主导,不是本路自己的分布(EXP-0019 实测:少数份额的路门槛可偏 15%)")
    if area >= 8000:
        return "地块 ≥8k sqft —— 尺寸曲线在这里证据最薄、拟合最不可靠(EXP-0011)"
    if fv["n_street_comps"] == 0:
        return "同街没有 lease-compatible 可比,点估值来自 pooled 兜底"
    if md.get("hard_case"):
        return f"各方法分歧 {md['spread_rel']*100:.0f}%(hard case)"
    if fv["confidence"] < 55:
        return f"置信度 {fv['confidence']}/100 过低"
    return "lease-matched 的同街成交太少,读不出四分位"


def _limits_zh(v: dict, ptype: str) -> list[str]:
    floor = {"Terrace": 6.0, "Semi-detached": 7.8, "Detached": 8.2}.get(ptype, 6.0)
    return [
        f"<b>URA 卖的是「地+房」捆绑价</b>,不含 condition/GFA/几何 → 每笔成交有约 "
        f"<b>{floor:.0f}% 的不可约噪声下界</b>(EXP-0010,同地块重复成交实测)。"
        f"在这份数据上,没有任何模型能突破它。",
        "引擎 LV1 实测 <b>中位 APE 9.1% / 区间覆盖 78.9%</b>(EXP-0017,walk-forward)—— "
        "诚实的高个位数,<b>不是</b> condo 级精度。",
        "<b>Regime 偏差(EXP-0014/0017,已部分收敛但仍披露):</b>平稳市场无偏,"
        "<b>加速市场系统性偏低</b>(实际成交高于估值的比例:2023-24 约 47-53%,2025 约 60-62%)。"
        "各 regime 的中位 APE 是平的 —— 误差是<b>有方向的</b>,不是更大。热市里把点估值当<b>地板</b>读。"
        "EXP-0018 又堵死了最后一条路:Investment Suite 与 URA 是<b>同一批 caveat、同样的滞后</b>,"
        "没有更新鲜的数据源 —— 这个残差是<b>永久性</b>的。",
        "引擎<b>看不见 condition,也看不见几何</b>(frontage/形状/转角/退界):不会因 condition "
        "移动点估值(无验证效应),也完全无法感知地块形状。区间含的是<b>平均</b> condition 无知。",
        "<b>区间是引擎的预测误差,不是能成交的议价区间。</b>区间宽的时候,买卖指导按设计会被抑制。",
    ]


def _verify_zh(v: dict, g: dict) -> list[str]:
    fv, md = v["fair_value"], v["method_disagreement"]
    out = [
        "<b>产权与规划(INLIS / URA)</b>:确切地块面积、tenure、road/drainage reserve 占用、"
        "退界、conservation 或 landed housing area 管制",
        "<b>地块几何</b>(frontage / 进深 / 形状 / 转角)—— URA <b>一个都没有</b>;模型对几何全盲,"
        "形状差或被 reserve 切掉在这里<b>没有定价</b>",
        "<b>建筑状况与楼龄</b> —— caveat 价是「地+房」捆绑;现场确认原装/翻新/翻建与 GFA",
        "<b>重建潜力没有被计价</b> —— 付这部分钱之前先核实 GPR/高度/地块规则",
    ]
    if g["area_src"] and "MP2025" in g["area_src"]:
        out.insert(0, "<b>地块面积来自 MP2025 宗地(指示性,非地籍丘块)</b> —— 估值 = land psf × 面积,"
                      "面积错则全错。用地契/实测面积重跑(<code>--area</code>)")
    if g["resolve"]["basis"] == "alias":
        out.insert(0, f"<b>可比取自 URA 的「{_esc(g['resolve']['ura_street'])}」桶</b>,它同时装着本路"
                      f"与同屋苑其它路的房子 —— 这个池子是否该按真实门牌路拆分,尚未有回测结论"
                      f"(roadmap L2f)。对本宗地,请人工核一眼可比表里的成交是否可比。")
    if fv["n_street_comps"] < 3 or md.get("hard_case"):
        out.append("<b>同街证据薄或方法分歧</b> —— 下单前先用 Investment Suite 拉本街同型"
                   "分布,与引擎点并排佐证"
                   "<details><summary class=note>内部操作命令</summary>"
                   "<code>research/lib/harvest_street_sale.py</code> 收获本街 → "
                   "<code>research/tools/is_street_compare.py --area … --engine-street …</code>"
                   "</details>")
    if g["land_area"] and g["land_area"] >= 8000:
        out.append("<b>大地块(≥8k sqft)</b>:尺寸曲线在这里证据最薄、拟合最不可靠(EXP-0011)—— "
                   "点估值只作<b>指示性</b>,逐案人工复核后再用")
    return out


# ------------------------------------------- A/B 回移(2026-07-19):近窗读数与年度趋势
# 来自 AI 盲写对照实验:AI 臂用「近12月/近半年/最近簇」三个口径互证当前市场水平,并给出
# 街道 vs 标的队列的年度趋势 —— 都是纯观测(原始 caveat,未调整),引擎报告此前没有渲染。
# 口径必须与引擎分开标注:这里是 RAW psf;引擎的点估值/门槛活在 adj psf(时间+尺寸调整)上。
def _ym_idx(ym: str) -> int:
    y, m = ym.split("-")
    return int(y) * 12 + int(m) - 1


def _cohort_rows(rows: list[dict], area: float, tol: float = 0.06) -> list[dict]:
    lo, hi = area * (1 - tol), area * (1 + tol)
    return [r for r in rows if lo <= (r.get("area_sqft") or 0) <= hi]


def _recent_windows(rows: list[dict], area: float) -> dict | None:
    """标的队列(±6%)的近窗观测:近12月 / 近半年 / 最近3笔簇 + 累计重估与隐含月漂移。
    rows = street_comps(...)(已按 contract_ym 升序)。全部 RAW psf。"""
    c = _cohort_rows(rows, area)
    if len(c) < 4:
        return None
    end = _ym_idx(c[-1]["contract_ym"])
    w12 = [r for r in c if _ym_idx(r["contract_ym"]) > end - 12]
    w6 = [r for r in c if _ym_idx(r["contract_ym"]) > end - 6]
    prev6 = [r for r in c if end - 12 < _ym_idx(r["contract_ym"]) <= end - 6]
    cluster = c[-3:]
    out = {
        "last_ym": c[-1]["contract_ym"], "cohort_n": len(c),
        "n12": len(w12), "med12_psf": statistics.median(r["psf"] for r in w12) if w12 else None,
        "med12_price": statistics.median(r["price"] for r in w12) if w12 else None,
        "n6": len(w6), "med6_psf": statistics.median(r["psf"] for r in w6) if w6 else None,
        "cluster": [(r["contract_ym"], r["psf"]) for r in cluster],
        "cluster_med": statistics.median(r["psf"] for r in cluster),
        "drift_mo": None, "cum_pct": None, "cum_from_year": None,
    }
    # 隐含月漂移:近6月中位 vs 其前6月中位,除以 6 —— 两窗各 ≥3 笔才报,否则是噪声
    if len(w6) >= 3 and len(prev6) >= 3:
        m_now = statistics.median(r["psf"] for r in w6)
        m_prev = statistics.median(r["psf"] for r in prev6)
        out["drift_mo"] = (m_now / m_prev - 1) / 6
    # 累计重估:首个日历年队列中位 -> 近12月中位(首年 ≥3 笔才报)
    first_year = c[0]["contract_ym"][:4]
    fy = [r for r in c if r["contract_ym"].startswith(first_year)]
    if len(fy) >= 3 and out["med12_psf"]:
        base = statistics.median(r["psf"] for r in fy)
        out["cum_pct"] = out["med12_psf"] / base - 1
        out["cum_from_year"] = first_year
    return out


def _year_trend(rows: list[dict], area: float) -> list[dict]:
    """按日历年:街道全体 vs 标的队列(±6%)的 n 与中位 —— 面积效应逼着两列分开看。"""
    c_set = {id(r) for r in _cohort_rows(rows, area)}
    years: dict[str, dict] = {}
    for r in rows:
        y = r["contract_ym"][:4]
        b = years.setdefault(y, {"street": [], "cohort": []})
        b["street"].append(r)
        if id(r) in c_set:
            b["cohort"].append(r)
    out, prev_med, prev_year = [], None, None
    for y in sorted(years):
        b = years[y]
        med_c = statistics.median(r["psf"] for r in b["cohort"]) if b["cohort"] else None
        out.append({
            "year": y, "n_street": len(b["street"]),
            "med_street": statistics.median(r["psf"] for r in b["street"]),
            "n_cohort": len(b["cohort"]), "med_cohort": med_c,
            "price_cohort": statistics.median(r["price"] for r in b["cohort"]) if b["cohort"] else None,
            "yoy": (med_c / prev_med - 1) if (med_c and prev_med) else None,
            # F18(2026-07-21 评审):YoY 与上一个**有数**的年份比 —— 跨了空档年必须说
            "yoy_gap": (int(y) - prev_year) if (med_c and prev_med and prev_year and
                                                int(y) - prev_year > 1) else None,
        })
        if med_c:
            prev_med, prev_year = med_c, int(y)
    return out


def _fresh_vs_cluster(comps: list[dict], ref: dict | None = None) -> dict | None:
    """最新一笔 adj psf 相对其前 3 笔簇中位的偏离 —— 决定它是「锚」还是「上/下尾单笔」。

    F7(2026-07-21 评审):引擎的 comps 是**按权重**排的,不是按月份 —— 第一版把 comps[0]
    当「最新」,三份 Bukit Timah 样本报告的「最新 vs 近簇」段全部算在错误的行上,与同段
    引用的 ref 月份自相矛盾。修正:先按月份降序排;「最新」优先取引擎自己的
    recent_street_reference(它才是引擎口径的最新可比),簇 = 严格早于它的 3 笔。"""
    rows = sorted(comps, key=lambda c: c["contract_ym"], reverse=True)
    if ref and ref.get("contract_ym") is not None:
        fresh_psf, fresh_ym = ref["adj_psf"], ref["contract_ym"]
        prior = [c for c in rows if c["contract_ym"] < fresh_ym][:3]
    elif rows:
        fresh_psf, fresh_ym = rows[0]["adj_land_psf"], rows[0]["contract_ym"]
        prior = rows[1:4]
    else:
        return None
    if len(prior) < 3:
        return None
    med = statistics.median(c["adj_land_psf"] for c in prior)
    return {"gap": fresh_psf / med - 1, "cluster_med": med, "n_cluster": len(prior)}


def _envelope_zh(env: str | None) -> str:
    """MP2025 SDCP 的 PERM_ENV("3-STOREY ENVELOPE")→ 中文读数。不认识的值原样保留。"""
    if not env:
        return "—"
    m = re.match(r"^(\d+)[- ]STOREY", env.upper())
    return f"{m.group(1)} 层包络" if m else env


def _aa_evidence(g: dict) -> dict | None:
    """A&A 节的市场证据(标的队列 ±6% 同型、同地契制度、去重后、近 24 个月)。
    F22(2026-07-23 评审):抽出来的原因是「读法句」要引用它 —— 第一版无条件写
    「原始极值见 A&A 节」,而 97/5 的 A&A 节根本没渲染极值段(悬空引用)。
    返回 kind ∈ {spread(≥15% 价差可读), flat(有样本但价差小), thin(样本不足)} 或 None。"""
    if not (g.get("street_rows_subject") and g["land_area"]):
        return None
    lo_a, hi_a = g["land_area"] * 0.94, g["land_area"] * 1.06
    coh = [r for r in g["street_rows_subject"]
           if r.get("property_type") == g["ptype"] and lo_a <= (r.get("area_sqft") or 0) <= hi_a]
    coh = sorted(coh, key=lambda r: r["contract_ym"], reverse=True)[:12]
    recent = ([r for r in coh if _ym_idx(coh[0]["contract_ym"]) - _ym_idx(r["contract_ym"]) <= 23]
              if coh else [])
    if len(recent) >= 2:
        hi = max(recent, key=lambda r: r["psf"])
        lo = min(recent, key=lambda r: r["psf"])
        spread = hi["psf"] / lo["psf"] - 1
        return dict(kind="spread" if spread > 0.15 else "flat", hi=hi, lo=lo, spread=spread,
                    n=len(recent), gap_mo=abs(_ym_idx(hi["contract_ym"]) - _ym_idx(lo["contract_ym"])))
    if coh:
        return dict(kind="thin", n=len(coh))
    return None


def _aa_block(g: dict) -> str:
    """A&A/重建潜力 —— 观测层(2026-07-21 评审新增,Bukit Timah 三样本驱动)。

    这一节回答的是「能不能加盖」被拆开后的三个问题里,桌面上答得了的那一个:
      ① 管制允许盖到几层 —— MP2025 SDCP,本节给出(此前渲染层把 envelope 键读错,
         层数管制被静默丢弃 —— 三份样本报告的 HTML 里 "ENVELOPE" 出现 0 次);
      ② 现楼是几层、GFA 多少 —— 只有现场/批准图则知道,本报告不知道,明说;
      ③ 结构与退界能否承载加建 —— QP(DD-3)。
    市场证据用标的队列(±6% 同型)的原始 psf 极值呈现:同尺寸段的价差主要由建筑状态
    (原装 vs 翻建/GFA)承载 —— 这就是 A&A 价值被本街市场支付的观测,caveat 拆不出来,
    所以它**不进点估值**(引擎 condition-blind),但读者必须看见它。"""
    d = g["dd"]
    lh = d.get("landed_housing_area") or {}
    if not lh:
        return ""
    env = (lh.get("envelope") or "").upper()
    cls = (lh.get("classification") or "").upper()
    gcba = cls.startswith("GOOD CLASS")
    n_storey = int(re.match(r"^(\d+)", env).group(1)) if re.match(r"^\d", env) else None
    # —— 管制读数
    rows = (f"<tr><td>landed 类型(MP2025 SDCP)</td><td class=r>{_esc(lh.get('type'))}</td></tr>"
            f"<tr><td>层数包络 storey envelope</td><td class=r><b>{_esc(_envelope_zh(lh.get('envelope')))}</b>"
            f" <span class=note>({_esc(lh.get('envelope'))})</span></td></tr>")
    if cls:
        rows += (f"<tr><td>管制类别</td><td class=r>{_esc(cls)}"
                 + (f" · <b>{_esc(lh.get('name'))}</b>" if lh.get("name") else "") + "</td></tr>")
    # —— 分制度的余量语言(管制是「面」的属性;这块地能否实现,②③说了算)
    if gcba:
        head = (f"<div class='banner warn'><b>本址位于 GCBA(Good Class Bungalow Area:"
                f"{_esc(lh.get('name') or '')})</b> —— 独立的管制与买家制度:仅限独立洋房形态,"
                f"细分地块下限 <b>1,400 sqm</b>(约 15,069 sqft),层高管制以 2 层为基调,"
                f"且 landed 买家池本就限公民,GCB 市场实质上是<b>全现金、超高净值、SC-only</b> 的"
                f"独立流动性池。规则细节以 URA 现行指引为准(DD-3 由 QP 核)。</div>")
        if g["land_area"] and g["land_area"] / 10.7639 < 1400:
            head += (f"<p class=note>⚠ 本宗地 {g['land_area']:,.0f} sqft ≈ "
                     f"{g['land_area']/10.7639:,.0f} sqm,<b>低于 GCB 的 1,400 sqm 细分下限</b> —— "
                     f"属 GCBA 内的「次标准尺寸」存量地块:不可再分割,能否按 GCB 规则重建、"
                     f"市场是否按 GCB 定价,都必须由 QP 与可比逐一核实;"
                     f"上文估值用的是全街 detached 成交,<b>未区分 GCBA 段与非 GCBA 段</b>。</p>")
        updown = ("向上空间:GCBA 以 2 层为基调(阁楼/地下室按现行指引)——「加盖」不是 GCB "
                  "价值的主轴;这里的重建价值轴是<b>地块本身</b>(形状、朝向、进深)与建筑品质。")
    elif n_storey and n_storey >= 3:
        updown = (f"管制允许 <b>{n_storey} 层</b>(+阁楼,按 URA envelope control 在包络内计)。"
                  f"若现楼低于 {n_storey} 层 —— 本报告<b>不知道现楼层数</b>(见下)—— 则存在"
                  f"实打实的包络余量:同地块通过 A&amp;A/重建增加 GFA,是本区(3 层混合 landed)"
                  f"价值最直接的一条路。能否实现取决于结构、退界、保留树、车位与 QP 可研。")
    else:
        updown = ("管制为 <b>2 层包络</b> —— 向上加盖空间受限;A&amp;A 的余量主要在"
                  "<b>阁楼(envelope control 在屋顶包络内)、地下室、后部/侧部扩建</b>,"
                  "每一项都要 QP 按退界与包络逐条核,不能从分区标签直接推。")
    # —— 三个问题,谁答得了
    tri = ("<table class=kv>"
           "<tr><td>① 管制允许几层</td><td class=r>已知 —— 上表(MP2025 SDCP)</td></tr>"
           "<tr><td>② 现楼几层 / 现有 GFA</td><td class=r><b>本报告不知道</b> —— 现场 + 批准图则"
           "(图则需业主授权,DD-3)</td></tr>"
           "<tr><td>③ 结构/退界能否承载加建</td><td class=r>QP 可研(DD-3)</td></tr></table>")
    # —— 市场证据:标的队列近 24 个月的原始 psf 极值(同型 ±6%,同地契制度,已去重)
    aa_ev = _aa_evidence(g)
    ev = ""
    if aa_ev and aa_ev["kind"] == "spread":
        hi, lo, spread, n = aa_ev["hi"], aa_ev["lo"], aa_ev["spread"], aa_ev["n"]
        gap_mo = aa_ev["gap_mo"]
        # 两笔相隔一年以上时,「相近月份」不成立 —— 价差里混着时间,必须说(10 Namly:
        # n=2、相隔 23 个月,23% 里有一段是 2023→2025 的市场重估,不全是建筑状态)。
        time_cav = (f"两笔相隔 {gap_mo} 个月 —— 价差里<b>混着这段时间的市场变动</b>,"
                    f"建筑状态承载的是其中大头但不是全部;" if gap_mo > 12 else
                    "同一条街、同一尺寸段、相近月份,")
        ev = (f"<h3>市场证据:同尺寸段的价差,大头在建筑状态</h3>"
              f"<p class=note>标的队列(同型 ±6%,近 24 个月,n={n})原始 psf 极值:"
              f"<b>${lo['psf']:,.0f}</b>({_esc(lo['contract_ym'])},{lo['area_sqft']:,.0f} sqft,"
              f"{_money(lo['price'])})至 <b>${hi['psf']:,.0f}</b>({_esc(hi['contract_ym'])},"
              f"{hi['area_sqft']:,.0f} sqft,{_money(hi['price'])})—— 价差 <b>{spread*100:.0f}%</b>。"
              f"{time_cav}这个量级的价差不是地价的波动,主要是"
              f"<b>建筑状态(原装 vs 翻建 / GFA 差异)</b>在 bundle 价里的体现 —— 即市场"
              f"实际支付的 A&amp;A/重建价值。caveat 无法把它拆出来,故它<b>不在</b>上文"
              f"点估值里;买翻建房请对照队列上沿,买原装房请对照下沿,勿用中位一把抹。</p>")
    elif aa_ev and aa_ev["kind"] == "flat":
        ev = (f"<p class=note>标的队列(同型 ±6%,近 24 个月,n={aa_ev['n']})原始 psf 价差仅 "
              f"{aa_ev['spread']*100:.0f}% —— 近窗未见显著的建筑状态分层;A&amp;A 价值的市场上沿"
              f"请以邻街/邻段已翻建可比实地核。</p>")
    elif aa_ev and aa_ev["kind"] == "thin":
        ev = (f"<p class=note>标的队列(同型 ±6%)近窗样本不足以呈现状态价差"
              f"(n={aa_ev['n']})—— A&amp;A 价值的市场证据请以已翻建可比实地核。</p>")
    # —— 评估框架(不计价)
    frame = ("<h3>评估框架(本报告不为潜力计价)</h3>"
             "<p class=note>A&amp;A/重建是否划算,只能这样核:<b>已翻建同型可比价 − 建安成本"
             "(2025-26 行情约 S$450–600/psf GFA,高端 S$700+,以 QP 可研 + 2-3 家承包商报价为准)"
             "− 拆除与 18-24 个月持有/机会成本 − 税费</b>,与「直接买已翻建」对照。"
             "若这笔账只有在地价年涨 &gt;5% 的假设下才成立,它不成立。"
             "引擎对 condition 与包络双盲 —— <b>潜力没有进入上文估值</b>,这是纪律不是遗漏:"
             "潜力值多少,由已翻建可比与成本核出来,不由分区标签想象出来。</p>")
    return (f"<div class=card><h2>3 · A&amp;A / 重建潜力 <span class=note>(观测层 —— 管制读数 + "
            f"市场证据;不计价,逐项核)</span></h2>{head if gcba else ''}"
            f"<table class=kv>{rows}</table><p class=note>{updown}</p>{tri}{ev}{frame}</div>")


def _split_stations(mrt: list[dict]) -> tuple[list[dict], list[dict]]:
    """全岛车站清单拆成 (MRT 重轨, LRT 轻轨) —— 混标会把 1.35km 的 LRT 报成「最近 MRT」。"""
    lrt = [n for n in mrt if "LRT" in (n.get("name") or "").upper()]
    heavy = [n for n in mrt if n not in lrt]
    return heavy, lrt


def _money(x) -> str:
    if x is None:
        return "—"
    if x >= 1e6:
        return f"S${x/1e6:.2f}M"
    if x >= 1e3:
        return f"S${x/1e3:.0f}k"
    return f"S${x:,.0f}"


def _esc(x) -> str:
    return html.escape(str(x if x is not None else "—"))


def gather(address: str, ptype: str, area: float | None, tenure: str | None,
           lease_start: int | None, condition: str | None, asof: str | None,
           profile: str = "SC", count: int = 1, digest: dict | None = None,
           postal: str | None = None) -> dict:
    """DD 链 + 街道解析 + 估值。任何一环诚实失败都不阻断其余部分。
    postal:部分地址只有邮编能在 OneMap 命中(实测 97 KING'S ROAD)—— 显示地址不变。"""
    d = dd_mod.run(address, query=postal)
    road = d["street"]
    res = street_alias.resolve(road, lambda s: bool(street_comps(s)))

    plot = d.get("plot") or {}
    # 面积优先级:用户实测 > MP2025 宗地(指示性)。估值对面积极敏感,来源必须写进报告。
    land_area = area or plot.get("area_sqft")
    area_src = ("用户提供(地契/实测)" if area else
                "MP2025 宗地面积 —— 指示性,非地籍丘块" if plot.get("area_sqft") else None)

    # F4:同一份报告里会出现两个可比数(判断层说街道 63 笔、估值说 n=54)—— 都对,但差在
    # 过滤,必须解释。F6:MP2025 面积若与 URA 桶内成交的地块面积大量重合,那是比「指示性」
    # 强得多的交叉验证(两个互不通气的官方源),要说出来。
    street_total, street_rows, area_xval = 0, [], ""
    if res["ura_street"]:
        rows = street_comps(res["ura_street"])
        street_total, street_rows = len(rows), rows
        if land_area and not area:                      # 面积来自 MP2025 时才谈交叉验证
            k = sum(1 for t in rows if abs((t.get("area_sqft") or 0) - land_area) <= 2)
            if k >= 10:
                area_xval = (f";与 URA 该桶 {k}/{street_total} 笔成交的地块面积一致 "
                             f"—— 两个互不通气的官方源交叉验证")
    if area_src and area_xval:
        area_src += area_xval

    val, val_error = None, None
    if not res["ura_street"]:
        val_error = res.get("evidence_zh") or res["evidence"]
    elif not land_area:
        val_error = ("没有地块面积:MP2025 在此处没有宗地,且未提供 --area。"
                     "land psf x 面积 是估值的全部,面积缺失即无法估值。")
    else:
        v = value_landed(LandedSpec(street=res["ura_street"], land_area_sqft=float(land_area),
                                    property_type=ptype, tenure_type=tenure,
                                    lease_start=lease_start, condition=condition, asof=asof))
        if v.get("error"):
            val_error = f"{v['error']}: {v['message']}"
        else:
            val = v
    # 成本栈锚在**引擎的点估值**上(而不是某个挂牌价):没有成交价时,这是唯一诚实的锚。
    # 只算买入侧 + SSD 窗口后的盈亏平衡。逐年 SSD 时钟表已删(用户裁定,2026-07-18):
    # landed 是自住/数十年持有资产,没人规划 4 年内退出 —— 枚举 16/12/8/4% 对任何真实
    # 决策都没有输入。有决策含量的只有「4 年 = 硬性最短持有期」和「窗口后盈亏平衡」。
    cost = None
    if val:
        p = val["fair_value"]["price"]
        cost = {"entry": costs_mod.entry_costs(p, profile, count),
                "be_after": costs_mod.breakeven_gain_pct(p, profile, count, 5)}
    # F20(2026-07-23 评审):URA 快照的重复 caveat(同月+同面积+同价,双批次入库)让 97 King's
    # 的可比表 6 行实为 3 笔×2、近窗 n=4 实为 2 —— 观测层一律按 (月,面积,价) 去重;引擎的 n
    # 保持原样(conformal 在未去重的库上校准),但表侧必须注明。
    n_raw = len(street_rows)
    seen_k, dedup = set(), []
    for t in street_rows:
        k = (t.get("contract_ym"), t.get("area_sqft"), t.get("price"))
        if k in seen_k:
            continue
        seen_k.add(k)
        dedup.append(t)
    street_rows = dedup
    street_total = len(street_rows)          # 分母统一用去重口径(F20 —— 16/32 不是 16/38)
    # F21(2026-07-23 评审):观测窗(近窗/年度趋势/A&A 队列)此前混着地契制度 —— 97 King's 的
    # 近窗把 102 年地契段的 $1,788 和 FH 排屋的 $3,147 摆在一行,还接「多口径彼此接近」的模板句。
    # 有 subject tenure 时,观测窗只读同制度(准永久 vs 真租赁)的行。
    def _quasi(tt): return tt in ("freehold", "freehold_equiv")
    subj_tenure = (val or {}).get("subject", {}).get("tenure_type") or tenure
    if subj_tenure:
        rows_subject = [t for t in street_rows
                        if _quasi(t.get("tenure_type")) == _quasi(subj_tenure)]
    else:
        rows_subject = street_rows
    # F17(2026-07-21 评审,F21 收紧):裸的 "freehold" 读起来像已核实的事实 —— 它是输入/推断。
    # 只有**准永久与真租赁混桶**才警告(FH 与 999y 同为准永久,视同一桶 —— 此前把它们也报成
    # 混合,和风险区「可视同一桶」自相矛盾)。
    tenure_mix = None
    if street_rows:
        q = sum(1 for t in street_rows if _quasi(t.get("tenure_type")))
        l = len(street_rows) - q
        if q and l:
            tenure_mix = f"准永久(FH/999y){q} / 真租赁 {l}"
    return {"address": address, "dd": d, "resolve": res, "land_area": land_area,
            "area_src": area_src, "val": val, "val_error": val_error, "ptype": ptype,
            "cost": cost, "profile": profile, "count": count, "digest": digest,
            "street_total": street_total, "street_rows": street_rows,
            "street_rows_subject": rows_subject, "street_dups": n_raw - len(street_rows),
            "tenure_mix": tenure_mix}


# --------------------------------------------------------------------------- 渲染
def _l0(g: dict) -> str:
    """结论层:一眼看完。"""
    v, d = g["val"], g["dd"]
    geo = d["geocode"]
    if v:
        fv = v["fair_value"]
        head = (f"<div class=big>{_money(fv['price'])}</div>"
                f"<div class=sub>{fv['land_psf']:,.0f} / sqft land · 区间 "
                f"{_money(fv['low'])} – {_money(fv['high'])} · 置信度 {fv['confidence']}/100</div>")
    else:
        head = (f"<div class=big>无法估值</div>"
                f"<div class=sub>{_esc((g['val_error'] or '')[:160])}</div>")
    z = d.get("zoning") or {}
    lh = d.get("landed_housing_area") or {}
    f = d.get("flood") or {}
    sch = d.get("schools_primary") or []
    # 层数管制属于首屏:它是「能不能加盖」的第一入口(2026-07-21 评审 —— 此前 envelope
    # 在整份报告里被静默丢弃)。GCBA 身份同理,它改写整个买家池。
    lh_chip = lh.get("type") or "不在范围内"
    if lh.get("envelope"):
        lh_chip += f" · {_envelope_zh(lh.get('envelope'))}"
    if (lh.get("classification") or "").upper().startswith("GOOD CLASS"):
        lh_chip = "GCBA · " + lh_chip
    chips = [
        ("地块", f"{g['land_area']:,.0f} sqft" if g["land_area"] else "未知"),
        ("分区", z.get("zone") or "—"),
        ("landed housing area", lh_chip),
        # 学区是量到的 landed 最大价值驱动 —— 它属于首屏,不属于第 2 节
        ("最近小学", f"{sch[0]['name']} · {sch[0]['km']}km" if sch else "2.2km 内无"),
        ("PUB 水浸名单", "在名单上" if f.get("on_list") else "不在名单上"),
    ]
    chip_html = "".join(f"<div class=chip><b>{_esc(a)}</b><span>{_esc(b)}</span></div>"
                        for a, b in chips)
    # F5:结论先行。人写的 verdict 是这份报告真正的「结论」,不能埋在第 4 节 ——
    # L0 放一句话版本,第 4 节保留全文与 archetype。
    vd = ((g.get("digest") or {}).get("verdict")) or {}
    if vd.get("call_zh") or vd.get("call"):
        verdict_strip = (f"<div class='banner ok'><b>结论(人写)</b> —— "
                         f"{vd.get('call_zh') or vd.get('call')} "
                         f"<span class=note>依据与 archetype 详见「深度尽调」节</span></div>")
    else:
        # F11(2026-07-21 评审):无判断层时,「不给 go/no-go」的声明此前埋在第 5 节,
        # 而买卖指导表在它之前就已经读起来像建议 —— 声明必须先于指导出现。
        verdict_strip = ("<p class=note><b>本报告不含人写判断层(go/no-go)</b> —— 以下为工具"
                         "产出的事实、估值、成本与必查项;结论需要实地与持有意图,完整说明见"
                         "「深度尽调」节。</p>")
    # A/B 回移:主要风险按「对价格路径的影响」排序,跟在结论后 —— 判断层人写,
    # 与 DD 的「谁能定/何时定」分层互补:那边回答怎么核,这边回答什么最可能改变价格。
    risks = ((g.get("digest") or {}).get("price_path_risks")) or []
    risk_html = ""
    if risks:
        items = ""
        for r in risks:
            t = r.get("title_zh") or r.get("title") or ""
            b = r.get("body_zh") or r.get("body") or ""
            items += (f"<li><b>{t}</b>"
                      + (f"<details><summary class=note>展开</summary>"
                         f"<div class=note>{b}</div></details>" if b else "") + "</li>")
        risk_html = (f"<div class=card><h3>主要风险 <span class=note>(按对价格路径的影响排序 · "
                     f"判断层,人写)</span></h3><ol class=alerts>{items}</ol></div>")
    return f"""<div class=hero>{head}</div>
<p class=addr>{_esc(g['address'])} · S({_esc(geo['postal'])}) · 估值基准日 {_esc(d['as_of'])}</p>
{verdict_strip}
{risk_html}
<div class=chips>{chip_html}</div>"""


def _street_banner(g: dict) -> str:
    r = g["resolve"]
    if r["basis"] == "direct":
        return ""
    cls = "warn" if r["ura_street"] else "stop"
    lead = (f"可比来自 URA 的 <b>{_esc(r['ura_street'])}</b>,不是 "
            f"<b>{_esc(g['dd']['street'])}</b>" if r["ura_street"] else "URA 街道无法解析")
    return (f"<div class='banner {cls}'><b>街道口径提示</b> —— {lead}。URA 的 landed 街道是"
            f"<b>发展项目登记的街道</b>,不是房子所在的路(EXP-0018)。<span class=note>"
            f"{r.get('evidence_zh') or _esc(r['evidence'])}</span></div>")


def _l1_valuation(g: dict) -> str:
    v = g["val"]
    if not v:
        return (f"<div class=card><h2>1 · 估值 Valuation</h2>"
                f"<div class='banner stop'>{_esc(g['val_error'])}</div></div>")
    fv, s = v["fair_value"], v["subject"]
    bg, sg = v["buyer_guidance"], v["seller_guidance"]
    ref = v.get("recent_street_reference")
    alias = g["resolve"]["basis"] == "alias"
    if sg.get("ask") is None or alias:
        # F16(2026-07-21 评审):抑制横幅只说了「为什么不给」,没给读者一条能走的路 ——
        # 10 Namly 的读者拿着一个指示性点估值,不知道下一步是什么。给三步,命令折叠。
        guide = (f"<div class='banner warn'><b>买卖指导已抑制</b> —— "
                 f"{_suppress_reason_zh(v, g['land_area'] or 0, g['resolve']['basis'])}。"
                 f"<span class=note>门槛只能来自<b>观测到的成交</b>;此时只剩引擎自己的误差棒,"
                 f"拿它当议价线是把「无知」包装成「进取」。下一步:"
                 f"① INLIS 拿法定面积与地契(约 S$16,当天出);"
                 f"② 现场/图则确定 condition 与现有 GFA;"
                 f"③ 用 Investment Suite 拉本街同型分布与本报告并读,再决定出价锚。</span></div>"
                 + (f"<p class=note>参考:引擎按 URA「{_esc(g['resolve']['ura_street'])}」桶算出的"
                    f"门槛是 {_money(bg['attractive_below'])} / {_money(bg['walk_away_above'])}"
                    f" —— <b>不要直接用</b>:桶内混着同屋苑其它路。"
                    f"<details><summary class=note>内部操作命令(第 ③ 步)</summary>"
                    f"先拉本路(<code>{_esc(g['dd']['street'])}</code>)自己的分布:"
                    f"<code>research/lib/harvest_street_sale.py</code>(设备上收获)→ "
                    f"<code>research/tools/is_street_compare.py --road</code></details></p>"
                    if alias and bg.get("attractive_below") else ""))
    else:
        guide = f"""<table class=kv>
<tr><th colspan=2>买家 Buyer</th></tr>
<tr><td>积极买入(低于)<span class=note> 便宜端 p25</span></td>
    <td class=r>{_money(bg['attractive_below'])}</td></tr>
<tr><td>放弃(高于)<span class=note> 贵端 p75</span></td>
    <td class=r>{_money(bg['walk_away_above'])}</td></tr>
<tr><th colspan=2>卖家 Seller</th></tr>
<tr><td>挂牌 ask</td><td class=r>{_money(sg['ask'])}</td></tr>
<tr><td>预期成交 <span class=note>= 公允价</span></td><td class=r>{_money(sg['expected_clear'])}</td></tr>
<tr><td>急售</td><td class=r>{_money(sg['quick_sale'])}</td></tr>
</table>
<p class=note>门槛 = {fv['n_street_comps']} 笔 lease-matched 同街成交、按时间+尺寸调整到本宗地后的
<b>p25/p75</b> —— 也就是「可比的地块<b>实际</b>成交出来的」便宜端/贵端,<b>不是</b>引擎的误差棒。
实测(EXP-0013/0017):约 <b>73-83%</b> 的真实成交落在 p25 之上、约 <b>32-38%</b> 落在 p75 之上,
且该比例<b>随 regime 漂移</b> —— 这是<b>证据标记</b>,不是校准过的概率。</p>"""
        # F2a:引擎的 seller note 自带「最新可比高于点」的内联提示,第一版中文层把它渲染丢了 ——
        # ask 4.83M 与「上月同尺寸孪生房成交 5.22M」隔了两屏。凡与表格同屏才有效的警示,必须内联。
        area_sf = v["subject"]["land_area_sqft"]
        if ref and v.get("directional_flag"):
            fresh_price = ref["adj_psf"] * area_sf
            if sg.get("ask") and fresh_price > sg["ask"]:
                guide += (f"<p class=note>⚠ <b>与上表并读:</b>最新同尺寸成交"
                          f"({ref['contract_ym']},调整后 {ref['adj_psf']:,.0f} psf ≈ "
                          f"{_money(fresh_price)})比表中 ask <b>高 "
                          f"{(fresh_price/sg['ask']-1)*100:.0f}%</b> —— 60 个月分位数在正在"
                          f"加速的街道上偏保守(这正是实测里 32-38% 成交高于 p75 的来源)。"
                          f"卖方定价可参考近窗成交;买方勿把上表当上限读。</p>")
            elif bg.get("attractive_below") and fresh_price < bg["attractive_below"]:
                guide += (f"<p class=note>⚠ <b>与上表并读:</b>最新同尺寸成交"
                          f"({_money(fresh_price)})已低于「积极买入」线 —— 街道可能转弱,"
                          f"勿把门槛当下限读。</p>")
        # F2b:近 12 个月窗口的补充标记(引擎 additive 输出;同过滤、同调整,纯观测)
        gr = v.get("guidance_recent_12mo")
        if gr:
            guide += (f"<p class=note><b>近 12 个月窗(n={gr['n']}):</b>"
                      f"p25 {_money(gr['p25'])} · p75 {_money(gr['p75'])} —— "
                      f"热市中比 60 个月窗更贴近当前水平;样本更薄,只作参照,不替代主门槛。</p>")
        # A/B 回移:出价指引叙事行 —— 裸的 p25/p75 拦不住「为单笔背书」这种错误;
        # 把「超过门槛需要什么」和「最高单笔是谁」写成一句话,和表同屏。
        # F8(2026-07-21 评审):证据层可比表只是引擎**权重前 8 笔**,不是整个桶 —— 第一版把
        # 表内最高说成「桶内最高」,而 119 Namly 队列里真正的天花板(2025-07 $4,150 psf /
        # S$13.1M)根本不在表里。措辞收敛为「表内」,队列的原始极值由 A&A 节呈现。
        max_c = max(v["comps"], key=lambda c: c["adj_land_psf"]) if v.get("comps") else None
        if max_c and sg.get("ask"):
            top_price = max_c["adj_land_psf"] * area_sf
            # F22:队列极值的指引只在 A&A 节真的渲染了极值段时才给(此前是悬空引用)
            aa_ev = _aa_evidence(g)
            tail = ("标的队列的原始极值见「A&amp;A/重建潜力」节。"
                    if aa_ev and aa_ev["kind"] == "spread" else
                    "标的队列近窗无可读的状态价差(见「A&amp;A/重建潜力」节)。")
            guide += (f"<p class=note><b>读法:</b>超过 p75({_money(bg['walk_away_above'])})的出价"
                      f"需要<b>可验证的理由</b>(高标准装修、已批准加建、边间/几何优势 —— 现场核实,"
                      f"不是听中介说);高于 {_money(top_price)} 即是在为<b>可比表内</b>最高单笔"
                      f"({max_c['adj_land_psf']:,.0f} adj psf,{_esc(max_c['contract_ym'])})背书 "
                      f"—— 表仅为权重前 {len(v['comps'])} 笔,{tail}</p>")
    flag = ""
    # 别名桶里的「最新同街成交」可能根本不在本路上 —— 实测:19 Cardiff Grove 的这条提示由一笔
    # 2,301sf @ $2,816psf 的成交驱动,调整后 3,175 psf,**高过 Cardiff Grove 自己的历史最高价
    # (2,847)**,而它并不在 Cardiff Grove 上。所以别名情况下不给方向性结论,只陈述事实。
    alias_ref = ("<span class=note>⚠ 该成交可能<b>不在本路上</b>(URA 桶混路),"
                 "不要据此判断方向 —— 见街道口径提示。</span>" if alias else "")
    if v.get("directional_flag") and ref and alias:
        flag = (f"<div class='banner warn'><b>方向性提示已弃用</b> —— 桶内最新成交调整后为 "
                f"{ref['adj_psf']:,.0f} land-psf({ref['contract_ym']}),与点估值差 "
                f"{abs(fv['land_psf']/ref['adj_psf']-1)*100:.0f}%,但它{alias_ref}</div>")
    elif v.get("directional_flag") and ref:
        gap = fv["land_psf"] / ref["adj_psf"] - 1
        if gap > 0:
            flag = (f"<div class='banner warn'><b>方向性提示</b> —— 点估值比<b>最新的可比成交</b>"
                    f"高 {gap*100:.0f}%({ref['adj_psf']:,.0f} land-psf 调整后,"
                    f"{ref['contract_ym']}):可比可能已<b>过时</b>,出价前先佐证。</div>")
        else:
            flag = (f"<div class='banner warn'><b>方向性提示</b> —— <b>最新的可比成交</b>比点估值"
                    f"高 {-gap*100:.0f}%({ref['adj_psf']:,.0f} land-psf 调整后,"
                    f"{ref['contract_ym']}):在加速的市场里把这个点当<b>地板</b>读(见 regime 偏差)。"
                    f"</div>")
    # A/B 回移:单笔 vs 近簇。「最新 = 最可信」只有在它与其前的成交簇一致时才成立;
    # 偏离近簇中位 >5% 的最新单笔是上/下尾,不做锚(实测:2026-06 尾数 888 的一笔比
    # 5 月三印簇高 8.7%,把它当「最可信」会系统性带高读数)。regime 地板提示保持不变。
    ref_html = ""
    if ref:
        fc = _fresh_vs_cluster(v["comps"], ref)
        if fc and abs(fc["gap"]) > 0.05:
            side = "上尾" if fc["gap"] > 0 else "下尾"
            ref_html = (f"<p class=note>最新可比成交:<b>{ref['adj_psf']:,.0f}</b> land-psf"
                        f"(已按时间+尺寸调整到本宗地,{ref['contract_ym']})—— "
                        f"比其前 {fc['n_cluster']} 笔簇的中位 {fc['cluster_med']:,.0f} "
                        f"{'高' if fc['gap'] > 0 else '低'} {abs(fc['gap'])*100:.0f}%,属<b>{side}单笔,"
                        f"不做锚</b>;<b>近簇(n={fc['n_cluster']},adj psf {fc['cluster_med']:,.0f})"
                        f"才是最可信读数</b>。单笔保留为区间{'上' if fc['gap'] > 0 else '下'}界的证据。</p>")
        else:
            ref_html = (f"<p class=note>最新可比成交:<b>{ref['adj_psf']:,.0f}</b> land-psf(已按时间+尺寸"
                        f"调整到本宗地,{ref['contract_ym']},原成交 {ref['area_sqft']:,.0f} sqft)"
                        + (f" —— 与其前 {fc['n_cluster']} 笔簇一致(偏离 {abs(fc['gap'])*100:.0f}%),"
                           f"可作当前水平读数" if fc else " —— 单条最可信的证据点") + "</p>")
    return f"""<div class=card><h2>1 · 估值 Valuation <span class=note>(引擎 LV1)</span></h2>
{flag}
<table class=kv>
<tr><td>公允价 fair value</td><td class=r><b>{_money(fv['price'])}</b></td></tr>
<tr><td>land psf</td><td class=r>{fv['land_psf']:,.0f}</td></tr>
<tr><td>公允价区间 <span class=note>(引擎预测误差,非议价区间)</span></td>
    <td class=r>{_money(fv['low'])} – {_money(fv['high'])}</td></tr>
<tr><td>置信度</td><td class=r>{fv['confidence']}/100</td></tr>
<tr><td>同街可比数 <span class=note>(URA {_esc(g['resolve']['ura_street'])})</span></td>
    <td class=r>{fv['n_street_comps']}{(f" <span class=note>(桶内 5 年全量 {g['street_total']} 笔;"
    f"n 为 60 个月窗 + lease-match + 同房型过滤后)</span>")
    if g.get('street_total', 0) > fv['n_street_comps'] else ''}</td></tr>
<tr><td>地契 tenure</td><td class=r>{_esc(s['tenure_type'])}
    {('· 剩余 %d 年' % s['remaining_lease_years']) if s.get('remaining_lease_years') else ''}
    {('<span class=note> ⚠ 街道桶混合地契(' + _esc(g['tenure_mix']) + ')—— 本宗地以 INLIS 为准</span>')
     if g.get('tenure_mix') else ''}</td></tr>
<tr><td>地块面积(估值输入)</td><td class=r>{g['land_area']:,.0f} sqft</td></tr>
<tr><td>面积来源</td><td class=r>{g['area_src'] or '—'}</td></tr>
</table>
<p class=note>注:文中 EXP-XXXX / GY-XXXX 为内部研究注册号 —— 标记该结论的实验出处,详见
「局限与方法」。</p>
{_reads_zh(v)}
{_conf_zh(v)}
{ref_html}
<h3>建筑状况 condition</h3>
<p class=note>{_COND_ZH.get((s.get('condition') or '').lower(), _COND_NONE_ZH)}</p>
<h3>买卖指导 <span class=note>(与公允价分开:读的是已成交的可比分布,不是引擎误差棒)</span></h3>
{guide}
{_recent_windows_zh(g)}
<details><summary class=note>引擎原文 engine's own words(备查,未翻译)</summary>
<p class=note>{_esc(fv['confidence_label'])}</p>
<p class=note>{_esc(v['condition_note'])}</p>
<p class=note>{_esc(sg['note'])}</p></details>
</div>"""


def _recent_windows_zh(g: dict) -> str:
    """近窗读数(A/B 回移):近12月 / 近半年 / 最近簇三个口径互证当前市场水平。
    仅 direct 街道渲染 —— 别名桶混路,近窗中位不是本路的读数。RAW psf,与引擎 adj 口径分开标。"""
    v = g["val"]
    if not v or g["resolve"]["basis"] != "direct" or not g.get("street_rows_subject"):
        return ""
    rw = _recent_windows(g["street_rows_subject"], v["subject"]["land_area_sqft"])
    if not rw or not rw["med12_psf"]:
        return ""
    cl = "、".join(f"{ym} ${psf:,.0f}" for ym, psf in rw["cluster"])
    drift = (f";隐含月漂移约 <b>{rw['drift_mo']*100:+.1f}%/月</b>(近6月中位 vs 前6月中位)"
             if rw["drift_mo"] is not None else "")
    cum = (f"自 {rw['cum_from_year']} 年队列中位累计重估 <b>{rw['cum_pct']*100:+.0f}%</b>{drift}。"
           if rw["cum_pct"] is not None else "")
    six = (f"近半年(n={rw['n6']})中位 <b>${rw['med6_psf']:,.0f}</b>;"
           if rw["med6_psf"] and rw["n6"] >= 3 else "")
    return (f"<h3>近窗读数 <span class=note>(标的队列 ±6% · 同地契制度 · 已去重 —— 原始 psf "
            f"未调整,观测,非引擎口径;数据端 {_esc(rw['last_ym'])})</span></h3>"
            f"<p class=note>近 12 个月(n={rw['n12']})中位 <b>${rw['med12_psf']:,.0f}</b> psf · "
            f"价格中位 {_money(rw['med12_price'])};{six}"
            f"最近 3 笔:{cl}。多口径彼此接近 = 当前水平可信;彼此背离 = 市场在动,读趋势表。"
            f"{cum}</p>")


def _l1_dd(g: dict) -> str:
    d = g["dd"]
    z, lh, p, f = (d.get("zoning") or {}), (d.get("landed_housing_area") or {}), \
                  (d.get("plot") or {}), (d.get("flood") or {})
    sch = d.get("schools_primary") or []
    mrt = d.get("mrt") or []
    scope = d.get("amenity_scope") or {}
    am = d.get("amenity_meta") or {}
    # 「2.2km 内无小学」只有在清单是**全岛**时才是关于新加坡的陈述;此前它是关于
    # dd.py 里那 15 所硬编码学校的陈述,而报告把它当成前者印了出来。
    near = [f"{n['name']} · {n['km']}km" for n in sch[:3]] or [
        "2.2km 内无" if scope.get("schools_primary") else "清单未覆盖本区域"]
    # A/B 回移:MRT 与 LRT 分行 —— 混在一行时,1.35km 的 LRT 会被读成「最近 MRT」,
    # 而「无步行可达重轨」这个结论只有分开标注才能被读者正确得出。
    heavy, lrt = _split_stations(mrt)
    mrt_txt = (f"{heavy[0]['name']} · {heavy[0]['km']}km" if heavy else
               ("4km 内无" if scope.get("mrt") else "清单未覆盖本区域"))
    # F9(2026-07-21 评审):mrt 列表在 dd 链里截断为最近 4 站(4km 半径)。四席都被 MRT 占满时,
    # 「LRT:4km 内无」是数据支撑不了的全称否定(159 Chun Tin 的 4km 内其实有武吉班让 LRT)。
    # 只陈述数据真正覆盖的范围。
    lrt_txt = (f"{lrt[0]['name']} · {lrt[0]['km']}km" if lrt else
               (f"最近 {len(mrt)} 站均为 MRT(清单截断于最近 {len(mrt)} 站 —— 更远的 LRT 未列)"
                if len(mrt) >= 4 else "4km 内无"))
    gpr = str(z.get("gpr") or "—")
    gpr_txt = "LND(有地住宅,无数值容积率)" if gpr.upper() == "LND" else gpr
    scope_zh = (f"清单口径:小学与 MRT/LRT 为<b>全岛官方清单</b>({am['n_schools']} 所招收 P1 "
                f"的 MOE 学校 · {am['n_mrt']} 个车站;构建于 {am['built']})"
                if am else "清单口径:未声明")
    # F10(2026-07-21 评审):商场/高速是人工东北片区短清单 —— Bukit Timah 的报告里它常是空的,
    # 但注脚仍宣称在报「这几个里最近的」,指向根本没渲染的数据。有数据才渲染,有渲染才注脚。
    exps = d.get("expressways") or []
    exp_row = (f"<tr><td>最近高速 <span class=note>(人工短清单,非全岛)</span></td>"
               f"<td class=r>{_esc(exps[0]['name'])} · {exps[0]['km']}km</td></tr>" if exps else "")
    mall_note = (";<b>商场/高速为人工短清单</b> —— 报的是「这几个里最近的」,不是「全新加坡最近的」"
                 if (d.get("amenities") or exps) else "")
    flood_zh = (("<b>在 PUB 易涝名单上</b>"
                 + (f"(匹配:{_esc(f.get('matches'))})" if f.get("matches") else "")
                 + " —— 强信号,列入 DD-3 重点核查。")
                if f.get("on_list") else
                ("不在名单上 —— 但对<b>单一地块</b>这几乎没有证据力:名单按<b>地名</b>匹配,"
                 "仅覆盖全国约 73,000 公顷中的 23.3 公顷(<b>0.032%</b>)、36 个命名地点;"
                 "几乎所有地址都「不在其上」,包括确实积水的。本址是否积水属实地问题(DD-3)。"))
    return f"""<div class=card><h2>2 · 尽调 Due Diligence <span class=note>(免费官方源:OneMap ·
MP2025 · PUB)</span></h2>
<table class=kv>
<tr><td>MP2025 分区 zone</td><td class=r>{_esc(z.get('zone'))} · 容积率 {_esc(gpr_txt)}</td></tr>
<tr><td>宗地面积 <span class=note>(指示性,非地籍)</span></td>
    <td class=r>{(f"{p['area_sqft']:,.0f} sqft" if p.get('area_sqft') else '—')}</td></tr>
<tr><td>landed housing area</td><td class=r>{_esc(lh.get('type'))}
    {('· <b>' + _esc(_envelope_zh(lh.get('envelope'))) + '</b>') if lh.get('envelope') else ''}
    {('· ' + _esc(lh.get('classification')) + (' — ' + _esc(lh.get('name')) if lh.get('name') else ''))
     if (lh.get('classification') or '').upper().startswith('GOOD CLASS') else ''}</td></tr>
<tr><td>PUB 水浸名单</td><td class=r>{'<b>在名单上</b>' if f.get('on_list') else '不在名单上'}</td></tr>
<tr><td>最近小学 <span class=note>(1km 官方口径以 OneMap SchoolQuery 为准)</span></td>
    <td class=r>{_esc(' / '.join(near))}</td></tr>
<tr><td>最近 MRT <span class=note>(重轨)</span></td><td class=r>{_esc(mrt_txt)}</td></tr>
<tr><td>最近 LRT</td><td class=r>{_esc(lrt_txt)}</td></tr>
{exp_row}
</table>
<p class=note>{scope_zh}{mall_note}</p>
<p class=note>水浸:{flood_zh}</p>
</div>"""


def _l1_costs(g: dict) -> str:
    """成本栈 —— 买入侧现金成本 + 最短持有期约束。

    逐年 SSD 时钟表已删(用户裁定,2026-07-18):landed 按自住/数十年持有读,没人规划
    4 年内退出 —— 按年枚举 16/12/8/4% 对任何真实决策都没有输入,是税务算术当占位。
    有决策含量的只有两句:4 年是硬性最短持有期;窗口后退出的盈亏平衡涨幅是多少。
    随之删掉的还有「1 年内退出盈亏平衡 28%」和「SSD 与买入成本孰大」的叙述 —— 都是
    只有在「打算短炒」这个对 landed 不存在的前提下才有意义的数字。"""
    c = g["cost"]
    if not c:
        return ""
    e, cm = c["entry"], costs_mod
    prof = costs_mod.PROFILES.get(g["profile"], g["profile"])
    return f"""<div class=card><h2>4 · 成本栈 Cost stack <span class=note>(按引擎点估值
{_money(e['price'])} 计;税率会变 —— 出价前以 IRAS 为准)</span></h2>
<table class=kv>
<tr><td>买家画像</td><td class=r>{_esc(prof)} · 第 {g['count']} 套</td></tr>
<tr><td>BSD <span class=note>(1-6% 累进,{_esc(cm.BSD_META['effective'])} 起)</span></td>
    <td class=r>{_money(e['bsd'])}</td></tr>
<tr><td>ABSD <span class=note>({e['absd_rate']*100:.0f}%,{_esc(cm.ABSD_META['effective'])} 起)</span></td>
    <td class=r>{_money(e['absd'])}</td></tr>
<tr><td>律师费(估)</td><td class=r>{_money(e['legal'])}</td></tr>
<tr><td><b>买入总成本</b></td>
    <td class=r><b>{_money(e['total'])}</b> <span class=note>= 房价的 {e['total_pct']*100:.1f}%</span></td></tr>
</table>
<p class=note><b>最短持有期(SSD,{_esc(cm.SSD_META['effective'])} 起购入):</b>4 年内退出按
<b>卖出价</b>征 16/12/8/4%(起算 = 行使 OTP 之日)—— 对 landed 这不是一张时间表,而是一条
<b>硬约束:4 年内不存在合理退出</b>。4 年后退出的盈亏平衡涨幅约 <b>{c['be_after']*100:.0f}%</b>
(覆盖 BSD/ABSD + 2% 中介;未计利息与持有成本)—— 这也是 landed 的 alpha 主要在
<b>买入那一刻</b>决定的算术原因。</p>
<p class=note>不含:中介佣金(landed 通常卖方付)、贷款利息、装修、房产税与持有成本。
ABSD 的夫妻联名 remission、FTA 国民豁免等情形本表未计。
来源:{_esc(cm.ABSD_META['source'])};{_esc(cm.SSD_META['source'])}。
{_esc(cm.ABSD_META['note'])}</p>
</div>"""


def _l1_alerts(g: dict) -> str:
    """深度尽调提示 —— DD-3:专业/实地/需卖方授权,与 OTP 挂钩。自动推导与人写合并渲染。"""
    rows = ""
    for a in _merged_alerts(g):
        tag = "<span class=gate>需卖方授权</span>" if a["gated"] else ""
        src = {"tool": "<span class=src>工具推导</span>",
               "authored": "<span class=src>人写</span>",
               "superseded": "<span class='src sup'>已取代</span>"}[a["src"]]
        title = f"<s>{a['title']}</s>" if a["sup"] else a["title"]
        sup = f"<div class=note><b>已被本报告取代:</b>{a['sup']}</div>" if a["sup"] else ""
        meta = f"<div class=note>{a['meta']}</div>" if a["meta"] else ""
        rows += f"<li><b>{title}</b> {tag}{src}{sup}<div class=note>{a['why']}</div>{meta}</li>"
    dig = g.get("digest") or {}
    verdict = ""
    if dig.get("verdict"):
        vd = dig["verdict"]
        # 判断层是**作者手写的 HTML**(highlights 里就带 <b>)。对它 _esc() 会把 <b> 当成
        # 字面文本印给读者 —— 实测在 14 Seletar Green Walk 的报告里就是这样。它是本仓库里的
        # 受信任文件、由人撰写,和引擎返回的字符串不同,按 HTML 渲染。
        arche = ""
        if dig.get("archetype_zh") or dig.get("archetype"):
            note = dig.get("archetype_note_zh") or dig.get("archetype_note") or ""
            arche = (f"<p class=note><b>archetype:</b> "
                     f"{dig.get('archetype_zh') or dig.get('archetype')}"
                     f"{'　' + note if note else ''}</p>")
        # 不截断:这是作者写下的结论,截一半比不显示更糟
        detail = vd.get("detail_zh") or vd.get("detail") or ""
        verdict = (f"<div class='banner ok'><b>结论 verdict</b> —— "
                   f"{vd.get('call_zh') or vd.get('call')}"
                   f"{'<span class=note>' + detail + '</span>' if detail else ''}</div>"
                   f"{arche}"
                   f"<p class=note>以上来自<b>已撰写的判断层</b>(<code>--digest</code>),"
                   f"不是工具产出 —— 它是人的判断,请按人的判断来核。</p>")
    else:
        verdict = ("<div class='banner warn'><b>本报告不给 go/no-go</b> —— "
                   "买/不买是<b>判断</b>,不是这条链条的产物。它需要 archetype(这条街这个年代的"
                   "房子该怎么看)、实地、以及你的持有意图。工具给的是事实、估值、成本与必查项;"
                   "结论请在做完下面这些之后自己下(已撰写的判断层可由内部流程挂载)。"
                   "</div>")
    return f"""<div class=card><h2>5 · 深度尽调 DD-3 <span class=note>(专业/实地/需卖方授权,
与 OTP 挂钩)</span></h2>
{verdict}
<ul class=alerts>{rows}</ul>
<p class=note>层级说明:<b>DD-1</b> 本人桌面、免费、每个候选都做(本报告的事实层);
<b>DD-2</b> 本人桌面、约 S$5-200、出价前完成(INLIS 产权);
<b>DD-3</b> 上面这些 —— 专业/实地/需卖方授权。三层分的是<b>「谁能定、何时定」</b>,
不是「免费还是收费」。</p>
</div>"""


_HL_ZH = re.compile(r"<span class=['\"]zh['\"]>(.*?)</span>\s*$", re.S)


def _l1_highlights(g: dict) -> str:
    """判断层的 highlights —— 挂载了就渲染,不丢弃。

    作者写的是**双语**:英文正文 + 末尾一个 `<span class='zh'>` 中文(第一版复审只看了
    截断文本,误判成纯英文)。本报告主体是中文,所以把 zh 段解析出来当正文,英文原文
    折叠备查;没有 zh 段的条目按英文照登并标注。"""
    hl = (g.get("digest") or {}).get("highlights") or []
    zh_items, en_items = "", ""
    for h in hl:
        t = (h.get("text_zh") or h.get("text") or "") if isinstance(h, dict) else str(h)
        if not t:
            continue
        m = _HL_ZH.search(t)
        if m:
            zh_items += f"<li>{m.group(1).strip()}</li>"
            en_items += f"<li>{t[:m.start()].strip()}</li>"
        else:
            zh_items += f"<li>{t}<span class=note>(原文,英文)</span></li>"
    if not zh_items:
        return ""
    fold = (f"<details><summary class=note>英文原文 original wording</summary>"
            f"<ul class=alerts>{en_items}</ul></details>" if en_items else "")
    return (f"<details><summary>要点 highlights · {len(hl)} 条 <span class=note>"
            f"(判断层,人写 —— 非工具产出)</span></summary>"
            f"<div class=card><ul class=alerts>{zh_items}</ul>{fold}</div></details>")


def _l2_evidence(g: dict) -> str:
    v, d = g["val"], g["dd"]
    comps = ""
    if v:
        # F13(2026-07-21 评审):表按引擎权重序渲染,读者当成「乱序」;且表只有权重前 8 笔,
        # n 声称 37 —— 不解释就是自相矛盾。显示按月份倒序,截断写明。
        # F20(2026-07-23 评审):URA 双批次重复 caveat 让 97 King's 的表 6 行实为 3 笔×2 ——
        # 显示层去重并标 ×2;引擎的 n 保持原口径,注里说清。
        comp_groups: dict = {}
        for c in v["comps"]:
            k = (c["contract_ym"], c["land_area_sqft"], c["price"])
            comp_groups.setdefault(k, {**c, "_dup": 0})["_dup"] += 1
        comp_rows = sorted(comp_groups.values(), key=lambda c: c["contract_ym"], reverse=True)
        rows = "".join(
            f"<tr><td>{_esc(c['contract_ym'])}{' ×' + str(c['_dup']) if c['_dup'] > 1 else ''}</td>"
            f"<td class=r>{c['land_area_sqft']:,.0f}</td>"
            f"<td class=r>{c['land_psf']:,.0f}</td><td class=r><b>{c['adj_land_psf']:,.0f}</b></td>"
            f"<td class=r>{_money(c['price'])}</td><td>{_esc(c['tenure'])}</td></tr>"
            for c in comp_rows)
        n_all = v["fair_value"]["n_street_comps"]
        dup_note = ("×N = URA 同月同面积同价的重复 caveat(双批次入库),按一笔读 —— "
                    "引擎 n 含重复;" if any(c["_dup"] > 1 for c in comp_rows) else "")
        trunc = (f"表为引擎<b>权重前 {len(v['comps'])} 笔</b>(参与计算共 {n_all} 笔);"
                 if n_all > len(v["comps"]) else "") + dup_note
        reads = "".join(f"<tr><td>{_esc(k)}</td><td class=r>{('%.0f' % x) if x else '—'}</td></tr>"
                        for k, x in v["independent_reads_land_psf"].items())
        comps = f"""<h3>同街可比 <span class=note>(lease-matched;{trunc}按月份倒序显示,
引擎实际加权与表序无关;adj psf = 该成交按时间+尺寸调整到本宗地后的值 ——
点估值与指导都活在这一列上)</span></h3>
<table><tr><th>月份</th><th class=r>地块 sqft</th><th class=r>原始 psf</th>
<th class=r>adj psf</th><th class=r>价格</th><th>tenure</th></tr>{rows}</table>
<h3>独立方法读数 <span class=note>(收敛=信号,发散=hard case)</span></h3>
<table><tr><th>method</th><th class=r>land psf</th></tr>{reads}</table>"""
    # A/B 回移:年度趋势表(街道全体 vs 标的队列)。面积效应逼着两列分开;读趋势先读 n。
    trend = ""
    if g.get("street_rows_subject") and g["land_area"] and g["resolve"]["basis"] == "direct":
        yrs = _year_trend(g["street_rows_subject"], g["land_area"])
        if len(yrs) >= 2:
            trows = ""
            for y in yrs:
                med_c = f"{y['med_cohort']:,.0f}" if y["med_cohort"] else "—"
                price_c = _money(y["price_cohort"]) if y["price_cohort"] else "—"
                yoy = (f"{y['yoy']*100:+.1f}%" + (f"(跨 {y['yoy_gap']} 年)" if y.get("yoy_gap") else "")
                       if y["yoy"] is not None else "—")
                trows += (f"<tr><td>{_esc(y['year'])}</td><td class=r>{y['n_street']}</td>"
                          f"<td class=r>{y['med_street']:,.0f}</td><td class=r>{y['n_cohort']}</td>"
                          f"<td class=r>{med_c}</td><td class=r>{price_c}</td>"
                          f"<td class=r>{yoy}</td></tr>")
            trend = f"""<h3>年度趋势 <span class=note>(街道同地契制度全体 vs 标的队列 ±6%,已去重,
RAW psf 中位;读趋势先读 n —— landed 街道年样本个位数,单笔即可扰动中位)</span></h3>
<table><tr><th>年份</th><th class=r>街道 n</th><th class=r>街道 psf 中位</th>
<th class=r>队列 n</th><th class=r>队列 psf 中位</th><th class=r>队列价格中位</th>
<th class=r>队列 YoY</th></tr>{trows}</table>"""
    # F14(2026-07-21 评审):邻地表此前丢掉面积与 GPR —— 而「先读面积再评级」是这条链
    # 自己的规矩。剖面此前截断在 6 段:119 的 PLACE OF WORSHIP 剖面把水体穿越和到达段
    # 都截没了 —— 连续重复段合并计数后全部渲染,到达与否用结构化字段标注。
    nb = "".join(f"<tr><td>{_esc(n['zone'])}</td><td class=r>{n['metres']:.0f} m</td>"
                 f"<td class=r>{n['bearing_deg']:.0f}°</td>"
                 f"<td class=r>{format(n['area_sqm'], ',.0f') + ' sqm' if n.get('area_sqm') else '—'}</td>"
                 f"<td class=r>{_esc(n.get('gpr') or '—')}</td></tr>"
                 for n in (d.get("neighbours") or [])[:8])
    tr = ""
    for t in (d.get("transects") or []):
        zs, comp = [s["zone"] for s in t["steps"]], []
        for z in zs:
            if comp and comp[-1][0] == z:
                comp[-1][1] += 1
            else:
                comp.append([z, 1])
        steps = " → ".join(z + (f"×{k}" if k > 1 else "") for z, k in comp)
        warn = ("　✓ 步进抵达目标地块" if t.get("reaches_target") is True else
                "　⚠ 射线未进入该地块(它瞄准的是共享边界上的最近点)—— 步进只说明中间隔着"
                "什么,不代表已经到达")
        tr += (f"<p class=note><b>朝 {_esc(t['toward'])}</b>({t['edge_m']:.0f}m):{_esc(steps)}"
               f"{warn}</p>")
    return f"""<details><summary>6 · 证据层 —— 可比、趋势、邻地、剖面(展开)</summary>
<div class=card>{comps}
{trend}
<h3>邻近分区 neighbours <span class=note>(先读面积:小地块多为电箱/设施)</span></h3>
<table><tr><th>zone</th><th class=r>距离</th><th class=r>方位</th><th class=r>地块面积</th>
<th class=r>GPR</th></tr>{nb}</table>
{tr}
</div></details>"""


_NOT_COVERED_ZH = {
    "Valuation": "本 DD 链条<b>不做估值</b> —— caveat 价是「地+房」捆绑,不可批量拆解出纯地价。"
                 "估值由上面的引擎 LV1 给出(两条链在本报告里已接上)。",
    "Legal": "<b>法律面</b>:业主、他项权利、法定地块面积、Certified Plan —— 需 INLIS(DD-2,S$16)。",
    "Approved plans": "<b>批准图则 / 违建</b> —— 需 BCA,且<b>受制于卖家</b>(须业主签字授权,买家自己买不到)。",
    "Anything site-observable": "<b>一切现场才能看到的</b>:噪音、积水、采光、车流、实际状况 —— DD-3。",
}


def _l3_limits(g: dict) -> str:
    v, d = g["val"], g["dd"]
    lims = "".join(f"<li>{x}</li>" for x in (_limits_zh(v, g["ptype"]) if v else []))
    verify = "".join(f"<li>{x}</li>" for x in (_verify_zh(v, g) if v else []))
    nc = ""
    for x in (d.get("not_covered") or []):
        zh = next((t for k, t in _NOT_COVERED_ZH.items() if x.startswith(k)), None)
        nc += f"<li>{zh or _esc(x)}</li>"
    # 本报告自己的边界 —— 说清楚没覆盖什么,和覆盖了什么一样重要
    nc += ("<li><b>租金收益 rental yield</b> —— URA 的 caveat 只有<b>成交</b>,没有租约。"
           "Investment Suite 有街道级与 500m 的 rental yield;要它就得去拉(本链条不自动调 IS)。</li>"
           "<li><b>重建经济 rebuild economics</b> —— 拆建成本、GFA 上限的实际可建量、施工期"
           "机会成本,都不在免费官方源里。管制读数与评估框架见「A&amp;A/重建潜力」节,"
           "但「重建划不划算」的实数只能由 QP 可研 + 承包商报价 + 已翻建可比核出来。</li>"
           "<li><b>持有成本</b> —— 贷款利息、房产税(自住 vs 出租税率不同)、维护。"
           "成本栈只算<b>交易</b>侧(BSD/ABSD/SSD)。</li>"
           "<li><b>判断</b> —— archetype、go/no-go、议价策略。工具给事实、估值、成本、必查项;"
           "结论需要实地与你的持有意图(可用 <code>--digest</code> 挂载已撰写的判断层)。</li>")
    # provenance 的英文串按 key 映射为中文(它们描述的是我们自己的固定数据源);
    # 没映射到的 key 保留原文 —— 宁可露出英文,不可静默丢来源。
    prov_zh = {
        "geocode": "OneMap 搜索 API(免费,无需密钥);路名已断言校验",
        "plot/zoning/neighbours": "URA Master Plan 2025(2025-12-01 宪报)Land Use + SDCP "
                                  "Landed 图层,经 data.gov.sg —— 指示性,非法定边界",
        "comps": "URA Data Service caveat(免费注册密钥)。landed 的 area = 土地面积;月粒度;"
                 "滚动约 5 年;caveat 滞后;landed 项目名匿名化 → street 是唯一 join 键,"
                 "且是母路标签(EXP-0018)",
        "flood": "PUB 易涝名单(2025-11)按地名匹配 + data.gov.sg 全国公顷数",
        "schools/mrt": "全岛清单:MOE School Directory(data.gov.sg)+ OneMap 车站枚举,"
                       "预地理编码;直线距离到目标点。P1 官方口径 = OneMap SchoolQuery"
                       "(量到校地边界),本报告的直线是保守高估",
        "amenities/expressways": "人工东北片区短清单 —— 「这几个里最近的」,非全岛",
    }
    prov = "".join(f"<li><b>{_esc(k)}</b> — {prov_zh.get(k) or _esc(val)}</li>"
                   for k, val in (d.get("provenance") or {}).items())
    eng = "".join(f"<li>{_esc(x)}</li>" for x in (v["limitations"] if v else []))
    eng += "".join(f"<li>{_esc(x)}</li>" for x in (v["verify_before_offer"] if v else []))
    return f"""<details open><summary>7 · 局限与方法 —— 下单前必读</summary>
<div class=card>
<p class=note>注:文中 EXP-XXXX / GY-XXXX 为内部研究注册号(research/registry)——
标记该结论出自哪个实验/哪次否定,供追溯,不影响阅读。</p>
<h3>下单前必查 verify before offer</h3><ul>{verify or '<li>—</li>'}</ul>
<h3>估值的局限 —— 这些不是免责声明,是量出来的</h3><ul>{lims or '<li>—</li>'}</ul>
<h3>本链条不覆盖</h3><ul>{nc}</ul>
<h3>数据来源 provenance</h3><ul class=note>{prov}</ul>
<details><summary class=note>引擎原文 engine's own words(备查,未翻译)</summary>
<ul class=note>{eng}</ul></details>
</div></details>"""


_CSS = """body{margin:0;background:#0f1115;color:#e6e6e6;font:15px/1.65 -apple-system,"Segoe UI",
"Microsoft YaHei",Roboto,sans-serif}
.wrap{max-width:940px;margin:0 auto;padding:28px}
h1{font-size:21px;margin:0 0 2px}h2{font-size:17px;margin:0 0 10px}
h3{font-size:14px;margin:16px 0 6px;color:#cfd6e4}
.addr{color:#9aa4b2;margin:6px 0 14px;font-size:13px}
.hero{background:#161a22;border:1px solid #232a36;border-radius:12px;padding:18px 20px}
.big{font-size:30px;font-weight:650;letter-spacing:-.5px}
.sub{color:#9aa4b2;font-size:13px;margin-top:4px}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 18px}
.chip{background:#161a22;border:1px solid #232a36;border-radius:8px;padding:7px 11px;font-size:12px}
.chip b{color:#9aa4b2;font-weight:500;margin-right:6px}
.card{background:#141821;border:1px solid #222a36;border-radius:12px;padding:16px 18px;margin:12px 0}
table{width:100%;border-collapse:collapse;font-size:13px;margin:6px 0}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid #222a36}
th{color:#9aa4b2;font-weight:500}.r{text-align:right}
.kv td:first-child{color:#c3cbd8}
.note{color:#8d97a5;font-size:12px}
.banner{border-radius:8px;padding:10px 12px;margin:8px 0;font-size:13px}
.banner.warn{background:#2a2412;border:1px solid #5c4a1a}
.banner.stop{background:#2a1616;border:1px solid #5c2020}
.banner.ok{background:#14231a;border:1px solid #2c5c3a}
.alerts{list-style:none;padding:0}
.alerts>li{border-left:2px solid #3a4560;padding:2px 0 8px 12px;margin:10px 0;font-size:13px}
.gate{background:#4a2320;border:1px solid #7a3a33;border-radius:4px;padding:1px 6px;
 font-size:11px;margin-left:6px;white-space:nowrap}
.src{background:#1d2634;border:1px solid #33405a;border-radius:4px;padding:1px 6px;
 font-size:11px;margin-left:6px;color:#9fb0cf;white-space:nowrap}
.src.sup{background:#241d2e;border-color:#4a3a5c;color:#b39fcf}
s{opacity:.65}
.banner .note{display:block;margin-top:5px}
details{margin:12px 0}summary{cursor:pointer;color:#cfd6e4;font-size:14px;padding:8px 0}
ul{margin:6px 0;padding-left:18px}li{font-size:13px;margin:3px 0}
@media(max-width:640px){.big{font-size:24px}.wrap{padding:16px}}"""


def render(g: dict) -> str:
    return f"""<!doctype html><html lang="zh-Hans"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(g['address'])} · landed 全面分析</title><style>{_CSS}</style>
<div class=wrap>
<h1>{_esc(g['address'])} · landed 全面分析</h1>
{_l0(g)}
{_street_banner(g)}
{_l1_valuation(g)}
{_l1_dd(g)}
{_aa_block(g)}
{_l1_costs(g)}
{_l1_alerts(g)}
{_l1_highlights(g)}
{_l2_evidence(g)}
{_l3_limits(g)}
<p class=note>估值 = 引擎 LV1(URA walk-forward:中位 APE 9.1%,区间覆盖 78.9%)。
尽调 = OneMap + URA MP2025 + PUB,全部免费官方源。本报告不是持牌估价,也不替代 INLIS/BCA/现场。</p>
</div>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("address", help='例:"19 CARDIFF GROVE"')
    ap.add_argument("--type", default="Terrace",
                    choices=["Terrace", "Semi-detached", "Detached"])
    ap.add_argument("--area", type=float, default=None,
                    help="实测地块面积 sqft(地契/IS)。不给则用 MP2025 宗地(指示性)")
    ap.add_argument("--tenure", default=None, choices=["freehold", "freehold_equiv", "leasehold"])
    ap.add_argument("--lease-start", type=int, default=None)
    ap.add_argument("--condition", default=None, choices=["original", "renovated", "rebuilt"])
    ap.add_argument("--asof", default=None)
    ap.add_argument("--profile", default="SC", choices=sorted(costs_mod.ABSD_RATES),
                    help="买家画像(决定 ABSD)")
    ap.add_argument("--count", type=int, default=1, help="这是买家的第几套住宅")
    ap.add_argument("--digest", default=None,
                    help="判断层 slug(researcher/landed/<slug>_dd.json:archetype/verdict/"
                         "highlights)。不给则报告明说「不给 go/no-go」")
    ap.add_argument("--postal", default=None,
                    help="OneMap 查询用邮编(地址含撇号等只在邮编下命中时用;显示地址不变)")
    a = ap.parse_args()

    digest = None
    if a.digest:
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "researcher", "landed", f"{a.digest}_dd.json")
        with open(p, encoding="utf-8-sig") as f:
            digest = json.load(f)

    g = gather(a.address, a.type, a.area, a.tenure, a.lease_start, a.condition, a.asof,
               profile=a.profile, count=a.count, digest=digest, postal=a.postal)
    slug = "".join(c if c.isalnum() else "_" for c in a.address.lower()).strip("_")
    # F19(2026-07-21 评审):skill 规定 AI-blind 对照臂只准读 <slug>_dd_raw.json,而本入口
    # 此前把 DD 事实留在内存里 —— 标准步骤的输入文件根本不存在,得再跑一遍 dd 链才能补。
    # 与 researcher.landed.dd 的落盘保持同路径同格式;报告可再生,raw 同理。
    raw_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "researcher", "landed", f"{slug}_dd_raw.json")
    with open(raw_p, "w", encoding="utf-8") as f:
        json.dump(g["dd"], f, ensure_ascii=False, indent=1)
    res = write_report(f"{slug}_landed_full_report.html", render(g))
    print(res.summary())
    v = g["val"]
    if v:
        fv = v["fair_value"]
        print(f"   {a.address}: {_money(fv['price'])} ({fv['land_psf']:,.0f} land-psf), "
              f"区间 {_money(fv['low'])}-{_money(fv['high'])}, 置信度 {fv['confidence']}/100, "
              f"可比 n={fv['n_street_comps']} @ {g['resolve']['ura_street']}")
    else:
        print(f"   估值不可用:{(g['val_error'] or '')[:120]}")


if __name__ == "__main__":
    main()
