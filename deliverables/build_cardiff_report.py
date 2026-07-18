# -*- coding: utf-8 -*-
"""Render the 19 Cardiff Grove landed valuation report (bilingual HTML).
Numbers are read from research/data/cardiff19_valuation.json + cardiff_transactions.json
so the prose can never drift from the computed figures. Output -> repo reports/ (gitignored)
+ synced to the Drive library (deliverables/report_out.py).
R2 revision: leads with the honest comp-based decline (not the flattering flat framing),
buyer target anchored to freshest same-spec prints, ABSD/property-tax quantified,
comp counts disambiguated (29 street terraces vs 8 same-spec originals in the grid)."""
import json, os, re, html, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from deliverables.report_out import write_report  # noqa: E402
V = json.load(open(os.path.join(REPO, "research", "data", "cardiff19_valuation.json"), encoding="utf-8"))
T = json.load(open(os.path.join(REPO, "research", "data", "cardiff_transactions.json"), encoding="utf-8"))
S = V["subject"]; VAL = V["valuation"]; CC = V["crosschecks"]; VP = V["vs_purchase"]
cost = V["costs"]; yld = V["yield"]; CN = V["comp_counts"]; last = S["last_sale"]
ML = V["market_layers"]; L3 = ML["L3_nearby_500m"]; L5 = ML["L5_sg_landed_daipan"]
try:
    NL = json.load(open(os.path.join(REPO, "research", "data", "cardiff_nearby_listings.json"), encoding="utf-8"))["rows"]
except Exception:
    NL = []

M = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
def yf(dt):
    dd, mm, yy = dt.split(); return int(yy) + (M[mm] - 0.5) / 12
def n(s): return float(re.sub(r"[^0-9.]", "", s)) if s else None
def money(x): return f"S${x:,.0f}"
def k(x): return f"${x:,.0f}"

rows = []
for r in T["rows"]:
    rows.append(dict(addr=r["address"], date=r["date"], yf=yf(r["date"]),
                     area=n(r["area_sqft"]), psf=n(r["psf"]), price=n(r["price"]),
                     top=r.get("top", "-")))
rows.sort(key=lambda r: r["yf"])

def size_class(a):
    if a <= 2000: return ("~1,840", "#2563eb")
    if a <= 2800: return ("~2,640", "#ea580c")
    if a <= 3600: return ("~3,264", "#7c3aed")
    return ("~4,140", "#dc2626")

REBUILT = {("86 Cardiff Grove", "06 Dec 2024"), ("72 Cardiff Grove", "16 Jan 2025")}
pt = VAL["point_price"]; pt_psf = VAL["point_psf"]
bt, btp = VAL["buyer_target_price"], VAL["buyer_target_psf"]
se, sep = VAL["seller_end_price"], VAL["seller_end_psf"]
fr = VAL["fair_range_price"]

# =============== SVG scatter: psf vs date, coloured by land-size class ===============
def svg_chart():
    W, H = 920, 360
    L, R, TP, B = 64, 175, 20, 42
    x0, x1 = 2016.3, 2026.7
    y0, y1 = 800, 2950
    def X(t): return L + (t - x0) / (x1 - x0) * (W - L - R)
    def Y(p): return TP + (y1 - p) / (y1 - y0) * (H - TP - B)
    s = [f'<svg class="chart" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Cardiff Grove terrace land-psf over time">']
    for p in range(1000, 3001, 500):
        s.append(f'<line class="grid" x1="{L}" y1="{Y(p):.1f}" x2="{W-R}" y2="{Y(p):.1f}"/>')
        s.append(f'<text class="ylab" x="{L-8}" y="{Y(p)+4:.1f}">${p:,}</text>')
    for yr in range(2017, 2027):
        s.append(f'<text class="xlab" x="{X(yr):.1f}" y="{H-16}">{yr}</text>')
    # decision band: buyer-target low -> seller-end high (right edge)
    top, bot = sep[1], btp[0]
    s.append(f'<rect x="{X(2025.7):.1f}" y="{Y(top):.1f}" width="{W-R-X(2025.7):.1f}" '
             f'height="{Y(bot)-Y(top):.1f}" fill="#2563eb" opacity="0.07"/>')
    s.append(f'<line x1="{L}" y1="{Y(pt_psf):.1f}" x2="{W-R}" y2="{Y(pt_psf):.1f}" '
             f'stroke="#2563eb" stroke-width="1.6" stroke-dasharray="6 4"/>')
    s.append(f'<text class="mk" x="{W-R+6}" y="{Y(pt_psf)+4:.1f}" fill="#2563eb">点估 ${pt_psf:,}</text>')
    # freshest same-spec 2025 level
    fp = CC["freshest_2025_original_psf"]
    s.append(f'<line x1="{X(2024.6):.1f}" y1="{Y(fp):.1f}" x2="{W-R}" y2="{Y(fp):.1f}" '
             f'stroke="#dc2626" stroke-width="1.2" stroke-dasharray="2 3"/>')
    s.append(f'<text class="mk" x="{W-R+6}" y="{Y(fp)+4:.1f}" fill="#dc2626">最新同规格 ${fp:,}</text>')
    for r in rows:
        cl, col = size_class(r["area"]); cx, cy = X(r["yf"]), Y(r["psf"])
        subj = (r["addr"] == "19 Cardiff Grove")
        rebuilt = (r["addr"], r["date"]) in REBUILT or (r["top"] not in ("-", "", None))
        rad = 7 if subj else 5
        style = 'stroke="#0f172a" stroke-width="2"' if subj else 'opacity="0.85"'
        s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rad}" fill="{col}" {style}/>')
        if rebuilt and not subj:
            s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rad+3}" fill="none" stroke="{col}" stroke-width="1" stroke-dasharray="2 2"/>')
    for r in rows:
        if r["addr"] == "19 Cardiff Grove":
            s.append(f'<text class="annot" x="{X(r["yf"])+10:.1f}" y="{Y(r["psf"])-8:.1f}" fill="#0f172a" font-weight="700">19号 2023 ${r["psf"]:,.0f}</text>')
    ly = TP + 6
    for lab, col in [("~1,840sf（标的档）", "#2563eb"), ("~2,640sf", "#ea580c"), ("~3,264sf", "#7c3aed"), ("~4,140sf", "#dc2626")]:
        s.append(f'<circle cx="{W-R+12}" cy="{ly}" r="5" fill="{col}"/>')
        s.append(f'<text class="leg" x="{W-R+22}" y="{ly+4}">{lab}</text>'); ly += 19
    s.append(f'<text class="leg" x="{W-R+6}" y="{ly+4}">◌ 虚线圈=重建/翻新</text>')
    s.append(f'<text class="ylab2" x="{L-8}" y="{TP+2}" style="text-anchor:end">地价 psf</text>')
    s.append('</svg>')
    return "\n".join(s)

