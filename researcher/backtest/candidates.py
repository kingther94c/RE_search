"""Candidate valuation methods that must BEAT the benchmarks to earn a skill slot.

C1 is the `value-a-property` adjustment grid ported to URA fields (the mandate's "treat
existing skills as candidate baselines", made literal). It is same-project comps adjusted
for time (PPI index, capped +/-25%), floor (band midpoint, 0.30%/floor) and size
(segment-specific elasticity, EXP-0007; size-matched comps preferred), similarity-weighted.
If C1 does not beat the plain same-project median (B2/B3), the grid adds nothing — a finding.
"""
from __future__ import annotations

import math

from .store import months_between

FLOOR_PP = 0.003        # per-floor premium (value-a-property default)
# psf ~ area^elasticity. Segment-specific, RE-FIT on URA same-project near-simultaneous
# pairs (EXP-0007, research/fit_elasticity.py): global median -0.068, but CCR is much
# flatter than OCR. Replaces the ported -0.08 constant (the reviewer's blocker).
SEG_ELASTICITY = {"CCR": -0.02, "RCR": -0.08, "OCR": -0.09}
DEFAULT_ELASTICITY = -0.07
SIZE_SIMILAR_LOGRATIO = 0.30   # ~+/-35% area: a shoebox must not set a large unit's value


def _mid(t) -> float | None:
    lo, hi = t.get("floor_lo"), t.get("floor_hi")
    return (lo + hi) / 2 if lo is not None and hi is not None else None


def _wquantile(pairs: list[tuple[float, float]], q: float) -> float:
    """Weighted quantile of (value, weight) pairs."""
    s = sorted(pairs)
    total = sum(w for _, w in s)
    if total <= 0:
        return s[len(s) // 2][0]
    cum, target = 0.0, q * total
    for v, w in s:
        cum += w
        if cum >= target:
            return v
    return s[-1][0]


def c1_grid_adapted(subject, mkt, ctx):
    """C1: value-a-property grid on URA data. Same-project, time/floor/size-adjusted,
    similarity-weighted median."""
    rows = mkt.same_project(subject["project"])
    if not rows:
        return None
    comps = None
    for win in (24, 36, 60):
        c = [r for r in rows if 0 <= months_between(r["contract_ym"], ctx["asof_ym"]) < win]
        if len(c) >= 3:
            comps = c
            break
    if comps is None:
        comps = rows[:5]  # fallback: the few most recent same-project prints

    area_s, fl_s = subject["area_sqft"], _mid(subject)
    # Size gating (EXP-0007): if >=3 same-project comps are within ~+/-35% of the subject
    # size, use ONLY those — extrapolating psf across a >1.5x size gap is unreliable, and a
    # shoebox trading at a high psf must not set a large unit's value. Fall back to the full
    # set (with elasticity doing more work) only when too few size-similar prints exist.
    similar = [c for c in comps
               if abs(math.log(c["area_sqft"] / area_s)) <= SIZE_SIMILAR_LOGRATIO]
    size_gated = len(similar) >= 3
    if size_gated:
        comps = similar
    elas = SEG_ELASTICITY.get(subject.get("market_segment"), DEFAULT_ELASTICITY)
    idx, to_q = ctx["index"], ctx["asof_q"]
    pairs: list[tuple[float, float]] = []
    for c in comps:
        raw_tf = idx.factor(c["contract_ym"], to_q, "non-landed") if to_q else 1.0
        tf = min(max(raw_tf, 0.80), 1.25)   # cap: a comp needing >25% index adj is unreliable
        fl_c = _mid(c)
        floor_adj = 1.0
        if fl_s is not None and fl_c is not None:
            floor_adj = min(max(1 + FLOOR_PP * (fl_s - fl_c), 0.85), 1.15)
        size_adj = (area_s / c["area_sqft"]) ** elas
        adj = c["psf"] * tf * floor_adj * size_adj
        dmonths = months_between(c["contract_ym"], ctx["asof_ym"])
        dfloor = abs((fl_s or 0) - (fl_c or 0))
        # Weight: heavier size penalty (x5), stronger recency (dmonths/15), and a
        # time-adjustment-QUALITY penalty abs(tf-1)*2 — a comp that needs a big index
        # adjustment (a stale print) is inherently lower-quality, so a fresh same-size
        # print outweighs an old one inflated +30% (EXP-0007 / the reviewer's stale-comp point).
        w = 1.0 / (1 + abs(math.log(area_s / c["area_sqft"])) * 5 + dfloor / 25
                   + dmonths / 15 + abs(raw_tf - 1.0) * 2)   # penalize TRUE staleness
        pairs.append((adj, w))

    psf = _wquantile(pairs, 0.50)
    area = area_s
    lo = round(_wquantile(pairs, 0.25) * area, 0) if len(pairs) >= 4 else None
    hi = round(_wquantile(pairs, 0.75) * area, 0) if len(pairs) >= 4 else None
    return {"method": "C1_grid_adapted", "psf": round(psf, 1), "price": round(psf * area, 0),
            "low": lo, "high": hi, "n_comps": len(comps),
            "note": f"grid, {len(comps)} same-project comps"
                    + (", size-matched" if size_gated else ", size-adjusted (few same-size)")}


CANDIDATES = {"C1_grid_adapted": c1_grid_adapted}
