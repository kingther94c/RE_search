"""Render a landed-valuation report (engine LV1) to bilingual HTML.

    python deliverables/build_landed_v2_report.py --street "ALNWICK ROAD" --area 2800 \
           --type Terrace [--condition original] [--asof 2026-07-01]

Writes to RESEARCH_REPORTS_DIR (default G:\\My Drive\\004 RES\\REsearch_Reports; falls back
to deliverables/). Self-contained, no external assets. Landed-specific emphasis vs the condo
report: LAND-psf vs bundle price, the geometry blind spot, the condition input, and the
noise floor — because those are what an honest landed number has to disclose.
"""
from __future__ import annotations

import argparse
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from researcher.backtest.value_landed import LandedSpec, value_landed


def _reports_dir() -> str:
    d = os.environ.get("RESEARCH_REPORTS_DIR", r"G:\My Drive\004 RES\REsearch_Reports")
    if os.path.isdir(os.path.dirname(d)) or os.path.isdir(d):
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except OSError:
            pass
    return os.path.dirname(os.path.abspath(__file__))


def _money(x):
    """3 significant figures. The engine brackets these at +/-20-44% and declares a ~6-8%
    noise floor — rendering 'S$21,829,823' claims 8 sig figs of precision the method does
    not have. Match the render to the stated uncertainty."""
    if x is None:
        return "—"
    if x >= 1e6:
        return f"S${x/1e6:.2f}M"
    if x >= 1e3:
        return f"S${x/1e3:.0f}k"
    return f"S${x:,.0f}"


def _banner(v):
    """Always surface the freshest comparable print — it is the single most credible evidence
    point, and rendering it ONLY when the directional flag fires meant that on the low side
    (where the engine IS biased, in a rising market) the report computed it and threw it
    away. Banner when flagged; a quiet line otherwise."""
    d, ref = v.get("directional_flag"), v.get("recent_street_reference")
    if not ref:
        return ""
    r = (f"最新可比街道成交 freshest comparable street print: {ref['adj_psf']:.0f} land-psf "
         f"(adj, {ref['contract_ym']}, {ref['area_sqft']:.0f} sqft)")
    if not d:
        return f"<p class=note>{html.escape(r)}</p>"
    return f"<div class=banner>⚠ {html.escape(d)}<span class=note>{html.escape(r)}</span></div>"


