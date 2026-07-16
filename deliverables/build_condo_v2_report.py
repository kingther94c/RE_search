"""Render a condo-resale-valuation report (engine v2) to bilingual HTML.

    python deliverables/build_condo_v2_report.py --project "TREASURE AT TAMPINES" \
           --area 936 --floor 12 [--asof 2026-07-01]

Values the unit with researcher.backtest.value_unit, then writes an HTML report to the
repo's gitignored reports/ AND syncs it to the Drive library (deliverables/report_out.py).
Self-contained (inline CSS), no external assets.
"""
from __future__ import annotations

import argparse
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deliverables.report_out import write_report  # noqa: E402
from researcher.backtest.value_unit import SubjectSpec, value


def _money(x):
    return f"S${x:,.0f}" if x is not None else "—"


def _directional_banner(v: dict) -> str:
    d, ref = v.get("directional_flag"), v.get("recent_same_size_reference")
    if not d:
        return ""
    r = (f" 最近同尺寸成交 latest same-size print: {ref['adj_psf']:.0f} psf "
         f"({ref['contract_ym']}, {ref['area_sqft']:.0f} sqft)") if ref else ""
    return (f"<div class=banner>⚠ {html.escape(d)}<span class=note>{html.escape(r)}</span></div>")


def render(v: dict) -> str:
    if v.get("error"):
        return f"<p>Cannot value: {html.escape(v['message'])}</p>"
    s, fv = v["subject"], v["fair_value"]
    ad = v["anchor_disagreement"]
    reads = "".join(
        f"<tr><td>{html.escape(k)}</td><td class=r>{('%.0f'%x) if x else '—'}</td></tr>"
        for k, x in v["independent_reads_psf"].items())
    comps = "".join(
        f"<tr><td>{c['contract_ym']}</td><td class=r>{c['area_sqft']:.0f}</td>"
        f"<td>{html.escape(c['floor_range'])}</td><td class=r>{c['psf']:.0f}</td>"
        f"<td class=r>{_money(c['price'])}</td></tr>" for c in v["comps"])
    verify = "".join(f"<li>{html.escape(x)}</li>" for x in v["verify_before_offer"])
    limits = "".join(f"<li>{html.escape(x)}</li>" for x in v["limitations"])
    hard = (" · <span class=warn>HARD CASE — anchors disagree "
            f"{ad['spread_rel']*100:.0f}%, corroborate before offering</span>"
            if ad["hard_case"] else "")
    return f"""<div class=wrap>
<h1>{html.escape(s['project'])} · {s['area_sqft']:.0f} sqft · Floor {s.get('floor') or '—'}</h1>
<p class=meta>{html.escape(s['market_segment'])} · District {html.escape(s['district'])} ·
{html.escape(s['tenure_type'])} · valued as of {html.escape(s['asof'])} · engine v2 (URA
walk-forward validated, ~4% median APE)</p>

<div class=hero>
  <div><div class=lbl>公允价 Fair value</div><div class=big>{_money(fv['price'])}</div>
    <div class=sub>{fv['psf']:.0f} psf</div></div>
  <div><div class=lbl>区间 Range (~82% of comparable prints)</div>
    <div class=big>{_money(fv['low'])} – {_money(fv['high'])}</div></div>
  <div><div class=lbl>置信度 Confidence</div><div class=big>{fv['confidence']}/100</div>
    <div class=sub>{html.escape(fv['confidence_label'])}{hard}</div></div>
</div>
{_directional_banner(v)}

<div class=cols>
  <div class=card>
    <h2>买家指导 Buyer guidance <span class=note>(separate from fair value)</span></h2>
    <table><tr><td>Attractive — 积极买入</td><td class=r>&lt; {_money(v['buyer_guidance']['attractive_below'])}</td></tr>
    <tr><td>Fair range 公允带</td><td class=r>{_money(fv['low'])} – {_money(fv['high'])}</td></tr>
    <tr><td>Walk away 放弃</td><td class=r>&gt; {_money(v['buyer_guidance']['walk_away_above'])}</td></tr></table>
  </div>
  <div class=card>
    <h2>卖家指导 Seller guidance</h2>
    <table><tr><td>Ask 挂牌</td><td class=r>{_money(v['seller_guidance']['ask'])}</td></tr>
    <tr><td>Expected clear 预期成交</td><td class=r>{_money(v['seller_guidance']['expected_clear'])}</td></tr>
    <tr><td>Quick sale 急售</td><td class=r>{_money(v['seller_guidance']['quick_sale'])}</td></tr></table>
  </div>
</div>

<div class=cols>
  <div class=card><h2>独立方法读数 Independent reads (psf)</h2>
    <table><tr><th>method</th><th class=r>psf</th></tr>{reads}</table>
    <p class=note>Convergence = signal; divergence = the "hard case" flag above.</p></div>
  <div class=card><h2>最相近可比 Most-similar same-project comps</h2>
    <table><tr><th>month</th><th class=r>sqft</th><th>floor</th><th class=r>psf</th><th class=r>price</th></tr>{comps}</table>
    <p class=note>n = {fv['n_same_project_comps']} same-project caveats drove the estimate.</p></div>
</div>

<div class=card><h2>下单前必查 Verify before offer</h2><ul>{verify}</ul></div>
<div class=card><h2>局限 Limitations</h2><ul>{limits}</ul>
  <p class=note>basis: {html.escape(fv['basis'])}. Not a substitute for a licensed valuation.</p></div>
</div>"""


