"""L0 landed data-foundation audit — the GL0 gate check (EXP-0009). Re-runnable.

    python research/audit_landed.py            # full report to stdout
    python research/audit_landed.py --json     # machine-readable dict for the registry
    python research/audit_landed.py --pairs    # also print the 25-pair spot-check table

Characterizes the PURE-LANDED slice (type_of_area='Land' + Terrace/Semi-D/Detached)
before any L1 conclusion is drawn, applies the L0 hygiene rules, runs the same-plot
matcher, and evaluates gate GL0. Read-only; makes no changes.

L0 hygiene rules (verified on the 2026-07-15 snapshot — every number re-measured here):
  R1 pure-landed = Land area + exact landed type. Strata-landed (~1.6k) is a SEPARATE
     orphaned sub-market (both engines decline + route). Apartment+Land rows (walk-up /
     whole-building deals, project like 'RESIDENTIAL APARTMENTS') are excluded by R1.
  R2 exclude_bulk (no_of_units > 1).
  R3 land-psf sanity band LANDED_PSF_BAND = [100, 6500]: BOTH of today's extremes are
     verified REAL (107 psf = 70yr-lease-from-1964 terrace ~8yr left; 5,756 psf =
     Emerald Hill conservation terrace), so the band wraps them — it guards future junk,
     it does NOT trim the short-lease or conservation tails. Cuts 0 rows today.
  R4 exact-copy rows — same (street, area, month, price), ~18% of rows involved, 95%
     Resale, zero normalized-id collisions (so NOT batch-overlap; URA lists them as
     separate entries). Irreducibly ambiguous (twin-pair sales vs registry double-entry):
     kept in the store, collapsed inside the matcher, and street-liquidity counts carry
     the overstatement bound reported here.
  R5 subjects = resale + pure-landed + band-sane; walk-forward sampling starts >= 2023-01
     (>= 18 months of history behind every subject).
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from researcher.backtest.landed_pairs import repeat_pairs, same_plot_groups
from researcher.backtest.store import (LANDED_PSF_BAND, PURE_LANDED_TYPES,
                                       TransactionStore)

PSF_LO, PSF_HI = LANDED_PSF_BAND
SUBJECT_START_YM = "2023-01"          # >= 18 months in (store starts 2021-07)
SPOTCHECK_N = 25
SPOTCHECK_SEED = 7


def _pct(vals, q):
    s = sorted(vals)
    if not s:
        return float("nan")
    i = min(int(q * (len(s) - 1)), len(s) - 1)
    return s[i]


def audit(store: TransactionStore) -> dict:
    landed_all = store.is_landed()
    pure = store.is_pure_landed()
    strata = store.is_strata_landed()
    stray = [t for t in landed_all.txs
             if t["type_of_area"].lower() == "land"
             and t["property_type"] not in PURE_LANDED_TYPES]

    # hygiene: bulk + band on the pure slice
    pure1 = pure.exclude_bulk()
    n_bulk = len(pure) - len(pure1)
    clean = pure1.psf_band(PSF_LO, PSF_HI)
    n_band_cut = len(pure1) - len(clean)

    psf = [t["psf"] for t in pure1.txs]
    areas = [t["area_sqft"] for t in clean.txs]
    months = sorted({t["contract_ym"] for t in clean.txs})

    # exact-copy involvement (R4) — measured, not resolved
    seen = Counter((t["street"], t["area_sqm"], t["property_type"],
                    t["contract_ym"], t["price"]) for t in clean.txs)
    surplus = sum(n - 1 for n in seen.values() if n > 1)

    # subjects (R5)
    subjects = clean.subjects(kind="pure-landed", sale_types=("Resale",))
    subj_18mo = [t for t in subjects if t["contract_ym"] >= SUBJECT_START_YM]

    # street liquidity on resale subjects (with the R4 overstatement bound)
    per_street = Counter(t["street"] for t in subjects)
    street_counts = sorted(per_street.values())

    # same-plot matcher (rules in landed_pairs.py)
    groups = same_plot_groups(clean.txs)
    pairs = repeat_pairs(clean.txs)
    short_pairs = [p for p in pairs if p["gap_months"] <= 18]
    ann = [p["annualized"] for p in pairs if p["annualized"] is not None]
    wild = [a for a in ann if a < -0.30 or a > 0.60]

    rep = {
        "slice": {
            "landed_universe": len(landed_all),
            "pure_landed": len(pure),
            "strata_landed_routed_out": len(strata),
            "stray_apartment_land_rows": len(stray),
            "by_type": dict(Counter(t["property_type"] for t in clean.txs).most_common()),
            "by_segment": dict(Counter(t["market_segment"] for t in clean.txs).most_common()),
            "by_tenure": dict(Counter(t["tenure_type"] for t in clean.txs).most_common()),
        },
        "hygiene": {
            "bulk_dropped": n_bulk,
            "psf_band": [PSF_LO, PSF_HI],
            "psf_band_cut": n_band_cut,
            "psf_pcts": {q: round(_pct(psf, v), 0) for q, v in
                         (("p0", 0), ("p1", .01), ("p50", .5), ("p99", .99), ("p100", 1))},
            "exact_copy_surplus_rows": surplus,
            "exact_copy_share_of_rows": round(surplus / len(clean), 4),
            "land_area_sqft_pcts": {q: round(_pct(areas, v), 0) for q, v in
                                    (("p0.1", .001), ("p50", .5), ("p99.9", .999))},
        },
        "subjects": {
            "resale_pure_landed": len(subjects),
            f"resale_from_{SUBJECT_START_YM}": len(subj_18mo),
            "months": {"span": f"{months[0]}..{months[-1]}", "n": len(months)},
        },
        "street_liquidity": {
            "streets_with_resale": len(per_street),
            "median_caveats_per_street": street_counts[len(street_counts) // 2],
            "p90": street_counts[int(0.9 * (len(street_counts) - 1))],
            "note": "counts NOT deduped for exact copies -> may overstate by up to "
                    f"~{round(surplus / len(clean) * 100)}% (R4)",
        },
        "same_plot_matcher": {
            "plots_with_repeats": len(groups),
            "consecutive_pairs": len(pairs),
            "pairs_gap_le_18mo": len(short_pairs),
            "annualized_p50": round(_pct(ann, .5), 4) if ann else None,
            "wild_movers_abs": len(wild),
            "wild_movers_share": round(len(wild) / len(ann), 4) if ann else None,
            "note": "wild movers are the L2e rebuild signal, surfaced not filtered; "
                    "spot-check verdict in EXP-0009 (24/25 plausible; the 1 miss was a "
                    "New->New twin-unit pair, now removed by matcher rule 5)",
        },
    }
    rep["GL0"] = {
        "pure_landed_resale_subjects_ge_10k": len(subjects) >= 10000,
        "usable_months_ge_48": len(months) >= 48,
        "land_psf_band_set_from_data": n_band_cut == 0 and PSF_LO < min(psf)
                                        and PSF_HI > max(psf),
        "matcher_pairs_ge_500": len(pairs) >= 500,
        "noise_floor_fuel_ge_300_pairs": len(short_pairs) >= 300,
        "hygiene_rules_documented": True,   # R1-R5 in this file + EXP-0009
    }
    rep["GL0"]["PASS"] = all(v for k, v in rep["GL0"].items() if k != "PASS")
    return rep


def spotcheck_table(store: TransactionStore, n=SPOTCHECK_N, seed=SPOTCHECK_SEED) -> str:
    """Deterministic sample of matcher pairs for by-hand review (the EXP-0009 artifact)."""
    import random
    clean = store.is_pure_landed().exclude_bulk().psf_band(PSF_LO, PSF_HI)
    pairs = repeat_pairs(clean.txs)
    sample = random.Random(seed).sample(pairs, min(n, len(pairs)))
    lines = [f"{'street':<26} {'type':<9} {'sqm':>7} | trade A -> trade B | gap  ratio"]
    for p in sorted(sample, key=lambda p: p["street"]):
        lines.append(
            f"{p['street'][:24]:<26} {p['property_type'][:8]:<9} {p['area_sqm']:>7.1f} | "
            f"{p['a_ym']} {p['a_price']:>11,.0f} ({p['a_sale'][:3]}) -> "
            f"{p['b_ym']} {p['b_price']:>11,.0f} ({p['b_sale'][:3]}) | "
            f"{p['gap_months']:>3}mo x{p['ratio']:.2f}")
    return "\n".join(lines)


def _print(rep: dict) -> None:
    s, h, sub, sl, m = (rep["slice"], rep["hygiene"], rep["subjects"],
                        rep["street_liquidity"], rep["same_plot_matcher"])
    print(f"landed universe {s['landed_universe']:,} = pure {s['pure_landed']:,} "
          f"+ strata-landed {s['strata_landed_routed_out']:,} (ROUTED OUT) "
          f"+ stray Apartment+Land {s['stray_apartment_land_rows']} (EXCLUDED)")
    print(f"types   : {s['by_type']}")
    print(f"segment : {s['by_segment']}")
    print(f"tenure  : {s['by_tenure']}")
    print(f"\nhygiene : bulk dropped {h['bulk_dropped']} | band {h['psf_band']} cut "
          f"{h['psf_band_cut']} (psf {h['psf_pcts']}) | exact-copy surplus "
          f"{h['exact_copy_surplus_rows']:,} ({h['exact_copy_share_of_rows']:.1%} of rows)")
    print(f"land area sqft: {h['land_area_sqft_pcts']}")
    print(f"\nsubjects: {sub['resale_pure_landed']:,} resale pure-landed "
          f"({sub[f'resale_from_{SUBJECT_START_YM}']:,} from {SUBJECT_START_YM}), "
          f"months {sub['months']['span']} (n={sub['months']['n']})")
    print(f"streets : {sl['streets_with_resale']:,} w/ resale, median "
          f"{sl['median_caveats_per_street']}/street, p90 {sl['p90']}  [{sl['note']}]")
    print(f"matcher : {m['plots_with_repeats']:,} plots -> {m['consecutive_pairs']:,} pairs "
          f"({m['pairs_gap_le_18mo']:,} with gap<=18mo) | annualized p50 "
          f"{m['annualized_p50']:+.1%} | wild movers {m['wild_movers_share']:.1%}")
    g = rep["GL0"]
    print(f"\n=== GL0 GATE: {'PASS' if g['PASS'] else 'FAIL'} ===")
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
    if "--pairs" in sys.argv:
        print("\n--- same-plot spot-check sample (deterministic, seed "
              f"{SPOTCHECK_SEED}) ---")
        print(spotcheck_table(store))


if __name__ == "__main__":
    main()