def render(v: dict) -> str:
    if v.get("error"):
        return (f"<div class=wrap><h1>Out of scope</h1><div class=banner>⚠ "
                f"{html.escape(v['message'])}</div></div>")
    s, fv = v["subject"], v["fair_value"]
    md = v["method_disagreement"]
    lease = (f"{s['remaining_lease_years']}y left" if s.get("remaining_lease_years")
             else "freehold / 999y")
    reads = "".join(
        f"<tr><td>{html.escape(k)}</td><td class=r>{('%.0f' % x) if x else '—'}</td></tr>"
        for k, x in v["independent_reads_land_psf"].items())
    comps = "".join(
        f"<tr><td>{c['contract_ym']}</td><td class=r>{c['land_area_sqft']:,.0f}</td>"
        f"<td class=r>{c['land_psf']:,.0f}</td><td class=r><b>{c['adj_land_psf']:,.0f}</b></td>"
        f"<td class=r>{_money(c['price'])}</td>"
        f"<td>{html.escape(c['tenure'])}</td></tr>" for c in v["comps"])
    verify = "".join(f"<li>{html.escape(x)}</li>" for x in v["verify_before_offer"])
    limits = "".join(f"<li>{html.escape(x)}</li>" for x in v["limitations"])
    hard = (f" · <span class=warn>HARD CASE — methods disagree {md['spread_rel']*100:.0f}%</span>"
            if md["hard_case"] else "")
    cond_val = (f"<b>{html.escape(s['condition'])}</b>" if s.get("condition")
                else "<span class=warn>not supplied</span>")
    cond_note = html.escape(v.get("condition_note") or "")
    # guidance is SUPPRESSED when the engine has declared itself unreliable — render that
    # honestly instead of printing an ask derived from the engine's own error bar
    bg, sg = v["buyer_guidance"], v["seller_guidance"]
    if sg.get("ask") is None:
        guidance = (f"<div class=card><h2>买卖指导 Buyer / seller guidance</h2>"
                    f"<div class=banner>⛔ {html.escape(sg['note'])}</div>"
                    f"<p class=note>公允价区间 fair-value band (engine uncertainty): "
                    f"{_money(bg['fair_value_band'][0])} – "
                    f"{_money(bg['fair_value_band'][1])}</p></div>")
    else:
        guidance = f"""<div class=cols>
  <div class=card>
    <h2>买家指导 Buyer guidance <span class=note>(from observed prints, not the band)</span></h2>
    <table><tr><td>Attractive 积极买入 <span class=note>(cheap end, p25)</span></td><td class=r>&lt; {_money(bg['attractive_below'])}</td></tr>
    <tr><td>Walk away 放弃 <span class=note>(dear end, p75)</span></td><td class=r>&gt; {_money(bg['walk_away_above'])}</td></tr></table>
    <p class=note>{html.escape(bg['note'])}</p>
  </div>
  <div class=card>
    <h2>卖家指导 Seller guidance</h2>
    <table><tr><td>Ask 挂牌</td><td class=r>{_money(sg['ask'])}</td></tr>
    <tr><td>Expected clear 预期成交</td><td class=r>{_money(sg['expected_clear'])}</td></tr>
    <tr><td>Quick sale 急售</td><td class=r>{_money(sg['quick_sale'])}</td></tr></table>
    <p class=note>{html.escape(sg['note'])}</p>
  </div>
</div>"""
    return f"""<div class=wrap>
<h1>{html.escape(s['street'])} · {s['land_area_sqft']:,.0f} sqft land · {html.escape(s['property_type'])}</h1>
<p class=meta>{html.escape(s['market_segment'])} · District {html.escape(s['district'])} ·
{html.escape(s['tenure_type'])} ({lease}) · valued as of {html.escape(s['asof'])} ·
engine LV1 (URA walk-forward: 9.3% median APE, 78.9% held-out band coverage)</p>

<div class=hero>
  <div><div class=lbl>公允价 Fair value <span class=note>(land+building bundle)</span></div>
    <div class=big>{_money(fv['price'])}</div>
    <div class=sub>{fv['land_psf']:,.0f} per sqft of LAND</div></div>
  <div><div class=lbl>公允价区间 Fair-value band <span class=note>(engine uncertainty,
    78.9% held-out coverage — NOT a negotiation range)</span></div>
    <div class=big>{_money(fv['low'])} – {_money(fv['high'])}</div></div>
  <div><div class=lbl>置信度 Confidence</div><div class=big>{fv['confidence']}/100</div>
    <div class=sub>{html.escape(fv['confidence_label'])}{hard}</div></div>
</div>
{_banner(v)}
<div class=card><h2>建筑状况 Building condition <span class=note>(engine is condition-BLIND)</span></h2>
  <p>{cond_val}</p>
  <p class=note>{cond_note}</p></div>

{guidance}

<div class=cols>
  <div class=card><h2>独立方法读数 Independent reads (land-psf)</h2>
    <table><tr><th>method</th><th class=r>land-psf</th></tr>{reads}</table>
    <p class=note>Convergence = signal; a wide spread raises the hard-case flag above.</p></div>
  <div class=card><h2>最相近同街可比 Most-similar street comps <span class=note>(lease-matched)</span></h2>
    <table><tr><th>month</th><th class=r>land sqft</th><th class=r>raw psf</th>
    <th class=r>adj psf</th><th class=r>price</th><th>tenure</th></tr>{comps}</table>
    <p class=note>n = {fv['n_street_comps']} lease-matched street comps drove the estimate.
    <b>adj psf</b> = that print moved to THIS plot for time (capped) and size (fitted curve)
    — the point and the guidance markers live on this adjusted column, not the raw one.</p></div>
</div>

<div class=card><h2>下单前必查 Verify before offer</h2><ul>{verify}</ul></div>
<div class=card><h2>局限 Limitations</h2><ul>{limits}</ul>
  <p class=note>basis: {html.escape(fv['basis'])}. Not a substitute for a licensed valuation.</p></div>
</div>"""


