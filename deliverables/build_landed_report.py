"""Render a Singapore landed-AREA research report (HTML) from a synthesized digest.

  python deliverables/build_landed_report.py <area_slug>

Reads  researcher/landed/<slug>_digest.json  (shape = the research workflow's synth
schema) and writes a self-contained HTML report to
  G:\\My Drive\\004 RES\\REsearch_Reports   (override with RESEARCH_REPORTS_DIR;
falls back to deliverables/ if the Drive isn't mounted). No external assets, no JS.
"""
from __future__ import annotations

import html
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)  # so `python deliverables/build_landed_report.py` finds researcher/

from researcher.sources.propertyguru import rank_listings, screen_verdict  # noqa: E402


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def li(items) -> str:
    return "".join(f"<li>{esc(x)}</li>" for x in (items or []))


def sev_class(s) -> str:
    s = (s or "").lower()
    return "sev-red" if any(k in s for k in ("high", "red", "severe")) else \
           "sev-amber" if any(k in s for k in ("med", "amber", "moderate")) else "sev-low"


def txn_rows(items) -> str:
    """example_transactions as structured rows (dict) or legacy strings."""
    if not items or not isinstance(items[0], dict):
        return ""
    return "".join(
        f"<tr><td>{esc(t.get('date'))}</td><td class='l'>{esc(t.get('street'))}</td>"
        f"<td>{esc(t.get('type'))}</td><td>{esc(t.get('price'))}</td>"
        f"<td>{esc(t.get('land_sqft'))}</td><td>{esc(t.get('land_psf'))}</td>"
        f"<td class='l'>{esc(t.get('note'))}{(' · ' + esc(t.get('source'))) if t.get('source') else ''}</td></tr>"
        for t in items
    )


def listings_table(slug: str) -> str:
    """Score + rank the live listings file for this area, if one exists."""
    path = os.path.join(ROOT, "researcher", "landed", f"{slug}_listings.json")
    if not os.path.exists(path):
        return ""
    data = json.load(open(path, encoding="utf-8-sig"))
    rows = rank_listings(data)
    if not rows:
        return ""
    body = ""
    for i, r in enumerate(rows, 1):
        l = r["lst"]
        price = f"S${l['price']:,}" if isinstance(l.get("price"), (int, float)) else "?"
        land = f"{l['land_sqft']:,}" if isinstance(l.get("land_sqft"), (int, float)) else "?"
        url = esc(l.get("url", ""))
        street = f"<a href='{url}'>{esc(l.get('street'))}</a>" if url else esc(l.get("street"))
        notes = esc(l.get("notes", ""))
        km = l.get("onemap_km")
        km_cell = esc(f"{km}" if isinstance(km, (int, float)) else "—")
        body += (
            f"<tr><td>{i}</td><td class='l'>{street}</td><td>{esc(l.get('type'))}</td>"
            f"<td>{price}</td><td>{land}</td><td>{esc(l.get('land_psf', '?'))}</td>"
            f"<td>{esc(l.get('tenure'))}</td><td>{km_cell}</td><td class='l'>{esc(r['value'])}</td>"
            f"<td>{r['score'].total:.0f}</td><td class='l'>{esc(screen_verdict(r))}</td></tr>"
            f"<tr class='notes'><td></td><td class='l' colspan='10'>{notes}</td></tr>"
        )
    pulled = esc(data.get("pulled", ""))
    bench = data.get("benchmark_land_psf") or {}
    legend = " · ".join(
        f"{k} {v[0]:,}–{v[1]:,}" for k, v in bench.items()
        if isinstance(v, (list, tuple)) and len(v) == 2)
    bench_note = (f"<p class='sub'>基准带口径 benchmark provenance: {esc(data.get('benchmark_note'))}</p>"
                  if data.get("benchmark_note") else "")
    return (
        f"<p class='sub'>数据拉取 pulled: {pulled} · 质量分 = landed scorecard (0-100) · "
        f"value = 地价 psf 对比区域基准带（{esc(legend)}）· ~km = OneMap 街道参考点到学校的直线距离"
        f"（街道有长度，成交前按门牌复测）· verdict 综合「质量分 × 价值带 × 数据完整度」——"
        f"BUILD-PRICED、tenure/洪水/地块口径不明的房源不会被标为 PURSUE</p>"
        f"<table><tr><th>#</th><th class='l'>Street</th><th>Type</th><th>Ask</th>"
        f"<th>Land sqft</th><th>Land psf</th><th>Tenure</th><th>~km</th><th class='l'>Value</th>"
        f"<th>Qual</th><th class='l'>Verdict</th></tr>{body}</table>{bench_note}"
    )


