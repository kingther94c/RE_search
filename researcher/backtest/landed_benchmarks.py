"""L1 landed benchmarks (LB1-LB5) + the craft port LC1 — the honest leaderboard's rows.

Every method prices the LAND+BUILDING BUNDLE via land-psf comps:
pred_price = pred_land_psf x subject LAND area. None of them sees the building's
condition — the same-plot noise floor (research/landed_noise_floor.py) says how much
accuracy that ceiling even permits, and the leaderboard is read against it.

Conventions (mirroring the condo benchmarks so numbers are comparable):
  - signature (subject, market, ctx) -> estimate | None (decline);
  - comps come ONLY from MarketView (as-of filtered by the harness);
  - time adjustment uses the LANDED PPI series to the last PUBLISHED quarter
    (ctx["asof_q"]), capped like C1 — a comp needing >25% adjustment is unreliable;
  - bands (n>=4) are the IQR of ADJUSTED comp psf — expected broken (condo's were, 43%);
    the calibrated fix is L3's conformal, not a benchmark's job;
  - windows default to 24 months: street volumes are thin (median 4-5 caveats/5y),
    12 months would mostly decline.

LC1 is the incumbent craft skeleton from the Cardiff Grove #19 valuation (PASS 8.8):
same-street same-type grid, recency half-life ~1.5y, and a PORTED cross-size prior
psf ~ area^-0.877 (fitted there on ONE street's two cross-size legs — guardrail-#5
flag: unvalidated globally until L2a re-fits it; that is exactly what L1 measures).
"""
from __future__ import annotations

import math
from statistics import median

from .store import months_between

WINDOW_MO = 24
TIME_ADJ_CAP = (0.80, 1.25)
# craft cross-size prior (Cardiff Grove #19, EXP-0009 provenance note above)
CRAFT_SIZE_ELASTICITY = -0.877
CRAFT_HALFLIFE_MO = 18.0
SIZE_SIMILAR_LOGRATIO = 0.18   # ~+/-20%: the craft's "same-spec" grid preference