_CSS = """body{margin:0;background:#0f1115;color:#e6e6e6;font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:940px;margin:0 auto;padding:28px}h1{font-size:22px;margin:0 0 4px}
.meta{color:#9aa4b2;margin:0 0 18px;font-size:13px}
.hero{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;background:#171a21;border:1px solid #262b36;border-radius:12px;padding:18px;margin-bottom:14px}
.lbl{color:#9aa4b2;font-size:12px}.big{font-size:22px;font-weight:650;margin-top:2px}.sub{color:#9aa4b2;font-size:12px;margin-top:2px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}
.card{background:#171a21;border:1px solid #262b36;border-radius:12px;padding:16px;margin-bottom:14px}
h2{font-size:15px;margin:0 0 10px}.note{color:#9aa4b2;font-size:12px}.warn{color:#ffb454;font-weight:600}
.banner{background:#2a2113;border:1px solid #5c4a1f;color:#ffcf87;border-radius:10px;padding:11px 14px;margin-bottom:14px;font-size:13px}
.banner .note{display:block;margin-top:3px;color:#c9b48a}
table{width:100%;border-collapse:collapse}td,th{padding:4px 6px;border-bottom:1px solid #21262f;text-align:left}
th{color:#9aa4b2;font-weight:500;font-size:12px}.r{text-align:right;font-variant-numeric:tabular-nums}
ul{margin:6px 0;padding-left:18px}li{margin:3px 0}
@media(max-width:680px){.hero,.cols{grid-template-columns:1fr}}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--street", required=True)
    ap.add_argument("--area", type=float, required=True, help="LAND area in sqft")
    ap.add_argument("--type", default="Terrace",
                    choices=["Terrace", "Semi-detached", "Detached"])
    ap.add_argument("--condition", default=None,
                    choices=["original", "renovated", "rebuilt"])
    # SKILL.md lists tenure / lease-start as supply-able inputs; the CLI must honour that.
    # A leasehold plot with an unestablished lease start is REFUSED, not freehold-priced.
    ap.add_argument("--tenure", default=None,
                    choices=["freehold", "freehold_equiv", "leasehold"],
                    help="override the street-inferred tenure")
    ap.add_argument("--lease-start", type=int, default=None,
                    help="lease commencement year (required for a leasehold subject)")
    ap.add_argument("--asof", default=None)
    a = ap.parse_args()
    v = value_landed(LandedSpec(a.street, a.area, a.type, tenure_type=a.tenure,
                                lease_start=a.lease_start, condition=a.condition,
                                asof=a.asof))
    doc = (f"<!doctype html><html><head><meta charset=utf-8>"
           f"<meta name=viewport content='width=device-width,initial-scale=1'>"
           f"<title>{html.escape(a.street)} landed valuation</title><style>{_CSS}</style>"
           f"</head><body>{render(v)}</body></html>")
    slug = a.street.lower().replace(" ", "_").replace("'", "")
    out = os.path.join(_reports_dir(), f"landed_v1_{slug}_{int(a.area)}sf.html")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)
    print(f"-> {out}")
    if not v.get("error"):
        fv = v["fair_value"]
        print(f"   {a.street} {a.area:,.0f}sf {a.type}: {_money(fv['price'])} "
              f"({fv['land_psf']:,.0f} land-psf), range {_money(fv['low'])}-{_money(fv['high'])}, "
              f"conf {fv['confidence']}/100")
    else:
        print(f"   OUT OF SCOPE: {v['error']}")


if __name__ == "__main__":
    main()
