"""Render a Singapore resale-condo VALUATION report (HTML) from a synthesized digest.

  python deliverables/build_condo_report.py <slug>

Reads  researcher/valuation/<slug>_digest.json  (subject + engine output + advisory,
shape documented in the value-a-property skill) and writes a self-contained bilingual
HTML report to the repo's gitignored reports/ AND the Drive library — see
deliverables/report_out.py. Unlike build_report.py (the Spottiswoode one-off with
embedded app screenshots), this builder is generic: web-sourced studies welcome.
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

from deliverables.report_out import write_report  # noqa: E402


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def li(items) -> str:
    return "".join(f"<li>{esc(x)}</li>" for x in (items or []))


def vclass(s) -> str:
    s = (s or "").lower()
    return "v-ok" if "confirm" in s else "v-bad" if "disput" in s or "wrong" in s else "v-warn"


def money(x) -> str:
    return f"S${x:,.0f}" if isinstance(x, (int, float)) else esc(x)


def render(d: dict) -> str:
    asof = esc(d.get("asof") or date.today().isoformat())
    s = d.get("subject") or {}
    v = d.get("valuation") or {}
    adv = d.get("advisory") or {}

    grid = "".join(
        f"<tr><td class='l'>{esc(g.get('label'))}</td><td>{g.get('raw_psf', 0):,.0f}</td>"
        f"<td>{g.get('time_adj', 1):.3f}</td><td>{g.get('floor_adj', 1):.3f}</td>"
        f"<td>{g.get('size_adj', 1):.3f}</td><td>{g.get('type_adj', 1):.3f}</td>"
        f"<td><b>{g.get('adj_psf', 0):,.0f}</b></td><td>{g.get('weight', 0):.2f}</td></tr>"
        for g in v.get("grid", [])
    )
    txns = "".join(
        f"<tr><td>{esc(t.get('date'))}</td><td>{esc(t.get('size_sqft'))}</td>"
        f"<td>{esc(t.get('level'))}</td><td>{esc(t.get('psf'))}</td>"
        f"<td>{money(t.get('price'))}</td><td class='l'>{esc(t.get('note'))}</td></tr>"
        for t in d.get("comps_table", [])
    )
    xcomps = "".join(
        f"<tr><td class='l'>{esc(c.get('project'))}</td><td>{esc(c.get('psf'))}</td>"
        f"<td class='l'>{esc(c.get('note'))}</td></tr>"
        for c in d.get("market_comps", [])
    )
    rents = "".join(
        f"<tr><td class='l'>{esc(r.get('unit_type'))}</td><td>{esc(r.get('monthly_rent'))}</td>"
        f"<td class='l'>{esc(r.get('note'))}</td></tr>"
        for r in d.get("rentals", [])
    )
    verif = "".join(
        f"<tr class='{vclass(x.get('status'))}'><td class='l'>{esc(x.get('claim'))}</td>"
        f"<td>{esc(x.get('status'))}</td><td class='l'>{esc(x.get('note'))}</td></tr>"
        for x in d.get("verification", [])
    )
    profits = "".join(
        f"<tr><td class='l'>{esc(p.get('unit'))}</td><td class='l'>{esc(p.get('bought'))}</td>"
        f"<td class='l'>{esc(p.get('sold'))}</td><td>{esc(p.get('profit'))}</td>"
        f"<td>{esc(p.get('holding'))}</td><td>{esc(p.get('annualised'))}</td></tr>"
        for p in d.get("profitability", [])
    )
    avm_rows = "".join(
        f"<tr><td>{esc(a.get('blk'))}</td><td>{esc(a.get('unit'))}</td><td>{esc(a.get('sqft'))}</td>"
        f"<td>{esc(a.get('est_val'))}</td><td><b>{esc(a.get('est_psf'))}</b></td></tr>"
        for a in d.get("avm_crosscheck", [])
    )
    tri = v.get("triangulation") or {}
    fresh = tri.get("freshest_same_spec") or {}
    band = tri.get("negotiation_band_psf") or []
    tri_html = ""
    if band:
        tri_html = (
            "<div class='tri'><b>三角定价 Triangulation</b>　"
            f"AVM cohort 中位 <b>{tri.get('avm_cohort_median_psf') or '—'}</b> psf · "
            f"模型点估 <b>{tri.get('model_psf') or '—'}</b> psf · "
            f"最新同规格成交 <b>{fresh.get('psf', '—')}</b> psf"
            + (f"（{esc(fresh.get('level'))}，{esc(fresh.get('date'))}）" if fresh else "")
            + f" → <b>谈判带 {band[0]:,}–{band[1]:,} psf</b>"
            + f"<div class='note'>{esc(tri.get('note'))}</div></div>")
    sens = v.get("sensitivity") or {}
    _sens_zh = {"trend_0pc": "趋势 0%", "trend_plus2pp": "趋势 +2pp", "no_anchor": "去锚",
                "resale_surfaces_only": "仅转售面（剔除首售/PP 印）"}
    sens_html = ("<div class='note'>敏感性 sensitivity（psf）：" + " · ".join(
        f"{_sens_zh.get(k, k)} → {x:,}" for k, x in sens.items()) + "</div>" if sens else "")
    sources = "".join(
        (f"<li><a href='{esc(u)}'>{esc(u)}</a></li>" if str(u).startswith("http")
         else f"<li>{esc(u)}</li>")
        for u in d.get("sources", []))

    # numbered sections are auto-counted — hand-numbered headings drift when a
    # section is empty/skipped (a review once caught a missing 四 + a 五·五 hack)
    _nums = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
             "十一", "十二", "十三", "十四"]
    _ctr = {"i": 0}

    def sec(zh, en, body, when=True, numbered=True):
        if not when:
            return ""
        if numbered:
            _ctr["i"] += 1
            zh = f"{_nums[_ctr['i'] - 1]} · {zh}"
        return f"<h2>{zh} <span class='en'>{en}</span></h2>{body}"

    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Condo 估值研报 · {esc(s.get('name'))}</title>
<style>
:root{{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--accent:#7c3aed;--bg:#f8fafc}}
*{{box-sizing:border-box}}
body{{font:15px/1.7 -apple-system,Segoe UI,Roboto,"Microsoft YaHei","PingFang SC",Arial,sans-serif;color:var(--ink);margin:0;background:var(--bg)}}
.wrap{{max-width:980px;margin:0 auto;padding:0 22px 80px;background:#fff;box-shadow:0 1px 40px rgba(15,23,42,.06)}}
header{{padding:36px 0 22px;border-bottom:3px solid var(--accent);margin-bottom:6px}}
.kicker{{color:var(--accent);font-weight:700;font-size:12px;letter-spacing:.04em}}
.sub{{color:var(--mut);font-size:13.5px}}
h1{{font-size:27px;margin:6px 0 4px}}
h2{{font-size:20px;margin:34px 0 10px;padding-top:12px;border-top:1px solid var(--line)}}
.en{{color:var(--mut);font-weight:400;font-size:.8em}}
.meta{{display:flex;flex-wrap:wrap;gap:6px 24px;margin-top:12px;font-size:13px;color:var(--mut)}}
.meta b{{color:var(--ink)}}
table{{border-collapse:collapse;width:100%;font-size:13.5px;margin:10px 0}}
th,td{{padding:7px 9px;text-align:right;border-bottom:1px solid var(--line)}}
th{{background:var(--bg);font-size:12px;color:var(--mut)}}
td.l,th.l{{text-align:left}}
ul{{margin:6px 0;padding-left:20px}} li{{margin:5px 0}}
.cn{{background:#f1f5f9;border-radius:10px;padding:14px 18px;margin:10px 0}}
.val{{background:#f5f3ff;border:1px solid #ddd6fe;border-radius:10px;padding:14px 18px;margin:12px 0}}
.val .big{{font-size:22px;font-weight:800}}
.tri{{background:#fff;border:1px dashed #a78bfa;border-radius:8px;padding:8px 12px;margin:10px 0 6px}}
.note{{color:var(--mut);font-size:12.5px;margin-top:6px;line-height:1.6}}
.stance{{display:inline-block;background:#ede9fe;border-radius:8px;padding:2px 12px;font-weight:700;margin-right:10px}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:0 26px}}
.v-ok td{{color:#166534}} .v-warn td{{color:#b45309}} .v-bad td{{color:#b91c1c}}
.foot{{color:var(--mut);font-size:12px;margin-top:26px;border-top:1px solid var(--line);padding-top:12px}}
a{{color:#1d4ed8;word-break:break-all}}
@media(max-width:720px){{.two{{grid-template-columns:1fr}}}}
</style></head><body><div class="wrap">

<header>
<div class="kicker">Condo 估值研报 · Resale Valuation Research</div>
<h1>{esc(s.get('name'))}</h1>
<div class="sub">{esc(d.get('subtitle', '可比成交调整法 sales-comparison · 数据经公开来源交叉验证'))}</div>
<div class="meta"><span><b>日期 Date</b> {asof}</span>
<span><b>方法 Method</b> value-a-property skill + comparable-adjustment engine</span>
<span><b>标的 Subject</b> {esc(s.get('development'))} · {esc(s.get('size_sqft'))} sqft · {esc(s.get('bedrooms'))}BR · L{esc(s.get('floor'))} · {esc(s.get('tenure'))}</span></div>
</header>

<div class="cn"><b>摘要 / Summary</b><br>{esc(d.get('summary'))}</div>

<div class="val"><span class="stance">{esc(adv.get('stance', '—'))}</span>
<span class="big">{money(v.get('estimate_price'))}</span>
&nbsp;({v.get('estimate_psf', 0):,.0f} psf) · 区间 range {money(v.get('low_price'))} – {money(v.get('high_price'))}
({v.get('low_psf', 0):,.0f}–{v.get('high_psf', 0):,.0f} psf)
{tri_html}{sens_html}
<div class='note'>{esc(v.get('params_note'))}</div></div>

{sec('项目事实', 'Development facts', '<ul>' + li(d.get('development_facts')) + '</ul>', d.get('development_facts'))}

{sec('本盘成交（估值输入）', 'Subject-project transactions (valuation inputs)',
  f"<table><tr><th>Date</th><th>Sqft</th><th>Level</th><th>PSF</th><th>Price</th><th class='l'>Note · Source</th></tr>{txns}</table>", txns)}

{sec('调整网格', 'Adjustment grid (comp → subject)',
  f"<table><tr><th class='l'>Comp</th><th>Raw psf</th><th>×time</th><th>×floor</th><th>×size</th><th>×type</th><th>Adj psf</th><th>Wt</th></tr>{grid}</table>"
  "<p class='sub'>time=市场趋势归一到估值日 · floor=楼层差 · size=面积/总价效应 · type=户型修正 · weight=相似度权重</p>", grid)}

{sec('AVM 逐户对照（app Est. Val）', 'Per-unit AVM crosscheck (cohort)',
  f"<table><tr><th>Blk</th><th>Unit</th><th>Sqft</th><th>Est. Val</th><th>Est. psf</th></tr>{avm_rows}</table>"
  "<p class='sub'>app 自有 AVM 为 LIVE 值（随行情日变）——以 capture 日期口径读；对新近成交存在滞后</p>", avm_rows)}

{sec('跨盘参照', 'Cross-project comps', f"<table><tr><th class='l'>Project</th><th>PSF</th><th class='l'>Note</th></tr>{xcomps}</table>", xcomps)}

{sec('租金与收益率', 'Rentals & yield',
  (f"<table><tr><th class='l'>Type</th><th>Rent / mo</th><th class='l'>Note</th></tr>{rents}</table>" if rents else "")
  + ('<ul>' + li(d.get('yield_analysis')) + '</ul>' if d.get('yield_analysis') else ''), rents or d.get('yield_analysis'))}

{sec('已实现回报（买卖配对）', 'Realised returns (matched pairs)',
  f"<table><tr><th class='l'>Unit</th><th class='l'>Bought</th><th class='l'>Sold</th>"
  f"<th>Profit</th><th>Holding</th><th>Ann.</th></tr>{profits}</table>", profits)}

{sec('学区与位置', 'Catchment & location', '<ul>' + li(d.get('catchment')) + '</ul>', d.get('catchment'))}

{sec('市场背景', 'Market context', '<ul>' + li(d.get('market_context')) + '</ul>', d.get('market_context'))}

{sec('论点 vs 风险', 'Bull vs bear',
  f"<div class='two'><div><h3 style='color:#15803d'>看多 Bull</h3><ul>{li(d.get('catalysts'))}</ul></div>"
  f"<div><h3 style='color:#b91c1c'>看空 Bear</h3><ul>{li(d.get('risks'))}</ul></div></div>",
  d.get('catalysts') or d.get('risks'))}

{sec('建议与成本', 'Advisory & cost stack',
  (f"<p><b>{esc(adv.get('stance'))}</b> — {esc(adv.get('detail'))}</p>" if adv.get('detail') else '')
  + ('<ul>' + li(adv.get('cost_stack')) + '</ul>' if adv.get('cost_stack') else ''),
  adv.get('detail') or adv.get('cost_stack'))}

{sec('验收：事实核查', 'Acceptance — fact-check',
  f"<table><tr><th class='l'>Claim</th><th>Status</th><th class='l'>Note</th></tr>{verif}</table>"
  "<p class='sub'>confirmed = 已证实 · unverified = 未能证实（谨慎对待）</p>", verif)}

{sec('数据缺口', 'Data gaps', '<ul>' + li(d.get('data_gaps')) + '</ul>', d.get('data_gaps'), numbered=False)}

{sec('来源', 'Sources', f"<ul>{sources}</ul>", sources, numbered=False)}

<p class="foot">仅供研究与说明，非正式估值/投资建议。实际以银行估价、URA REALIS 与律师尽调为准。
Generated by RE_search value-a-property pipeline, {asof}.</p>
</div></body></html>"""


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else "gallop_gables"
    d = json.load(open(os.path.join(ROOT, "researcher", "valuation", f"{slug}_digest.json"),
                       encoding="utf-8-sig"))
    htmls = render(d)
    if "â€" in htmls or "Ã©" in htmls:
        raise SystemExit("mojibake gate: double-encoded UTF-8 detected — fix the digest first")
    name = d.get("report_basename") or f"{slug}_Condo_Valuation_Report.html"
    print(write_report(name, htmls).summary())


if __name__ == "__main__":
    main()
