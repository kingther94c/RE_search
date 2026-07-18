"""L1 noise-floor study (EXP-0010): how accurate can ANY landed bundle model be?

    python research/landed_noise_floor.py           # report
    python research/landed_noise_floor.py --json    # machine-readable

Same-plot repeat pairs with gap <= 18 months, price moved to the later trade's quarter
via the LANDED PPI. If valuation were information-complete, the adjusted ratio would be
1.0; its dispersion = bundle noise (condition changes + negotiation variance + timing
within the month) — the LOWER BOUND on achievable pricing accuracy for any model that
sees what URA sees. This number caps every accuracy claim the landed skill may make.

Honesty notes, both directions:
  - Renovation/rebuild inside the gap INFLATES the measured dispersion (the house really
    changed). The trimmed row (drops |annualized| > 60%) bounds that bias; the truth sits
    between "all pairs" and "trimmed".
  - This is an OFFLINE data property, not a walk-forward prediction: using the full
    published index history here is deliberate and leakage-irrelevant (documented).
  - Pair dispersion stacks TWO prints' noise: per-print floor = pair median / sqrt(2)
    under iid — reported alongside the raw pair number.
"""
from __future__ import annotations

import json
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from researcher.backtest.index import PriceIndex, q_of_ym
from researcher.backtest.landed_pairs import repeat_pairs
from researcher.backtest.store import LANDED_PSF_BAND, TransactionStore

MAX_GAP_MO = 18
REBUILD_ANN = 0.60          # |annualized| beyond this = rebuild/reno suspect (trim row)


def _pct(vals, q):
    s = sorted(vals)
    if not s:
        return None
    pos = q * (len(s) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def _stats(errs):
    if not errs:
        return None
    return {"n": len(errs),
            "median": round(_pct(errs, .5), 4),
            "p75": round(_pct(errs, .75), 4),
            "p90": round(_pct(errs, .9), 4),
            "per_print_floor_median": round(_pct(errs, .5) / math.sqrt(2), 4)}


def study(store: TransactionStore, index: PriceIndex) -> dict:
    clean = store.is_pure_landed().exclude_bulk().psf_band(*LANDED_PSF_BAND)
    pairs = [p for p in repeat_pairs(clean.txs) if 1 <= p["gap_months"] <= MAX_GAP_MO]

    rows = []
    for p in pairs:
        f = index.factor(p["a_ym"], q_of_ym(p["b_ym"]), "landed")
        r = p["b_price"] / (p["a_price"] * f)
        rows.append({**p, "adj_ratio": r, "abs_log_err": abs(math.log(r))})

    all_errs = [r["abs_log_err"] for r in rows]
    trimmed = [r["abs_log_err"] for r in rows
               if r["annualized"] is None or abs(r["annualized"]) <= REBUILD_ANN]

    by_type = defaultdict(list)
    by_gap = defaultdict(list)
    for r in rows:
        by_type[r["property_type"]].append(r["abs_log_err"])
        g = r["gap_months"]
        by_gap["1-6mo" if g <= 6 else "7-12mo" if g <= 12 else "13-18mo"].append(
            r["abs_log_err"])

    return {
        "pairs_used": len(rows),
        "trimmed_out_as_rebuild_suspects": len(rows) - len(trimmed),
        "all_pairs": _stats(all_errs),
        "trimmed": _stats(trimmed),
        "by_type": {k: _stats(v) for k, v in sorted(by_type.items())},
        "by_gap": {k: _stats(v) for k, v in sorted(by_gap.items())},
        "reading": "abs_log_err ~ APE for small errors. The achievable per-print floor "
                   "sits between trimmed and all-pairs per_print_floor_median; any model "
                   "claiming a median APE below it is overfit or leaking.",
    }


def main() -> None:
    rep = study(TransactionStore.load(), PriceIndex.load())
    if "--json" in sys.argv:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
        return
    print(f"same-plot pairs, gap 1..{MAX_GAP_MO}mo, landed-index adjusted: "
          f"{rep['pairs_used']} pairs ({rep['trimmed_out_as_rebuild_suspects']} "
          f"trimmed as rebuild suspects)")
    for name in ("all_pairs", "trimmed"):
        s = rep[name]
        print(f"  {name:<10} median {s['median']:.3f}  p75 {s['p75']:.3f}  "
              f"p90 {s['p90']:.3f}  -> per-print floor ~{s['per_print_floor_median']*100:.1f}%")
    print("  by type:")
    for k, s in rep["by_type"].items():
        print(f"    {k:<14} n={s['n']:<4} median {s['median']:.3f} "
              f"floor ~{s['per_print_floor_median']*100:.1f}%")
    print("  by gap:")
    for k, s in rep["by_gap"].items():
        print(f"    {k:<8} n={s['n']:<4} median {s['median']:.3f}")
    print(f"\n{rep['reading']}")


if __name__ == "__main__":
    main()
