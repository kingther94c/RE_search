"""南洋小学 1km 圈 · FREEHOLD(含 999y)landed 综述 —— 2026-07-23 练手轮的汇总产物。

    python deliverables/build_nanyang_freehold_overview.py

自包含:URA 快照(researcher/sources/snapshots)算队列,research/data/is_street/*.json
提供真实路覆盖层(有则渲染,无则明说),街道元数据(距离/管制/地契结构)来自本轮
逐门牌探测(OneMap + MP2025,2026-07-23)。三份深度样例挂链接。

口径纪律(与 landed-valuation skill 一致):
- 本综述是**观测层**:RAW 捆绑 psf(地+房,未调整),不是估值。估值以逐址引擎报告为准。
- FREEHOLD 桶 = tenure_type ∈ {freehold, freehold_equiv(999y)}。99/102/103 年真租赁一律剔除,
  且被剔除的量必须写出来(King's Road 38 笔剔 26 笔 —— 桶结构本身就是信息)。
- 距离 = URA landed 行 SVY21 质心到校点直线(街级),样本地址逐门牌复核;官方口径是
  OneMap SchoolQuery(量到校地边界、每年重算)—— 直线是保守高估,报名年必须重核。
"""
from __future__ import annotations

import collections
import gzip
import html
import json
import math
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deliverables.report_out import write_report  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = os.path.join(REPO, "researcher", "sources", "snapshots", "ura_transactions_2026-07-15.json.gz")
IS_DIR = os.path.join(REPO, "research", "data", "is_street")
SX, SY = 25154.4872114761, 33678.1373927556          # 南洋小学(52 King's Rd)SVY21,OneMap 2026-07-23
ASOF = "2026-07-23"           # = IS 收获日(meta.harvested_at);URA 快照 2026-07-15

# 本轮逐门牌探测的街道元数据(MP2025 SDCP + IS 逐门牌;探测记录见会话与 is_street 文件)
STREETS = {
    "KINGSMEAD ROAD":         dict(zh="金士美路", ring="内", envelope="BUNGALOWS · 2 层包络",
                                   is_slug="kingsmead_road",
                                   note="全街 FH 独立宅;IS 5/5 与 URA 完全一致 —— 圈内唯一无桶合并的样本街。"),
    "PRINCESS OF WALES ROAD": dict(zh="威尔士王妃路", ring="内", envelope="SEMI-DETACHED · 2 层包络",
                                   is_slug="princess_of_wales_road",
                                   note="999y 为主(IS 逐门牌 9 笔中 7 笔「999 yrs from 1875」+ FH 2 笔),同为准永久桶;半独立高度同质(3,774-3,829 sqft 主力档)。"),
    "KING'S ROAD":            dict(zh="国王路", ring="内", envelope="SEMI-D/BUNGALOWS · 2 层包络",
                                   is_slug="king_s_road",
                                   note="三制度拼合街:FH 排屋段(97-107 单号)· 102 年地契半独立段(60-104 偶号,占桶 26 笔,全部剔除)· FH 大独立段(54 段)。跨段类比必错价。"),
    "CORONATION DRIVE":       dict(zh="加冕径", ring="内", envelope="SEMI-DETACHED · <b>3 层包络</b>",
                                   is_slug=None,
                                   note="<b>圈内唯一探得的 3 层管制口袋</b>(2/7/15/23 号四点一致)—— 2 层现楼在此有真实的向上 A&A 余量;是本圈「加盖」主轴的所在街。"),
    "CORONATION ROAD":        dict(zh="加冕路", ring="内", envelope="SEMI-DETACHED · 2 层包络",
                                   is_slug=None,
                                   note="圈内型态最全(排屋/半独立/独立都有 FH 成交),预算跨度 S$6.2M-22.5M。"),
    "DUCHESS AVENUE":         dict(zh="公爵夫人道", ring="内(街参考点 0.61km)", envelope="未探测",
                                   is_slug=None,
                                   note="小街,URA 行无坐标 —— 距离按 OneMap 街参考点;逐门牌待核。"),
    "VICTORIA PARK GROVE":    dict(zh="维多利亚园", ring="内", envelope="未探测",
                                   is_slug=None,
                                   note="18/18 全部为租赁地契(99y)—— <b>不在本综述的 FH 桶内</b>,列此只为说明它被排除的原因。"),
}
DIST_OVERRIDE = {"DUCHESS AVENUE": 0.61}   # URA 行无坐标的街,用 OneMap 街参考点
OUT_CONTEXT = [   # 圈外但常被中介归入「南洋学区」的街 —— 质心距离一并给出,防混淆
    ("CHEE HOON AVENUE", 1.14), ("CORONATION ROAD WEST", 1.05), ("DUNEARN ROAD(landed 群)", 1.39),
    ("NAMLY AVENUE", 1.46),
]
SAMPLES = [
    ("97 KING'S ROAD", "排屋 Terrace · FH · 2,697 sqft", "S$8.33M · $3,087 psf · 置信 66",
     "97_king_s_road_landed_full_report.html",
     "IS 真实路近窗互证 +2%;三制度拼合街的段内读法见报告风险区"),
    ("5 PRINCESS OF WALES ROAD", "半独立 Semi-D · 准永久 · 3,382 sqft", "S$10.16M · $3,006 psf · 置信 74",
     "5_princess_of_wales_road_landed_full_report.html",
     "本宗地卡在两个尺寸队列之间 —— 点估值是插值,上下锚见报告风险区"),
    ("15 KINGSMEAD ROAD", "独立 Detached · FH · 10,447 sqft", "S$25.17M · $2,409 psf · 置信 45(指示性)",
     "15_kingsmead_road_landed_full_report.html",
     "两笔最新大地块印花($1,808/$2,271)都低于引擎点 —— 出价以印花为锚"),
]

