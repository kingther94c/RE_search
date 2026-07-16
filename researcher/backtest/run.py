"""Run the condo-resale walk-forward backtest against the simple benchmarks.

    python -m researcher.backtest.run                       # all resale condos
    python -m researcher.backtest.run --max 500 --min-ym 2024-01
    python -m researcher.backtest.run --slice market_segment --method B1_latest_same_project

Prereq: researcher/sources/ura_transactions.json exists
        (python -m researcher.sources.ura). Prints the benchmark leaderboard; the first
        method that beats these on median/P90 APE earns a registry entry, not before.
"""
from __future__ import annotations

import argparse
import json
import os
import random

from .avm import ANCHORS
from .avm_knn import KNN_ANCHORS
from .avm_pooled import ANCHORS_POOLED
from .benchmarks import BENCHMARKS
from .candidates import CANDIDATES
from .ensemble import ENSEMBLES
from .ensemble_learned import ENSEMBLES_LEARNED
from .engine_v2 import ENGINE_V2
from .harness import walk_forward
from .store import TransactionStore

_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_condo.json")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=None, help="cap #subjects (quick run)")
    ap.add_argument("--sample", type=int, default=None, help="random subject sample (seed 42)")
    ap.add_argument("--min-ym", default="2023-01",
                    help="earliest subject month (>=18mo history; YYYY-MM)")
    ap.add_argument("--max-ym", default=None, help="latest subject month YYYY-MM")
    ap.add_argument("--lag-days", type=int, default=56, help="caveat visibility buffer")
    ap.add_argument("--slice", default=None, help="single dimension to break down by")
    ap.add_argument("--slices", action="store_true", help="standard G1 slice panel")
    ap.add_argument("--dump", default=None, help="save all per-subject rows to JSON path")
    ap.add_argument("--method", default="C1_grid_adapted")
    args = ap.parse_args()

    # R0 hygiene: drop bulk/en-bloc and gross psf outliers as subject AND comp
    store = TransactionStore.load().exclude_bulk().psf_band(500, 6500)
    subjects = store.subjects(kind="condo", sale_types=("Resale",),
                              min_ym=args.min_ym, max_ym=args.max_ym)
    if args.sample and args.sample < len(subjects):
        subjects = random.Random(42).sample(subjects, args.sample)
    print(f"store: {len(store):,} caveats (cleaned); subjects: {len(subjects):,} "
          f"resale condos (>= {args.min_ym})")
    if not subjects:
        print("no subjects — is the store populated and the date window sane?")
        return

    methods = {**BENCHMARKS, **CANDIDATES, **ANCHORS, **ANCHORS_POOLED,
               **KNN_ANCHORS, **ENSEMBLES, **ENSEMBLES_LEARNED, **ENGINE_V2}
    res = walk_forward(store, subjects, methods,
                       lag_days=args.lag_days, max_subjects=args.max)
    print("\n=== benchmark leaderboard (sorted by median APE) ===")
    print(res.table())

    def _liq(r):
        n = r["n_comps"]
        return "0" if n == 0 else "1-2" if n <= 2 else "3-5" if n <= 5 \
            else "6-15" if n <= 15 else "16+"

    def _quantum(r):
        p = r["actual"]
        return "<1.0M" if p < 1e6 else "1-1.5M" if p < 1.5e6 else "1.5-2.5M" \
            if p < 2.5e6 else "2.5-4M" if p < 4e6 else ">4M"

    def _show(title, d):
        print(f"\n=== {args.method} by {title} ===")
        for b, m in d.items():
            print(f"  {b:<10} n={m.get('n', 0):<6} medAPE={m.get('median_ape', ''):<8}"
                  f"p90={m.get('p90_ape', ''):<8} >10%={m.get('pct_over_10', ''):<8}"
                  f"cover={m.get('coverage_rate', '')}")

    if args.slices:
        _show("segment", res.slice("market_segment", args.method))
        _show("tenure", res.slice("tenure_type", args.method))
        _show("regime(year)", res.slice_by(lambda r: r["contract_ym"][:4], args.method))
        _show("liquidity(#comps)", res.slice_by(_liq, args.method))
        _show("quantum", res.slice_by(_quantum, args.method))
    elif args.slice:
        _show(args.slice, res.slice(args.slice, args.method))

    with open(_OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"summary": res.summary(), "n_subjects": len(subjects)}, f,
                  ensure_ascii=False, indent=1)
    print(f"\n-> {_OUT}")

    if args.dump:
        keep = ("method", "market_segment", "tenure_type", "contract_ym", "n_comps",
                "actual", "pred", "lo", "hi")
        with open(args.dump, "w", encoding="utf-8", newline="\n") as f:
            json.dump([{k: r.get(k) for k in keep} for r in res.rows], f, ensure_ascii=False)
        print(f"-> dumped {len(res.rows)} rows to {args.dump}")


if __name__ == "__main__":
    main()