def render(d: dict, slug: str = "") -> str:
    area = esc(d.get("area_name", "Singapore landed area"))
    asof = esc(d.get("asof") or date.today().isoformat())

    estates = "".join(
        f"<tr><td class='l'>{esc(e.get('name'))}</td><td>{esc(e.get('type'))}</td>"
        f"<td>{esc(e.get('distance'))}</td><td>{esc(e.get('gcba'))}</td>"
        f"<td>{esc(e.get('indicative_land_psf'))}</td><td class='l'>{esc(e.get('note'))}</td></tr>"
        for e in d.get("estates", [])
    )
    prices = "".join(
        f"<tr><td class='l'>{esc(p.get('segment'))}</td><td>{esc(p.get('land_psf'))}</td>"
        f"<td>{esc(p.get('quantum'))}</td><td class='l'>{esc(p.get('note'))}</td></tr>"
        for p in d.get("price_structure", [])
    )
    hazards = "".join(
        f"<li class='{sev_class(h.get('severity'))}'><b>{esc(h.get('where'))}</b> — "
        f"{esc(h.get('issue'))}{(' · ' + esc(h.get('severity'))) if h.get('severity') else ''}</li>"
        for h in d.get("hazards_watchouts", [])
    )
    recs = "".join(
        f"<li><b>{esc(r.get('title'))}</b> — {esc(r.get('detail'))}</li>"
        for r in d.get("screening_recommendations", [])
    )
    txn_table = txn_rows(d.get("example_transactions"))
    txns = "" if txn_table else li(d.get("example_transactions"))
    listings = listings_table(slug) if slug else ""
    sources = "".join(
        f"<li><a href='{esc(u)}'>{esc(u)}</a></li>" for u in d.get("sources", [])
    )

    def section(title_zh, title_en, body, when=True):
        if not when:
            return ""
        return f"<h2>{title_zh} <span class='en'>{title_en}</span></h2>{body}"

    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Landed 区域研报 · {area}</title>
