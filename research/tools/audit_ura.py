"""R0 data-foundation audit — characterize the URA store before any conclusion is drawn.

    python research/audit_ura.py            # full report to stdout
    python research/audit_ura.py --json     # machine-readable dict for the registry

Answers the G0 gate: enough months / subjects / projects? And surfaces what must be
EXCLUDED (bulk deals, outliers, EC, townhouses) before the store feeds the harness.
Read-only; makes no changes.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from researcher.backtest.store import TransactionStore

OUT_PSF_LO, OUT_PSF_HI = 500, 6500        # psf sanity band (private residential)
LIQUID_MIN = 8                            # same-project caveats to call a project liquid


def _pct(vals, q):
    s = sorted(vals)
    if not s:
        return float("nan")
    i = min(int(q * (len(s) - 1)), len(s) - 1)
    return s[i]


def audit(store: TransactionStore) -> dict:
    txs = store.txs
    months = sorted({t["contract_ym"] for t in txs})
    seg = Counter(t["market_segment"] or "?" for t in txs)
    ptype = Counter(t["property_type"] or "?" for t in txs)
    sale = Counter(t["type_of_sale"] or "?" for t in txs)
    tenure = Counter(t["tenure_type"] for t in txs)

    condo = store.is_condo()               # Apartment+Condominium, strata, EC excluded
    landed = store.is_landed()
    ec = [t for t in txs if t["property_type"] == "Executive Condominium"]

    # resale-condo subjects under current default rules
    subjects = store.subjects(kind="condo", sale_types=("Resale",))

    # same-project liquidity among condo caveats
    proj_counts = Counter(t["project"] for t in condo.txs if t["project"])
    liquid = [p for p, c in proj_counts.items() if c >= LIQUID_MIN]

    # psf outliers & bulk deals
    psf_all = [t["psf"] for t in txs]
    out_lo = [t for t in txs if t["psf"] < OUT_PSF_LO]
    out_hi = [t for t in txs if t["psf"] > OUT_PSF_HI]
    bulk = [t for t in txs if t["no_of_units"] > 1]

    # monthly density (condo resale) — thin-month check
    monthly = Counter(t["contract_ym"] for t in subjects)
    thin = sorted(m for m in months if monthly.get(m, 0) < 50)

    rep = {
        "n_transactions": len(txs),
        "months": {"span": f"{months[0]}..{months[-1]}", "n": len(months)},
        "by_segment": dict(seg),
        "by_property_type": dict(ptype.most_common()),
        "by_sale_type": dict(sale),
        "by_tenure_type": dict(tenure),
        "condo_universe": len(condo.txs),
        "landed_universe": len(landed.txs),
        "ec_excluded": len(ec),
        "resale_condo_subjects": len(subjects),
        "distinct_condo_projects": len(proj_counts),
        f"liquid_projects_ge{LIQUID_MIN}": len(liquid),
        "psf": {"min": round(min(psf_all), 0), "p1": round(_pct(psf_all, .01), 0),
                "p50": round(_pct(psf_all, .5), 0), "p99": round(_pct(psf_all, .99), 0),
                "max": round(max(psf_all), 0)},
        "outliers": {f"psf_lt_{OUT_PSF_LO}": len(out_lo), f"psf_gt_{OUT_PSF_HI}": len(out_hi)},
        "bulk_deals_gt1_unit": len(bulk),
        "thin_subject_months_lt50": thin,
        # G0 gate
        "G0": {
            "months_ge_48": len(months) >= 48,
            "subjects_ge_20k": len(subjects) >= 20000,
            "projects_ge_800": len(proj_counts) >= 800,
        },
    }
    rep["G0"]["PASS"] = all(v for k, v in rep["G0"].items() if k != "PASS")
    return rep


def _print(rep: dict) -> None:
    print(f"URA store: {rep['n_transactions']:,} caveats, "
          f"{rep['months']['span']} ({rep['months']['n']} months)")
    print("\nsegment :", rep["by_segment"])
    print("sale    :", rep["by_sale_type"])
    print("tenure  :", rep["by_tenure_type"])
    print("types   :", rep["by_property_type"])
    print(f"\ncondo universe (Apt+Condo, EC excl): {rep['condo_universe']:,}")
    print(f"landed universe                    : {rep['landed_universe']:,}")
    print(f"EC excluded                        : {rep['ec_excluded']:,}")
    print(f"resale-condo SUBJECTS              : {rep['resale_condo_subjects']:,}")
    print(f"distinct condo projects           : {rep['distinct_condo_projects']:,}  "
          f"(liquid >={LIQUID_MIN}: {rep[f'liquid_projects_ge{LIQUID_MIN}']:,})")
    print(f"\npsf distribution: {rep['psf']}")
    print(f"outliers        : {rep['outliers']}   bulk(>1 unit): {rep['bulk_deals_gt1_unit']:,}")
    if rep["thin_subject_months_lt50"]:
        print(f"thin subject-months (<50): {rep['thin_subject_months_lt50']}")
    g = rep["G0"]
    print(f"\n=== G0 GATE: {'PASS' if g['PASS'] else 'FAIL'} ===")
    for k, v in g.items():
        if k != "PASS":
            print(f"  {'OK ' if v else 'XX '} {k}")


def main() -> None:
    store = TransactionStore.load()
    rep = audit(store)
    if "--json" in sys.argv:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        _print(rep)


if __name__ == "__main__":
    main()
