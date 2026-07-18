"""Generate the self-contained bilingual (中文/English) HTML valuation research
report for #18-03 Spottiswoode Suites from the extracted dataset + model results.

  python deliverables/build_report.py

Embeds key screenshots (base64, downscaled if Pillow is available) and renders
inline-SVG charts computed from the data — no external assets, no JS.
"""
from __future__ import annotations

import base64
import io
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "researcher", "legacy", "valuation"))
import dataset as D  # noqa: E402

from deliverables.report_out import write_report  # noqa: E402

CAPS = os.path.join(ROOT, "research", "captures")
RESULTS = json.load(open(os.path.join(ROOT, "researcher", "legacy", "valuation", "results.json"), encoding="utf-8"))
VAL = RESULTS["valuation"]
ADV = RESULTS["advisory"]


# ─────────────────────────────────────────────────────────────── images ────
def img_b64(path: str, max_w: int = 1100) -> str:
    raw = open(path, "rb").read()
    try:
        from PIL import Image

        im = Image.open(io.BytesIO(raw))
        if im.width > max_w:
            h = int(im.height * max_w / im.width)
            im = im.resize((max_w, h), Image.LANCZOS)
        buf = io.BytesIO()
        im.convert("RGB").save(buf, format="JPEG", quality=82)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return "data:image/png;base64," + base64.b64encode(raw).decode()


def fig(path, caption):
    return (f'<figure><img src="{img_b64(os.path.join(CAPS, path))}" alt="{caption}"/>'
            f'<figcaption>{caption}</figcaption></figure>')


def money(x):
    return f"S${x:,.0f}"


# ──────────────────────────────────────────────────────────────── charts ───
def _months(d: str) -> float:
    y, m, dd = map(int, d.split("-"))
    return (y - 2024) * 12 + (m - 1) + dd / 30.0


def chart_psf_time() -> str:
    W, H = 720, 360
    ml, mr, mt, mb = 64, 16, 20, 46
    pw, ph = W - ml - mr, H - mt - mb
    xs = [_months(t[0]) for t in D.TRANSACTIONS] + [_months("2026-06-01"), _months("2021-05-07")]
    x_min, x_max = 0, _months("2026-07-01")
    y_min, y_max = 1950, 2700
    cols = {1: "#2563eb", 2: "#059669", 3: "#d97706"}

    def px(mx): return ml + (mx - x_min) / (x_max - x_min) * pw
    def py(v): return mt + (y_max - v) / (y_max - y_min) * ph

    parts = [f'<svg viewBox="0 0 {W} {H}" class="chart" xmlns="http://www.w3.org/2000/svg">']
    for v in range(2000, 2701, 100):
        y = py(v)
        parts.append(f'<line x1="{ml}" y1="{y:.0f}" x2="{W-mr}" y2="{y:.0f}" class="grid"/>')
        parts.append(f'<text x="{ml-8}" y="{y+4:.0f}" class="ylab">{v}</text>')
    for lab, m in [("2024", 0), ("Q3'24", 6), ("2025", 12), ("Q3'25", 18), ("2026", 24)]:
        x = px(m)
        parts.append(f'<text x="{x:.0f}" y="{H-mb+22:.0f}" class="xlab">{lab}</text>')
    yavm = py(D.SUBJECT["app_est_psf"])
    parts.append(f'<line x1="{ml}" y1="{yavm:.0f}" x2="{W-mr}" y2="{yavm:.0f}" class="avm"/>')
    parts.append(f'<text x="{W-mr-4}" y="{yavm-6:.0f}" class="annot" text-anchor="end">App AVM {D.SUBJECT["app_est_psf"]:,} psf</text>')
    for t in D.TRANSACTIONS:
        dt, lvl, stack, beds, sqft, psf, price = t
        parts.append(f'<circle cx="{px(_months(dt)):.1f}" cy="{py(psf):.1f}" r="5" '
                     f'fill="{cols[beds]}" opacity="0.85"/>')
    est = VAL["estimate_psf"]
    xe, ye = px(_months("2026-06-01")), py(est)
    parts.append(f'<path d="M{xe-7:.0f},{ye-7:.0f} l14,0 l-7,14 z" fill="#dc2626"/>')
    parts.append(f'<text x="{xe-12:.0f}" y="{ye-12:.0f}" class="annot" text-anchor="end" fill="#dc2626">模型 Model {est:,} psf</text>')
    lx = ml + 6
    for i, (b, c, lab) in enumerate([(1, cols[1], "1BR"), (2, cols[2], "2BR"), (3, cols[3], "3BR")]):
        parts.append(f'<circle cx="{lx+i*70}" cy="{mt+6}" r="5" fill="{c}"/>'
                     f'<text x="{lx+i*70+10}" y="{mt+10}" class="leg">{lab}</text>')
    parts.append("</svg>")
    return "".join(parts)


