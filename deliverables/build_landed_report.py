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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def li(items) -> str:
    return "".join(f"<li>{esc(x)}</li>" for x in (items or []))


def sev_class(s) -> str:
    s = (s or "").lower()
    return "sev-red" if any(k in s for k in ("high", "red", "severe")) else \
           "sev-amber" if any(k in s for k in ("med", "amber", "moderate")) else "sev-low"


def render(d: dict) -> str:
    area = esc(d.get("area_name", "Singapore landed area"))

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
    txns = li(d.get("example_transactions"))
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
<div class="sub">学区入手 · 实战 Checklist 驱动 · 数据通过公开来源(OneMap / URA / EdgeProp / PUB / SLA)交叉验证</div>
<div class="meta"><span><b>日期 Date</b> 2026-06-30</span>
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
  + (f"<p class='sub'>近期成交样本 / recent deals:</p><ul>{txns}</ul>" if txns else ""), prices)}

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
PUB / 银行估价为准。Generated by RE_search landed-area-research pipeline, 2026-06-30.</p>
</div></body></html>"""


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else "nanyang"
    digest_path = os.path.join(ROOT, "researcher", "landed", f"{slug}_digest.json")
    d = json.load(open(digest_path, encoding="utf-8-sig"))  # tolerate a BOM
    htmls = render(d)

    reports = os.environ.get("RESEARCH_REPORTS_DIR", r"G:\My Drive\004 RES\REsearch_Reports")
    name = f"{slug}_1km_Landed_Area_Report.html"
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
