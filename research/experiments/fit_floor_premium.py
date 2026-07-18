"""EXP-0008: re-fit the per-floor premium on URA (the last ported constant in C1).

FLOOR_PP=0.003/floor came from value-a-property and was never validated on URA — the same
guardrail-#5 defect class as the elasticity constant fixed in EXP-0007. Estimate it from
SAME-PROJECT, NEAR-SIMULTANEOUS (<=3mo), SIZE-SIMILAR (+/-10%) caveat pairs in DIFFERENT
floor bands, so the psf ratio isolates the floor effect:

    premium_pair = ln(psf_a / psf_b) / (band_mid_a - band_mid_b)

Median across pairs (robust to view/stack/reno noise), global and per segment.

    python research/fit_floor_premium.py
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

MAX_MONTHS = 3
MAX_LOG_AREA = 0.10        # near-identical size, so size doesn't contaminate the floor read
MIN_FLOOR_DELTA = 5        # different URA bands (mids are 5+ apart)
PAIRS_PER_PROJECT = 120


def _mid(t):
    lo, hi = t.get("floor_lo"), t.get("floor_hi")
    return (lo + hi) / 2 if lo is not None and hi is not None else None


def fit(store: TransactionStore):
    condo = store.is_condo()
    by_proj: dict[str, list[dict]] = defaultdict(list)
    for t in condo.txs:
        if t["project"] and _mid(t) is not None:
            by_proj[t["project"]].append(t)

    all_p: list[float] = []
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
            if abs(math.log(a["area_sqft"] / b["area_sqft"])) > MAX_LOG_AREA:
                continue
            df = _mid(a) - _mid(b)
            if abs(df) < MIN_FLOOR_DELTA:
                continue
            p = math.log(a["psf"] / b["psf"]) / df
            if -0.05 < p < 0.05:           # drop degenerate pairs (mispriced/data error)
                all_p.append(p)
                by_seg[a["market_segment"] or "?"].append(p)
    return all_p, by_seg


def main():
    store = TransactionStore.load().exclude_bulk().psf_band(500, 6500)
    all_p, by_seg = fit(store)
    s = sorted(all_p)
    print(f"pairs used: {len(all_p):,}")
    print(f"GLOBAL floor premium/floor  median={median(all_p):+.4f}  "
          f"p25={s[len(s)//4]:+.4f}  p75={s[3*len(s)//4]:+.4f}")
    for seg in ("CCR", "RCR", "OCR"):
        v = by_seg.get(seg, [])
        if v:
            print(f"  {seg}: median={median(v):+.4f}  n={len(v):,}")
    print("\ncurrent constant in candidates.py: FLOOR_PP = 0.003")


if __name__ == "__main__":
    main()
