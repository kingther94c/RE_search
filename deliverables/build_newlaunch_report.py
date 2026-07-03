"""Render a Singapore new-launch research report (HTML) from a synthesized digest.

  python deliverables/build_newlaunch_report.py <slug>

Reads  researcher/newlaunch/<slug>_digest.json  (the research+verify workflow's synth
schema) and writes a self-contained bilingual HTML report to
  G:\\My Drive\\004 RES\\REsearch_Reports   (override RESEARCH_REPORTS_DIR; falls back
to deliverables/ if the Drive isn't mounted). Includes the verification (验收) table.
"""
from __future__ import annotations

import html
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def li(items) -> str:
    return "".join(f"<li>{esc(x)}</li>" for x in (items or []))


def vstatus_class(s) -> str:
    s = (s or "").lower()
    return "v-ok" if "confirm" in s else "v-bad" if "disput" in s else "v-warn"


def stance_class(s) -> str:
    s = (s or "").upper()
    return "st-buy" if s.startswith("BUY") else "st-avoid" if "AVOID" in s else \
           "st-wait" if "WAIT" in s else "st-sel"


def render(d: dict) -> str:
    asof = esc(d.get("asof") or date.today().isoformat())
    name = esc(d.get("project_name", "New launch"))
    idn = d.get("identity") or {}
    verdict = d.get("verdict") or {}

    idrows = "".join(
        f"<tr><td class='l'>{esc(k.replace('_',' ').title())}</td><td class='l'>{esc(v)}</td></tr>"
        for k, v in idn.items() if v
    )
    units = "".join(
        f"<tr><td class='l'>{esc(u.get('type'))}</td><td>{esc(u.get('size_sqft'))}</td>"
        f"<td>{esc(u.get('indicative_price'))}</td><td>{esc(u.get('indicative_psf'))}</td></tr>"
        for u in d.get("unit_mix", [])
    )
    comps = "".join(
        f"<tr><td class='l'>{esc(c.get('name'))}</td><td>{esc(c.get('kind'))}</td>"
        f"<td>{esc(c.get('psf'))}</td><td class='l'>{esc(c.get('note'))}</td></tr>"
        for c in d.get("comparables", [])
    )
    verif = "".join(
        f"<tr class='{vstatus_class(v.get('status'))}'><td class='l'>{esc(v.get('claim'))}</td>"
        f"<td>{esc(v.get('status'))}</td><td class='l'>{esc(v.get('note'))}</td></tr>"
        for v in d.get("verification", [])
    )
    sources = "".join(f"<li><a href='{esc(u)}'>{esc(u)}</a></li>" for u in d.get("sources", []))

    def sec(zh, en, body, when=True):
        return f"<h2>{zh} <span class='en'>{en}</span></h2>{body}" if when else ""

    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>新盘研报 · {name}</title>