def _pct(vals: list[float], q: float) -> float:
    s = sorted(vals)
    if len(s) == 1:
        return s[0]
    pos = q * (len(s) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def _tadj_psf(c: dict, ctx) -> float:
    """Time-adjust a comp's land-psf to the AS-OF MONTH — not merely to the last published
    index quarter. The published quarter is structurally 1-2 quarters stale (35d pub lag), so
    stopping there left the point ~1.2pp low in a rising market (measured: actual exceeded
    the point 63% of the time). `drift_factor` projects that gap at the recent PUBLISHED
    trend, so no unpublished data is used."""
    idx, to_q = ctx["index"], ctx["asof_q"]
    if not to_q:
        return c["psf"]
    f = idx.factor(c["contract_ym"], to_q, "landed")
    f = min(max(f, TIME_ADJ_CAP[0]), TIME_ADJ_CAP[1])
    return c["psf"] * f * idx.drift_factor(to_q, ctx["asof_ym"], "landed")


def _recent(rows, ctx, window=WINDOW_MO):
    return [r for r in rows
            if 0 <= months_between(r["contract_ym"], ctx["asof_ym"]) < window]


def _est(method, psf, subject, adj_psfs, note=""):
    area = subject["area_sqft"]
    lo = hi = None
    if len(adj_psfs) >= 4:
        lo = round(_pct(adj_psfs, 0.25) * area, 0)
        hi = round(_pct(adj_psfs, 0.75) * area, 0)
    return {"method": method, "psf": round(psf, 1), "price": round(psf * area, 0),
            "low": lo, "high": hi, "n_comps": len(adj_psfs), "note": note}


def _wq(pairs: list[tuple[float, float]], q: float) -> float:
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


# ------------------------------------------------------------------ the benchmarks
def lb1_same_street(subject, mkt, ctx):
    """LB1: same-street same-type recent land-psf, time-adjusted median. Declines with
    zero street comps — that decline rate is itself a finding."""
    comps = _recent([r for r in mkt.landed_on_street(subject["street"])
                     if r["property_type"] == subject["property_type"]], ctx)
    if not comps:
        return None
    adj = [_tadj_psf(c, ctx) for c in comps]
    return _est("LB1_same_street", median(adj), subject, adj,
                f"street n={len(adj)}, time-adj")


def lb2_street_district_pooled(subject, mkt, ctx):
    """LB2: street if n>=3 else district, type-matched, time-adjusted median —
    the simplest partial pooling (streets are thin: median 4-5 caveats/5y)."""
    street = _recent([r for r in mkt.landed_on_street(subject["street"])
                      if r["property_type"] == subject["property_type"]], ctx)
    if len(street) >= 3:
        adj = [_tadj_psf(c, ctx) for c in street]
        return _est("LB2_street_district_pooled", median(adj), subject, adj,
                    f"street n={len(adj)}")
    pool = _recent([r for r in mkt.landed()
                    if r["district"] == subject["district"]
                    and r["property_type"] == subject["property_type"]], ctx)
    if not pool:
        return None
    adj = [_tadj_psf(c, ctx) for c in pool]
    return _est("LB2_street_district_pooled", median(adj), subject, adj,
                f"district pool n={len(adj)} (street had {len(street)})")


def lb3_type_tenure_segment(subject, mkt, ctx):
    """LB3: type x tenure x segment pool median land-psf, time-adjusted (landed index)."""
    pool = _recent([r for r in mkt.landed()
                    if r["property_type"] == subject["property_type"]
                    and r["tenure_type"] == subject["tenure_type"]
                    and r["market_segment"] == subject["market_segment"]], ctx)
    if not pool:
        return None
    adj = [_tadj_psf(c, ctx) for c in pool]
    return _est("LB3_type_tenure_segment", median(adj), subject, adj,
                f"pool n={len(adj)}")


def lb4_spatial_knn(subject, mkt, ctx, k=8, radius_m=1000.0):
    """LB4: k nearest landed sales, same type, size-similar (+/-35%), time-adjusted."""
    if subject.get("x") is None or subject.get("y") is None:
        return None
    area = subject["area_sqft"]
    cands = [r for r in _recent(mkt.landed_near(subject["x"], subject["y"], radius_m), ctx)
             if r["property_type"] == subject["property_type"]
             and abs(math.log(r["area_sqft"] / area)) <= 0.30]
    if len(cands) < 3:
        return None
    cands.sort(key=lambda r: math.hypot(r["x"] - subject["x"], r["y"] - subject["y"]))
    near = cands[:k]
    adj = [_tadj_psf(c, ctx) for c in near]
    return _est("LB4_spatial_knn", median(adj), subject, adj,
                f"kNN k={len(adj)}@{radius_m:.0f}m")


def lb5_district_median_price(subject, mkt, ctx):
    """LB5: district median TOTAL price by type — the naive quantum benchmark (no
    time adjustment, no size logic; the floor every method must clear)."""
    pool = _recent([r for r in mkt.landed()
                    if r["district"] == subject["district"]
                    and r["property_type"] == subject["property_type"]], ctx)
    if not pool:
        return None
    price = median(r["price"] for r in pool)
    area = subject["area_sqft"]
    psfs = sorted(r["price"] / area for r in pool)   # in subject-psf units for the band
    est = _est("LB5_district_median_price", price / area, subject, psfs,
               f"district median price n={len(pool)}")
    est["price"] = round(price, 0)
    return est


def lc1_craft_landed(subject, mkt, ctx):
    """LC1: the Cardiff craft skeleton. Same-street same-type grid; prefer same-spec
    (+/-20%) comps; when fewer than 3, widen to ALL street sizes with the ported
    psf ~ area^-0.877 prior. Recency half-life ~18mo; time-adjusted; weighted median."""
    area = subject["area_sqft"]
    street = _recent([r for r in mkt.landed_on_street(subject["street"])
                      if r["property_type"] == subject["property_type"]], ctx,
                     window=60)                       # craft used up to ~5y of street prints
    if not street:
        return None
    similar = [r for r in street
               if abs(math.log(r["area_sqft"] / area)) <= SIZE_SIMILAR_LOGRATIO]
    use, size_adjusted = (similar, False) if len(similar) >= 3 else (street, True)
    pairs = []
    for c in use:
        psf = _tadj_psf(c, ctx)
        if size_adjusted:
            psf *= (area / c["area_sqft"]) ** CRAFT_SIZE_ELASTICITY
        age_mo = months_between(c["contract_ym"], ctx["asof_ym"])
        w = 0.5 ** (age_mo / CRAFT_HALFLIFE_MO)
        pairs.append((psf, w))
    psf = _wq(pairs, 0.50)
    return _est("LC1_craft_landed", psf, subject, [p for p, _ in pairs],
                ("same-spec grid" if not size_adjusted else
                 f"size-adjusted grid (elasticity {CRAFT_SIZE_ELASTICITY}, ported)")
                + f" n={len(pairs)}")


LANDED_BENCHMARKS = {
    "LB1_same_street": lb1_same_street,
    "LB2_street_district_pooled": lb2_street_district_pooled,
    "LB3_type_tenure_segment": lb3_type_tenure_segment,
    "LB4_spatial_knn": lb4_spatial_knn,
    "LB5_district_median_price": lb5_district_median_price,
    "LC1_craft_landed": lc1_craft_landed,
}
