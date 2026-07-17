"""EXP-0016 — L2b diagnosis: WHY does the landed engine run low in accelerating regimes?

Mechanism under test (the cap-binding hypothesis): `_tadj_psf` clamps the PUBLISHED
landed-PPI factor at TIME_ADJ_CAP=(0.80,1.25) while LC2's comp window is 60 months.
The published index moved x1.335 from 2021Q3 to 2025Q4 — so for late-2025+ valuations
the cap swallows up to ~8.5pp of PUBLISHED growth on old comps, while for 2023-24
valuations the store's oldest comp (2021-07) never needs >x1.21 and the cap never binds.
That timing exactly matches the sign-test swing (47.6-51.6% in 2023-24 -> 66.3-66.5%
in 2025) that GY-0003's index-momentum hack failed to fix (it repriced the wrong layer:
the tail beyond the published quarter, not the swallowed published growth).

Three measurements, no fitting:
  P1  cap-binding exposure: per subject, LC2's own comp universe -> weight share with
      uncapped factor > cap_hi, and the weighted capped-away log gap. By half-year.
  P2  last-mile staleness: months from the last PUBLISHED quarter's midpoint to the
      as-of month, by half-year (bounds what a fitted local trend could still add).
  P3  counterfactual leaderboard: LV1 with tadj_cap hi in {1.25 (shipped), 1.60, 2.50},
      regime table (sign / median_signed / medAPE) per variant. If widening the cap
      repairs 2025 without breaking 2023-24, the mechanism is confirmed.

Usage:  python research/diagnose_l2b.py [--sample N] [--skip-runs]
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from collections import defaultdict
from statistics import median

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from researcher.backtest.harness import walk_forward, _prev_ym          # noqa: E402
from researcher.backtest.index import PriceIndex, quarter_end           # noqa: E402
from researcher.backtest.landed_benchmarks import (TIME_ADJ_CAP, _recent)  # noqa: E402
from researcher.backtest.landed_candidates import (CRAFT_HALFLIFE_MO,   # noqa: E402
                                                   lease_compatible)
from researcher.backtest.landed_engine import LANDED_ENGINE             # noqa: E402
from researcher.backtest.market import MarketView                       # noqa: E402
from researcher.backtest.store import (LANDED_PSF_BAND, TransactionStore,  # noqa: E402
                                       month_end, months_between)

HY = lambda ym: f"{ym[:4]}H{1 if int(ym[5:7]) <= 6 else 2}"


def load():
    store = (TransactionStore.load().is_pure_landed().exclude_bulk()
             .psf_band(*LANDED_PSF_BAND))
    subjects = store.subjects(kind="pure-landed", sale_types=("Resale",),
                              min_ym="2023-01")
    return store, subjects


def p1_p2_exposure(store, subjects, idx):
    """Cap-binding weight share + capped-away gap inside LC2's own comp universe,
    and the published-quarter staleness — both by subject half-year."""
    by_month = defaultdict(list)
    for s in subjects:
        by_month[_prev_ym(s["contract_ym"])].append(s)

    expo = defaultdict(list)      # HY -> per-subject capped-away weighted mean ln gap
    share = defaultdict(list)     # HY -> per-subject weight share of cap-bound comps
    stale = defaultdict(list)     # HY -> months from published-quarter midpoint to asof
    for asof_ym in sorted(by_month):
        t = month_end(asof_ym)
        view = store.as_of(t, 56)
        mkt = MarketView(view.txs, asof_ym)
        to_q = idx.as_of_quarter(t)
        if not to_q:
            continue
        # staleness: quarter midpoint ~= 45d before quarter end
        qe = quarter_end(to_q)
        stale_mo = (t - qe).days / 30.44 + 1.5
        for subj in by_month[asof_ym]:
            hy = HY(subj["contract_ym"])
            stale[hy].append(stale_mo)
            street = _recent([r for r in mkt.landed_on_street(subj["street"])
                              if r["property_type"] == subj["property_type"]],
                             {"asof_ym": asof_ym}, window=60)
            comps = [r for r in street if lease_compatible(r, subj, asof_ym)]
            if not comps:
                continue
            wtot = wbound = gap = 0.0
            for c in comps:
                f = idx.factor(c["contract_ym"], to_q, "landed")
                fc = min(max(f, TIME_ADJ_CAP[0]), TIME_ADJ_CAP[1])
                age = months_between(c["contract_ym"], asof_ym)
                w = 0.5 ** (age / CRAFT_HALFLIFE_MO)
                wtot += w
                if f > TIME_ADJ_CAP[1] or f < TIME_ADJ_CAP[0]:
                    wbound += w
                    gap += w * (math.log(f) - math.log(fc))
            if wtot > 0:
                share[hy].append(wbound / wtot)
                expo[hy].append(gap / wtot)

    print("\n=== P1 cap-binding exposure inside LC2's comp universe (by half-year) ===")
    print(f"{'regime':<8}{'n_subj':>7}{'mean w-share bound':>20}"
          f"{'mean capped-away':>18}{'p90 capped-away':>17}")
    for hy in sorted(share):
        sh, ex = share[hy], sorted(expo[hy])
        p90 = ex[int(0.9 * (len(ex) - 1))] if ex else 0.0
        print(f"{hy:<8}{len(sh):>7}{sum(sh)/len(sh):>19.1%}"
              f"{sum(ex)/len(ex):>17.2%}{p90:>16.2%}")

    print("\n=== P2 published-quarter staleness at the valuation date (months) ===")
    for hy in sorted(stale):
        v = stale[hy]
        print(f"  {hy}: mean {sum(v)/len(v):.1f}mo  (range {min(v):.1f}-{max(v):.1f})")


def p3_counterfactuals(store, subjects, caps, max_subjects=None):
    print("\n=== P3 counterfactual: LV1 under tadj_cap variants ===")
    for hi in caps:
        res = walk_forward(store, subjects, LANDED_ENGINE,
                           extra_ctx={"tadj_cap": (0.80, hi)},
                           max_subjects=max_subjects)
        s = res.summary()["LV1_landed_engine"]
        print(f"\n--- cap hi = {hi}  (pooled: medAPE {s['median_ape']:.4f}  "
              f"p90 {s['p90_ape']:.4f}  sign {s['pct_actual_above']:.3f}  "
              f"medSigned {s['median_signed']:+.4f}  cover {s['coverage_rate']:.3f}) ---")
        reg = res.slice_by(lambda r: HY(r["contract_ym"]), "LV1_landed_engine")
        print(f"{'regime':<8}{'n':>6}{'sign':>8}{'medSigned':>11}{'medAPE':>9}{'p90':>9}")
        for hy, m in reg.items():
            print(f"{hy:<8}{m['n']:>6}{m['pct_actual_above']:>8.3f}"
                  f"{m['median_signed']:>+11.4f}{m['median_ape']:>9.4f}"
                  f"{m['p90_ape']:>9.4f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--skip-runs", action="store_true", help="P1/P2 only")
    ap.add_argument("--caps", default="1.25,1.60,2.50")
    args = ap.parse_args()

    store, subjects = load()
    if args.sample and args.sample < len(subjects):
        import random
        subjects = random.Random(42).sample(subjects, args.sample)
    print(f"pure-landed caveats {len(store):,}; subjects {len(subjects):,}")
    idx = PriceIndex.load()

    p1_p2_exposure(store, subjects, idx)
    if not args.skip_runs:
        p3_counterfactuals(store, subjects,
                           [float(c) for c in args.caps.split(",")])


if __name__ == "__main__":
    main()