def _esc(x): return html.escape(str(x if x is not None else "—"))
def _money(x):
    return f"S${x/1e6:.2f}M" if x and x >= 1e6 else (f"S${x:,.0f}" if x else "—")

def load_rows():
    rows = json.load(gzip.open(SNAP, "rt", encoding="utf-8"))
    return [r for r in rows if r["type_of_area"] == "Land"]

def street_stats(rows, st):
    sub = [r for r in rows if r["street"] == st]
    fh, lease = [], 0
    seen = set()
    for r in sub:
        k = (r["contract_ym"], r["area_sqft"], r["price"])
        if k in seen:
            continue
        seen.add(k)
        if r["tenure_type"] in ("freehold", "freehold_equiv"):
            fh.append(r)
        else:
            lease += 1
    xs = [r for r in sub if r.get("x")]           # 距离对全体行算(FH 桶为空的街也要有距离)
    km = (statistics.median(math.hypot(r["x"]-SX, r["y"]-SY) for r in xs)/1000 if xs
          else DIST_OVERRIDE.get(st))
    byt = collections.defaultdict(list)
    for r in fh:
        byt[r["property_type"]].append(r)
    cohorts = {}
    for t, rs in sorted(byt.items()):
        rs.sort(key=lambda r: r["contract_ym"], reverse=True)
        areas = sorted(r["area_sqft"] for r in rs)
        psfs = sorted(r["psf"] for r in rs)
        cohorts[t] = dict(
            n=len(rs), a0=areas[0], am=statistics.median(areas), a1=areas[-1],
            psf_med=statistics.median(psfs), price_med=statistics.median(r["price"] for r in rs),
            recent=[(r["contract_ym"], r["area_sqft"], r["psf"], r["price"]) for r in rs[:3]])
    return dict(n_all=len(seen), n_fh=len(fh), n_lease=lease, km=km, cohorts=cohorts)