<style>
:root{{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--accent:#7c3aed;--bg:#f8fafc}}
*{{box-sizing:border-box}}
body{{font:15px/1.7 -apple-system,Segoe UI,Roboto,"Microsoft YaHei","PingFang SC",Arial,sans-serif;color:var(--ink);margin:0;background:var(--bg)}}
.wrap{{max-width:980px;margin:0 auto;padding:0 22px 80px;background:#fff;box-shadow:0 1px 40px rgba(15,23,42,.06)}}
header{{padding:36px 0 18px;border-bottom:3px solid var(--accent);margin-bottom:6px}}
.kicker{{color:var(--accent);font-weight:700;font-size:12px}}
h1{{font-size:28px;margin:6px 0 4px}}
h2{{font-size:20px;margin:32px 0 10px;padding-top:12px;border-top:1px solid var(--line)}}
.en{{color:var(--mut);font-weight:400;font-size:.8em}}
.sub{{color:var(--mut);font-size:14px}}
.meta{{display:flex;flex-wrap:wrap;gap:6px 24px;margin-top:12px;font-size:13px;color:var(--mut)}}
.verdict{{display:flex;align-items:center;gap:16px;border-radius:12px;padding:14px 18px;margin:16px 0;border:1px solid var(--line)}}
.badge{{font-size:22px;font-weight:800;padding:6px 16px;border-radius:10px;white-space:nowrap}}
.st-buy{{background:#dcfce7;color:#15803d}} .st-sel{{background:#fef9c3;color:#a16207}}
.st-wait{{background:#ffedd5;color:#c2410c}} .st-avoid{{background:#fee2e2;color:#b91c1c}}
.conf{{background:#faf5ff;border:1px solid #e9d5ff;border-radius:10px;padding:12px 16px;margin:10px 0;font-size:13.5px}}
table{{border-collapse:collapse;width:100%;font-size:13.5px;margin:10px 0}}
th,td{{padding:7px 9px;text-align:right;border-bottom:1px solid var(--line)}}
th{{background:var(--bg);font-size:12px;color:var(--mut)}}
td.l,th.l{{text-align:left}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}
ul{{margin:6px 0;padding-left:20px}} li{{margin:4px 0}}
.v-ok td:nth-child(2){{color:#15803d;font-weight:600}}
.v-bad td{{background:#fef2f2}} .v-bad td:nth-child(2){{color:#b91c1c;font-weight:700}}
.v-warn td:nth-child(2){{color:#b45309;font-weight:600}}
.cn{{background:#f1f5f9;border-radius:10px;padding:14px 18px;margin:10px 0}}
.foot{{color:var(--mut);font-size:12px;margin-top:26px;border-top:1px solid var(--line);padding-top:12px}}
a{{color:#1d4ed8;word-break:break-all}}
@media(max-width:720px){{.two{{grid-template-columns:1fr}}}}
</style></head><body><div class="wrap">

<header>
<div class="kicker">新盘研报 · Singapore New-Launch Research</div>
<h1>{name}</h1>
<div class="sub">研究 → 对抗式验收 → 综合 · 数据经多源交叉验证(URA / EdgeProp / 99.co / 新闻 / 发展商)</div>
<div class="meta"><span><b>日期 Date</b> {asof}</span>
<span><b>方法 Method</b> new-launch-research skill + verify pass + scorecard/pricing</span>
<span><b>输出</b> G:\\My Drive\\004 RES\\REsearch_Reports</span></div>
</header>

<div class="verdict"><span class="badge {stance_class(verdict.get('stance'))}">{esc(verdict.get('stance','—'))}</span>
<span>{esc(verdict.get('detail'))}</span></div>

<div class="conf"><b>身份与置信度 / Identity &amp; confidence</b><br>{esc(d.get('confidence_note'))}</div>

<div class="cn"><b>摘要 / Summary</b><br>{esc(d.get('summary'))}</div>

{sec('一 · 项目事实', 'Identity, developer &amp; site', f"<table>{idrows}</table>", idrows)}

{sec('二 · 户型与定价', 'Unit mix &amp; pricing',
  (f"<table><tr><th class='l'>Type</th><th>Size sqft</th><th>Price</th><th>PSF</th></tr>{units}</table>" if units else "")
  + (f"<p><b>定位 Positioning:</b> {esc(d.get('pricing_positioning'))}</p>" if d.get('pricing_positioning') else ""),
  units or d.get('pricing_positioning'))}

{sec('三 · 可比 / 竞品', 'Comparables',
  f"<table><tr><th class='l'>Project</th><th>New/Resale</th><th>PSF</th><th class='l'>Note</th></tr>{comps}</table>", comps)}

{sec('四 · 位置与未来', 'Location, connectivity &amp; future', '<ul>' + li(d.get('location')) + '</ul>', d.get('location'))}

{sec('五 · 需求与供应', 'Demand, take-up &amp; supply', '<ul>' + li(d.get('demand_supply')) + '</ul>', d.get('demand_supply'))}

<h2>六 · 论点 vs 风险 <span class="en">Bull thesis vs bear risks</span></h2>
<div class="two">
<div><h3 style="color:#15803d">看多 Bull</h3><ul>{li(d.get('investment_thesis'))}</ul></div>
<div><h3 style="color:#b91c1c">看空 Bear</h3><ul>{li(d.get('risks'))}</ul></div>
</div>

{sec('七 · 付款 / 监管 / 融资', 'Payment, stamp duty &amp; financing', '<ul>' + li(d.get('payment_regulatory')) + '</ul>', d.get('payment_regulatory'))}

{sec('八 · 验收:对抗式事实核查', 'Acceptance — adversarial fact-check',
  f"<table><tr><th class='l'>Claim</th><th>Status</th><th class='l'>Note</th></tr>{verif}</table>"
  "<p class='sub'>confirmed = 已证实 · disputed = 有矛盾 · unverified = 未能证实(谨慎对待)</p>", verif)}

{sec('数据缺口', 'Data gaps', '<ul>' + li(d.get('data_gaps')) + '</ul>', d.get('data_gaps'))}

{sec('来源', 'Sources', f"<ul>{sources}</ul>", sources)}

<p class="foot">仅供研究与说明,非投资建议/估值/要约。新盘"indicative"定价为参考,实际以发展商价单与 URA 成交为准;
DISPUTED/UNVERIFIED 项务必自行复核。Generated by RE_search new-launch-research pipeline, {asof}.</p>
</div></body></html>"""


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else "thomson_reserve"
    d = json.load(open(os.path.join(ROOT, "researcher", "newlaunch", f"{slug}_digest.json"), encoding="utf-8-sig"))
    htmls = render(d)
    if "â€" in htmls or "Ã©" in htmls:
        raise SystemExit(
            "mojibake gate: double-encoded UTF-8 detected in the rendered report — "
            "fix the digest strings before shipping")
    reports = os.environ.get("RESEARCH_REPORTS_DIR", r"G:\My Drive\004 RES\REsearch_Reports")
    fname = f"{slug}_NewLaunch_Report.html"
    try:
        os.makedirs(reports, exist_ok=True)
        out = os.path.join(reports, fname)
        open(out, "w", encoding="utf-8").write(htmls)
    except OSError:
        out = os.path.join(HERE, fname)
        open(out, "w", encoding="utf-8").write(htmls)
    print(f"wrote {out}  ({len(htmls)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
