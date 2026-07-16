"""Render a Singapore landed per-property DD report (HTML) — summary first, then dimensions.

  python -m researcher.landed.dd "14 SELETAR GREEN WALK" --road "SELETAR GREEN WALK" \
      --slug seletar_green_walk_14          # 1. machine facts  -> <slug>_dd_raw.json
  python deliverables/build_landed_dd_report.py seletar_green_walk_14   # 2. render

TWO INPUTS, ON PURPOSE:
  researcher/landed/<slug>_dd_raw.json   FACTS, produced by the tool chain. Never hand-edited.
  researcher/landed/<slug>_dd.json       JUDGEMENT: archetype, verdict, deep-DD alerts, claims.

The split is the point. Facts are reproducible by re-running the chain; judgement is the
agent's and must be argued. Hand-editing the raw file would destroy the only property that
makes it worth trusting. If a raw number looks wrong, fix the TOOL, re-run, and say so.

Writes a self-contained bilingual HTML file (no JS, no external assets) to
G:\\My Drive\\004 RES\\REsearch_Reports (override with RESEARCH_REPORTS_DIR; falls back to
deliverables/).

The deep-DD alert section is STRUCTURAL: an empty alert list renders as a contract breach, not
a clean bill of health. A landed DD that escalates nothing did not look.
"""
from __future__ import annotations

import html
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from deliverables import charts  # noqa: E402


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def sev_class(s) -> str:
    s = (s or "").lower()
    return "sev-red" if s in ("high", "red") else \
           "sev-amber" if s in ("medium", "med", "amber") else "sev-low"


def when_class(w) -> str:
    w = (w or "").upper()
    return "w-hard" if ("OTP" in w or "PRE-OFFER" in w or "BEFORE" in w) else \
           "w-soft" if "PRICED" in w else "w-mid"


CSS = """
:root{--ink:#16202b;--mut:#6b7a8c;--line:#e2e8f0;--bg:#fff;--red:#c0392b;--amber:#b7791f;
--grn:#2f6f4f;--blue:#4a6fa5;--chip:#f1f5f9}
*{box-sizing:border-box}
body{margin:0;background:#f6f8fa;color:var(--ink);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans CJK SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding:26px 20px 70px}
h1{font-size:26px;margin:0 0 3px}
h2{font-size:17px;margin:36px 0 10px;padding-bottom:7px;border-bottom:2px solid var(--ink)}
h3{font-size:13.5px;margin:18px 0 7px;color:#3d4a5c;letter-spacing:.03em;text-transform:uppercase}
.sub{color:var(--mut);font-size:13px;margin-bottom:14px}
.card{background:var(--bg);border:1px solid var(--line);border-radius:9px;padding:15px 17px;margin:11px 0}
.verdict{border-left:5px solid var(--grn);background:#f4fbf7}
.blocked{border-left:5px solid var(--red);background:#fdf4f3}
.arch{border-left:5px solid var(--blue);background:#f4f7fc}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));gap:10px;margin:14px 0}
.kpi{background:var(--bg);border:1px solid var(--line);border-radius:9px;padding:11px 13px}
.kpi .k{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--mut)}
.kpi .v{font-size:20px;font-weight:700;margin:3px 0 1px;font-variant-numeric:tabular-nums}
.kpi .n{font-size:11px;color:var(--mut)}
.kpi.hi{border-left:4px solid var(--grn)}
.kpi.warn{border-left:4px solid var(--amber)}
.kpi.bad{border-left:4px solid var(--red)}
.hl{margin:0;padding-left:19px}
.hl li{margin:7px 0}
.hl b{color:var(--ink)}
table{width:100%;border-collapse:collapse;background:var(--bg);border:1px solid var(--line);
border-radius:9px;overflow:hidden;font-size:13.5px}
th{background:#eef2f6;text-align:left;padding:8px 11px;font-size:11px;letter-spacing:.06em;
text-transform:uppercase;color:#48566a}
td{padding:8px 11px;border-top:1px solid var(--line);vertical-align:top}
td.l{text-align:left}td.c{text-align:center;white-space:nowrap}
td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.zh{color:var(--mut);font-size:12.5px;margin-top:3px}
.src{font-size:11px;color:var(--mut);max-width:230px}
.why{margin-top:6px;padding-left:9px;border-left:2px solid var(--line);font-size:12.5px;color:#4a5768}
.pill{display:inline-block;padding:1px 7px;border-radius:9px;font-size:10.5px;font-weight:700;
text-transform:uppercase;margin-left:6px;letter-spacing:.04em}
.sev-red>td:first-child{box-shadow:inset 3px 0 0 var(--red)}
.sev-amber>td:first-child{box-shadow:inset 3px 0 0 var(--amber)}
.pill.sev-red{background:#fdecea;color:var(--red)}
.pill.sev-amber{background:#fdf3e2;color:var(--amber)}
.pill.sev-low{background:#eaf5ef;color:var(--grn)}
.pill.gate{background:#2b2b2b;color:#fff}
.pill.w-hard{background:#fdecea;color:var(--red)}
.pill.w-mid{background:#fdf3e2;color:var(--amber)}
.pill.w-soft{background:var(--chip);color:#48566a}
.defect{display:inline-block;margin-left:8px;padding:1px 6px;border-radius:4px;background:var(--red);
color:#fff;font-size:10px;font-weight:700}
svg{display:block;max-width:100%;height:auto;margin:8px 0}
.scroll{overflow-x:auto}
.foot{margin-top:34px;color:var(--mut);font-size:11.5px;border-top:1px solid var(--line);padding-top:12px}
code{background:var(--chip);padding:1px 4px;border-radius:3px;font-size:11.5px}
ul{margin:6px 0;padding-left:19px}li{margin:3px 0}
"""


