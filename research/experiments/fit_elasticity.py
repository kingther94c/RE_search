"""EXP-0007: re-fit the condo size elasticity on URA (the reviewer's blocker).

psf ~ area^elasticity. Estimate it from SAME-PROJECT, NEAR-SIMULTANEOUS caveat pairs
(<=3 months apart, so the market barely moves and the ratio reflects size, not time):
    elasticity_pair = ln(psf_a/psf_b) / ln(area_a/area_b)
Aggregate the median across many pairs (robust to floor/stack/reno noise), globally and per
segment. This replaces the ported -0.08 constant with a validated figure.

    python research/fit_elasticity.py
"""
from __future__ import annotations

import math
import os
import random
import sys
from collections import defaultdict
from statistics import median

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from researcher.backtest.store import TransactionStore, months_between

MIN_LOG_AREA = 0.20     # only pairs whose sizes differ by >~22% (elasticity is ill-defined near 1)
MAX_MONTHS = 3          # near-simultaneous
PAIRS_PER_PROJECT = 120  # cap dense projects (random sample) so it stays O(n)


def fit(store: TransactionStore):
    condo = store.is_condo()
    by_proj: dict[str, list[dict]] = defaultdict(list)
    for t in condo.txs:
        if t["project"]:
            by_proj[t["project"]].append(t)

    all_e: list[float] = []
    by_seg: dict[str, list[float]] = defaultdict(list)
    rng = random.Random(42)
    for rows in by_proj.values():
        if len(rows) < 2:
            continue
        pairs = [(a, b) for i, a in enumerate(rows) for b in rows[i + 1:]]
        if len(pairs) > PAIRS_PER_PROJECT:
            pairs = rng.sample(pairs, PAIRS_PER_PROJECT)
        for a, b in pairs:
            if abs(months_between(a["contract_ym"], b["contract_ym"])) > MAX_MONTHS:
                continue
            la = math.log(a["area_sqft"] / b["area_sqft"])
            if abs(la) < MIN_LOG_AREA:
                continue
            e = math.log(a["psf"] / b["psf"]) / la
            if -1.0 < e < 0.5:              # drop degenerate/absurd pairs
                all_e.append(e)
                by_seg[a["market_segment"] or "?"].append(e)
    return all_e, by_seg


def main():
    store = TransactionStore.load().exclude_bulk().psf_band(500, 6500)
    all_e, by_seg = fit(store)
    print(f"pairs used: {len(all_e):,}")
    print(f"GLOBAL elasticity  median={median(all_e):+.3f}  "
          f"p25={sorted(all_e)[len(all_e)//4]:+.3f}  p75={sorted(all_e)[3*len(all_e)//4]:+.3f}")
    for seg in ("CCR", "RCR", "OCR"):
        v = by_seg.get(seg, [])
        if v:
            print(f"  {seg}: median={median(v):+.3f}  n={len(v):,}")
    print(f"\ncurrent constant in candidates.py: -0.08")


if __name__ == "__main__":
    main()
