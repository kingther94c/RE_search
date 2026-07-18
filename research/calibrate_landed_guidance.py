"""EXP-0013 / L4: calibrate the landed guidance quantiles against OUTCOMES.

The buyer/seller thresholds are read off the lease-matched, time+size-adjusted comp
distribution and LABELLED "cheap quartile" / "dear quartile". That label is a testable
claim: if p75 is really the dear quartile, an actual sale should land above it ~25% of the
time. A reviewer measured 44.8% (i.e. p75 was empirically the ~58th percentile of outcomes)
— the labels were asserted, never verified.

This walks real resales through the PRODUCTION path (as-of firewalled, the subject's own
print invisible) and reports where the actual sale falls versus the guidance quartiles, so
the label either earns its name or gets re-cut.

    python research/calibrate_landed_guidance.py [n_subjects]
"""
from __future__ import annotations

import datetime as _dt
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from researcher.backtest.index import PriceIndex
from researcher.engine.landed_engine import shipped_time_ctx
from researcher.backtest.landed_size_curve import size_factor
from researcher.backtest.market import MarketView
from researcher.backtest.store import TransactionStore, month_end
from researcher.engine.value_landed import _adjusted_comp_psfs, _pctl, _landed_store

QUANTILES = (0.10, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70, 0.75, 0.80, 0.90)


def _prev_ym(ym: str) -> str:
    y, m = (int(x) for x in ym.split("-"))
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def main():
    # default 800 = the invocation behind the SHIPPED marker rates (EXP-0017: n=547 scored,
    # p25 73.3/83.4, p75 31.6/37.8). A hostile reviewer re-ran the then-default 600 and got
    # p75 29.2% — OUTSIDE the quoted range — purely from the smaller sample: the documented
    # command must reproduce the documented number.
    n_want = int(sys.argv[1]) if len(sys.argv) > 1 else 800
    store = _landed_store(TransactionStore.load())
    idx = PriceIndex.load()
    subs = [t for t in store.txs
            if t["type_of_sale"] == "Resale" and t["contract_ym"] >= "2024-01"
            and t["street"] and 800 <= t["area_sqft"] <= 20000]
    subs = random.Random(7).sample(subs, min(n_want, len(subs)))

    # group by valuation month so the as-of view is built once per month
    by_month: dict[str, list[dict]] = {}
    for s in subs:
        by_month.setdefault(_prev_ym(s["contract_ym"]), []).append(s)

    # TIME SPLIT: choose the quantile on the EARLY slice, report it on the LATER one, so the
    # published "achieved" rate is not the number we tuned against (the same discipline the
    # conformal calibration uses).
    CUT = "2025-07"
    cal = {q: [0, 0] for q in QUANTILES}      # [above, n]
    test = {q: [0, 0] for q in QUANTILES}
    for asof_ym, group in by_month.items():
        t = month_end(asof_ym)
        mkt = MarketView(store.as_of(t, lag_days=56).txs, asof_ym)
        # NOTE: view built once more inside ctx below — kept identical (same as_of args)
        view = store.as_of(t, lag_days=56)
        ctx = {"asof_ym": asof_ym, "asof_date": t, "index": idx,
               "asof_q": idx.as_of_quarter(t),
               # the SHIPPED time adjustment (EXP-0017 lt_tail) — marker rates must be
               # measured under the same adjustment production applies
               **shipped_time_ctx(view.txs, asof_ym)}
        for s in group:
            adj = _adjusted_comp_psfs(s, mkt, ctx)
            if len(adj) < 4:
                continue
            bucket = cal if s["contract_ym"] < CUT else test
            for q in QUANTILES:
                bucket[q][1] += 1
                if s["psf"] > _pctl(adj, q):
                    bucket[q][0] += 1

    n_cal, n_test = cal[0.25][1], test[0.25][1]
    print(f"landed guidance calibration — production path, as-of firewalled\n"
          f"calibrate on <{CUT} (n={n_cal:,})  /  report on >={CUT} (n={n_test:,})\n")
    print(f"{'comp quantile':>14} | {'% ABOVE (cal)':>14} | {'% ABOVE (test)':>15} | target")
    print("-" * 70)
    for q in QUANTILES:
        c = cal[q][0] / cal[q][1] if cal[q][1] else 0
        te = test[q][0] / test[q][1] if test[q][1] else 0
        tgt = ("<- 'cheap' wants 75%" if q == 0.25 else
               "<- median wants 50%" if q == 0.50 else
               "<- 'dear' wants 25%" if q == 0.75 else "")
        print(f"{q:>14.2f} | {c*100:>13.1f}% | {te*100:>14.1f}% | {tgt}")

    # pick the upper quantile that delivers ~25% above on the CAL slice
    best = min(QUANTILES, key=lambda q: abs((cal[q][0] / cal[q][1] if cal[q][1] else 0) - 0.25))
    te_best = test[best][0] / test[best][1] if test[best][1] else 0
    lo_cal = cal[0.25][0] / cal[0.25][1] if cal[0.25][1] else 0
    lo_te = test[0.25][0] / test[0.25][1] if test[0.25][1] else 0
    print(f"\n-> CHOSEN on cal: HIGH_Q = p{best:.2f} (cal {cal[best][0]/cal[best][1]*100:.1f}% "
          f"above) -> held-out {te_best*100:.1f}% above (target 25%)")
    print(f"   LOW_Q = p0.25: cal {lo_cal*100:.1f}% / held-out {lo_te*100:.1f}% above "
          f"(target 75%)")
    print("\nRead: the comp distribution is NARROWER than the outcome distribution (adjustment "
          "shrinks spread; the subject carries condition/idiosyncratic variance the comps do "
          "not), so the 'dear' threshold must sit above p75 for the LABEL to be true.")


if __name__ == "__main__":
    main()
