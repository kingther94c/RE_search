"""地址 -> 一份完整的 landed 分析报告(估值 + 尽调),中文为主,详略分层。

    python deliverables/build_landed_full_report.py "19 CARDIFF GROVE" --type Terrace
    python deliverables/build_landed_full_report.py "385 LOYANG RISE" --area 1645.8

把两条本来分开的链子接成一个入口:
  - `researcher.landed.dd.run(address)`      -> 地理编码、MP2025 地块/分区/邻地、学校/MRT、水浸
  - `researcher.backtest.value_landed`       -> 引擎 LV1 的公允价、区间、可比、买卖指导

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
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deliverables.report_out import write_report                      # noqa: E402
from researcher.backtest.value_landed import LandedSpec, value_landed  # noqa: E402
from researcher.landed import costs as costs_mod                      # noqa: E402
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
    for nb in (d.get("neighbours") or []):
        z, m = (nb.get("zone") or ""), nb.get("metres") or 9e9
        if z in dd_mod.TRANSECT_ZONES and m <= dd_mod.TRANSECT_WITHIN_M:
            out.append((f"{_esc(z)} 用地在 {m:.0f} m {_esc(nb.get('bearing_deg') and str(int(nb['bearing_deg'])) + '°' or '')}",
                        False,
                        f"分区<b>标签</b>不等于地上<b>今天</b>在做什么 —— 标签本身误导过人。"
                        f"要看的是:实际经营内容、作业时段、噪音/气味,以及中间隔着什么。"
                        f"报告里的剖面只说明「隔着什么」,不代表已经到达。属实地问题(DD-3)。"))
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
                    "≥8k sqft 上尺寸曲线 identification 最差(EXP-0011);点估值请走 case protocol。"))
    if g["resolve"]["basis"] == "alias":
        out.append((f"本路({_esc(g['dd']['street'])})自己的成交分布", False,
                    f"URA 把本路的 caveat 归在「{_esc(g['resolve']['ura_street'])}」桶里,桶内混着"
                    f"同屋苑其它路 —— 议价门槛因此在本报告中<b>被抑制</b>。要门槛,得用 "
                    f"Investment Suite 拉本路自己的分布(见 harvest_street_sale.py)。"))
    if v:
        out.append(("建筑状况 condition —— bundle 价里最大的未观测项", False,
                    "引擎是 condition-blind 的。实测(Cardiff Grove,同期同尺寸):原装 "
                    "$1,767-1,946/psf、翻建 $2,327-2,848/psf —— <b>同一条路上价差 60%</b>。"
                    "现场定原装/翻新/翻建与 GFA,否则这份估值的最大不确定性没有被消除。"))
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


def _suppress_reason_zh(v: dict, area: float, basis: str = "direct") -> str:
    """抑制原因用**结构化字段**重建,不解析引擎的英文串。"""
    md, fv = v["method_disagreement"], v["fair_value"]
    if basis == "alias":
        # 报告层自己加的一道闸,引擎没有(引擎不知道街道是别名解析来的)。
        # 实测的理由,不是谨慎的姿态:19 Cardiff Grove 的 URA 桶是 ALNWICK ROAD,桶里
        # p25/p75 给出 S$3.87M / S$5.02M,而 Cardiff Grove 自己的**原装**房成交在
        # $1,767-1,946 psf ≈ S$3.25-3.58M —— 照这个"积极买入 < S$3.87M"买会买贵。
        # 点估值可以留(它是引擎在这个桶上验证过的输出),但**议价门槛不能**:
        # 门槛的全部意义是「可比的地块实际成交出来的分布」,而这个分布混了别的路。
        return ("URA 街道是<b>别名解析</b>来的 —— 门槛所依赖的「同街成交分布」里混着同屋苑"
                "其它路的房子,不是本路的分布")
    if area >= 8000:
        return "地块 ≥8k sqft —— 尺寸曲线在这里identification最差(EXP-0011)"
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
        out.append("<b>同街证据薄或方法分歧</b> —— 下单前先从 Investment Suite 拉这条街的 "
                   "Type Summary 佐证")
    if g["land_area"] and g["land_area"] >= 8000:
        out.append("<b>大地块(≥8k sqft)</b>:尺寸曲线在这里identification最差(EXP-0011)—— "
                   "点估值只作<b>指示性</b>,走 case protocol")
    return out


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
           profile: str = "SC", count: int = 1, digest: dict | None = None) -> dict:
    """DD 链 + 街道解析 + 估值。任何一环诚实失败都不阻断其余部分。"""
    d = dd_mod.run(address)
    road = d["street"]
    res = street_alias.resolve(road, lambda s: bool(street_comps(s)))

    plot = d.get("plot") or {}
    # 面积优先级:用户实测 > MP2025 宗地(指示性)。估值对面积极敏感,来源必须写进报告。
    land_area = area or plot.get("area_sqft")
    area_src = ("用户提供(地契/实测)" if area else
                "MP2025 宗地面积 —— 指示性,非地籍丘块" if plot.get("area_sqft") else None)

    val, val_error = None, None
    if not res["ura_street"]:
        val_error = res["evidence"]
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
    cost = None
    if val:
        p = val["fair_value"]["price"]
        cost = {"entry": costs_mod.entry_costs(p, profile, count),
                "ssd": costs_mod.ssd_clock(p),
                "be_1y": costs_mod.breakeven_gain_pct(p, profile, count, 1),
                "be_5y": costs_mod.breakeven_gain_pct(p, profile, count, 5)}
    return {"address": address, "dd": d, "resolve": res, "land_area": land_area,
            "area_src": area_src, "val": val, "val_error": val_error, "ptype": ptype,
            "cost": cost, "profile": profile, "count": count, "digest": digest}


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
    chips = [
        ("地块", f"{g['land_area']:,.0f} sqft" if g["land_area"] else "未知"),
        ("分区", z.get("zone") or "—"),
        ("landed housing area", (lh.get("type") or "不在范围内")),
        ("PUB 水浸名单", "在名单上" if f.get("on_list") else "不在名单上"),
    ]
    chip_html = "".join(f"<div class=chip><b>{_esc(a)}</b><span>{_esc(b)}</span></div>"
                        for a, b in chips)
    return f"""<div class=hero>{head}</div>
