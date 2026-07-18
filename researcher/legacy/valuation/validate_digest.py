"""Digest quality gates — the automated half of the hostile-analyst review.

Every check here encodes a defect that actually slipped into (or nearly
slipped into) a shipped report: stale point-estimate bases surviving a
re-valuation, BSD/mortgage lines computed off an old price, comps counts that
disagree with the table, markdown asterisks leaking into HTML, mojibake from
Windows codepages, Tier-3-sourced load-bearing rows. Run it after ANY digest
edit; the condo-valuation pipeline runs it automatically.

Usage:
    python -m researcher.legacy.valuation.validate_digest <digest.json> [--report <report.html>]

Exit 0 = all gates pass. Exit 1 = at least one FAIL (each printed with a fix
hint). Narrative TODO markers also fail — a digest ships only when a human/
model has replaced them.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

from researcher.tax import bsd

REQUIRED = ["subject", "asof", "summary", "valuation", "comps_table",
            "advisory", "verification", "data_gaps", "sources", "report_basename"]
SUBJECT_REQ = ["name", "size_sqft", "floor", "bedrooms", "tenure"]
VAL_REQ = ["estimate_psf", "estimate_price", "low_psf", "high_psf", "params_note", "grid"]
MOJIBAKE = ("�", "â€", "锘", "ï¼")
TIER1_MARKERS = ("Investment Suite", "URA", "caveat", "Tower View", "Profitability",
                 "Sale", "卖出腿", "REALIS")


def _strings(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from _strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from _strings(v)
    elif isinstance(o, str):
        yield o


def check(d: dict, report_path: str | None = None) -> list[dict]:
    res: list[dict] = []

    def gate(name: str, ok: bool, detail: str = "", fix: str = ""):
        res.append({"gate": name, "ok": bool(ok), "detail": detail, "fix": fix})

    # 1. schema
    missing = [k for k in REQUIRED if k not in d]
    gate("schema-keys", not missing, f"missing: {missing}" if missing else "all present",
         "add the missing sections (see an existing *_digest.json for the shape)")
    s, v = d.get("subject", {}), d.get("valuation", {})
    miss2 = [k for k in SUBJECT_REQ if k not in s] + [k for k in VAL_REQ if k not in v]
    gate("subject+valuation-fields", not miss2, f"missing: {miss2}" if miss2 else "complete",
         "fill subject/valuation fields (pipeline generates valuation)")

    # 2. arithmetic on the load-bearing numbers
    if all(k in v for k in ("estimate_psf", "estimate_price")) and s.get("size_sqft"):
        drift = abs(v["estimate_price"] - v["estimate_psf"] * s["size_sqft"])
        gate("price=psf*sqft", drift <= 2000,
             f"|{v['estimate_price']:,} - {v['estimate_psf']}*{s['size_sqft']}| = {drift:,.0f}",
             "regenerate valuation via the pipeline — do not hand-edit one side")
        gate("point-inside-range",
             v.get("low_psf", 0) <= v["estimate_psf"] <= v.get("high_psf", 10 ** 9),
             f"{v.get('low_psf')} <= {v['estimate_psf']} <= {v.get('high_psf')}",
             "regenerate valuation")

    # 3. one point-estimate base everywhere (the stale-base defect) — both the
    #    price scale (点估 S$1,716,000) and the psf scale (点估 ~S$2,309 psf)
    if "estimate_price" in v:
        est = int(v["estimate_price"])
        est_psf = int(v.get("estimate_psf") or 0)
        # numbers that legitimately appear next to 点估 in prose: the current
        # estimate, its band, the declared sensitivities and triangulation legs
        ok_psf = {est_psf, int(v.get("low_psf") or 0), int(v.get("high_psf") or 0)}
        ok_psf |= {int(x) for x in (v.get("sensitivity") or {}).values()
                   if isinstance(x, (int, float))}
        tri = v.get("triangulation") or {}
        ok_psf |= {int(x) for x in (tri.get("avm_cohort_median_psf"),
                                    tri.get("model_psf")) if x}
        ok_psf |= {int(x) for x in (tri.get("negotiation_band_psf") or [])}
        stale = set()
        for txt in _strings(d):
            for m in re.finditer(r"点估[（(]?[^0-9$]{0,8}S\$([\d,]{7,})", txt):
                n = int(m.group(1).replace(",", ""))
                if n >= 100_000 and n != est:
                    stale.add(f"S${n:,}")
            if est_psf:
                for m in re.finditer(r"点估[^0-9$]{0,6}~?S?\$?([\d,]{4,5}) psf", txt):
                    n = int(m.group(1).replace(",", ""))
                    if 500 <= n <= 20_000 and n not in ok_psf:
                        stale.add(f"{n:,} psf")
        gate("single-estimate-base", not stale,
             f"strings mention 点估 bases {sorted(stale)} but valuation says "
             f"S${est:,} / {est_psf:,} psf"
             if stale else f"all 点估 mentions = S${est:,} / {est_psf:,} psf",
             "sweep the digest with a .py patch script (never inline shell regex) "
             "or rerun the pipeline")

    # 4. BSD / mortgage recompute (cost stack must be on the current base)
    stack = " ".join(d.get("advisory", {}).get("cost_stack", []))
    m = re.search(r"BSD（点估 S\$([\d,]+)）≈ S\$([\d,]+)", stack)
    if m and "estimate_price" in v:
        base, claimed = (int(x.replace(",", "")) for x in m.groups())
        want = round(bsd(base))
        gate("bsd-recompute", base == int(v["estimate_price"]) and abs(claimed - want) <= 1,
             f"base S${base:,} (est S${int(v['estimate_price']):,}), BSD S${claimed:,} (recomputed S${want:,})",
             "regenerate cost_stack via the pipeline")
    m = re.search(r"75% LTV @([\d.]+)% 固定 ≈ S\$([\d,]+)/mo", stack)
    if m and "estimate_price" in v:
        rate = float(m.group(1)) / 100
        claimed = int(m.group(2).replace(",", ""))
        p = v["estimate_price"] * 0.75
        want = p * (rate / 12) / (1 - (1 + rate / 12) ** -360)
        gate("mortgage-recompute", abs(claimed - want) <= 2,
             f"claimed S${claimed:,}/mo vs recomputed S${want:,.0f}/mo",
             "regenerate cost_stack via the pipeline")

    # 5. comps count consistency
    n = len(d.get("comps_table", []))
    note = v.get("params_note", "")
    gate("comps-count-in-note", f"{n} 笔" in note,
         f"comps_table has {n} rows; params_note {'mentions' if f'{n} 笔' in note else 'does NOT mention'} '{n} 笔'",
         "regenerate params_note via the pipeline")

    # 6. rendering hygiene
    bad = [w for w in MOJIBAKE for t in _strings(d) if w in t]
    gate("no-mojibake", not bad, f"found {set(bad)}" if bad else "clean",
         "re-encode the offending strings (UTF-8, PYTHONIOENCODING=utf-8)")
    stars = [t[:60] for t in _strings(d) if "**" in t]
    gate("no-markdown-asterisks", not stars, f"e.g. {stars[:2]}" if stars else "clean",
         "strip ** — the HTML builder renders them literally")
    todos = [t[:60] for t in _strings(d) if "TODO" in t]
    gate("no-todo-placeholders", not todos, f"e.g. {todos[:2]}" if todos else "clean",
         "write the narrative sections (summary/risks/catalysts/advisory) before shipping")

    # 6b. per-row arithmetic on the comps table (a hostile review found 41
    #     cross-cell-misaligned rows where price != psf x sqft)
    bad_rows = [c.get("level") or c.get("date") for c in d.get("comps_table", [])
                if all(isinstance(c.get(k), (int, float)) for k in ("price", "psf", "size_sqft"))
                and abs(c["price"] - c["psf"] * c["size_sqft"]) / c["price"] > 0.02]
    gate("comps-rows-arithmetic", not bad_rows,
         f"{len(bad_rows)} rows fail price=psf*sqft (2%): {bad_rows[:4]}" if bad_rows
         else f"all {len(d.get('comps_table', []))} rows consistent",
         "re-run the pipeline — reconstruct_comps quarantines misaligned rows now")

    # 7. Tier-1 provenance on load-bearing rows
    untier = [c.get("level") or c.get("date") for c in d.get("comps_table", [])
              if not any(k in (c.get("note") or "") for k in TIER1_MARKERS)]
    gate("comps-tier1-provenance", not untier,
         f"rows without a Tier-1 marker in note: {untier[:4]}" if untier else "all tagged",
         "every comp must trace to Investment Suite / URA caveat data — "
         "reconstruct_comps tags this automatically")

    # 8. report render check
    if report_path:
        if not os.path.exists(report_path):
            gate("report-exists", False, report_path, "run deliverables/legacy/build_condo_report.py")
        else:
            html_txt = open(report_path, encoding="utf-8").read()
            gate("report-exists", True, f"{len(html_txt) / 1024:.0f} KB")
            gate("report-clean", not any(w in html_txt for w in MOJIBAKE) and len(html_txt) > 10_000,
                 "mojibake or truncation" if any(w in html_txt for w in MOJIBAKE) else "clean",
                 "rebuild the report with UTF-8 environment")
            if "estimate_psf" in v:
                tok = f"{int(v['estimate_psf']):,}"
                gate("report-has-current-estimate", tok in html_txt,
                     f"looked for '{tok}'", "rebuild the report from the current digest")
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("digest")
    ap.add_argument("--report", default=None)
    args = ap.parse_args()
    d = json.load(open(args.digest, encoding="utf-8"))
    results = check(d, args.report)
    fails = [r for r in results if not r["ok"]]
    for r in results:
        print(f"[{'PASS' if r['ok'] else 'FAIL'}] {r['gate']}: {r['detail']}")
        if not r["ok"] and r["fix"]:
            print(f"    -> {r['fix']}")
    print(f"\n{len(results) - len(fails)}/{len(results)} gates pass"
          + ("" if not fails else " — fix the FAILs above, then re-run"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
