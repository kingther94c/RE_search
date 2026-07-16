"""L2 landed candidates — must BEAT the L1 bar (LC1_craft_landed: 10.51% median APE /
87.3% coverage / P90 0.341) to earn a place in the L3 engine.

LC2 = LC1's craft skeleton with the two L2 fixes the L1 error map demanded:
  - **L2a fitted size curve** (`landed_size_curve`) instead of the ported -0.877, applied
    ALWAYS (not only when the grid widens): with a validated curve, a 15% size gap is a
    real 8-10% psf effect worth correcting, and the piecewise form stops the -0.877
    over-correction that made big plots explode (L1: 24% @8-15k, 41% @15k+).
  - **L2c lease matching** — the decisive L1 failure: cross-street methods priced ~20-yr-left
    99yr terraces off freehold neighbours at 6-10x (LB4 median APE 232% on sub-2M subjects).
    Even same-street grids need it: a street can mix tenures. Comps whose remaining lease is
    far from the subject's are dropped; freehold/999yr are pooled as quasi-freehold.
"""
from __future__ import annotations

import math
from statistics import median

from .landed_benchmarks import (TIME_ADJ_CAP, WINDOW_MO, _est, _recent, _tadj_psf, _wq)
from .landed_size_curve import size_factor
from .store import months_between

CRAFT_HALFLIFE_MO = 18.0
LEASE_MATCH_YEARS = 25.0     # comps within +/-25y of remaining lease are comparable
QUASI_FH_YEARS = 800.0       # 999yr/freehold treated as one bucket


def remaining_lease(t, asof_ym: str) -> float:
    """Years of lease left at the valuation date. Freehold/999yr -> QUASI_FH_YEARS."""
    if t.get("tenure_type") in ("freehold", "freehold_equiv"):
        return QUASI_FH_YEARS
    start = t.get("lease_start")
    if not start:
        return QUASI_FH_YEARS       # unknown leasehold start: don't fabricate a short lease
    total = 99.0
    raw = (t.get("tenure_raw") or "").lower()
    for n in (999, 103, 99, 60, 30):
        if str(n) in raw:
            total = float(n)
            break
    if total >= QUASI_FH_YEARS:
        return QUASI_FH_YEARS
    return max(0.0, start + total - int(asof_ym[:4]))


def lease_compatible(comp, subject, asof_ym) -> bool:
    """Both quasi-freehold, or remaining leases within LEASE_MATCH_YEARS. This is the
    guard the 232% LB4 failure demanded — never price a short-lease plot off a freehold."""
    rs, rc = remaining_lease(subject, asof_ym), remaining_lease(comp, asof_ym)
    if rs >= QUASI_FH_YEARS and rc >= QUASI_FH_YEARS:
        return True
    if (rs >= QUASI_FH_YEARS) != (rc >= QUASI_FH_YEARS):
        return False                # quasi-FH vs real leasehold: never comparable
    return abs(rs - rc) <= LEASE_MATCH_YEARS


def lc2_fitted_curve(subject, mkt, ctx):
    """LC2: same-street same-type grid, LEASE-MATCHED, with the fitted size curve applied
    to every comp; recency half-life 18mo; weighted median."""
    area = subject["area_sqft"]
    asof_ym = ctx["asof_ym"]
    street = _recent([r for r in mkt.landed_on_street(subject["street"])
                      if r["property_type"] == subject["property_type"]], ctx, window=60)
    comps = [r for r in street if lease_compatible(r, subject, asof_ym)]
    if not comps:
        return None
    pairs = []
    for c in comps:
        psf = _tadj_psf(c, ctx) * size_factor(c["area_sqft"], area)
        age_mo = months_between(c["contract_ym"], asof_ym)
        w = 0.5 ** (age_mo / CRAFT_HALFLIFE_MO)
        pairs.append((psf, w))
    psf = _wq(pairs, 0.50)
    dropped = len(street) - len(comps)
    return _est("LC2_fitted_curve", psf, subject, [p for p, _ in pairs],
                f"street grid n={len(pairs)}, fitted size curve"
                + (f", {dropped} lease-mismatched dropped" if dropped else ""))


def la1_pooled_anchor(subject, mkt, ctx):
    """LA1 (L2d): lease-matched, type-matched, size-curve-adjusted POOLED anchor —
    district pool, widening to segment then island. Its job is COVERAGE and hard-case
    detection, NOT point accuracy: L1/EXP-0010 showed pooled methods cost 4-5pp of median
    vs a street grid, and the condo reversal showed anchors never beat local comps where
    local comps exist. LC2 declines on ~13% of subjects (no lease-compatible street comp);
    this answers there so the L3 engine can reach ~100% coverage.
    """
    area = subject["area_sqft"]
    asof_ym = ctx["asof_ym"]

    def pool_of(rows):
        return [r for r in _recent(rows, ctx, window=WINDOW_MO)
                if r["property_type"] == subject["property_type"]
                and lease_compatible(r, subject, asof_ym)]

    landed = mkt.landed()
    for scope, rows in (("district", [r for r in landed
                                      if r["district"] == subject["district"]]),
                        ("segment", [r for r in landed
                                     if r["market_segment"] == subject["market_segment"]]),
                        ("island", landed)):
        pool = pool_of(rows)
        if len(pool) >= 3:
            adj = [_tadj_psf(c, ctx) * size_factor(c["area_sqft"], area) for c in pool]
            return _est("LA1_pooled_anchor", median(adj), subject, adj,
                        f"{scope} pool n={len(adj)}, lease-matched, size-curve")
    return None


LANDED_CANDIDATES = {
    "LC2_fitted_curve": lc2_fitted_curve,
    "LA1_pooled_anchor": la1_pooled_anchor,
}