<p class=addr>{_esc(g['address'])} · blk {_esc(geo['blk_no'])} {_esc(geo['road_name'])}
S({_esc(geo['postal'])}) · 估值基准日 {_esc(d['as_of'])}</p>
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
            f"{_esc(r['evidence'])}</span></div>")


def _l1_valuation(g: dict) -> str:
    v = g["val"]
    if not v:
        return (f"<div class=card><h2>1 · 估值 Valuation</h2>"
                f"<div class='banner stop'>{_esc(g['val_error'])}</div></div>")
    fv, s = v["fair_value"], v["subject"]
    bg, sg = v["buyer_guidance"], v["seller_guidance"]
    alias = g["resolve"]["basis"] == "alias"
    if sg.get("ask") is None or alias:
        guide = (f"<div class='banner warn'><b>买卖指导已抑制</b> —— "
                 f"{_suppress_reason_zh(v, g['land_area'] or 0, g['resolve']['basis'])}。"
                 f"<span class=note>门槛只能来自<b>观测到的成交</b>;此时只剩引擎自己的误差棒,"
                 f"拿它当议价线是把「无知」包装成「进取」。请把点估值当<b>指示性</b>,现场确认 "
                 f"condition 与几何,用 Investment Suite 佐证后再重估。</span></div>"
                 + (f"<p class=note>参考:引擎按 URA「{_esc(g['resolve']['ura_street'])}」桶算出的"
                    f"门槛是 {_money(bg['attractive_below'])} / {_money(bg['walk_away_above'])}"
                    f" —— <b>不要直接用</b>,先用 Investment Suite 拉本路"
                    f"(<code>{_esc(g['dd']['street'])}</code>)自己的成交分布。</p>"
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
    flag = ""
    ref = v.get("recent_street_reference")
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
    ref_html = (f"<p class=note>最新可比成交:<b>{ref['adj_psf']:,.0f}</b> land-psf(已按时间+尺寸"
                f"调整到本宗地,{ref['contract_ym']},原成交 {ref['area_sqft']:,.0f} sqft)"
                f"—— 单条最可信的证据点</p>" if ref else "")
    return f"""<div class=card><h2>1 · 估值 Valuation <span class=note>(引擎 LV1)</span></h2>
{flag}
<table class=kv>
<tr><td>公允价 fair value</td><td class=r><b>{_money(fv['price'])}</b></td></tr>
<tr><td>land psf</td><td class=r>{fv['land_psf']:,.0f}</td></tr>
<tr><td>公允价区间 <span class=note>(引擎预测误差,非议价区间)</span></td>
    <td class=r>{_money(fv['low'])} – {_money(fv['high'])}</td></tr>
<tr><td>置信度</td><td class=r>{fv['confidence']}/100</td></tr>
<tr><td>同街可比数 <span class=note>(URA {_esc(g['resolve']['ura_street'])})</span></td>
    <td class=r>{fv['n_street_comps']}</td></tr>
<tr><td>地契 tenure</td><td class=r>{_esc(s['tenure_type'])}
    {('· 剩余 %d 年' % s['remaining_lease_years']) if s.get('remaining_lease_years') else ''}</td></tr>
<tr><td>地块面积(估值输入)</td><td class=r>{g['land_area']:,.0f} sqft</td></tr>
<tr><td>面积来源</td><td class=r>{_esc(g['area_src'])}</td></tr>
</table>
{ref_html}
<h3>建筑状况 condition</h3>
<p class=note>{_COND_ZH.get((s.get('condition') or '').lower(), _COND_NONE_ZH)}</p>
<h3>买卖指导 <span class=note>(与公允价分开:读的是已成交的可比分布,不是引擎误差棒)</span></h3>
{guide}
<details><summary class=note>引擎原文 engine's own words(备查,未翻译)</summary>
<p class=note>{_esc(fv['confidence_label'])}</p>
<p class=note>{_esc(v['condition_note'])}</p>
<p class=note>{_esc(sg['note'])}</p></details>
</div>"""


def _l1_dd(g: dict) -> str:
    d = g["dd"]
    z, lh, p, f = (d.get("zoning") or {}), (d.get("landed_housing_area") or {}), \
                  (d.get("plot") or {}), (d.get("flood") or {})
    sch = d.get("schools_primary") or []
    mrt = d.get("mrt") or []
    scope = d.get("amenity_scope") or {}
    # 「2.2km 内无小学」只有在清单是**全岛**时才是关于新加坡的陈述;此前它是关于
    # dd.py 里那 15 所硬编码学校的陈述,而报告把它当成前者印了出来。
    near = [f"{n['name']} · {n['km']}km" for n in sch[:3]] or [
        "2.2km 内无" if scope.get("schools_primary") else "清单未覆盖本区域"]
    mrts = [f"{n['name']} · {n['km']}km" for n in mrt[:2]] or [
        "4km 内无" if scope.get("mrt") else "清单未覆盖本区域"]
    return f"""<div class=card><h2>2 · 尽调 Due Diligence <span class=note>(免费官方源:OneMap ·
MP2025 · PUB)</span></h2>
<table class=kv>
<tr><td>MP2025 分区 zone</td><td class=r>{_esc(z.get('zone'))} · GPR {_esc(z.get('gpr'))}</td></tr>
<tr><td>宗地面积 <span class=note>(指示性,非地籍)</span></td>
    <td class=r>{(f"{p['area_sqft']:,.0f} sqft" if p.get('area_sqft') else '—')}</td></tr>
<tr><td>landed housing area</td><td class=r>{_esc(lh.get('type'))}
    {('· ' + str(lh.get('storeys')) + ' 层') if lh.get('storeys') else ''}</td></tr>
<tr><td>PUB 水浸名单</td><td class=r>{'<b>在名单上</b>' if f.get('on_list') else '不在名单上'}</td></tr>
<tr><td>最近小学 <span class=note>(1km 官方口径以 OneMap SchoolQuery 为准)</span></td>
    <td class=r>{_esc(' / '.join(near))}</td></tr>
<tr><td>最近 MRT/LRT</td><td class=r>{_esc(' / '.join(mrts))}</td></tr>
</table>
<p class=note>清单口径:小学 {_esc(scope.get('schools_primary', '未声明'))};
MRT {_esc(scope.get('mrt', '未声明'))}。<b>商场/高速是人工清单</b> —— 报的是「这几个里最近的」,
不是「全新加坡最近的」。</p>
<p class=note>水浸:{_esc((f.get('evidential_weight') or '')[:220])}</p>
</div>"""


def _ssd_vs_entry_zh(c: dict) -> str:
    """SSD 与买入成本孰大 —— **算出来**,不写死。

    这句话原本是硬编码的「一年内的 SSD 比全部买入成本还大」。它只在**公民首套**(ABSD 0%)
    时成立;换成 PR 二套(ABSD 30% → 买入成本 S$1.47M)后,报告就在用自己的表格打自己的脸:
    S$680k 并不比 S$1.47M 大。凡是能被同一份报告里的数字证伪的句子,都必须由那些数字生成。
    """
    y1, entry = c["ssd"][0]["amount"], c["entry"]["total"]
    if y1 > entry:
        return (f"<b>短持有期上,SSD 主导一切</b>:一年内卖出的 SSD ≈ {_money(y1)},"
                f"比全部买入成本({_money(entry)})<b>还大</b>。")
    return (f"<b>两头都很重</b>:一年内卖出的 SSD ≈ {_money(y1)},买入成本 {_money(entry)}"
            f"(ABSD {c['entry']['absd_rate']*100:.0f}% 占了大头)—— "
            f"合计 {_money(y1 + entry)} ≈ 房价的 {(y1+entry)/c['entry']['price']*100:.0f}%。")


def _l1_costs(g: dict) -> str:
    """成本栈 —— 一份只有估值和 DD 的报告是不完整的:短持有期上 SSD 压倒一切。"""
    c = g["cost"]
    if not c:
        return ""
    e, cm = c["entry"], costs_mod
    prof = costs_mod.PROFILES.get(g["profile"], g["profile"])
    ssd_rows = "".join(
        f"<tr><td>{_esc(r['held'])}</td><td class=r>{r['rate']*100:.0f}%</td>"
        f"<td class=r>{'—' if not r['amount'] else _money(r['amount'])}</td></tr>"
        for r in c["ssd"])
    return f"""<div class=card><h2>3 · 成本栈 Cost stack <span class=note>(按引擎点估值
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
<h3>SSD 时钟 <span class=note>({_esc(cm.SSD_META['effective'])} 起购入:<b>4 年</b>期,按卖出价计,
起算 = 行使 OTP 之日)</span></h3>
<table><tr><th>持有</th><th class=r>SSD</th><th class=r>金额</th></tr>{ssd_rows}</table>
<p class=note><b>{_ssd_vs_entry_zh(c)}</b> 盈亏平衡所需涨幅:1 年内退出约
<b>{c['be_1y']*100:.0f}%</b>,4 年后退出约 <b>{c['be_5y']*100:.0f}%</b>
(含 BSD/ABSD + 2% 中介,未计利息与持有成本)。差出来的
<b>{(c['be_1y']-c['be_5y'])*100:.0f} 个百分点</b>就是 SSD 窗口的价格 —— 这也是 landed 的 alpha
主要在<b>买入那一刻</b>决定的算术原因。</p>
<p class=note>不含:中介佣金(landed 通常卖方付)、贷款利息、装修、房产税与持有成本。
ABSD 的夫妻联名 remission、FTA 国民豁免等情形本表未计。
来源:{_esc(cm.ABSD_META['source'])};{_esc(cm.SSD_META['source'])}。
{_esc(cm.ABSD_META['note'])}</p>
</div>"""


def _l1_alerts(g: dict) -> str:
    """深度尽调提示 —— DD-3:专业/实地/需卖方授权,与 OTP 挂钩。"""
    rows = ""
    for item, gated, why in _alerts_zh(g):
        tag = "<span class=gate>需卖方授权</span>" if gated else ""
        rows += f"<li><b>{item}</b> {tag}<div class=note>{why}</div></li>"
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
                   "结论请在做完下面这些之后自己下,或用 <code>--digest</code> 挂载已撰写的判断层。"
                   "</div>")
    return f"""<div class=card><h2>4 · 深度尽调 DD-3 <span class=note>(专业/实地/需卖方授权,
与 OTP 挂钩)</span></h2>
{verdict}
<ul class=alerts>{rows}</ul>
<p class=note>层级说明:<b>DD-1</b> 本人桌面、免费、每个候选都做(本报告的事实层);
<b>DD-2</b> 本人桌面、约 S$5-200、出价前完成(INLIS 产权);
<b>DD-3</b> 上面这些 —— 专业/实地/需卖方授权。三层分的是<b>「谁能定、何时定」</b>,
不是「免费还是收费」。</p>
</div>"""


def _l1_highlights(g: dict) -> str:
    """判断层的 highlights —— 挂载了就渲染,不丢弃。

    它们是**英文**的(digest 的作者只给 verdict 写了 `_zh`)。本报告主体是中文,所以这里
    如实标为「原文,英文」并折叠 —— 不假装它是中文,也不因为语言不合就把人已经看出来的
    东西扔掉。有 `_zh` 的字段(verdict)照常用中文。"""
    hl = (g.get("digest") or {}).get("highlights") or []
    items = ""
    for h in hl:
        t = (h.get("text_zh") or h.get("text") or "") if isinstance(h, dict) else h
        if t:
            items += f"<li>{t}</li>"
    if not items:
        return ""
    return (f"<details><summary>要点 highlights · {len(hl)} 条 <span class=note>"
            f"(判断层原文,英文 —— 人写的,非工具产出)</span></summary>"
            f"<div class=card><ul class=alerts>{items}</ul></div></details>")


def _l2_evidence(g: dict) -> str:
    v, d = g["val"], g["dd"]
    comps = ""
    if v:
        rows = "".join(
            f"<tr><td>{_esc(c['contract_ym'])}</td><td class=r>{c['land_area_sqft']:,.0f}</td>"
            f"<td class=r>{c['land_psf']:,.0f}</td><td class=r><b>{c['adj_land_psf']:,.0f}</b></td>"
            f"<td class=r>{_money(c['price'])}</td><td>{_esc(c['tenure'])}</td></tr>"
            for c in v["comps"])
        reads = "".join(f"<tr><td>{_esc(k)}</td><td class=r>{('%.0f' % x) if x else '—'}</td></tr>"
                        for k, x in v["independent_reads_land_psf"].items())
        comps = f"""<h3>同街可比 <span class=note>(lease-matched;adj psf = 该成交按时间+尺寸
调整到本宗地后的值 —— 点估值与指导都活在这一列上)</span></h3>
<table><tr><th>月份</th><th class=r>地块 sqft</th><th class=r>原始 psf</th>
<th class=r>adj psf</th><th class=r>价格</th><th>tenure</th></tr>{rows}</table>
<h3>独立方法读数 <span class=note>(收敛=信号,发散=hard case)</span></h3>
<table><tr><th>method</th><th class=r>land psf</th></tr>{reads}</table>"""
    nb = "".join(f"<tr><td>{_esc(n['zone'])}</td><td class=r>{n['metres']:.0f} m</td>"
                 f"<td class=r>{n['bearing_deg']:.0f}°</td></tr>"
                 for n in (d.get("neighbours") or [])[:8])
    tr = ""
    for t in (d.get("transects") or []):
        steps = " → ".join(f"{s['zone']}" for s in t["steps"][:6])
        tr += (f"<p class=note><b>朝 {_esc(t['toward'])}</b>({t['edge_m']:.0f}m):{_esc(steps)}"
               f"{'　⚠ ' + _esc(t['note'][:120]) if t.get('note') else ''}</p>")
    return f"""<details><summary>3 · 证据层 —— 可比、邻地、剖面(展开)</summary>
<div class=card>{comps}
<h3>邻近分区 neighbours</h3>
<table><tr><th>zone</th><th class=r>距离</th><th class=r>方位</th></tr>{nb}</table>
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
           "机会成本,都不在免费官方源里。分区/层数包络在上面,但「重建划不划算」是另一件事。</li>"
           "<li><b>持有成本</b> —— 贷款利息、房产税(自住 vs 出租税率不同)、维护。"
           "成本栈只算<b>交易</b>侧(BSD/ABSD/SSD)。</li>"
           "<li><b>判断</b> —— archetype、go/no-go、议价策略。工具给事实、估值、成本、必查项;"
           "结论需要实地与你的持有意图(可用 <code>--digest</code> 挂载已撰写的判断层)。</li>")
    prov = "".join(f"<li><b>{_esc(k)}</b> — {_esc(val)}</li>"
                   for k, val in (d.get("provenance") or {}).items())
    eng = "".join(f"<li>{_esc(x)}</li>" for x in (v["limitations"] if v else []))
    eng += "".join(f"<li>{_esc(x)}</li>" for x in (v["verify_before_offer"] if v else []))
    return f"""<details><summary>4 · 局限与方法 —— 下单前必读(展开)</summary>
<div class=card>
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
    a = ap.parse_args()

    digest = None
    if a.digest:
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "researcher", "landed", f"{a.digest}_dd.json")
        with open(p, encoding="utf-8-sig") as f:
            digest = json.load(f)

    g = gather(a.address, a.type, a.area, a.tenure, a.lease_start, a.condition, a.asof,
               profile=a.profile, count=a.count, digest=digest)
    slug = "".join(c if c.isalnum() else "_" for c in a.address.lower()).strip("_")
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