# ------------------------------------------------------------------ small builders
def kpi(k, v, n="", cls="") -> str:
    return (f'<div class="kpi {cls}"><div class="k">{esc(k)}</div>'
            f'<div class="v">{esc(v)}</div><div class="n">{esc(n)}</div></div>')


def dd1_rows(items) -> str:
    out = []
    for it in items or []:
        missing = [k for k in ("value", "source", "date") if not it.get(k)]
        flag = (f"<span class='defect'>MISSING {', '.join(missing).upper()}</span>"
                if missing else "")
        sev = it.get("severity")
        badge = f"<span class='pill {sev_class(sev)}'>{esc(sev)}</span>" if sev else ""
        out.append(f"<tr class='{sev_class(sev) if sev else ''}'>"
                   f"<td class='l'><b>{esc(it.get('item'))}</b>{badge}"
                   f"<div class='zh'>{esc(it.get('item_zh'))}</div></td>"
                   f"<td class='l'>{esc(it.get('value'))}{flag}"
                   f"<div class='zh'>{esc(it.get('value_zh'))}</div></td>"
                   f"<td class='l src'>{esc(it.get('source'))}"
                   f"<div>{esc(it.get('date'))}</div></td></tr>")
    return "".join(out)


def alert_rows(items) -> str:
    out = []
    for a in items or []:
        gate = ("<span class='pill gate'>SELLER-GATED 需卖方授权</span>"
                if a.get("seller_gated") else "")
        note = (f"<div class='why'>{esc(a.get('note'))}"
                f"<div class='zh'>{esc(a.get('note_zh'))}</div></div>") if a.get("note") else ""
        out.append(f"<tr class='{sev_class(a.get('severity'))}'>"
                   f"<td class='l'><b>{esc(a.get('item'))}</b>{gate}"
                   f"<div class='zh'>{esc(a.get('item_zh'))}</div></td>"
                   f"<td class='l'>{esc(a.get('why'))}"
                   f"<div class='zh'>{esc(a.get('why_zh'))}</div>{note}</td>"
                   f"<td class='l'>{esc(a.get('who'))}<div class='zh'>{esc(a.get('who_zh'))}</div></td>"
                   f"<td class='c'>{esc(a.get('cost'))}</td>"
                   f"<td class='c'><span class='pill {when_class(a.get('when'))}'>"
                   f"{esc(a.get('when'))}</span><div class='zh'>{esc(a.get('when_zh'))}</div></td></tr>")
    return "".join(out)


