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

from .benchmarks import BENCHMARKS
from .harness import walk_forward
from .store import TransactionStore

_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_condo.json")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=None, help="cap #subjects (quick run)")
    ap.add_argument("--min-ym", default=None, help="earliest subject month YYYY-MM")
    ap.add_argument("--max-ym", default=None, help="latest subject month YYYY-MM")
    ap.add_argument("--lag-days", type=int, default=56, help="caveat visibility buffer")
    ap.add_argument("--slice", default=None, help="dimension to break a method down by")
    ap.add_argument("--method", default="B1_latest_same_project")
    args = ap.parse_args()

    store = TransactionStore.load()
    subjects = store.subjects(kind="condo", sale_types=("Resale",),
                              min_ym=args.min_ym, max_ym=args.max_ym)
    print(f"store: {len(store):,} caveats; subjects: {len(subjects):,} resale condos")
    if not subjects:
        print("no subjects — is the store populated and the date window sane?")
        return

    res = walk_forward(store, subjects, BENCHMARKS, lag_days=args.lag_days,
                       max_subjects=args.max)
    print("\n=== benchmark leaderboard (sorted by median APE) ===")
    print(res.table())

    if args.slice:
        print(f"\n=== {args.method} by {args.slice} ===")
        for bucket, m in res.slice(args.slice, args.method).items():
            print(f"  {bucket:<10} n={m.get('n',0):<6} "
                  f"medAPE={m.get('median_ape','')} p90={m.get('p90_ape','')} "
                  f"cover={m.get('coverage_rate','')}")

    with open(_OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"summary": res.summary(), "n_subjects": len(subjects)}, f,
                  ensure_ascii=False, indent=1)
    print(f"\n-> {_OUT}")


if __name__ == "__main__":
    main()
