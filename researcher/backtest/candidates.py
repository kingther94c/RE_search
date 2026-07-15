"""Candidate valuation methods that must BEAT the benchmarks to earn a skill slot.

C1 is the `value-a-property` adjustment grid ported to URA fields (the mandate's "treat
existing skills as candidate baselines", made literal). It is same-project comps adjusted
for time (PPI index), floor (band midpoint, 0.30%/floor) and size (elasticity -0.08), then
similarity-weighted. If C1 does not beat the plain same-project median (B2/B3), the grid's
adjustments add nothing on URA data — itself a finding.
"""
from __future__ import annotations

import math

from .store import months_between

FLOOR_PP = 0.003        # per-floor premium (value-a-property default)
SIZE_ELASTICITY = -0.08  # psf ~ area^elasticity


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
    idx, to_q = ctx["index"], ctx["asof_q"]
    pairs: list[tuple[float, float]] = []
    for c in comps:
        tf = idx.factor(c["contract_ym"], to_q, "non-landed") if to_q else 1.0
        fl_c = _mid(c)
        floor_adj = 1.0
        if fl_s is not None and fl_c is not None:
            floor_adj = min(max(1 + FLOOR_PP * (fl_s - fl_c), 0.85), 1.15)
        size_adj = (area_s / c["area_sqft"]) ** SIZE_ELASTICITY
        adj = c["psf"] * tf * floor_adj * size_adj
        dmonths = months_between(c["contract_ym"], ctx["asof_ym"])
        dfloor = abs((fl_s or 0) - (fl_c or 0))
        w = 1.0 / (1 + abs(math.log(area_s / c["area_sqft"])) * 3 + dfloor / 25 + dmonths / 24)
        pairs.append((adj, w))

    psf = _wquantile(pairs, 0.50)
    area = area_s
    lo = round(_wquantile(pairs, 0.25) * area, 0) if len(pairs) >= 4 else None
    hi = round(_wquantile(pairs, 0.75) * area, 0) if len(pairs) >= 4 else None
    return {"method": "C1_grid_adapted", "psf": round(psf, 1), "price": round(psf * area, 0),
            "low": lo, "high": hi, "n_comps": len(comps),
            "note": f"grid, {len(comps)} same-project comps"}


CANDIDATES = {"C1_grid_adapted": c1_grid_adapted}