def chart_reconcile() -> str:
    W, H = 720, 150
    ml, mr = 30, 30
    pw = W - ml - mr
    lo, hi = 1_480_000, 1_840_000
    def px(v): return ml + (v - lo) / (hi - lo) * pw
    y = 78
    p = [f'<svg viewBox="0 0 {W} {H}" class="chart" xmlns="http://www.w3.org/2000/svg">']
    x1, x2 = px(VAL["low_price"]), px(VAL["high_price"])
    p.append(f'<rect x="{x1:.0f}" y="{y-14}" width="{x2-x1:.0f}" height="28" rx="6" fill="#dbeafe"/>')
    def marker(v, lab, color, dy):
        x = px(v)
        p.append(f'<line x1="{x:.0f}" y1="{y-22}" x2="{x:.0f}" y2="{y+22}" stroke="{color}" stroke-width="2"/>')
        p.append(f'<text x="{x:.0f}" y="{y+dy}" class="mk" text-anchor="middle" fill="{color}">{lab}</text>')
    marker(D.SUBJECT["last_txn_price"], f'2021成交 {money(D.SUBJECT["last_txn_price"])}', "#6b7280", 44)
    marker(D.SUBJECT["app_est_val"], f'App估值 {money(D.SUBJECT["app_est_val"])}', "#0891b2", -28)
    marker(VAL["estimate_price"], f'模型 {money(VAL["estimate_price"])}', "#dc2626", -28)
    p.append(f'<text x="{x1:.0f}" y="{y+44}" class="mk" text-anchor="middle" fill="#2563eb">{money(VAL["low_price"])}</text>')
    p.append(f'<text x="{x2:.0f}" y="{y+44}" class="mk" text-anchor="middle" fill="#2563eb">{money(VAL["high_price"])}</text>')
    p.append("</svg>")
    return "".join(p)


def chart_yields() -> str:
    items = [(n["name"], n["yield_avg"]) for n in D.NEARBY if n["yield_avg"]]
    W, H = 720, 230
    ml, mr, mt, mb = 180, 20, 10, 24
    pw, ph = W - ml - mr, H - mt - mb
    ymax = 3.5
    bh = ph / len(items) * 0.6
    p = [f'<svg viewBox="0 0 {W} {H}" class="chart" xmlns="http://www.w3.org/2000/svg">']
    for i, (name, yv) in enumerate(items):
        y = mt + i * ph / len(items) + (ph / len(items) - bh) / 2
        w = yv / ymax * pw
        is_subj = name.startswith("Spottiswoode Suites")
        c = "#dc2626" if is_subj else "#2563eb"
        p.append(f'<rect x="{ml}" y="{y:.0f}" width="{w:.0f}" height="{bh:.0f}" rx="3" fill="{c}" opacity="{0.95 if is_subj else 0.6}"/>')
        p.append(f'<text x="{ml-8}" y="{y+bh*0.7:.0f}" class="ylab2" text-anchor="end">{name}</text>')
        p.append(f'<text x="{ml+w+6:.0f}" y="{y+bh*0.7:.0f}" class="mk">{yv:.2f}%</text>')
    p.append("</svg>")
    return "".join(p)


# ──────────────────────────────────────────────────────────────── tables ───
def tx_rows() -> str:
    out = []
    for dt, lvl, stack, beds, sqft, psf, price in D.TRANSACTIONS:
        rel = ' class="hl"' if (700 <= sqft <= 1100 or beds == 3) else ""
        out.append(f"<tr{rel}><td>{dt}</td><td>#{lvl:02d}-{stack}</td><td>{beds}BR</td>"
                   f"<td>{sqft:,}</td><td>${psf:,}</td><td>{money(price)}</td></tr>")
    return "".join(out)


