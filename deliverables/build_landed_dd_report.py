"""Render a Singapore landed per-property DD report (HTML) from a DD digest.

  python deliverables/build_landed_dd_report.py <slug>

Reads  researcher/landed/<slug>_dd.json  and writes a self-contained bilingual HTML
report to  G:\\My Drive\\004 RES\\REsearch_Reports  (override with RESEARCH_REPORTS_DIR;
falls back to deliverables/ if the Drive isn't mounted). No external assets, no JS.

Sibling of build_landed_report.py, which renders the AREA report. This one is per-address
and enforces the DD contract from the landed-property-due-diligence skill:

  - every DD-1 row must carry value + source + date, or it renders as a defect;
  - the deep-DD alert section is STRUCTURAL, not optional. An empty alert list is a
    rendering error, not a clean bill of health — a DD that found nothing to escalate
    did not look. Same for a report that silently omits the blocked sections.
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


def sev_class(s) -> str:
    s = (s or "").lower()
    return "sev-red" if s in ("high", "red") else \
           "sev-amber" if s in ("medium", "med", "amber") else "sev-low"


def when_class(w) -> str:
    w = (w or "").upper()
    return "w-hard" if "OTP" in w or "PRE-OFFER" in w or "BEFORE" in w else \
           "w-soft" if "PRICED" in w else "w-mid"


# ------------------------------------------------------------------- sections
def dd1_rows(items) -> str:
    out = []
    for it in items or []:
        missing = [k for k in ("value", "source", "date") if not it.get(k)]
        # The contract is value+source+date. Render the breach rather than hide it.
        flag = (f"<span class='defect'>MISSING {', '.join(missing).upper()}</span>"
                if missing else "")
        sev = it.get("severity")
        badge = f"<span class='pill {sev_class(sev)}'>{esc(sev)}</span>" if sev else ""
        out.append(
            f"<tr class='{sev_class(sev) if sev else ''}'>"
            f"<td class='l'><b>{esc(it.get('item'))}</b>{badge}"
            f"<div class='zh'>{esc(it.get('item_zh'))}</div></td>"
            f"<td class='l'>{esc(it.get('value'))}{flag}"
            f"<div class='zh'>{esc(it.get('value_zh'))}</div></td>"
            f"<td class='l src'>{esc(it.get('source'))}<div class='date'>{esc(it.get('date'))}</div></td>"
            f"</tr>")
    return "".join(out)


def dd2_rows(items) -> str:
    return "".join(
        f"<tr><td class='l'><b>{esc(i.get('item'))}</b>"
        f"<div class='zh'>{esc(i.get('item_zh'))}</div></td>"
        f"<td class='c'><b>{esc(i.get('cost'))}</b></td>"
        f"<td class='c'><span class='pill {'sev-amber' if i.get('status')=='OUTSTANDING' else 'sev-low'}'>"
        f"{esc(i.get('status'))}</span></td>"
        f"<td class='l'>{esc(i.get('gets'))}<div class='zh'>{esc(i.get('gets_zh'))}</div>"
        f"<div class='why'>{esc(i.get('why'))}<div class='zh'>{esc(i.get('why_zh'))}</div></div></td></tr>"
        for i in items or [])


def alert_rows(items) -> str:
    out = []
    for a in items or []:
        gate = ("<span class='pill gate'>SELLER-GATED 需卖方授权</span>"
                if a.get("seller_gated") else "")
        out.append(
            f"<tr class='{sev_class(a.get('severity'))}'>"
            f"<td class='l'><b>{esc(a.get('item'))}</b>{gate}"
            f"<div class='zh'>{esc(a.get('item_zh'))}</div></td>"
            f"<td class='l'>{esc(a.get('why'))}<div class='zh'>{esc(a.get('why_zh'))}</div>"
            + (f"<div class='why'>{esc(a.get('note'))}<div class='zh'>{esc(a.get('note_zh'))}</div></div>"
               if a.get("note") else "")
            + f"</td>"
            f"<td class='l'>{esc(a.get('who'))}<div class='zh'>{esc(a.get('who_zh'))}</div></td>"
            f"<td class='c'>{esc(a.get('cost'))}</td>"
            f"<td class='c'><span class='pill {when_class(a.get('when'))}'>{esc(a.get('when'))}</span>"
            f"<div class='zh'>{esc(a.get('when_zh'))}</div></td>"
            f"</tr>")
    return "".join(out)


def claim_rows(items) -> str:
    return "".join(
        f"<tr><td class='l'>{esc(c.get('claim'))}<div class='zh'>{esc(c.get('claim_zh'))}</div></td>"
        f"<td class='c'>{esc(c.get('tier'))}</td>"
        f"<td class='l'>{esc(c.get('status'))}</td></tr>"
        for c in items or [])


CSS = """
:root{--ink:#16202b;--mut:#6b7a8c;--line:#e2e8f0;--bg:#fff;--red:#c0392b;--amber:#b7791f;
--grn:#2f6f4f;--chip:#f1f5f9}
*{box-sizing:border-box}
body{margin:0;background:#f6f8fa;color:var(--ink);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans CJK SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 70px}
h1{font-size:25px;margin:0 0 4px}
h2{font-size:17px;margin:34px 0 10px;padding-bottom:7px;border-bottom:2px solid var(--ink)}
.sub{color:var(--mut);font-size:13px;margin-bottom:16px}
.card{background:var(--bg);border:1px solid var(--line);border-radius:9px;padding:16px 18px;margin:12px 0}
.verdict{border-left:5px solid var(--grn);background:#f4fbf7}
.blocked{border-left:5px solid var(--red);background:#fdf4f3}
.arch{border-left:5px solid #4a6fa5;background:#f4f7fc}
table{width:100%;border-collapse:collapse;background:var(--bg);
border:1px solid var(--line);border-radius:9px;overflow:hidden;font-size:13.5px}
th{background:#eef2f6;text-align:left;padding:9px 11px;font-size:11.5px;
letter-spacing:.06em;text-transform:uppercase;color:#48566a}
td{padding:9px 11px;border-top:1px solid var(--line);vertical-align:top}
td.l{text-align:left}td.c{text-align:center;white-space:nowrap}
.zh{color:var(--mut);font-size:12.5px;margin-top:3px}
.src{font-size:11.5px;color:var(--mut);max-width:250px}
.date{font-variant-numeric:tabular-nums;margin-top:2px}
.why{margin-top:6px;padding-left:9px;border-left:2px solid var(--line);font-size:12.5px;color:#4a5768}
.pill{display:inline-block;padding:1px 7px;border-radius:9px;font-size:10.5px;
font-weight:700;text-transform:uppercase;margin-left:6px;letter-spacing:.04em}
.sev-red>td:first-child{box-shadow:inset 3px 0 0 var(--red)}
.sev-amber>td:first-child{box-shadow:inset 3px 0 0 var(--amber)}
.pill.sev-red{background:#fdecea;color:var(--red)}
.pill.sev-amber{background:#fdf3e2;color:var(--amber)}
.pill.sev-low{background:#eaf5ef;color:var(--grn)}
.pill.gate{background:#2b2b2b;color:#fff}
.pill.w-hard{background:#fdecea;color:var(--red)}
.pill.w-mid{background:#fdf3e2;color:var(--amber)}
.pill.w-soft{background:var(--chip);color:#48566a}
.defect{display:inline-block;margin-left:8px;padding:1px 6px;border-radius:4px;
background:var(--red);color:#fff;font-size:10px;font-weight:700}
.tiers{font-size:12.5px;color:#4a5768}
.tiers b{color:var(--ink)}
ul{margin:6px 0;padding-left:20px}
li{margin:3px 0}
.foot{margin-top:34px;color:var(--mut);font-size:11.5px;border-top:1px solid var(--line);padding-top:12px}
"""


def render(d: dict) -> str:
    v = d.get("verdict") or {}
    alerts = d.get("dd3_alerts") or []
    # The alert section is structural. Say so loudly rather than render an empty table.
    alert_body = alert_rows(alerts) if alerts else (
        "<tr><td colspan='5' class='l'><span class='defect'>CONTRACT BREACH</span> "
        "No deep-DD alerts recorded. A landed DD that escalates nothing did not look — "
        "this is a defect in the digest, not a clean result.</td></tr>")
    gated = sum(1 for a in alerts if a.get("seller_gated"))
    tax = d.get("tax_clock") or {}

    return f"""<!doctype html><html lang="en"><meta charset="utf-8">
<title>DD Report — {esc(d.get('address'))}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}</style>
<div class="wrap">
<h1>DD Report · {esc(d.get('address'))}</h1>
<div class="sub">{esc(d.get('address_zh'))} · Singapore {esc(d.get('postal'))} ·
{esc(d.get('lat'))}, {esc(d.get('lon'))} · as of {esc(d.get('as_of'))} ·
generated {date.today().isoformat()}</div>

<div class="card arch">
<b>Archetype 资产类型 · {esc(d.get('archetype'))}</b>
<div class="zh">{esc(d.get('archetype_zh'))}</div>
<div class="why">{esc(d.get('archetype_note'))}<div class="zh">{esc(d.get('archetype_note_zh'))}</div></div>
</div>

<div class="card verdict">
<b>Verdict 结论 · {esc(v.get('call'))}</b>
<div class="zh">{esc(v.get('call_zh'))}</div>
<div class="why">{esc(v.get('detail'))}<div class="zh">{esc(v.get('detail_zh'))}</div></div>
</div>

<div class="card blocked">
<b>&#9888; Blocked 数据阻断</b>
<ul>{''.join(f'<li>{esc(x)}</li>' for x in d.get('blocked') or [])}</ul>
<div class="zh"><ul>{''.join(f'<li>{esc(x)}</li>' for x in d.get('blocked_zh') or [])}</ul></div>
</div>

<div class="card tiers">
<b>It is all DD 全部都是 DD</b> — the tiers are about <b>who settles it and when</b>, not free vs paid.
<b>DD-1</b> you, desk, free, every candidate ·
<b>DD-2</b> you, desk, ~S$5–200, before offering ·
<b>DD-3</b> professional / on-site / <b>seller-gated</b>, OTP-conditioned.
<div class="zh">三层划分的依据是「谁能定、何时定」，不是「免费还是收费」。
DD-1 本人桌面、免费、每个候选都做；DD-2 本人桌面、约 S$5–200、出价前完成；
DD-3 专业/实地/<b>需卖方授权</b>，与 OTP 挂钩。</div>
</div>

<h2>1 · DD-1 verified — free, official, reproducible 免费官方可复现</h2>
<div class="sub">Every row carries value + source + date. A row without them renders as a defect.
每行必须有「数值 + 来源 + 日期」，缺一即标记为缺陷。</div>
<table><tr><th>Item 项目</th><th>Verified value 已核实数值</th><th>Source / date 来源与日期</th></tr>
{dd1_rows(d.get('dd1'))}</table>

<h2>2 · DD-2 — cheap, self-serve, belongs BEFORE the offer 出价前应完成</h2>
<table><tr><th>Item 项目</th><th>Cost 费用</th><th>Status 状态</th><th>What it settles 能解决什么</th></tr>
{dd2_rows(d.get('dd2'))}</table>
<div class="card"><div class="why">{esc(d.get('dd2_note'))}
<div class="zh">{esc(d.get('dd2_note_zh'))}</div></div></div>

<h2>&#9888; 3 · Deep-DD alerts 深入 DD 预警 &mdash; {len(alerts)} items, {gated} seller-gated</h2>
<div class="sub">What the desk cannot settle, who settles it, and <b>when in the deal it must happen</b>.
An item with no answer to &ldquo;when&rdquo; is a wish, not a finding. A landed OTP is typically
~14 days &mdash; survey + soil + PE does not fit inside it.<br>
<span class="zh">桌面无法解决的事项、由谁解决、以及<b>必须在交易的哪个节点完成</b>。
没有「何时」的条目只是愿望，不是结论。Landed 的 OTP 通常约 14 天 —— 测量 + 土壤 + 结构工程师报告塞不进去。</span></div>
<table><tr><th>Unresolved 未决事项</th><th>Why the desk can't settle it 桌面为何无法定论</th>
<th>Who settles it 由谁解决</th><th>Cost 费用</th><th>When 何时</th></tr>
{alert_body}</table>

<h2>4 · Tier-2 claims — NOT facts 门户说法，非事实</h2>
<table><tr><th>Claim 说法</th><th>Tier</th><th>Status 状态</th></tr>
{claim_rows(d.get('claims'))}</table>

<h2>5 · Tax clock 税务时钟</h2>
<div class="card blocked"><b>{esc(tax.get('source'))}</b>
<div>{esc(tax.get('note'))}</div><div class="zh">{esc(tax.get('note_zh'))}</div></div>

<div class="foot">
Generated by <code>deliverables/build_landed_dd_report.py</code> from
<code>researcher/landed/{esc(d.get('slug',''))}_dd.json</code> ·
skill <code>landed-property-due-diligence</code>.<br>
DD-1 rows are reproducible from free official sources with no account:
<code>researcher/sources/onemap.py</code> (address, distances) and
<code>researcher/sources/mp_zoning.py</code> (URA Master Plan 2025, gazetted 1 Dec 2025,
via data.gov.sg). This report contains no valuation — see Blocked.<br>
<span class="zh">DD-1 各行均可用免费官方来源、无需账号复现。本报告不含任何估值，原因见「数据阻断」。</span>
</div>
</div></html>"""


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    slug = sys.argv[1]
    src = os.path.join(ROOT, "researcher", "landed", f"{slug}_dd.json")
    with open(src, encoding="utf-8-sig") as f:
        d = json.load(f)
    d["slug"] = slug

    reports = os.environ.get("RESEARCH_REPORTS_DIR",
                             r"G:\My Drive\004 RES\REsearch_Reports")
    if not os.path.isdir(reports):
        reports = HERE  # Drive not mounted — keep the artifact next to the builder
    out = os.path.join(reports, f"{slug}_DD_Report.html")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(render(d))

    alerts = d.get("dd3_alerts") or []
    gated = [a["item"] for a in alerts if a.get("seller_gated")]
    print(f"-> {out}")
    print(f"   DD-1 verified rows : {len(d.get('dd1') or [])}")
    print(f"   DD-2 outstanding   : {sum(1 for i in d.get('dd2') or [] if i.get('status')=='OUTSTANDING')}")
    print(f"   deep-DD alerts     : {len(alerts)}  ({len(gated)} seller-gated)")
    for g in gated:
        print(f"     seller-gated: {g}")
    if not alerts:
        print("   WARNING: no deep-DD alerts — that is a digest defect, not a clean result.")


if __name__ == "__main__":
    main()