<style>
:root{{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--accent:#15803d;--bg:#f8fafc;--hl:#f0fdf4}}
*{{box-sizing:border-box}}
body{{font:15px/1.7 -apple-system,Segoe UI,Roboto,"Microsoft YaHei","PingFang SC",Arial,sans-serif;color:var(--ink);margin:0;background:var(--bg)}}
.wrap{{max-width:980px;margin:0 auto;padding:0 22px 80px;background:#fff;box-shadow:0 1px 40px rgba(15,23,42,.06)}}
header{{padding:36px 0 22px;border-bottom:3px solid var(--accent);margin-bottom:6px}}
.kicker{{color:var(--accent);font-weight:700;font-size:12px;letter-spacing:.04em}}
h1{{font-size:28px;margin:6px 0 4px}}
h2{{font-size:20px;margin:34px 0 10px;padding-top:12px;border-top:1px solid var(--line)}}
.en{{color:var(--mut);font-weight:400;font-size:.8em}}
.sub{{color:var(--mut);font-size:14px}}
.meta{{display:flex;flex-wrap:wrap;gap:6px 24px;margin-top:12px;font-size:13px;color:var(--mut)}}
.meta b{{color:var(--ink)}}
table{{border-collapse:collapse;width:100%;font-size:13.5px;margin:10px 0}}
th,td{{padding:7px 9px;text-align:right;border-bottom:1px solid var(--line)}}
th{{background:var(--bg);font-size:12px;color:var(--mut)}}
td.l,th.l{{text-align:left}}
ul{{margin:6px 0;padding-left:20px}} li{{margin:5px 0}}
tr.notes td{{border-bottom:1px solid var(--line);color:var(--mut);font-size:12px;padding-top:0;text-align:left}}
.order{{background:#ecfdf5;border:1px solid #a7f3d0;border-radius:10px;padding:12px 16px;margin:12px 0;font-weight:600}}
.recs{{background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:12px 18px;margin:12px 0}}
.sev-red{{color:#b91c1c}} .sev-amber{{color:#b45309}} .sev-low{{color:#334155}}
.cn{{background:#f1f5f9;border-radius:10px;padding:14px 18px;margin:10px 0}}
.foot{{color:var(--mut);font-size:12px;margin-top:26px;border-top:1px solid var(--line);padding-top:12px}}
a{{color:#1d4ed8;word-break:break-all}}
</style></head><body><div class="wrap">

<header>
<div class="kicker">Landed 区域研报 · Singapore Landed Area Research</div>
<h1>{area}</h1>
<div class="sub">{esc(d.get('subtitle', '实战 Checklist 驱动 · 数据通过公开来源(OneMap / URA / EdgeProp / PUB / SLA)交叉验证'))}</div>
<div class="meta"><span><b>日期 Date</b> {asof}</span>
<span><b>方法 Method</b> landed-area-research skill + landed scorecard</span>
<span><b>输出 Output</b> G:\\My Drive\\004 RES\\REsearch_Reports</span></div>
</header>

<div class="cn"><b>摘要 / Summary</b><br>{esc(d.get('summary'))}</div>

<div class="order">价值排序 / Value ordering：Location → Street → Land → Zoning → Neighbours → Future → House（先买地,再买房;房可重建,地与位置不可改）</div>

{section('一 · 学校与可达学区', 'Schools within 1km', '<ul>' + li(d.get('schools_within_1km')) + '</ul>', d.get('schools_within_1km'))}

{section('二 · 区内 landed 楼盘/街区', 'Estates in the catchment',
  f"<table><tr><th class='l'>Estate</th><th>Type</th><th>~Dist</th><th>GCBA</th><th>Land psf</th><th class='l'>Note</th></tr>{estates}</table>", estates)}

{section('三 · 价格结构', 'Price structure (read the spread, not the average)',
  f"<table><tr><th class='l'>Segment</th><th>Land psf</th><th>Quantum</th><th class='l'>Note</th></tr>{prices}</table>"
  + (f"<p class='sub'>近期成交样本 / recent deals:</p><table><tr><th>Date</th><th class='l'>Street</th><th>Type</th><th>Price</th><th>Land sqft</th><th>Land psf</th><th class='l'>Note · Source</th></tr>{txn_table}</table>" if txn_table else "")
  + (f"<p class='sub'>近期成交样本 / recent deals:</p><ul>{txns}</ul>" if txns else ""), prices)}

{section('三·五 · 在售房源筛选榜', 'Live listings — screened & ranked', listings, listings)}

{section('四 · 分区与未来规划', 'Zoning & future planning (URA)',
  '<ul>' + li(d.get('zoning_planning_notes')) + '</ul>'
  + ('<h3>未来规划 Future</h3><ul>' + li(d.get('future_planning')) + '</ul>' if d.get('future_planning') else ''),
  d.get('zoning_planning_notes') or d.get('future_planning'))}

{section('五 · 风险与避坑(按位置)', 'Hazards & watch-outs by location',
  f"<ul>{hazards}</ul>", hazards)}

<div class="recs"><h2 style="border:0;margin-top:4px">六 · 选房建议 <span class="en">Screening recommendations</span></h2>
<ul>{recs}</ul>
<p class="sub">逐套打分用 <code>researcher/landed/scorecard.py</code>(0–100 + 红/黄旗 + go/no-go);法律/产权用 SLA INLIS;重建成本计入"地价 + 重建"。</p></div>

{section('七 · 监管 / 重建 / 融资', 'Regulatory · rebuild · financing', '<ul>' + li(d.get('regulatory')) + '</ul>', d.get('regulatory'))}

{section('适合谁 / 数据缺口', 'Best for · data gaps',
  (f"<p><b>Best for:</b> {esc(d.get('best_for'))}</p>" if d.get('best_for') else '')
  + ('<p class="sub"><b>Data gaps:</b></p><ul>' + li(d.get('data_gaps')) + '</ul>' if d.get('data_gaps') else ''),
  d.get('best_for') or d.get('data_gaps'))}

{section('来源', 'Sources', f"<ul>{sources}</ul>", sources)}

<p class="foot">仅供研究与说明,非正式估值/法律/投资建议。数字含估算,实际以 OneMap / URA / SLA INLIS /
PUB / 银行估价为准。Generated by RE_search landed-area-research pipeline, {asof}.</p>
</div></body></html>"""


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else "nanyang"
    digest_path = os.path.join(ROOT, "researcher", "landed", f"{slug}_digest.json")
    d = json.load(open(digest_path, encoding="utf-8-sig"))  # tolerate a BOM
    htmls = render(d, slug)
    if "â€" in htmls or "Ã©" in htmls:
        raise SystemExit(
            "mojibake gate: double-encoded UTF-8 detected in the rendered report — "
            "fix the digest strings before shipping")

    reports = os.environ.get("RESEARCH_REPORTS_DIR", r"G:\My Drive\004 RES\REsearch_Reports")
    # generic name; a digest can pin its own (e.g. keep nanyang's historical `_1km_` name)
    name = d.get("report_basename") or f"{slug}_Landed_Area_Report.html"
    try:
        os.makedirs(reports, exist_ok=True)
        out = os.path.join(reports, name)
        open(out, "w", encoding="utf-8").write(htmls)
    except OSError:
        out = os.path.join(HERE, name)
        open(out, "w", encoding="utf-8").write(htmls)
    print(f"wrote {out}  ({len(htmls)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