def is_overlay(slug):
    if not slug:
        return None
    p = os.path.join(IS_DIR, f"{slug}_sale.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    rows = d["rows"]
    import re as _re
    def num(x): return float(_re.sub(r"[^\d.]", "", str(x)))
    latest = rows[0]
    return dict(n=len(rows), latest=f"{latest['date']} · {latest['address']} · "
                f"{latest.get('type','')} · {latest['area_sqft']} sqft · {latest['psf']} psf · {latest['price']}",
                harvested=d["meta"]["harvested_at"][:10])

_CSS = """body{margin:0;background:#0f1115;color:#e6e6e6;font:15px/1.65 -apple-system,"Segoe UI",
"Microsoft YaHei",Roboto,sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:28px}
h1{font-size:21px;margin:0 0 2px}h2{font-size:17px;margin:0 0 10px}
h3{font-size:14px;margin:14px 0 6px;color:#cfd6e4}
.sub{color:#9aa4b2;font-size:13px;margin:4px 0 16px}
.card{background:#141821;border:1px solid #222a36;border-radius:12px;padding:16px 18px;margin:12px 0}
table{width:100%;border-collapse:collapse;font-size:13px;margin:6px 0}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid #222a36;vertical-align:top}
th{color:#9aa4b2;font-weight:500}.r{text-align:right}
.note{color:#8d97a5;font-size:12px}
.banner{border-radius:8px;padding:10px 12px;margin:8px 0;font-size:13px}
.banner.warn{background:#2a2412;border:1px solid #5c4a1a}
.banner.ok{background:#14231a;border:1px solid #2c5c3a}
a{color:#7fb0e8}
details{margin:10px 0}summary{cursor:pointer;color:#cfd6e4;font-size:14px;padding:6px 0}
@media(max-width:640px){.wrap{padding:16px}}"""

def build() -> str:
    rows = load_rows()
    ring_rows, cards = "", ""
    for st, meta in STREETS.items():
        s = street_stats(rows, st)
        ov = is_overlay(meta["is_slug"])
        share = f"{ov['n']}/{s['n_all']}" if ov else "—"
        types = " · ".join(f"{t[:4]}×{c['n']}" for t, c in s["cohorts"].items()) or "(FH 桶为空)"
        ring_rows += (f"<tr><td><b>{_esc(st)}</b><div class=note>{_esc(meta['zh'])}</div></td>"
                      f"<td class=r>{s['km']:.2f} km</td><td>{_esc(meta['ring'])}</td>"
                      f"<td class=r>{s['n_fh']}<span class=note>/{s['n_all']}</span></td>"
                      f"<td>{_esc(types)}</td><td>{meta['envelope']}</td>"
                      f"<td class=r>{_esc(share)}</td></tr>")
        if not s["cohorts"]:
            continue
        crows = ""
        for t, c in s["cohorts"].items():
            rec = ";".join(f"{ym} · {a:,.0f}sf · <b>${p:,.0f}</b> · {_money(pr)}"
                           for ym, a, p, pr in c["recent"])
            crows += (f"<tr><td>{_esc(t)}</td><td class=r>{c['n']}</td>"
                      f"<td class=r>{c['a0']:,.0f}–{c['a1']:,.0f}<div class=note>中位 {c['am']:,.0f}</div></td>"
                      f"<td class=r><b>${c['psf_med']:,.0f}</b></td>"
                      f"<td class=r>{_money(c['price_med'])}</td><td>{rec}</td></tr>")
        ov_html = ""
        if ov:
            ov_html = (f"<p class=note><b>IS 真实路覆盖层</b>(收获 {ov['harvested']},逐门牌):"
                       f"真实路 {ov['n']} 笔 vs URA 桶 {s['n_all']} 笔;最新:{_esc(ov['latest'])}</p>")
        cards += (f"<div class=card><h3>{_esc(st)} <span class=note>({_esc(meta['zh'])} · "
                  f"质心 {s['km']:.2f} km · FH/999 {s['n_fh']} 笔,剔除租赁 {s['n_lease']} 笔)</span></h3>"
                  f"<p class=note>{meta['note']}</p>"
                  f"<table><tr><th>型态</th><th class=r>n</th><th class=r>地块 sqft</th>"
                  f"<th class=r>RAW psf 中位</th><th class=r>价格中位</th><th>最近 3 笔(未调整)</th></tr>"
                  f"{crows}</table>{ov_html}</div>")
    out_rows = "".join(f"<tr><td>{_esc(st)}</td><td class=r>{km:.2f} km</td></tr>" for st, km in OUT_CONTEXT)
    sample_rows = "".join(
        f"<tr><td><b>{_esc(a)}</b><div class=note>{_esc(spec)}</div></td>"
        f"<td class=r>{_esc(val)}</td><td><a href='{fn}'>{fn}</a><div class=note>{_esc(note)}</div></td></tr>"
        for a, spec, val, fn, note in SAMPLES)
    return f"""<!doctype html><html lang="zh-Hans"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>南洋小学 1km · Freehold landed 综述</title><style>{_CSS}</style>
<div class=wrap>
<h1>南洋小学 1km 圈 · Freehold(含 999y)landed 综述</h1>
<p class=sub>基准日 {ASOF} · 锚点:南洋小学(52 King's Road,OneMap)· URA 快照 2026-07-15 ·
IS 逐门牌收获 2026-07-23 · <b>观测层,非估值</b> —— 逐址估值见下方三份深度样例</p>

<div class='banner ok'><b>一屏结论</b> —— 圈内有 FH/999 成交的街共六条(含小样本的 Duchess
Ave),三个预算档:<b>排屋 S$6.2-8.2M</b>(King's Rd 97-107 段 $2,158-3,443 psf ·
Coronation Rd $2,526-3,200)、<b>半独立 S$8.4-13.2M</b>(Princess of Wales $2,223-3,755 ·
Coronation Rd/Drive $1,844-2,954 · King's Rd FH 段 $2,970-3,000)、<b>独立 S$13.4-26.8M</b>
(Kingsmead $1,808-2,516 · Coronation Rd $2,336-3,379 · Duchess $13.4-14.1M)。近 12 个月
各街成交活跃(RAW 多在 $2,600-3,150),未见跳档。<b>A&amp;A 主轴在 Coronation Drive</b>:
圈内唯一 3 层包络口袋 —— 2 层现楼有真实向上余量。</div>

<div class=card><h2>1 · 哪些街道符合条件</h2>
<p class=note>距离 = 该街 <b>URA landed 成交行 SVY21 质心</b>到校点直线(比 OneMap 街参考点更贴
landed 群;样本地址已逐门牌复核)。官方口径是 OneMap SchoolQuery(量到<b>校地边界</b>、每年
6 月重算)—— 直线是保守高估:「内」可信,贴线未定,<b>报名当年必须重核</b>。</p>
<table><tr><th>街道</th><th class=r>质心距离</th><th>1km</th><th class=r>FH/999 笔数<span class=note>/全部</span></th>
<th>FH 型态×笔数</th><th>MP2025 管制</th><th class=r>IS 真实路份额</th></tr>
{ring_rows}</table>
<p class=note><b>IS 真实路份额</b>:IS 逐门牌行数 / URA 同名桶行数 —— 小于 1 说明 URA 把邻路/支路
并进了这个桶(本轮实测 King's Road 桶内混着 King's Close、King's Drive)。「—」= 本轮未收获。</p>
<details><summary>圈外对照 —— 常被归入「南洋学区」但质心在 1km 外的街</summary>
<table><tr><th>街道</th><th class=r>质心距离</th></tr>{out_rows}</table>
<p class=note>Chee Hoon / Coronation Rd West 的部分门牌可能贴线 —— 具体地址逐门牌用
SchoolQuery 核,街级归类不可作报名依据。</p></details></div>

<div class=card><h2>2 · 各街价位与最近成交 <span class=note>(FH/999 桶 · RAW 捆绑 psf,未调整
—— 读水平与方向,不读精确公允价)</span></h2>
<p class=note>逐街一张卡:队列按型态分行,「最近 3 笔」为未调整原始印花;有 IS 覆盖层的街
(King's/Princess of Wales/Kingsmead)另附真实路读数。Victoria Park Grove 无 FH 成交
(18/18 全部为 99 年租赁地契),故无价位卡 —— 它的「便宜」是地契结构,不是错价。</p></div>
{cards}

<div class=card><h2>3 · 三份深度样例(引擎 LV1 逐址估值)</h2>
<table><tr><th>样本</th><th class=r>引擎读数</th><th>报告</th></tr>{sample_rows}</table>
<p class=note>每份含:估值+校准区间 · DD(分区/邻地/学校/水浸)· A&amp;A/重建潜力节 · 成本栈 ·
IS 真实路佐证后的风险区。三份的 AI 盲写对照臂与敌对评审记录在案。</p></div>

<div class=card><h2>4 · 口径与局限 —— 读数前必看</h2>
<ul class=note>
<li><b>FH 桶口径</b>:freehold + 999y(准永久,定价上视同一桶)。真租赁全部剔除并计数:
King's Road 剔 26 笔(102 yrs from 1996 段)、Victoria Park Grove 剔 18 笔(整街租赁)——
两处的「便宜」都是地契结构,不是错价。</li>
<li><b>RAW ≠ 估值</b>:表中 psf 是「地+房」捆绑价,未按时间/尺寸/状态调整。同街同尺寸段
psf 价差 20-60% 属常态,大头在建筑状态(原装 vs 翻建)—— 何时买哪一侧,见样例报告的
A&amp;A 节。</li>
<li><b>URA 桶合并</b>:URA 的 street 是母路标签。本轮实测(分母 = 剔除双批次重复 caveat
后的去重口径,与 §1 表一致):King's Road 真实路 16/32(50%,King's Close/Drive 混桶)、
Princess of Wales 9/11、Kingsmead 5/5(唯一无合并)。桶级分位数读门槛前先看份额。</li>
<li><b>Caveat 滞后</b>:URA 月粒度+滞后;IS 收获(2026-07-23)逐门牌到日,且捕捉到快照外的
2026-07-13 成交(30 Princess of Wales,$17.5M)。最新水平以 IS 覆盖层为准。</li>
<li><b>学区因子</b>:GEP 已停招(2026 为最后一届 P4 遴选)—— 学区溢价论以 SAP 品牌 +
报名超额为基础重估,勿引用旧 GEP 叙事。1km 身份每年重算,非永久属性。</li>
<li><b>本综述不给买卖建议</b>:它回答「市场长什么样」;「这栋值多少、出多少」由逐址
引擎报告回答(含校准区间与出价读法)。</li>
</ul></div>
<p class=note>数据源:URA Data Service caveats(快照 2026-07-15)· Investment Suite 逐门牌
街道表(2026-07-23,完整性门与 View All 计数对账)· OneMap / MP2025 SDCP(逐门牌探测)。
生成:deliverables/build_nanyang_freehold_overview.py(可重跑)。</p>
</div>"""

def main():
    res = write_report("nanyang_1km_Freehold_Landed_Overview.html", build())
    print(res.summary())

if __name__ == "__main__":
    main()