_CSS = """body{margin:0;background:#0f1115;color:#e6e6e6;font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:920px;margin:0 auto;padding:28px}h1{font-size:22px;margin:0 0 4px}
.meta{color:#9aa4b2;margin:0 0 18px;font-size:13px}
.hero{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;background:#171a21;border:1px solid #262b36;border-radius:12px;padding:18px;margin-bottom:16px}
.lbl{color:#9aa4b2;font-size:12px}.big{font-size:22px;font-weight:650;margin-top:2px}.sub{color:#9aa4b2;font-size:12px;margin-top:2px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}
.card{background:#171a21;border:1px solid #262b36;border-radius:12px;padding:16px}
h2{font-size:15px;margin:0 0 10px}.note{color:#9aa4b2;font-size:12px}.warn{color:#ffb454;font-weight:600}
.banner{background:#2a2113;border:1px solid #5c4a1f;color:#ffcf87;border-radius:10px;padding:11px 14px;margin-bottom:14px;font-size:13px}
.banner .note{display:block;margin-top:3px;color:#c9b48a}
table{width:100%;border-collapse:collapse}td,th{padding:4px 6px;border-bottom:1px solid #21262f;text-align:left}
th{color:#9aa4b2;font-weight:500;font-size:12px}.r{text-align:right;font-variant-numeric:tabular-nums}
ul{margin:6px 0;padding-left:18px}li{margin:3px 0}
@media(max-width:680px){.hero,.cols{grid-template-columns:1fr}}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--area", type=float, required=True)
    ap.add_argument("--floor", type=int, default=None)
    ap.add_argument("--asof", default=None)
    a = ap.parse_args()
    v = value(SubjectSpec(a.project, a.area, floor=a.floor, asof=a.asof))
    doc = (f"<!doctype html><html><head><meta charset=utf-8>"
           f"<meta name=viewport content='width=device-width,initial-scale=1'>"
           f"<title>{html.escape(a.project)} valuation</title><style>{_CSS}</style></head>"
           f"<body>{render(v)}</body></html>")
    slug = a.project.lower().replace(" ", "_").replace("'", "")
    print(write_report(f"condo_v2_{slug}.html", doc).summary())
    if not v.get("error"):
        fv = v["fair_value"]
        print(f"   {a.project}: {_money(fv['price'])} ({fv['psf']:.0f} psf), "
              f"range {_money(fv['low'])}-{_money(fv['high'])}, conf {fv['confidence']}/100")


if __name__ == "__main__":
    main()