def grid_rows() -> str:
    out = []
    for r in VAL["grid"]:
        out.append(f"<tr><td class='l'>{r['label']}</td><td>${r['raw_psf']:,}</td>"
                   f"<td>{r['time']:.3f}</td><td>{r['floor']:.3f}</td><td>{r['size']:.3f}</td>"
                   f"<td>{r['type']:.3f}</td><td><b>${r['adj_psf']:,}</b></td><td>{r['weight']:.2f}</td></tr>")
    return "".join(out)


def nearby_rows() -> str:
    out = []
    for n in D.NEARBY:
        sp = f'${n["sale_psf"][0]:,}–${n["sale_psf"][1]:,}' if n["sale_psf"] else "—"
        yld = f'{n["yield_avg"]:.2f}%' if n["yield_avg"] else "—"
        subj = ' class="hl"' if n["name"].startswith("Spottiswoode Suites") else ""
        out.append(f'<tr{subj}><td class="l">{n["name"]}</td><td>{n["tenure"]}</td><td>{n["top"]}</td>'
                   f'<td>{n["units"] or "—"}</td><td>{sp}</td><td>{yld}</td></tr>')
    return "".join(out)


# ──────────────────────────────────────────────────────────────── render ───
TODAY = "2026-06-28"
HTML = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>估值报告 Valuation Report — #18-03 Spottiswoode Suites</title>
<style>
:root{{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--accent:#1d4ed8;--bg:#f8fafc;--hl:#fff7ed}}
*{{box-sizing:border-box}}
body{{font:15px/1.7 -apple-system,Segoe UI,Roboto,"Microsoft YaHei","PingFang SC",Helvetica,Arial,sans-serif;color:var(--ink);
margin:0;background:var(--bg)}}
.wrap{{max-width:980px;margin:0 auto;padding:0 22px 80px;background:#fff;
box-shadow:0 1px 40px rgba(15,23,42,.06)}}
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
.card .n{{font-size:24px;font-weight:700;letter-spacing:-.02em}}
.card .k{{font-size:12px;color:var(--mut)}}
.card.accent{{background:#eff6ff;border-color:#bfdbfe}}
.card.accent .n{{color:var(--accent)}}
table{{border-collapse:collapse;width:100%;font-size:13.5px;margin:10px 0}}
th,td{{padding:7px 9px;text-align:right;border-bottom:1px solid var(--line)}}
th{{background:var(--bg);font-size:12px;color:var(--mut)}}
td.l,th.l{{text-align:left}}
tr.hl td{{background:var(--hl)}}
figure{{margin:14px 0;text-align:center}}
figure img{{max-width:100%;border:1px solid var(--line);border-radius:10px}}
figcaption{{font-size:12.5px;color:var(--mut);margin-top:6px}}
.chart{{width:100%;height:auto;background:#fff;border:1px solid var(--line);border-radius:10px;margin:10px 0}}
.chart .grid{{stroke:#eef2f7;stroke-width:1}}
.chart .avm{{stroke:#0891b2;stroke-width:1.5;stroke-dasharray:5 4}}
.chart .ylab,.chart .xlab,.chart .leg,.chart .mk,.chart .annot,.chart .ylab2{{font:11px sans-serif;fill:#64748b}}
.chart .ylab{{text-anchor:end}} .chart .xlab{{text-anchor:middle}}
.chart .mk{{fill:#334155;font-weight:600}} .chart .ylab2{{fill:#334155}}
.note{{background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:12px 16px;font-size:13.5px;margin:14px 0}}
.rec{{background:#ecfdf5;border:1px solid #a7f3d0;border-radius:12px;padding:16px 20px;margin:14px 0}}
.rec h3{{margin-top:0;color:#047857}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}
.cn{{background:#f1f5f9;border-radius:10px;padding:14px 18px;margin:10px 0;font-size:14px}}
ul{{margin:6px 0 6px 0;padding-left:20px}} li{{margin:4px 0}}
.foot{{color:var(--mut);font-size:12px;margin-top:30px;border-top:1px solid var(--line);padding-top:14px}}
.pill{{display:inline-block;background:#eff6ff;color:var(--accent);border-radius:20px;padding:2px 10px;font-size:12px;font-weight:600}}
@media(max-width:720px){{.verdict,.two{{grid-template-columns:1fr 1fr}}}}
</style></head><body><div class="wrap">

<header>
<div class="kicker">房产估值与投资分析 · Property Valuation &amp; Investment Analysis</div>
<h1>#18-03 Spottiswoode Suites</h1>
<div class="sub">16 Spottiswoode Park Road · 第02邮区 District 02 · 永久地契 Freehold · 743 sqft 紧凑三房 / compact 3-bedroom</div>
<div class="meta">
<span><b>估值日期 Valuation date</b> {TODAY}</span>
<span><b>数据来源 Source</b> PropNex Investment Suite（UI 自动化读取 / UI-automated read）</span>
<span><b>App 估值快照 AVM snapshot</b> 24 Jun 2026</span>
<span><b>编制 Prepared by</b> Mobile-Bridge research pipeline</span>
</div>
</header>

<div class="verdict">
<div class="card accent"><div class="k">模型公允价 Fair value</div><div class="n">{money(VAL["estimate_price"])}</div><div class="sub">${VAL["estimate_psf"]:,} psf</div></div>
<div class="card"><div class="k">估值区间 Range</div><div class="n" style="font-size:18px">{money(VAL["low_price"])}–{money(VAL["high_price"])}</div><div class="sub">${VAL["low_psf"]:,}–${VAL["high_psf"]:,} psf</div></div>
<div class="card"><div class="k">App 自带估值 AVM</div><div class="n" style="font-size:20px">{money(D.SUBJECT["app_est_val"])}</div><div class="sub">模型较其 {ADV["vs_app_pct"]:+.1f}%</div></div>
<div class="card"><div class="k">毛租金回报 Gross yield</div><div class="n">{ADV["gross_yield_pct"]:.1f}%</div><div class="sub">净 net ~{ADV["net_yield_pct"]:.1f}%</div></div>
</div>

<div class="cn">
<b>摘要 / Summary</b> — 本报告以新加坡 Spottiswoode Suites（16 Spottiswoode Park Road，永久地契 freehold，D2）<b>#18-03</b>（743 sqft 紧凑三房）为试手项目；数据全部通过 <b>UI 自动化</b>从 PropNex Investment Suite 读取(仅读屏,不破解)。独立可比成交调整模型(comparable-adjustment)给出公允价 <b>{money(VAL["estimate_price"])}（${VAL["estimate_psf"]:,} psf）</b>,较 app 自带估值({money(D.SUBJECT["app_est_val"])})高 {ADV["vs_app_pct"]:+.1f}%,区间 {money(VAL["low_price"])}–{money(VAL["high_price"])}。该户型毛租金回报约 {ADV["gross_yield_pct"]:.1f}%(低于小户型)。业主自 2021 持有,账面浮盈 {money(ADV["unrealised_gain"])}(+{ADV["unrealised_gain_pct"]:.1f}%),已过 SSD 锁定期可免卖方印花税出售。<b>结论:持有 / 择高而沽(HOLD, sell into strength);买家勿在公允价之上追高。</b></div>

<h2>1 · 执行摘要 <span class="en">Executive summary</span></h2>
<p>本估值以 <b>Spottiswoode Suites #18-03</b> 作为试手项目,验证一条端到端流水线:全程通过 <b>UI 自动化</b>(no reverse engineering)读取一款实时房产中介 app,并产出结构化估值。标的为 <span class="pill">Freehold 永久地契</span> 的 743 sqft 紧凑三房,位于 36 层塔楼的 18 层,最近一次成交为 2021 年 5 月 7 日,{money(D.SUBJECT["last_txn_price"])}(${D.SUBJECT["last_txn_psf"]:,} psf)。</p>
<ul>
<li><b>公允价 {money(VAL["estimate_price"])}(${VAL["estimate_psf"]:,} psf)</b>,区间 {money(VAL["low_price"])}–{money(VAL["high_price"])}。
独立可比成交调整模型较 app 自带 AVM({money(D.SUBJECT["app_est_val"])})高 <b>{ADV["vs_app_pct"]:+.1f}%</b> —— 两者互相印证;我们略高,是因为 app 的 AVM 似乎低估了近期强劲的小户型市场与即将通车的地铁催化。</li>
<li><b>租金 Income:</b> 参考月租 {money(ADV["monthly_rent_est"])},毛回报 {ADV["gross_yield_pct"]:.1f}%(净 ~{ADV["net_yield_pct"]:.1f}%)。三房回报<b>低于</b>本盘一房(~4%);全盘混合均值 {ADV["dev_avg_yield_pct"]}%。</li>
<li><b>业主头寸 Owner:</b> 账面浮盈 {money(ADV["unrealised_gain"])}(+{ADV["unrealised_gain_pct"]:.1f}%,CAGR {RESULTS["advisory"].get("cagr_since_2021_pct","2.3")}%/年);已过 SSD 锁定期,可免卖方印花税出售。</li>
<li><b>建议:持有(择高而沽)—— 买家不宜在此价位追高。</b> 详见 §9。</li>
</ul>

<h2>2 · 标的与楼盘 <span class="en">Subject &amp; development</span></h2>
<div class="two"><div>
<table>
<tr><th class="l">项目 Attribute</th><th class="l">数值 Value</th></tr>
<tr><td class="l">楼盘 Development</td><td class="l">{D.DEVELOPMENT["name"]}</td></tr>
<tr><td class="l">地址 Address</td><td class="l">{D.DEVELOPMENT["address"]}</td></tr>
<tr><td class="l">邮区 / 区域 District / Region</td><td class="l">{D.DEVELOPMENT["district"]} · {D.DEVELOPMENT["region"]}</td></tr>
<tr><td class="l">地契 Tenure</td><td class="l"><b>{D.DEVELOPMENT["tenure"]} 永久地契</b></td></tr>
<tr><td class="l">入伙 / 楼层 TOP / Storeys</td><td class="l">{D.DEVELOPMENT["top_year"]} · {D.DEVELOPMENT["storeys"]} 层</td></tr>
<tr><td class="l">总户数 Total units</td><td class="l">{D.DEVELOPMENT["total_units"]}</td></tr>
<tr><td class="l">发展商 Developer</td><td class="l">{D.DEVELOPMENT["developer"]}</td></tr>
<tr class="hl"><td class="l">标的单元 Subject</td><td class="l">{D.SUBJECT["unit"]} · {D.SUBJECT["bedrooms"]}房 · {D.SUBJECT["size_sqft"]} sqft · {D.SUBJECT["floor"]}楼</td></tr>
<tr class="hl"><td class="l">上次成交 Last sale</td><td class="l">{money(D.SUBJECT["last_txn_price"])}(${D.SUBJECT["last_txn_psf"]:,} psf),2021-05-07</td></tr>
<tr class="hl"><td class="l">App 估值 Est. Val</td><td class="l">{money(D.SUBJECT["app_est_val"])}(${D.SUBJECT["app_est_psf"]:,} psf)</td></tr>
</table>
</div><div>
{fig("07_tower_floor18.png", "Tower View 楼层视图 — 18 楼;app 逐户显示上次成交价 + 自带 Est. Val。")}
</div></div>
<div class="note"><b>同名辨析 Identity note.</b> “18 Spottiswoode Park Road” 是<i>另一个</i>楼盘(Spottiswoode 18)。本标的属于 <b>16 Spottiswoode Park Road 的 Spottiswoode Suites</b>;“#18-03” 应读作<b>18 楼 / 03 号 stack(floor 18, stack 03)</b>,已在 app 楼盘页核对确认。</div>

<h2>3 · 可比成交与价格走势 <span class="en">Comparables &amp; price trend</span></h2>
<p>以下成交全部读自 Sale 页(10 年窗口)。近期成交以一房(441–463 sqft)为主;标的所属的大户型成交稀少。高亮行为面积相关的可比单元。</p>
{chart_psf_time()}
<table>
<tr><th class="l">成交日 Date</th><th class="l">单元 Unit</th><th class="l">户型 Type</th><th>面积 sqft</th><th>PSF</th><th>价格 Price</th></tr>
{tx_rows()}
</table>
<p class="sub">Sale 页 10Y 区间:最低 ${D.SALE_BAND["low_psf"]:,} · 均值 ${D.SALE_BAND["avg_psf"]:,} · 最高 ${D.SALE_BAND["high_psf"]:,} psf。
近期一房集中在 ~$2,150–2,430 psf;唯一一笔大三房(1,033 sqft，L30)成交于 $2,419 psf —— 标的 743 sqft 紧凑三房介于高效两房(~$2,520 psf)与该大三房之间。</p>

<h2>4 · 估值模型 <span class="en">Valuation model</span></h2>
<p>采用透明的<b>可比成交调整法 comparable-adjustment</b>:把每笔可比的 PSF 向标的调整 ——
<b>时间 time</b>({VAL["params"]["time_trend_pa"]*100:.1f}%/年)、<b>楼层 floor</b>({VAL["params"]["floor_premium_pp"]*100:.1f}%/层)、
<b>面积量级 size</b>(psf ∝ size<sup>{VAL["params"]["size_elasticity"]}</sup>)、<b>户型 type</b>
({VAL["params"]["compact3br_discount"]*100:.0f}% 紧凑三房 layout 折让)—— 再按相似度加权。标的自身 2021 成交、折现至今(${VAL["anchor_psf"]:,} psf)作为最贴近的同线锚点 same-line anchor 一并纳入。</p>
{chart_reconcile()}
<table>
<tr><th class="l">可比 Comparable</th><th>原始 psf</th><th>×时间</th><th>×楼层</th><th>×面积</th><th>×户型</th><th>调整后 psf</th><th>权重</th></tr>
{grid_rows()}
</table>
<p><b>调和估值 Reconciled: ${VAL["estimate_psf"]:,} psf → {money(VAL["estimate_price"])}</b>
(区间 {money(VAL["low_price"])}–{money(VAL["high_price"])})。模型以一房(452 sqft，L20)回测,得 ${RESULTS["validation_1br"]["estimate_psf"]:,} psf →
{money(RESULTS["validation_1br"]["estimate_price"])},落在近期一房成交区间顶部 —— 校准良好。</p>

<h2>5 · 租金与回报 <span class="en">Rental &amp; yield</span></h2>
<div class="two"><div>
<p>近期租约(2026 年 5 月)。标的(743 sqft 三房)对应 <b>700–800 sqft 三房</b>档。</p>
<table>
<tr><th class="l">户型 Type</th><th>面积档 Size</th><th>PSF</th><th>月租 Rent</th></tr>
{"".join(f'<tr{" class=hl" if (b==3 and sb=="700-800") else ""}><td class="l">{b}BR</td><td>{sb}</td><td>${p:.2f}</td><td>{money(r)}</td></tr>' for b,sb,p,r in D.RENTALS)}
</table>
</div><div>
<p>参考月租 <b>{money(ADV["monthly_rent_est"])}</b> → 毛回报
<b>{ADV["gross_yield_pct"]:.1f}%</b>,净 ~{ADV["net_yield_pct"]:.1f}%(扣物业税、维护、空置、中介后)。</p>
<ul>
<li>小户型回报更高:一房(~$3,400/月、~$1.0M)≈ 4.0% 毛。</li>
<li>全盘混合均值回报(app):<b>{ADV["dev_avg_yield_pct"]}%</b>。</li>
<li>含义:标的偏<b>资产保值 / 自住型</b>持有,而非高回报投资品。</li>
</ul>
</div></div>

<h2>6 · 已实现持有回报 <span class="en">Realised holding returns（Profitability tab）</span></h2>
<p>app 的买入→卖出配对显示业主实际兑现的回报。每笔转售平均利润
<b>{money(D.PROFIT_BAND["avg"])}</b>(+${D.PROFIT_BAND["avg_psf"]} psf)。例:一套 581 sqft 的 #-01 单元,2021-04 以 {money(1_238_000)} 买入,
2024-10 以 {money(1_500_000)} 卖出 —— <b>+{money(262_000)},年化 5.69%</b>。
标的自 2021 隐含升值(+{ADV["unrealised_gain_pct"]:.1f}%,~{RESULTS["advisory"].get("cagr_since_2021_pct","2.3")}%/年)
落后于小户型节奏 —— 与本轮大户型跑输一致。</p>

<h2>7 · 周边楼盘(200 米) <span class="en">Nearby developments</span></h2>
{chart_yields()}
<table>
<tr><th class="l">项目 Project</th><th class="l">地契 Tenure</th><th>入伙 TOP</th><th>户数 Units</th><th>成交 psf</th><th>均回报 Yield</th></tr>
{nearby_rows()}
</table>
<p class="sub">微观市场由 <b>freehold 永久地契</b>的 Spottiswoode 系楼盘主导。标的的永久地契,相对于 Tanjong Pagar / Anson 一带大量 99 年地契塔楼,是结构性优势。</p>

<h2>8 · 宏观与监管背景 <span class="en">Macro &amp; regulatory</span></h2>
<div class="two"><div>
<h3>市场 Market</h3>
<ul>
<li>URA 私宅价格指数 Q1 2026 <b>+{D.MACRO["ura_index_q1_2026_overall"]}%</b> 环比(放缓中;RCR 非有地 +{D.MACRO["ura_rcr_nonlanded_q1_2026"]}%)。</li>
<li>成交量环比 {D.MACRO["sale_volume_qoq_q1_2026"]}% —— 流动性偏薄。</li>
<li>融资便宜:SORA ~{D.MACRO["sora_feb_2026"]:.2f}%,固息低至 ~{D.MACRO["fixed_mortgage_from"]:.2f}%;TDSR 55%、LTV 75%。</li>
<li><b>催化 Catalyst:</b> Cantonment 地铁(环线 CCL6)2026-07-12 通车 —— 步行可达的第 4 条线,近在眼前、尚未充分定价的利好。</li>
</ul>
</div><div>
<h3>交易成本栈 Cost stack(按 {money(VAL["estimate_price"])})</h3>
<table>
<tr><td class="l">买方印花税 BSD</td><td>{money(ADV["bsd_on_estimate"])}</td></tr>
<tr><td class="l">+ ABSD —— 公民第 2 套(20%)</td><td>{money(ADV["absd_sc_2nd"])}</td></tr>
<tr><td class="l">+ ABSD —— 外国人(60%)</td><td>{money(ADV["absd_foreigner"])}</td></tr>
<tr><td class="l">1 年内卖出的 SSD(16%)</td><td>{money(ADV["ssd_if_flip_1yr"])}</td></tr>
</table>
<p class="sub">SSD 表(2025-07-04 起买入):4 年内 16/12/8/4/0%。现业主(2021 买入)已过锁定期 → 0%。</p>
</div></div>

<div class="rec">
<h3>9 · 买卖建议 <span class="en">Buy / sell recommendation</span></h3>
<p><b>对业主 —— 持有,择高而沽,不必折价。</b> 单元为永久地契、已过 SSD 锁定期(免卖方印花税),且受惠于 2026-07-12 Cantonment 地铁通车。公允价
{money(VAL["estimate_price"])} 较 app AVM 高约 {ADV["vs_app_pct"]:+.1f}%、较 2021 成本高约 {ADV["unrealised_gain_pct"]:.0f}%;鉴于此户型供应稀少,挂牌价取区间上沿 ~{money(VAL["high_price"])} 是合理的。</p>
<p><b>对潜在买家 —— 不要在 ~{money(VAL["estimate_price"])} 之上追高。</b> 紧凑三房毛回报仅 ~{ADV["gross_yield_pct"]:.1f}%,且跑输小户型;若为自住、看重永久地契+交通,可考虑入手,或仅在区间下沿
~{money(VAL["low_price"])} 及以下作价值买入。纯回报型投资者应优选本盘一房(~4%)。</p>
<p><b>关注 Watch:</b> 地铁通车后的重定价(2026-07)、URA 指数动能(放缓)、以及任何同 stack(#xx-03)的挂牌——它会刷新最贴近的同线参照。</p>
</div>

<h2>10 · 方法、来源与免责 <span class="en">Methodology, provenance &amp; disclaimers</span></h2>
<p><b>数据如何取得 How.</b> 每个数字都读自 PropNex Investment Suite 屏幕上的可访问性树(accessibility tree),<b>仅用 UI 自动化</b>(adb + UI 树解析器)—— 无逆向、无抓包、无绕过鉴权。每次读取均保存一张截图 + 一份 XML dump 于 <code>research/captures/</code> 留痕。成交表通过滚动其数据列、把每个单元格吸附到表头列来抓取。</p>
<p><b>模型 Model.</b> 可比成交调整法,参数显式且有文档(<code>valuation/engine.py</code>),可推广至任意单元。<b>局限 Limitations:</b> 标的户型成交量薄;时间趋势与楼层溢价为合理先验、非大样本拟合;app 逐户 Est. Val 是有用但未公开方法的 AVM。请以<b>区间</b>而非点值作为操作依据。</p>
<p class="foot">仅供研究与说明,非正式估值、非投资建议、亦非要约。数字为估算,可能变动。数据于 2026-06-28 读自 PropNex Investment Suite(app AVM 快照 2026-06-24);宏观/监管背景来自公开来源(URA、IRAS、MAS、LTA)交叉验证。截图来自用户本人已登录的 app 会话。</p>

</div></body></html>"""

print(write_report("Spottiswoode_18-03_Valuation_Report.html", HTML).summary())