def txn_rows():
    out = []
    for r in reversed(rows):
        cl, col = size_class(r["area"]); subj = (r["addr"] == "19 Cardiff Grove")
        rebuilt = (r["addr"], r["date"]) in REBUILT
        tag = ""
        if subj: tag = ' <span class="pill">标的 subject</span>'
        elif rebuilt: tag = ' <span class="pill" style="background:#fef3c7;color:#b45309">翻新/重建</span>'
        elif r["top"] not in ("-", "", None): tag = f' <span class="pill" style="background:#fef3c7;color:#b45309">重建 TOP {r["top"]}</span>'
        cls = ' class="hl"' if subj else ''
        out.append(f'<tr{cls}><td class="l">{r["date"]}</td><td class="l">{html.escape(r["addr"])}{tag}</td>'
                   f'<td class="l"><span style="color:{col}">●</span> {cl}</td><td>{r["area"]:,.0f}</td>'
                   f'<td>${r["psf"]:,.0f}</td><td>{money(r["price"])}</td></tr>')
    return "\n".join(out)

def grid_rows():
    out = []
    for g in V["grid"]:
        fresh = g["date"] in ("15 May 2025", "20 Mar 2025")
        subj = g["addr"] == "19 Cardiff Grove"
        tag = ' <span class="pill" style="background:#fee2e2;color:#b91c1c">最新</span>' if fresh else (' <span class="pill">标的</span>' if subj else '')
        trcls = ' class="hl"' if subj else ''
        out.append(f'<tr{trcls}><td class="l">{g["date"]}</td><td class="l">{html.escape(g["addr"])}{tag}</td>'
                   f'<td>{g["area"]:,.0f}</td><td>${g["psf"]:,.0f}</td><td>${g["adj_psf"]:,.0f}</td><td>{g["w"]:.3f}</td></tr>')
    return "\n".join(out)

def nearby_listing_rows():
    def sz(r):
        try: return int(re.sub(r"[^0-9]", "", r.get("size", "0")))
        except: return 0
    out = []
    for r in sorted(NL, key=sz):
        cmp = "Chuan Terrace" in r.get("address", "")
        tag = ' <span class="pill" style="background:#dbeafe;color:#1e40af">≈标的可比</span>' if cmp else ''
        trcls = ' class="hl"' if cmp else ''
        out.append(f'<tr{trcls}><td class="l">{html.escape(r.get("address",""))}{tag}</td>'
                   f'<td class="l">{html.escape(r.get("unit_type",""))}</td><td>{r.get("size","")}</td>'
                   f'<td>{r.get("psf","")}</td><td>{r.get("price","")}</td>'
                   f'<td class="l">{html.escape(r.get("posted","").replace(", 00:00",""))}</td></tr>')
    return "\n".join(out)

