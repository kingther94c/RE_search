"""EXP-0017 — L2b candidate runs against the PRE-REGISTERED gates (EXP-0016).

V1 (cap widening) is already REFUTED by EXP-0016 P3: cap-bound weight is ~0-7% and the
counterfactual moved nothing (2025H2 sign 66.5 -> 66.1). What P2 exposed instead: the
published quarter's midpoint is ~4.5 months stale at EVERY valuation date — invisible at
+0.9%/yr (2024), ~3.2-3.5% at +7.6%/yr (2025) — the size of the measured bias. GY-0003's
extrapolation failed because a trailing published trend is late at every turn; the fitted
LOCAL trend closes the gap with OBSERVATIONS (visible caveats reach ~asof-2mo).

Variants (walk-forward, full subjects, regime panel = sign / medSigned / medAPE / p90):
  V0 baseline      — shipped: PPI to last published quarter, cap 1.25 (reference)
  V2 lt_tail       — PPI leg (shipped cap) x fitted-trend bridge from max(comp month,
                     published quarter's mid month) to the newest fitted month <= asof
                     (per-comp anchor: a fresh comp must not be double-bridged; no forecast)
  V3 lt_full       — fitted trend as the whole adjustment (sanity clamp 0.5/2.0)
Also prints: fitted-trend vs PPI cumulative sanity, and T3 same-plot pair thinness.

Usage:  python research/run_l2b_variants.py [--sample N] [--variants V2,V3]
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from researcher.backtest.harness import walk_forward                    # noqa: E402
from researcher.backtest.index import PriceIndex                        # noqa: E402
from researcher.backtest.landed_engine import LANDED_ENGINE             # noqa: E402
from researcher.backtest.local_trend import fit_landed_trend            # noqa: E402
from researcher.backtest.store import LANDED_PSF_BAND, TransactionStore  # noqa: E402

HY = lambda ym: f"{ym[:4]}H{1 if int(ym[5:7]) <= 6 else 2}"


def trend_hook(view, ctx):
    lt = fit_landed_trend(view.txs, ctx["asof_ym"])
    return {"ltrend": lt}


def show(res, tag):
    s = res.summary()["LV1_landed_engine"]
    print(f"\n--- {tag}  (pooled: medAPE {s['median_ape']:.4f}  p90 {s['p90_ape']:.4f}  "
          f"sign {s['pct_actual_above']:.3f}  medSigned {s['median_signed']:+.4f}  "
          f"cover {s['coverage_rate']:.3f}) ---")
    reg = res.slice_by(lambda r: HY(r["contract_ym"]), "LV1_landed_engine")
    print(f"{'regime':<8}{'n':>6}{'sign':>8}{'medSigned':>11}{'medAPE':>9}{'p90':>9}")
    for hy, m in reg.items():
        print(f"{hy:<8}{m['n']:>6}{m['pct_actual_above']:>8.3f}"
              f"{m['median_signed']:>+11.4f}{m['median_ape']:>9.4f}{m['p90_ape']:>9.4f}")


def sanity_trend_vs_ppi(store, idx):
    """Fit ONCE on the full store (NOT as-of — sanity display only, never a backtest input)
    and compare cumulative movement against the published landed PPI."""
    lt = fit_landed_trend(store.txs, "2026-07")
    print("\n=== sanity: fitted local trend vs published landed PPI (cumulative) ===")
    print(f"fitted months: {lt.months[0]} .. {lt.last_ym}  "
          f"(n rows in terminal month: {lt.n_by_month.get(lt.last_ym)})")
    for a, b in (("2021-08", "2022-12"), ("2022-12", "2023-12"), ("2023-12", "2024-12"),
                 ("2024-12", "2025-12"), ("2025-12", lt.last_ym)):
        f_lt = lt.factor(a, b)
        f_ppi = idx.factor(a, b, "landed")
        print(f"  {a} -> {b}:  local {f_lt:.3f}   ppi {f_ppi:.3f}")


def t3_pair_thinness(store):
    """Same-plot repeat pairs per month — is a repeat-sales index even identifiable?"""
    by_plot = defaultdict(list)
    for t in store.txs:
        by_plot[(t["street"], round(t["area_sqft"], 0), t["property_type"])].append(
            t["contract_ym"])
    months = defaultdict(int)
    npairs = 0
    for yms in by_plot.values():
        yms = sorted(yms)
        for a, b in zip(yms, yms[1:]):
            if a != b:
                npairs += 1
                months[b] += 1
    per_mo = sorted(months.values())
    med = per_mo[len(per_mo) // 2] if per_mo else 0
    print(f"\n=== T3 same-plot repeat signal thinness ===")
    print(f"  {npairs} pairs over {len(months)} months -> median {med} pairs/month "
          f"(a monthly index needs ~30+; VERDICT: too thin, cross-check only)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--variants", default="V2,V3")
    args = ap.parse_args()

    store = (TransactionStore.load().is_pure_landed().exclude_bulk()
             .psf_band(*LANDED_PSF_BAND))
    subjects = store.subjects(kind="pure-landed", sale_types=("Resale",),
                              min_ym="2023-01")
    if args.sample and args.sample < len(subjects):
        import random
        subjects = random.Random(42).sample(subjects, args.sample)
    print(f"pure-landed caveats {len(store):,}; subjects {len(subjects):,}")
    idx = PriceIndex.load()

    sanity_trend_vs_ppi(store, idx)
    t3_pair_thinness(store)

    want = {v.strip().upper() for v in args.variants.split(",")}
    if "V0" in want:
        show(walk_forward(store, subjects, LANDED_ENGINE), "V0 baseline (shipped)")
    if "V2" in want:
        show(walk_forward(store, subjects, LANDED_ENGINE,
                          extra_ctx={"tadj_mode": "lt_tail"}, ctx_hook=trend_hook),
             "V2 lt_tail (PPI + observed bridge)")
    if "V3" in want:
        show(walk_forward(store, subjects, LANDED_ENGINE,
                          extra_ctx={"tadj_mode": "lt_full"}, ctx_hook=trend_hook),
             "V3 lt_full (fitted trend only)")


if __name__ == "__main__":
    main()
