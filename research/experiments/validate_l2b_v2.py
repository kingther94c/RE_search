"""EXP-0017 (cont.) — V2 lt_tail remaining validation before any integration:
  1. lag stability 42/56/70 (pre-registered A6: medAPE within +-0.3pp of lag 56);
  2. FULL leaderboard under V2 (shared _tadj_psf -> the LC1 bar moves too; LV1 must
     still clear it apples-to-apples) + the GL1 slice panel for LV1;
  3. --dump rows for the conformal recalibration (analyze_landed.py).

Usage:  python research/validate_l2b_v2.py --dump research/rows_l2b_v2.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from researcher.backtest.harness import walk_forward                    # noqa: E402
from researcher.backtest.landed_benchmarks import LANDED_BENCHMARKS     # noqa: E402
from researcher.backtest.landed_candidates import LANDED_CANDIDATES     # noqa: E402
from researcher.engine.landed_engine import LANDED_ENGINE             # noqa: E402
from researcher.backtest.local_trend import fit_landed_trend            # noqa: E402
from researcher.backtest.store import LANDED_PSF_BAND, TransactionStore  # noqa: E402

HY = lambda ym: f"{ym[:4]}H{1 if int(ym[5:7]) <= 6 else 2}"
V2 = {"tadj_mode": "lt_tail"}


def hook(view, ctx):
    return {"ltrend": fit_landed_trend(view.txs, ctx["asof_ym"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", default=None)
    args = ap.parse_args()

    store = (TransactionStore.load().is_pure_landed().exclude_bulk()
             .psf_band(*LANDED_PSF_BAND))
    subjects = store.subjects(kind="pure-landed", sale_types=("Resale",),
                              min_ym="2023-01")
    print(f"subjects {len(subjects):,}")

    print("\n=== A6 lag stability (LV1 under V2) ===")
    for lag in (42, 56, 70):
        res = walk_forward(store, subjects, LANDED_ENGINE, lag_days=lag,
                           extra_ctx=V2, ctx_hook=hook)
        s = res.summary()["LV1_landed_engine"]
        print(f"  lag {lag}d: medAPE {s['median_ape']:.4f}  p90 {s['p90_ape']:.4f}  "
              f"sign {s['pct_actual_above']:.3f}  medSigned {s['median_signed']:+.4f}")

    print("\n=== full leaderboard under V2 (bar and engine on the SAME adjustment) ===")
    res = walk_forward(store, subjects,
                       {**LANDED_BENCHMARKS, **LANDED_CANDIDATES, **LANDED_ENGINE},
                       lag_days=56, extra_ctx=V2, ctx_hook=hook)
    print(res.table())

    def _liq(r):
        n = r["n_comps"]
        return "0" if n == 0 else "1-2" if n <= 2 else "3-5" if n <= 5 \
            else "6-15" if n <= 15 else "16+"

    def _size(r):
        a = r["area_sqft"]
        return "<1.5k" if a < 1500 else "1.5-3k" if a < 3000 else "3-5k" \
            if a < 5000 else "5-8k" if a < 8000 else "8-15k" if a < 15000 else "15k+"

    def _show(title, d):
        print(f"\n=== LV1(V2) by {title} ===")
        for b, m in d.items():
            print(f"  {b:<14} n={m.get('n', 0):<6} medAPE={m.get('median_ape', ''):<8}"
                  f"p90={m.get('p90_ape', ''):<8}sign={m.get('pct_actual_above', ''):<8}"
                  f"medSigned={m.get('median_signed', ''):<9}")

    M = "LV1_landed_engine"
    _show("type", res.slice("property_type", M))
    _show("tenure", res.slice("tenure_type", M))
    _show("segment", res.slice("market_segment", M))
    _show("land size", res.slice_by(_size, M))
    _show("street-liquidity", res.slice_by(_liq, M))
    _show("regime(half-year)", res.slice_by(lambda r: HY(r["contract_ym"]), M))

    if args.dump:
        keep = ("method", "street", "market_segment", "district", "property_type",
                "tenure_type", "contract_ym", "area_sqft", "n_comps",
                "actual", "pred", "lo", "hi")
        with open(args.dump, "w", encoding="utf-8", newline="\n") as f:
            json.dump([{k: r.get(k) for k in keep} for r in res.rows], f,
                      ensure_ascii=False)
        print(f"\n-> dumped {len(res.rows)} rows to {args.dump}")


if __name__ == "__main__":
    main()