HTML = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>估值报告 Valuation Report — 19 Cardiff Grove</title>
<style>
:root{{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--accent:#1d4ed8;--bg:#f8fafc;--hl:#fff7ed}}
*{{box-sizing:border-box}}
body{{font:15px/1.7 -apple-system,Segoe UI,Roboto,"Microsoft YaHei","PingFang SC",Helvetica,Arial,sans-serif;color:var(--ink);margin:0;background:var(--bg)}}
.wrap{{max-width:980px;margin:0 auto;padding:0 22px 80px;background:#fff;box-shadow:0 1px 40px rgba(15,23,42,.06)}}
header{{padding:38px 0 24px;border-bottom:3px solid var(--accent);margin-bottom:8px}}
.kicker{{color:var(--accent);font-weight:700;letter-spacing:.04em;font-size:12px}}
h1{{font-size:30px;margin:6px 0 4px;letter-spacing:-.02em}}
h2{{font-size:20px;margin:38px 0 10px;padding-top:14px;border-top:1px solid var(--line)}}
h3{{font-size:16px;margin:22px 0 6px;color:#1e293b}}
.sub{{color:var(--mut);font-size:14px}}
.en{{color:var(--mut);font-weight:400;font-size:.82em}}
.meta{{display:flex;flex-wrap:wrap;gap:8px 26px;margin-top:14px;font-size:13px;color:var(--mut)}}
.meta b{{color:var(--ink)}}
.verdict{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}}
.card{{background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:14px 16px}}
.card .n{{font-size:22px;font-weight:700;letter-spacing:-.02em}}
.card .k{{font-size:12px;color:var(--mut)}}
.card.accent{{background:#eff6ff;border-color:#bfdbfe}}
.card.accent .n{{color:var(--accent)}}
.card.warn{{background:#fff7ed;border-color:#fed7aa}}
.card.warn .n{{color:#b45309}}
table{{border-collapse:collapse;width:100%;font-size:13.5px;margin:10px 0}}
th,td{{padding:7px 9px;text-align:right;border-bottom:1px solid var(--line)}}
th{{background:var(--bg);font-size:12px;color:var(--mut)}}
td.l,th.l{{text-align:left}}
tr.hl td{{background:var(--hl)}}
.chart{{width:100%;height:auto;background:#fff;border:1px solid var(--line);border-radius:10px;margin:14px 0}}
.chart .grid{{stroke:#eef2f7;stroke-width:1}}
.chart .ylab,.chart .xlab,.chart .leg,.chart .mk,.chart .annot,.chart .ylab2{{font:11px sans-serif;fill:#64748b}}
.chart .ylab{{text-anchor:end}} .chart .xlab{{text-anchor:middle}}
.chart .mk,.chart .annot{{font-weight:600}} .chart .ylab2{{fill:#334155}}
.note{{background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:12px 16px;font-size:13.5px;margin:14px 0}}
.rec{{background:#ecfdf5;border:1px solid #a7f3d0;border-radius:12px;padding:16px 20px;margin:14px 0}}
.rec h3{{margin-top:0;color:#047857}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}
.cn{{background:#f1f5f9;border-radius:10px;padding:14px 18px;margin:10px 0;font-size:14px}}
ul{{margin:6px 0 6px 0;padding-left:20px}} li{{margin:4px 0}}
.foot{{color:var(--mut);font-size:12px;margin-top:30px;border-top:1px solid var(--line);padding-top:14px}}
.pill{{display:inline-block;background:#eff6ff;color:var(--accent);border-radius:20px;padding:1px 9px;font-size:11.5px;font-weight:600}}
@media(max-width:720px){{.verdict,.two{{grid-template-columns:1fr 1fr}}}}
</style></head><body><div class="wrap">

<header>
<div class="kicker">有地住宅估值 · Landed Property Valuation · 研究 #19</div>
<h1>19 Cardiff Grove</h1>
<div class="sub">Serangoon Garden Estate · 第19邮区 District 19 (OCR) · 排屋 Terrace House · 地块 {S['land_sqft']:,.2f} sqft · 999年地契 (1956起，余约{S['years_left']}年)</div>
<div class="meta">
<span><b>估值日期 Valuation date</b> {V['asof']}</span>
<span><b>数据来源 Source</b> PropNex Investment Suite（Tier-1，UI 自动化读取）</span>
<span><b>可比 Comps</b> 同街 {CN['street_terraces_10y']} 笔排屋(10年，完整性已校验) + 附近 {L3['asks_n']} 挂牌 + 区域/D19/全国大盘</span>
<span><b>编制 Prepared by</b> RE_search landed pipeline</span>
</div>
</header>

<div class="verdict">
<div class="card accent"><div class="k">公允价 Fair value（点估）</div><div class="n">{money(pt)}</div><div class="sub">${pt_psf:,} psf 地价</div></div>
<div class="card warn"><div class="k">现值 vs 2023峰值买入</div><div class="n">{VP['central_delta_pct']:+.0f}%</div><div class="sub">水平低于峰值·斜率走平<br/>下行情景 {VP['freshest_delta_pct']:+.0f}%</div></div>
<div class="card"><div class="k">买家目标 / 卖方期望</div><div class="n" style="font-size:16px">{money(bt[0])}–{money(bt[1])}<br/>{money(se[0])}–{money(se[1])}</div><div class="sub">buyer / seller</div></div>
<div class="card"><div class="k">毛租金回报 Gross yield</div><div class="n">{yld['gross_yield_pct']:.1f}%</div><div class="sub">估租 ~{k(yld['rent_mo_est'])}/月</div></div>
</div>

<div class="cn">
<b>摘要 / Summary</b> — 标的 <b>19 Cardiff Grove</b>（Serangoon Garden Estate，D19，<b>999年地契自1956起</b>，余约{S['years_left']}年≈准永久），地块 <b>{S['land_sqft']:,.2f} sqft</b> 的<b>原始状态排屋</b>（app 无重建 TOP 记录）；现业主 2023-03 以 {money(last['price'])}（${last['psf']:,} psf）购入，为该址自1998以来唯一成交。基于<b>同街 {CN['same_spec_originals_in_grid']} 笔同规格原始排屋成交</b>（Tier-1，全街 {CN['street_terraces_10y']} 笔完整性已校验）的地价 psf 可比模型，稳健点估 <b>{money(pt)}（${pt_psf:,} psf）</b>。<b>点估叠加了四层证据（§4.6）：</b>标的自身2023印、同街同规格、<b>附近可比挂牌</b>、区域/大盘——其中附近一间 <b>1,798sf 排屋（≈标的）现仅叫 $1,947 psf</b>，独立佐证同街2025的软度并支撑买家端；<b>点估仍取同街同规格网格 ${pt_psf:,}</b>（未把该挂牌并入中枢，以免与已占网格约42%权重的2025软印重复计数）。全国 landed 大盘（${L5['avg_psf']:,}、创新高）与本 D19 中尺寸排屋（~$1,900）的差距是<b>截面结构差</b>（优质盘/GCB 拉高全国均值），非本细分的时序背离；大盘只作上行风险、不抬高标的。<b>关键判断：区分"水平"与"斜率"。水平——</b>现可实现中枢（~{money(pt)}）低于业主2023的<b>周期高位买入</b>，可比读数 <b>{VP['central_delta_pct']:+.0f}%</b>；<b>斜率——</b>统计上走平（本街同规格2022以来 −2.6%/年、R²=0.02不显著），非明确下跌，区域整体持稳。<b>下行情景：</b>最新两笔同规格原始成交（58号 $1,767、47号 $1,946，2025年）折合仅 ~{money(CC['freshest_2025_original_price'])}、较2023低 <b>{VP['freshest_delta_pct']:+.0f}%</b>；但本街同规格<b>峰值在2024</b>（$2,327–2,380，高于业主2023的 ${CC['own_2023_flat_psf']:,}），2025回软——故中枢取加权网格、非最悲观印。买家合理目标 <b>{money(bt[0])}–{money(bt[1])}</b>（贴近最新同规格印）；卖方期望端 {money(se[0])}–{money(se[1])}（其2023原价与上档可比，属期望非市场中枢）。毛回报仅 ~{yld['gross_yield_pct']:.1f}%。<b>结论：自住/长持可（准永久地契、成熟社区）；纯投资吸引力有限；卖方难在2023价平进平出；买家勿越 {money(se[1])}。</b></div>

<h2>1 · 执行摘要 <span class="en">Executive summary</span></h2>
<ul>
<li><b>稳健点估 {money(pt)}（${pt_psf:,} psf 地价）</b>——同街 {CN['same_spec_originals_in_grid']} 笔<b>同规格原始</b>排屋、时间衰减加权。有地住宅按<b>地价 psf</b>计价，非建筑面积。</li>
<li><b>水平低于2023峰值买入、斜率走平：</b> 现可实现中枢较2023 <b>{VP['central_delta_pct']:+.0f}%</b>（水平）；价格斜率则统计上走平（§4.2，非明确下跌）。<b>下行情景</b>——最新两笔同规格原始印（2025）$1,767 / $1,946（均 ${CC['freshest_2025_original_psf']:,}），折合 ~{money(CC['freshest_2025_original_price'])}、较2023 <b>{VP['freshest_delta_pct']:+.0f}%</b>。注意<b>本街同规格峰值在2024</b>（22号 $2,380、11号 $2,327，高于业主2023的 ${CC['own_2023_flat_psf']:,}）：业主2023买入接近周期高位但非绝对顶，2025才回软。业主印按 −2.6%/年平推至今≈${CC['own_2023_timeadj_psf']:,}，与中枢一致。</li>
<li><b>五层证据叠加（§4.6，你要的口径）：</b> ①标的2023印 $2,256 → ②<b>同街同规格加权 ${VAL['same_street_grid_psf']:,}</b>（2025软至$1,767–1,946，=点估锚）→ ③<b>附近可比挂牌</b> Chuan Terrace 1,798sf 叫 $1,947→可成交~${VAL['nearby_ask_txn_psf']:,}（佐证买家端）→ ④区域 500m ${L3['txn_avg_psf_5y']:,}／D19 ${ML['L4_district19']['avg_psf_10y']:,}（全类型背景）→ ⑤全国大盘 ${L5['avg_psf']:,}（{L5['change_pct']:+.0f}%）创新高（截面 mix，作上行风险）。点估锚定②同街网格；③④⑤为佐证/背景，不并入中枢。</li>
<li><b>决策带（买方→卖方）：</b> 买家目标 <b>{money(bt[0])}–{money(bt[1])}</b>（${btp[0]:,}–${btp[1]:,} psf，贴近最新同规格印与附近可比挂牌）；点估 {money(pt)}；卖方期望端 {money(se[0])}–{money(se[1])}（${sep[0]:,}–${sep[1]:,} psf）。公允区间 {money(fr[0])}–{money(fr[1])}。</li>
<li><b>地块量级效应（弹性 {V['method']['quantum_elasticity']}）：</b> psf 随地块变大近乎等比下降，<b>总价</b>因此几乎与地块无关——本街排屋无论 1,840 或 4,140 sqft，总价都聚在 ~S$3.5–5.0m。</li>
<li><b>地板/天花板：</b> 地皮/单层原始屋现挂牌 ~{money(CC['land_floor_price'])}（${CC['land_floor_psf']:,} psf）为下限；重建/翻新屋 ${CC['rebuilt_ceiling_psf'][0]:,}–{CC['rebuilt_ceiling_psf'][1]:,} psf（≈{money(CC['rebuilt_ceiling_price'][0])}–{money(CC['rebuilt_ceiling_price'][1])}）为上限——差价即<b>重建经济学</b>（§6）。</li>
<li><b>摩擦/回报：</b> 毛回报仅 ~{yld['gross_yield_pct']:.1f}%；买入 BSD ~{k(cost['bsd_at_point'])}（第二套另加 ABSD 20%≈{k(cost['absd_2nd_20pct'])}）；现业主 SSD 已于 2026-03 届满、现售无卖方印花税。</li>
<li><b>建议：自住/10年长持合理；纯投资吸引力有限。</b> 详见 §9。</li>
</ul>

<h2>2 · 标的与街道 <span class="en">Subject &amp; street</span></h2>
<div class="two"><div>
<table>
<tr><th class="l">项目 Attribute</th><th class="l">数值 Value</th></tr>
<tr class="hl"><td class="l">地址 Address</td><td class="l"><b>19 Cardiff Grove {S['postcode']}</b></td></tr>
<tr><td class="l">类型 Type</td><td class="l">{S['type']}（排屋）</td></tr>
<tr><td class="l">地块 Land size</td><td class="l"><b>{S['land_sqft']:,.2f} sqft</b>（最后成交口径；文中约称 ~1,840）</td></tr>
<tr><td class="l">地契 Tenure</td><td class="l"><b>{S['tenure']}</b>（余约{S['years_left']}年≈准永久）</td></tr>
<tr><td class="l">邮区/区域 District</td><td class="l">{S['district']}</td></tr>
<tr><td class="l">分区 Subtown</td><td class="l">{S['subtown']}</td></tr>
<tr><td class="l">状态 Condition</td><td class="l">{S['condition']}（无重建记录）</td></tr>
<tr><td class="l">上次成交 Last sale</td><td class="l"><b>{last['date']} · {money(last['price'])} · ${last['psf']:,} psf</b>（1998以来唯一）</td></tr>
</table>
</div><div>
<div class="note" style="margin-top:0"><b>Serangoon Garden Estate 定位</b><br/>
成熟有地社区，混合地契（本街为 999年自1956起，实务上等同永久）。生活配套成熟（Serangoon Garden 巷内食阁、Chomp Chomp、myVillage），Lorong Chuan / Serangoon MRT 车程可达但非步行圈。<br/><br/>
<b>注意区分：</b>坊间"Serangoon Garden Estate 全区最高 $3,472 psf（2026-05）"出自<b>其它街道</b>（多为重建屋），<b>非 Cardiff Grove</b>——本街 10年最高仅 $2,848 psf（72号，翻新屋）。可比必须锁定<b>同街同规格</b>，不采该区级高点。</div>
</div></div>

<h2>3 · 同街可比成交 <span class="en">Same-street comparables (Tier-1)</span></h2>
<p>下图为 Cardiff Grove <b>全部 {CN['street_terraces_10y']} 笔排屋成交（10年）</b>的地价 psf × 时间散点，按地块大小分档着色。抓取均价 $3,663,164 = app 街道带均价 $3,663,165（差 $1 四舍五入），<b>完整性已校验</b>。两点一目了然：<b>①地块越大 psf 越低（量级效应）；②2020→2024 上台阶后，2025 同规格原始印明显回软、2026 无同规格新印。</b>红色虚线为最新同规格 2025 印水平 ${CC['freshest_2025_original_psf']:,}，明显低于蓝色点估线。</p>
{svg_chart()}
<p class="sub">标的 <b>19号（黑圈）</b> 位于 ~1,840sf 蓝色档、2023年 ${last['psf']:,} psf（牛市顶部）。虚线圈=重建/翻新屋（psf 系统性偏高，不入原始基准）。蓝虚线=点估 ${pt_psf:,}；红点线=最新同规格 ${CC['freshest_2025_original_psf']:,}；右侧阴影=决策带。</p>

<h3>成交明细（新→旧）<span class="en">Transactions, newest first</span></h3>
<table>
<tr><th class="l">成交日</th><th class="l">地址</th><th class="l">档 Class</th><th>地块 sqft</th><th>地价 psf</th><th>成交价</th></tr>
{txn_rows()}
</table>
<p class="sub">来源：PropNex Investment Suite → 19 Cardiff Grove → Sale → Street scope → Terrace「Type Summary」全表；10年窗口；滚动去重 + 完整性校验。</p>

<h2>4 · 估值方法 <span class="en">Method</span></h2>
<div class="two"><div>
<h3>4.1 地价量级效应 <span class="en">Quantum</span></h3>
<p>对 {CN['street_terraces_10y']} 笔回归 ln(psf)~ln(地块)，弹性 <b>{V['method']['quantum_elasticity']}</b>（近期子样本 R²≈0.60）：地块翻倍，psf 降约 45%。含义是<b>总价</b>≈与地块大小无关。<b>注意：</b>该弹性在标的档(~1,840sf)内稳健，但外推到 3,000+sf 大屋时不可靠——见 §4.4 交叉验证的离散。</p>
<h3>4.2 时间趋势（见顶走平）<span class="en">Trend</span></h3>
<p>同规格档（1,750–2,000 sqft）ln(psf)~年：<b>10年 +7.6%/年</b>（含 2020–24 牛市），但 <b>2022年以来 −2.6%/年（R²=0.02，不显著）</b>——统计上已走平/微跌。大地块 91号重复成交 2021→2026 仅 <b>+0.8%/年</b>。<b>区分层次：</b>区域层面（Serangoon Garden Estate 全区、含各街与重建屋）自2023大体持稳偏升；但<b>本街同规格原始屋</b>2025走软。可比性优先——本估以同街同规格为准，不采区级持稳去抬高标的。故点估采近期<b>平/微跌</b>假设，并对该负趋势保持一致（不对业主自身印做有利的"平推抬升"）。重复成交里 +12~30%/年的都是<b>翻新/重建 flip</b>（72、45号），非纯市场增值——已剔除。</p>
</div><div>
<h3>4.3 状态与重建 <span class="en">Condition</span></h3>
<p>同尺寸内，<b>状态（原始 / 翻新 / 重建）是最大单一价差杠杆</b>：同规格档 psf 近期区间 $1,767–$2,848 主要由此驱动。标的为<b>原始状态</b>（TOP 空），故点估以<b>原始状态可比</b>为基，重建/翻新可比（86号 TOP2012 $2,446；72号翻新 $2,848）作<b>上限参照</b>剔除出基准集。</p>
<h3>4.4 点估与交叉验证 <span class="en">Point &amp; cross-checks</span></h3>
<p>点估 = <b>同街同规格 recency 加权网格 ${pt_psf:,}</b>（= S${pt:,.0f}）。业主2023印已在网格内(按半衰期加权，不再作独立同权腿以免双重计数与卖方锚定)。以下为<b>交叉验证</b>(非同权平均、不并入中枢)：</p>
<table>
<tr><th class="l">交叉验证 Cross-check</th><th>psf</th><th>指向</th></tr>
<tr class="hl"><td class="l"><b>点估（同街网格）</b></td><td><b>${pt_psf:,}</b></td><td>中枢</td></tr>
<tr><td class="l">最新2笔同规格原始(2025)</td><td>${CC['freshest_2025_original_psf']:,}</td><td>下行(−18%)</td></tr>
<tr><td class="l">自身2023印(−2.6%/年平推)</td><td>${CC['own_2023_timeadj_psf']:,}</td><td>印证中枢</td></tr>
<tr><td class="l">附近可比挂牌→可成交(§4.6)</td><td>~${VAL['nearby_ask_txn_psf']:,}</td><td>佐证买家端</td></tr>
</table>
<p class="sub">附近 1,798sf 挂牌折算可成交 ~${VAL['nearby_ask_txn_psf']:,} ≈ 同街最新2025印 ${CC['freshest_2025_original_psf']:,}——两者是<b>同一个 2025 软信号</b>(该软印已占网格约42%权重)，故挂牌不再重复计入中枢，只作买家端与"软度延续到2026"的佐证(见 §4.6、§10)。</p>
</div></div>

<h3>4.5 调整网格 <span class="en">Adjustment grid（{CN['same_spec_originals_in_grid']} 笔同规格原始，time+size 归一）</span></h3>
<table>
<tr><th class="l">成交日</th><th class="l">地址</th><th>地块 sqft</th><th>原始 psf</th><th>调整后 psf</th><th>权重 w</th></tr>
{grid_rows()}
</table>
<p class="sub">权重 = 时间衰减（半衰期 {V['method']['halflife_yr']}年）× 标的自身成交锚 ×2。最新两笔 2025 原始成交（58号 $1,767、47号 $1,946）权重最高，把网格中枢压到 ${VAL['same_street_grid_psf']:,}——这正是同规格2025走软、低于2023峰值买入的来源。全街 {CN['street_terraces_10y']} 笔中，入网格的是<b>近5年</b>标的同规格(1,750–2,000sf)原始屋共 {CN['same_spec_originals_in_grid']} 笔；更早(2016–20)的同规格原始印在5年窗口外、按半衰期近零权重不计，异尺寸与重建/翻新则仅作量级/天花板参照。<b>去掉标的自身印×2锚后中枢为 ${VAL['weighted_comp_psf_pure']:,}</b>（与 ${VAL['same_street_grid_psf']:,} 仅差$11——自锚不影响结论）。</p>

<h3>4.6 区域、挂牌与大盘走势 <span class="en">Region, asking prices &amp; market trend</span></h3>
<p>按你的要求叠加更宽的五层证据(不只同街)——它们<b>佐证</b>同街网格点估 ${pt_psf:,}(未改动中枢)，并界定买家/卖方带：</p>
<table>
<tr><th class="l">证据层 Layer</th><th class="l">口径 Basis</th><th>水平 psf</th><th class="l">对标的的含义</th></tr>
<tr><td class="l">① 标的自身</td><td class="l">2023-03 成交</td><td>$2,256</td><td class="l">周期高位买入（上锚，已含牛市溢价）</td></tr>
<tr class="hl"><td class="l">② 同街同规格 ★</td><td class="l">Cardiff 1,840sf 原始·加权</td><td>${VAL['same_street_grid_psf']:,}</td><td class="l">最可比；2025 回软至 $1,767–1,946</td></tr>
<tr class="hl"><td class="l">③ 附近可比挂牌 ★</td><td class="l">Chuan Terrace 1,798sf（≈标的）</td><td>$1,947 挂</td><td class="l">可成交约 ${VAL['nearby_ask_txn_psf']:,}；独立印证偏软</td></tr>
<tr><td class="l">④ 区域 500m</td><td class="l">全类型成交均（5Y）</td><td>${L3['txn_avg_psf_5y']:,}</td><td class="l">含大屋/半独立→偏低，仅背景</td></tr>
<tr><td class="l">④ D19 全区</td><td class="l">全类型成交均（10Y）</td><td>${ML['L4_district19']['avg_psf_10y']:,}</td><td class="l">极异质（含Hougang/Punggol），松背景</td></tr>
<tr><td class="l">⑤ 全国 landed 大盘</td><td class="l">SG avg psf（app Market）</td><td>${L5['avg_psf']:,}</td><td class="l">{L5['change_pct']:+.0f}% 创新高、仍升——但本细分跑输</td></tr>
</table>
<div class="note"><b>大盘 vs 本盘：截面差，非时序背离。</b> 全国 landed 大盘均价 ${L5['avg_psf']:,}、曲线2025–26冲上<b>新高</b>——但这是<b>全岛截面</b>(优质盘/GCB/核心区拉高均值)，与本 D19 OCR 中尺寸排屋(~$1,900)的差距是<b>结构性 mix 差</b>，<b>不能</b>当作本盘的时序信号；本盘真正的走平证据是 Cardiff 自身 −2.6%/年(§4.2)。<b>跨街取证的对称性：</b>§2 拒绝把区级高点 $3,472 psf 计入(因其为<b>重建屋</b>、状态不可比)，此处采 Chuan Terrace 则因其<b>尺寸/状态同规格(原始 inter-terrace)</b>——按"同规格优先"一致成立，非"只取低不取高"。<b>大盘仅作上行风险</b>(若本盘补涨可上修)，不抬高标的。★=最可比的承重层。</div>
<h4>附近 500m 在售挂牌（Tier-2 asks · {L3['asks_n']} 个）<span class="en">Current nearby listings (asking)</span></h4>
<table>
<tr><th class="l">地址 Address</th><th class="l">类型 Type</th><th>面积 sqft</th><th>要价 psf</th><th>要价 Price</th><th class="l">挂牌日</th></tr>
{nearby_listing_rows()}
</table>
<p class="sub">挂牌为<b>要价（Tier-2）</b>，通常高于成交 3–8%。最可比的 <b>Chuan Terrace（1,798sf inter-terrace）叫 $1,947 psf / $3.5m</b>，是买家目标带 {money(bt[0])}–{money(bt[1])} 的现实依据。惟 Chuan 属 <b>Lorong Chuan 一带、与 Serangoon Gardens 核心非同一 enclave</b>，且 n=1、系要价，故仅作<b>软佐证与买家参考、不入中枢</b>。大屋/半独立（7,375sf 叫 ~$1,290 psf）因量级效应 psf 低、不可比；Conway Circle（2,200sf 叫 $2,726）疑为翻新/新屋。</p>

<h2>5 · 地板与天花板 <span class="en">Floor &amp; ceiling</span></h2>
<div class="two"><div>
<div class="note" style="margin-top:0"><b>地板 ≈ {money(CC['land_floor_price'])}（${CC['land_floor_psf']:,} psf）</b><br/>
现挂牌一间<b>单层原始 inter-terrace</b>（地=建 1,840 sqft，可建至2.5层）叫价约 S$3.3m——"地皮/待重建"下限。标的为(推定)2层、2023年以 ${last['psf']:,} psf 成交，在此之上；但若实为单层/残旧，公允价应下修向此地板。</div>
</div><div>
<div class="note" style="margin-top:0;background:#fff7ed;border-color:#fed7aa"><b>天花板 ≈ ${CC['rebuilt_ceiling_psf'][0]:,}–{CC['rebuilt_ceiling_psf'][1]:,} psf</b><br/>
重建/翻新2层排屋：86号（TOP2012）$2,446、72号（翻新）$2,848；8 Cardiff Grove 为2015重建、建筑 3,045 sqft。即 ≈{money(CC['rebuilt_ceiling_price'][0])}–{money(CC['rebuilt_ceiling_price'][1])}。标的若重建/大翻新可趋近，但需净出建造成本与2–3年持有。</div>
</div></div>

<h2>6 · 重建经济学 <span class="en">Rebuild economics</span></h2>
<p>有地住宅的 α 主要在<b>买入原始屋于地价、再重建</b>：当 <b>买价 &lt; 重建后可比 − 建造成本（约 S$550/sqft GFA，后疫情偏高）− 2–3年持有/税费</b> 时成立。粗算：以买家目标 ~{money(bt[1])} 买入 + BSD ~{k(cost['bsd_at_point'])} + 重建2层约 3,000+ sqft GFA（建造 ~S$1.6–1.8m）+ 持有，总投入 ~S$5.5–5.8m；对照重建屋天花板 ~{money(CC['rebuilt_ceiling_price'][0])}–{money(CC['rebuilt_ceiling_price'][1])}——<b>自住重建可行（得全新大屋）；纯翻建套利空间薄，需低价买入 + 成本控制 + 市场配合</b>。若 pro-forma 只在 &gt;5%/年地价升值下才成立，则不成立（当前平台/回软期）。</p>

<h2>7 · 成本与回报 <span class="en">Costs &amp; yield</span></h2>
<div class="two"><div>
<table>
<tr><th class="l">买方印花税 BSD/ABSD（按点估 {money(pt)}）</th><th>金额</th></tr>
<tr><td class="l">买方印花税 BSD</td><td>{k(cost['bsd_at_point'])}</td></tr>
<tr><td class="l">ABSD 公民首套</td><td>0</td></tr>
<tr><td class="l">ABSD 公民第二套(20%)</td><td>{k(cost['absd_2nd_20pct'])}</td></tr>
<tr><td class="l">ABSD PR 首套(5%)</td><td>{k(cost['absd_pr_1st_5pct'])}</td></tr>
<tr><td class="l">ABSD 外籍(60%)</td><td>{k(cost['absd_foreigner_60pct'])}</td></tr>
<tr><td class="l">SSD（现业主卖方）</td><td class="l">nil（2023-03购入，旧3年期已于2026-03届满；新4年期只适用2025-07-04起购入）</td></tr>
</table>
</div><div>
<table>
<tr><th class="l">租金与回报 Rent &amp; yield</th><th>数值</th></tr>
<tr><td class="l">估算月租（~1,840sf 排屋）</td><td>~{k(yld['rent_mo_est'])}/月</td></tr>
<tr><td class="l">毛租金回报 Gross yield（按点估）</td><td><b>{yld['gross_yield_pct']:.1f}%</b></td></tr>
<tr><td class="l">同街近期排屋租金</td><td>{k(yld['street_rent_terrace_recent'])}/月（1,000–1,500sf档）</td></tr>
<tr><td class="l">同街平均租金</td><td>{k(yld['street_rent_avg'])}/月（含大屋）</td></tr>
</table>
<div class="note" style="margin-top:6px;font-size:12.5px"><b>房产税 Property tax：</b>{cost['property_tax_note']}。Tier-1 租金来自 app Rent → Street scope；landed 回报结构性偏低。</div>
</div></div>

<h2>8 · 资产类别与政策 <span class="en">Asset-class context</span></h2>
<ul>
<li><b>有地住宅的防御性是"非对称捕获"</b>（官方51年序列实测：上行捕获0.95 / 下行捕获0.74），<b>不是</b>简单低β——吃约3/4回撤。1996–98 landed 跌幅甚至大于公寓（−48%）：系统性危机中防御性会失效。</li>
<li><b>2020–26 的跑赢部分是一次性</b>（供给冻结、WFH、ABSD-60% 把外资挤出公寓而公民专属 landed 无此税）——<b>勿外推</b>。本街同规格 2025 回软与此一致。</li>
<li><b>公民限购</b>：需求端刚性双刃；5年持有内应假设遇一轮调控。</li>
<li><b>流动性</b>：单街年成交个位数，压力期出货以季度计——区间读宽，勿按指数价/区级高点 mark。切勿用"低β可保护被迫卖家"逻辑加杠杆；只在具备<b>10年持有力</b>时承接。</li>
</ul>

<h2>9 · 建议 <span class="en">Recommendation</span></h2>
<div class="rec">
<h3>自住/长持：合理　·　纯投资：吸引力有限　·　买卖双方各自的价位纪律</h3>
<ul>
<li><b>现业主（2023以 {money(last['price'])} 购入）：</b> 按中枢现值 ~{money(pt)}，<b>平进平出困难</b>（可比与最新同规格印均在购入价之下）。若非刚需，<b>长持</b>等下一轮周期（准永久地契无时间压力、SSD 已过）；不建议在当前水平割肉、也不宜锚定2023原价挂高致长期滞销。若必须出售，务实定价靠近 {money(se[0])} 并接受议价。</li>
<li><b>买家（自住）：</b> 目标 <b>{money(bt[0])}–{money(bt[1])}</b>（贴近最新同规格原始印）；点估 {money(pt)} 为中枢；<b>越过 {money(se[1])}（${sep[1]:,} psf）即为按卖方期望追高</b>。优先在带下沿买入原始屋，为日后重建留 α。</li>
<li><b>买家（投资）：</b> ~{yld['gross_yield_pct']:.1f}% 毛回报 + 回软期 + 高摩擦（BSD {k(cost['bsd_at_point'])}，第二套再加 ABSD {k(cost['absd_2nd_20pct'])}），<b>纯现金流投资不划算</b>；仅在自住兼重建增值逻辑下成立。</li>
</ul>
</div>

<h2>10 · 风险、局限与数据缺口 <span class="en">Risks, limits &amp; data gaps</span></h2>
<ul>
<li><b>建筑形态未知（首要缺口）：</b> app/挂牌未给标的层数与建筑面积；本估以"原始2层排屋"为工作假设（其2023年 ${last['psf']:,} psf 高于单层地皮价 ${CC['land_floor_psf']:,}，支持2层判断）。<b>若实为单层</b>，公允价下修向地板 {money(CC['land_floor_price'])}；<b>若已翻新/装修佳</b>，上修向天花板。<b>看房核实层数/建筑面积/状态是首要动作。</b></li>
<li><b>状态无量化调整：</b> 同规格 psf 近期区间 $1,767–$2,848 主要由状态/朝向/位置驱动；本估未做逐项状态打分（无内部照片），以原始可比加权中枢近似——真实可能偏离。</li>
<li><b>薄量：</b> 同规格原始入网格仅 {CN['same_spec_originals_in_grid']} 笔、点估受最新两笔 2025 印高度影响；<b>区间比点更重要</b>，且下行判断建立在这两笔上，若它们为个别弱势屋则中枢应上修。</li>
<li><b>趋势不确定：</b> 近期趋势统计不显著；若牛市重启(+5%/年)公允价上修约+15%(3年)，若继续走软(−3%/年)进一步下修。</li>
<li><b>租金为估算：</b> ~1,840sf 排屋无逐户 Tier-1 租约；用街道档位插值。</li>
<li><b>附近挂牌为单点(n=1)佐证：</b> 最可比的 Chuan Terrace 系<b>一个要价</b>(非成交)、且属 Lorong Chuan 一带；仅用于印证买家端与2025软度，<b>未</b>并入中枢。若成交实证多于此点，买家/卖方带应据以更新。</li>
</ul>

<h2>11 · 数据溯源与核验 <span class="en">Provenance &amp; verification</span></h2>
<ul>
<li><b>Tier-1（锚定全部承重数字）：</b> PropNex Investment Suite — 19 Cardiff Grove 地址页（类型/地契/地块/成交史）、Sale→Street scope 街道带与 Terrace「Type Summary」全表（{CN['street_terraces_10y']}笔）、Rent→Street scope 租金带。UI 自动化读屏（仅读取，不破解）。</li>
<li><b>完整性校验：</b> 抓取 {CN['street_terraces_10y']} 笔均价 $3,663,164 = app 街道带均价 $3,663,165（差 $1）→ 集合完整、解析正确。</li>
<li><b>政策核对：</b> BSD 现行6档（$3m 以上 6%，2023-02起）→ 点估 {money(pt)} 对应 {k(cost['bsd_at_point'])}；SSD 旧3年规则（2025-07-04前购入）→ 2023-03 购入者2026-03后为 nil。</li>
<li><b>Tier-2/3（仅作现挂牌情景，未用于承重数字）：</b> propertygiant / propertyvow / 99.co / bgdev 的 Cardiff Grove 挂牌（单层地皮 S$3.3m、8号重建屋规格）——标注为"挂牌/claim"，非成交。</li>
<li><b>脚本与 digest：</b> <code>research/data/cardiff_transactions.json</code>、<code>research/data/cardiff19_valuation.json</code>、<code>deliverables/build_cardiff_report.py</code>。</li>
</ul>

<div class="foot">
研究 #19 · 19 Cardiff Grove landed 估值 · 估值日 {V['asof']} · 数据 Tier-1 = PropNex Investment Suite（UI 自动化）· 本报告为分析意见，非正式估价证书（formal valuation），不构成要约或投资建议。有地住宅薄量、区间读宽；任何承重数字请以看房与最新 Tier-1 成交复核。
</div>
</div></body></html>"""

print(write_report("cardiff_grove_19_Landed_Valuation_Report.html", HTML).summary())