def render(raw: dict, cur: dict, slug: str) -> str:
    g = raw["geocode"]
    plot = raw.get("plot") or {}
    z = raw.get("zoning") or {}
    lh = raw.get("landed_housing_area") or {}
    c = raw.get("comps") or {}
    sub = (c.get("subject") or {}) if c else {}
    flood = raw.get("flood") or {}
    v = cur.get("verdict") or {}
    alerts = cur.get("dd3_alerts") or []
    tax = cur.get("tax_clock") or {}
    gated = sum(1 for a in alerts if a.get("seller_gated"))
    tr = c.get("trend") or []

    # KPI strip — the numbers a reader wants before any prose
    ks = []
    if plot.get("area_sqft"):
        ks.append(kpi("Plot 地块", f"{plot['area_sqft']:,} sqft",
                      f"{plot['area_sqm']:,.0f} sqm · MP2025 parcel", "hi"))
    if lh.get("envelope"):
        ks.append(kpi("Landed control 管制", esc(lh.get("type", "")),
                      esc(lh.get("envelope", ""))))
    if c.get("tenure", {}).get("distinct"):
        t = list(c["tenure"]["distinct"])[0]
        ks.append(kpi("Tenure 地契", "999 yrs" if "999" in t else t[:14],
                      f"n={c['n']} caveats, unanimous" if c["tenure"]["unanimous"] else "MIXED",
                      "hi" if c["tenure"]["unanimous"] else "warn"))
    if sub.get("n"):
        ks.append(kpi("Cohort land psf 同尺寸单价", f"${sub['psf_med']:,}",
                      f"median · n={sub['n']} @ {sub['area_sqft']:,.0f} sqft ±{sub['tol']:.0%}", "hi"))
    if tr:
        first, last = tr[0], tr[-1]
        chg = (last["psf_med"] / first["psf_med"] - 1) * 100
        ks.append(kpi(f"psf {first['period']}→{last['period']}", f"{chg:+.0f}%",
                      f"${first['psf_med']:,} → ${last['psf_med']:,}", "hi" if chg > 0 else "bad"))
    ks.append(kpi("Deep-DD alerts 预警", str(len(alerts)),
                  f"{gated} seller-gated 需卖方授权", "bad" if gated else "warn"))

    # dimension: comps
    comps_rows = "".join(
        f"<tr><td class='c'>{esc(b['band'])}</td><td class='n'>{b['n']}</td>"
        f"<td class='n'>${b['psf_min']:,}</td><td class='n'><b>${b['psf_med']:,}</b></td>"
        f"<td class='n'>${b['psf_max']:,}</td><td class='n'>${b['price_med']:,}</td>"
        f"<td class='n'>{b['area_med']:,}</td></tr>" for b in (c.get("cohorts") or []))
    recent_rows = "".join(
        f"<tr><td class='c'>{esc(r['ym'])}</td><td class='n'>${r['price']:,.0f}</td>"
        f"<td class='n'>{r['area_sqft']:,}</td><td class='n'><b>${r['psf']:,}</b></td>"
        f"<td class='l'>{esc(r['type'])}</td></tr>" for r in reversed(sub.get("recent") or []))

    nb_rows = "".join(
        f"<tr><td class='l'>{esc(n['zone'])}</td><td class='c'>{esc(n['gpr'])}</td>"
        f"<td class='n'>{n['metres']:,}</td><td class='n'>{n['bearing_deg']}&#176;</td>"
        f"<td class='n'>{float(n['area_sqm']):,.0f}</td></tr>"
        for n in (raw.get("neighbours") or []) if n["metres"] <= 420 and n.get("area_sqm"))

    def dist_rows(key):
        return "".join(
            f"<tr><td class='l'>{esc(r['name'].title())}</td><td class='n'>{r['km']:.2f}</td>"
            f"<td class='c'>{'<b>within 1km</b>' if r['km']<=1.0 else ('1–2km' if r['km']<=2.0 else '')}</td>"
            f"<td class='l src'>{esc(r['matched'])}</td></tr>" for r in (raw.get(key) or []))

    alert_body = alert_rows(alerts) if alerts else (
        "<tr><td colspan='5' class='l'><span class='defect'>CONTRACT BREACH</span> "
        "No deep-DD alerts recorded. A landed DD that escalates nothing did not look — "
        "this is a defect in the digest, not a clean result.</td></tr>")

    transect_svgs = "".join(charts.transect(t) for t in (raw.get("transects") or [])
                            if t.get("edge_m", 999) <= 260)

    return f"""<!doctype html><html lang="en"><meta charset="utf-8">
<title>DD Report — {esc(raw['address'])}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}</style>
<div class="wrap">

<h1>DD Report · {esc(raw['address'])}</h1>
<div class="sub">{esc(cur.get('address_zh'))} · Singapore {esc(g['postal'])} ·
{g['lat']:.6f}, {g['lon']:.6f} · data as of {esc(raw['as_of'])} ·
rendered {date.today().isoformat()}</div>

<h2>摘要 Summary</h2>
<div class="kpis">{''.join(ks)}</div>

<div class="card verdict">
<b>Verdict 结论 · {esc(v.get('call'))}</b>
<div class="zh">{esc(v.get('call_zh'))}</div>
<div class="why">{esc(v.get('detail'))}<div class="zh">{esc(v.get('detail_zh'))}</div></div>
</div>

<div class="card">
<h3>Highlights 重点</h3>
<ul class="hl">{''.join(f"<li>{h}</li>" for h in cur.get('highlights') or [])}</ul>
</div>

<div class="card arch">
<b>Archetype 资产类型 · {esc(cur.get('archetype'))}</b>
<div class="zh">{esc(cur.get('archetype_zh'))}</div>
<div class="why">{esc(cur.get('archetype_note'))}
<div class="zh">{esc(cur.get('archetype_note_zh'))}</div></div>
</div>

<div class="card tiers" style="font-size:12.5px;color:#4a5768">
<b>It is all DD 全部都是 DD</b> — tiers are about <b>who settles it and when</b>, not free vs paid.
<b>DD-1</b> you, desk, free, every candidate · <b>DD-2</b> you, desk, ~S$5–200, before offering ·
<b>DD-3</b> professional / on-site / <b>seller-gated</b>, OTP-conditioned.
<div class="zh">三层依据是「谁能定、何时定」，不是「免费还是收费」。DD-1 本人桌面免费、每个候选都做；
DD-2 本人桌面、约 S$5–200、出价前完成；DD-3 专业/实地/<b>需卖方授权</b>，与 OTP 挂钩。</div>
</div>

<h2>1 · 地块与规划 Plot &amp; planning</h2>
<div class="kpis">
{kpi("Plot area 地块面积", f"{plot.get('area_sqft', 0):,} sqft", f"{plot.get('area_sqm', 0):,.1f} sqm")}
{kpi("Zone 分区", esc(z.get('zone')), f"GPR {esc(z.get('gpr'))}")}
{kpi("Landed type 类型", esc(lh.get('type')), esc(lh.get('envelope')))}
</div>
<div class="card"><div class="why">{esc(plot.get('caveat'))}
<div class="zh">此地块面积取自 MP2025 分区宗地，属指示性、非地籍丘块 —— 法定面积须以 INLIS 产权资料（S$16）为准。
它与本街 URA caveat 的土地面积精确吻合，故可用于选取可比队列与校验挂牌数字。</div></div></div>

<h2>2 · 邻地 Neighbours — the value-killer</h2>
<div class="sub">The landed value-killer is usually an adjacent parcel's zoning, not the house.
A zone label plus a distance invents risks — read the parcel AREA, and walk the transect.<br>
<span class="zh">最大的价值杀手通常是邻地分区而非房子本身。但「标签＋距离」会凭空造出风险 ——
必须看地块<b>面积</b>，并走一遍剖面。</span></div>
<div class="scroll">{charts.distance_bars(raw.get('neighbours') or [])}</div>
<table><tr><th>Zone 分区</th><th>GPR</th><th>Nearest edge 最近边 (m)</th><th>Bearing 方位</th>
<th>Parcel area 地块面积 (sqm)</th></tr>{nb_rows}</table>
<h3>Transects 剖面 — what actually lies between</h3>
<div class="scroll">{transect_svgs}</div>

<h2>3 · 成交与定价 Transactions &amp; pricing</h2>
<div class="sub">URA caveats for {esc(c.get('street'))} — {c.get('n', 0)} landed prints
{esc(c.get('first_ym'))}..{esc(c.get('last_ym'))}. For landed, URA's area IS the land area.<br>
<span class="zh">{esc(c.get('street'))} 的 URA 官方 caveat，{c.get('n', 0)} 笔，
{esc(c.get('first_ym'))}..{esc(c.get('last_ym'))}。landed 的 area 即土地面积。</span></div>

<h3>The land-size effect 地块面积效应 — why a street "average psf" is a lie</h3>
<div class="scroll">{charts.psf_vs_size(sub.get('rows') and c.get('_all') or raw.get('_comps_all') or [], plot.get('area_sqft'))}</div>
<table><tr><th>Plot band 面积区间 (sqft)</th><th>n</th><th>psf min</th><th>psf median</th>
<th>psf max</th><th>Median price 中位价</th><th>Median area 中位面积</th></tr>{comps_rows}</table>

<h3>Trend 趋势</h3>
<div class="scroll">{charts.trend(tr)}</div>

<h3>Subject cohort 同尺寸可比 — {sub.get('area_sqft', 0):,.0f} sqft ±{sub.get('tol', 0):.0%}, n={sub.get('n', 0)}</h3>
<table><tr><th>Contract 月份</th><th>Price 成交价</th><th>Land sqft 土地面积</th>
<th>Land psf 土地单价</th><th>Type 类型</th></tr>{recent_rows}</table>

<h2>4 · 学校 Schools</h2>
<div class="sub">Our haversine is to the school's POINT. MOE measures from the school LAND
BOUNDARY via OneMap SchoolQuery — nearer than the point, so ours over-estimates: safe when it
says inside, undecided near the line, never a substitute for the category itself.<br>
<span class="zh">本表为到学校「点」的直线距离。MOE 按「学校地界」经 OneMap SchoolQuery 计算，
必然更近 —— 故本表系高估：说「在内」是安全的，贴近 1km 线则未定，且<b>不能替代官方分类</b>。</span></div>
<table><tr><th>School 学校</th><th>km</th><th>Band 区间</th><th>Matched 匹配到</th></tr>
{dist_rows('schools_primary')}</table>

<h2>5 · 交通与配套 Transport &amp; amenities</h2>
<table><tr><th>MRT</th><th>km</th><th></th><th>Matched</th></tr>{dist_rows('mrt')}</table>
<table style="margin-top:10px"><tr><th>Amenity 配套</th><th>km</th><th></th><th>Matched</th></tr>
{dist_rows('amenities')}</table>
<table style="margin-top:10px"><tr><th>Expressway 快速路</th><th>km</th><th></th><th>Matched</th></tr>
{dist_rows('expressways')}</table>

<h2>6 · 洪水 Flood</h2>
<div class="card {'blocked' if flood.get('on_list') else ''}">
<b>On PUB flood-prone list 是否在 PUB 易涝清单: {esc(flood.get('on_list'))}</b>
<div class="why">{esc(flood.get('evidential_weight'))}</div>
<div class="why">Method 方法: {esc(flood.get('method'))}</div>
<div class="zh">PUB 全国易涝地合计仅
{esc((flood.get('national_hectares') or {}).get('hectares'))} 公顷
（{esc(flood.get('national_pct_of_land'))}% 的国土），清单共 {esc(flood.get('list_size'))} 条。
「不在清单上」对单一地块几乎没有证据力 —— 该地块是否积水属实地问题（DD-3）。</div>
</div>

<h2>7 · 税务时钟 Tax clock</h2>
<div class="card blocked"><b>{esc(tax.get('source'))}</b>
<div>{esc(tax.get('note'))}</div><div class="zh">{esc(tax.get('note_zh'))}</div></div>

<h2>&#9888; 8 · 深入 DD 预警 Deep-DD alerts — {len(alerts)} items, {gated} seller-gated</h2>
<div class="sub">What the desk cannot settle, who settles it, and <b>when in the deal it must
happen</b>. An item with no answer to "when" is a wish, not a finding. A landed OTP is typically
~14 days — survey + soil + PE does not fit inside it.<br>
<span class="zh">桌面无法解决的事项、由谁解决、<b>必须在交易哪个节点完成</b>。没有「何时」的条目只是愿望。
Landed 的 OTP 通常约 14 天 —— 测量＋土壤＋结构工程师报告塞不进去。</span></div>
<table><tr><th>Unresolved 未决事项</th><th>Why the desk can't settle it 桌面为何无法定论</th>
<th>Who 由谁</th><th>Cost 费用</th><th>When 何时</th></tr>{alert_body}</table>

<h2>9 · 来源与未覆盖 Provenance &amp; not covered</h2>
<div class="card"><h3>Provenance 来源</h3>
<ul>{''.join(f"<li><b>{esc(k)}</b> — {esc(val)}</li>" for k, val in (raw.get('provenance') or {}).items())}</ul>
</div>
<div class="card blocked"><h3>Not covered by this chain 本链未覆盖</h3>
<ul>{''.join(f"<li>{esc(x)}</li>" for x in (raw.get('not_covered') or []))}</ul>
</div>

<div class="foot">
Facts: <code>python -m researcher.landed.dd "{esc(raw['address'])}" --slug {esc(slug)}</code>
&#8594; <code>researcher/landed/{esc(slug)}_dd_raw.json</code> (never hand-edited).
Judgement: <code>researcher/landed/{esc(slug)}_dd.json</code>.
Rendered by <code>deliverables/build_landed_dd_report.py</code> · skill
<code>landed-property-due-diligence</code>.<br>
Every fact above is reproducible from free official sources — OneMap, URA Master Plan 2025 (gazetted
1 Dec 2025) via data.gov.sg, URA Data Service caveats, PUB. No Investment Suite, no paid data.<br>
<span class="zh">以上事实均可用免费官方来源复现：OneMap、data.gov.sg 上的 URA Master Plan 2025
（2025-12-01 颁布）、URA Data Service caveat、PUB。未使用 Investment Suite 或任何付费数据。</span>
</div>
</div></html>"""


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    slug = sys.argv[1]
    base = os.path.join(ROOT, "researcher", "landed")
    with open(os.path.join(base, f"{slug}_dd_raw.json"), encoding="utf-8-sig") as f:
        raw = json.load(f)
    with open(os.path.join(base, f"{slug}_dd.json"), encoding="utf-8-sig") as f:
        cur = json.load(f)

    # the scatter needs every caveat, not just the subject cohort
    try:
        from researcher.landed.comps import street_comps
        raw["_comps_all"] = street_comps(raw["street"])
    except Exception:
        raw["_comps_all"] = (raw.get("comps") or {}).get("subject", {}).get("rows") or []

    reports = os.environ.get("RESEARCH_REPORTS_DIR",
                             r"G:\My Drive\004 RES\REsearch_Reports")
    if not os.path.isdir(reports):
        reports = HERE
    out = os.path.join(reports, f"{slug}_DD_Report.html")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(render(raw, cur, slug))

    alerts = cur.get("dd3_alerts") or []
    gated = [a["item"] for a in alerts if a.get("seller_gated")]
    print(f"-> {out}")
    print(f"   comps          : {(raw.get('comps') or {}).get('n', 0)} caveats")
    print(f"   neighbours     : {len(raw.get('neighbours') or [])} zones")
    print(f"   deep-DD alerts : {len(alerts)}  ({len(gated)} seller-gated)")
    for g in gated:
        print(f"     seller-gated: {g}")
    if not alerts:
        print("   WARNING: no deep-DD alerts — a digest defect, not a clean result.")


if __name__ == "__main__":
    main()
