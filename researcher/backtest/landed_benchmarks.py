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
    """Time-adjust a comp's land-psf: published landed PPI to the last PUBLISHED quarter
    (35d pub lag), capped — PLUS, when ctx carries the shipped L2b configuration
    (`landed_engine.shipped_time_ctx`), an OBSERVED local-trend bridge from that quarter's
    midpoint to the newest visible caveat month ("lt_tail", EXP-0017).

    NO forecasts, ever. What died here, in order:
      - GY-0003 `drift_factor` (trailing-index momentum): broke the four already-unbiased
        regimes (2023H1 51.6->41.6 ... 2024H2 50.1->44.7) while worsening its target
        (2025H2 66.5->67.1) — a trailing trend is late at every turn.
      - GY-0004 cap widening: the published PPI moved x1.335 2021Q3->2025Q4 (over the
        x1.25 cap inside LC2's 60mo window) but the 18mo recency half-life leaves ~0-7%
        of comp WEIGHT on comps old enough to bind — counterfactual moved nothing.
      - GY-0005 "lt_full" (fitted caveat trend replacing the PPI outright): pooled numbers
        looked better but it broke 2023H1 (51.6->43.4) — the monthly caveat curve is
        noisier than the stratified official index on the LONG span.
    What shipped (EXP-0017 "lt_tail"): PPI stays the long-span backbone; the fitted local
    trend (local_trend.py, as-of two-way FE, clamped, never extrapolated) closes ~2 of the
    ~4.5 months of publication staleness WITH OBSERVATIONS, each comp bridged from
    max(its own month, the published quarter's midpoint) — a fresh comp must not be
    double-bridged. Regime panel: stable half-years stay 47.1-53.0; hot regimes improve
    66.3/66.5/60.4 -> 60.8/62.1/59.6; pooled median APE 9.34% -> 9.05%. The residual
    hot-regime bias (~-3.9% medSigned) did NOT meet the pre-registered "fixed" bar (all
    regimes in [42,58]) and stays DISCLOSED: in an accelerating market the point still
    reads as a floor.

    ctx knobs (defaults with a bare ctx = PPI-only, for ablations):
      - ctx["ltrend"] + ctx["tadj_mode"]="lt_tail": the shipped bridge (above).
      - ctx["tadj_mode"]="lt_full": REJECTED, kept for experiments (GY-0005).
      - ctx["tadj_cap"]: (lo, hi) clamp on the published factor (data-error guard;
        widening it is NOT a bias fix, GY-0004).
    """
    idx, to_q = ctx["index"], ctx["asof_q"]
    lt, mode = ctx.get("ltrend"), ctx.get("tadj_mode")
    if lt is not None and mode == "lt_full":
        f = lt.factor(c["contract_ym"], ctx["asof_ym"])
        return c["psf"] * min(max(f, 0.50), 2.00)       # data-error guard only
    if not to_q:
        # no published index yet — the OBSERVED bridge needs none: anchor at the comp's
        # own month (unreachable on the current store's subject window; latent-consistency
        # fix from the L2b hostile review)
        if lt is not None and mode == "lt_tail":
            return c["psf"] * lt.factor(c["contract_ym"], ctx["asof_ym"])
        return c["psf"]
    cap = ctx.get("tadj_cap", TIME_ADJ_CAP)
    f = min(max(idx.factor(c["contract_ym"], to_q, "landed"), cap[0]), cap[1])
    if lt is not None and mode == "lt_tail":
        # PER-COMP anchor: a comp NEWER than the published quarter's midpoint is already
        # at (or past) that level and the PPI leg was ~1.0 — bridging it from the quarter
        # mid would DOUBLE-COUNT the recent move on exactly the comps that carry the most
        # recency weight (caught live: a subject's own same-month print was pushed +4%).
        y, q = int(to_q[:4]), int(to_q[-1])
        anchor = max(c["contract_ym"], f"{y}-{q * 3 - 1:02d}")
        f *= lt.factor(anchor, ctx["asof_ym"])       # observed bridge, never a forecast
    return c["psf"] * f


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
