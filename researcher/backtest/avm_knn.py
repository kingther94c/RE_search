"""A3: feature-space kNN anchor — a second INDEPENDENT valuation opinion that needs no
same-project comp, complementing A1's global hedonic regression with a local,
non-parametric read: the time-adjusted median psf of the k~40 most similar condo
caveats in STANDARDIZED feature space, drawn from a spatially prefiltered ~2km pool.

Method (per-month, memoized in market.cache):
  1. Build ONE population scaler over market.condo() (as-of only): for every condo
     caveat, a raw feature vector [log(area), floor-mid, segment one-hot (CCR/RCR/OCR),
     tenure one-hot (leasehold/freehold/freehold_equiv), lease-age, time-in-months], then
     z-score every dimension by that month's population mean/std. (Any fixed linear
     rescaling of a raw feature -- e.g. /10 -- is a no-op after z-scoring, so raw units
     are kept for clarity.)
  2. For the subject: spatially prefilter via market.condo_near to a ~2km pool (widen to
     5km if too thin), cap the pool for speed, then rank by standardized Euclidean
     distance PLUS a fixed penalty when the neighbour's district differs from the
     subject's ("same-district flag" -- inherently a pairwise subject-vs-comp comparison,
     so it is folded into the query-time distance rather than the per-comp vector).
  3. Take the k nearest, time-adjust each one's psf to the as-of quarter (PriceIndex),
     and return the MEDIAN as the anchor psf.

Leakage discipline (identical contract to avm.py's HedonicAVM):
  - the scaler and the neighbour pool are built ONLY from market.condo() / market.cache
    (already as-of filtered by the harness -- the subject's own row cannot appear, see
    harness.py's comment on the M-1 valuation date);
  - the subject's "time" feature uses the AS-OF time coordinate (market.asof_ym), never
    its own (future) contract month -- the one feature that would leak price-level info
    if left at the subject's own month, exactly as avm.py's docstring flags;
  - lease-age (like avm.py) reads the subject's own contract_ym, an explicitly allowed
    attribute, and differs from the as-of month by at most the harness's one-month gap --
    immaterial to a year-granularity lease-age figure;
  - subject psf/price/id are never read; only market/ctx and subject attributes.
"""
from __future__ import annotations

import heapq
import math
import random

from statistics import median

from .store import months_between

_T0 = "2021-07"            # time origin, kept in sync with avm.py's HedonicAVM
_K = 40                     # target neighbour count
_POOL_RADIUS_M = 2000.0     # primary spatial prefilter ("~2km pool" per spec)
_WIDE_RADIUS_M = 5000.0     # fallback radius when the 2km pool is too thin
_MIN_POOL = 2 * _K          # below this at 2km, widen to 5km
_MIN_NEIGHBOURS = 5         # below this after ranking, decline (too little evidence)
_POOL_CAP = 800             # bound worst-case per-subject cost in ultra-dense districts
_MIN_SCALER_N = 200         # minimum as-of condo population to trust a population scaler
_DISTRICT_PENALTY = 1.0     # fixed additive penalty (standardized-distance units) for a
                            # neighbour outside the subject's district (soft, not a filter)

# NOTE on market.condo_near: its 3x3 grid scan is an EXACT radius query only up to
# radius <= its internal cell size (1000m); beyond that (our 2km/5km calls) it can miss a
# genuine neighbour sitting 1-2 grid cells away near a cell boundary. That is an existing,
# documented property of the shared prefilter utility (it names itself a "prefilter"), not
# something this method attempts to patch -- the exact ranking step afterwards is unaffected
# by which comps make it into the pool, only the pool's completeness. Reported as a known
# limitation, not hidden.


def _lease_age(tx) -> float:
    if tx["tenure_type"] == "leasehold" and tx.get("lease_start"):
        return max(0.0, int(tx["contract_ym"][:4]) - tx["lease_start"])
    return 0.0


def _floor_mid(tx) -> float:
    lo = tx.get("floor_lo")
    return ((lo + tx["floor_hi"]) / 2) if lo is not None else 8.0


def _raw_features(tx, t_months: float) -> tuple:
    """Keep in sync with _Scaler.fit / _Scaler.vector_for."""
    seg = tx["market_segment"]
    ten = tx["tenure_type"]
    return (
        math.log(tx["area_sqft"]),
        _floor_mid(tx),
        1.0 if seg == "CCR" else 0.0,
        1.0 if seg == "RCR" else 0.0,
        1.0 if seg == "OCR" else 0.0,
        1.0 if ten == "leasehold" else 0.0,
        1.0 if ten == "freehold" else 0.0,
        1.0 if ten == "freehold_equiv" else 0.0,
        _lease_age(tx),
        t_months,
    )


class _Scaler:
    """Per-month feature standardizer fit ONCE on market.condo() (as-of only)."""
    __slots__ = ("mean", "std", "std_by_id")

    def __init__(self, mean, std, std_by_id):
        self.mean = mean
        self.std = std
        self.std_by_id = std_by_id   # {id(tx): standardized feature vector} for condo()

    @classmethod
    def fit(cls, condos: list) -> "_Scaler | None":
        if len(condos) < _MIN_SCALER_N:
            return None
        ids, raws = [], []
        for t in condos:
            tm = months_between(_T0, t["contract_ym"])
            ids.append(id(t))
            raws.append(_raw_features(t, tm))
        n, k = len(raws), len(raws[0])
        mean = [0.0] * k
        for r in raws:
            for i in range(k):
                mean[i] += r[i]
        mean = [m / n for m in mean]
        var = [0.0] * k
        for r in raws:
            for i in range(k):
                d = r[i] - mean[i]
                var[i] += d * d
        std = [max((v / n) ** 0.5, 1e-9) for v in var]
        std_by_id = {tid: [(r[i] - mean[i]) / std[i] for i in range(k)]
                     for tid, r in zip(ids, raws)}
        return cls(mean, std, std_by_id)

    def vector_for(self, tx, t_months: float) -> list:
        """Standardize an arbitrary row (the subject) with this month's population stats."""
        raw = _raw_features(tx, t_months)
        return [(raw[i] - self.mean[i]) / self.std[i] for i in range(len(raw))]


def _scaler(market) -> "_Scaler | None":
    if "knn_scaler" not in market.cache:
        market.cache["knn_scaler"] = _Scaler.fit(market.condo())
    return market.cache["knn_scaler"]


def _pct(vals: list, q: float) -> float:
    s = sorted(vals)
    if len(s) == 1:
        return s[0]
    pos = q * (len(s) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def avm_knn(subject, market, ctx):
    """A3: feature-space kNN anchor. Standardized distance (log-area, floor, segment,
    tenure, lease-age, time) + a same-district penalty, over a ~2km-prefiltered pool;
    returns the time-adjusted median psf of the k nearest condo neighbours."""
    if subject.get("x") is None or subject.get("y") is None:
        return None                                    # no coordinate -> no spatial pool
    scaler = _scaler(market)
    if scaler is None:
        return None                                    # too little as-of history to trust

    x, y = subject["x"], subject["y"]
    pool = market.condo_near(x, y, _POOL_RADIUS_M)
    radius_used = _POOL_RADIUS_M
    if len(pool) < _MIN_POOL:
        pool = market.condo_near(x, y, _WIDE_RADIUS_M)
        radius_used = _WIDE_RADIUS_M
    if len(pool) > _POOL_CAP:
        pool = random.Random(42).sample(pool, _POOL_CAP)
    if len(pool) < _MIN_NEIGHBOURS:
        return None

    t_asof = months_between(_T0, market.asof_ym)        # subject at the AS-OF coordinate
    subj_vec = scaler.vector_for(subject, t_asof)
    subj_district = subject.get("district")
    by_id = scaler.std_by_id

    def _dist(c) -> float:
        v = by_id.get(id(c))
        if v is None:
            return float("inf")
        s = 0.0
        for a, b in zip(subj_vec, v):
            d = a - b
            s += d * d
        dist = math.sqrt(s)
        if c.get("district") != subj_district:
            dist += _DISTRICT_PENALTY
        return dist

    neighbours = heapq.nsmallest(_K, pool, key=_dist)
    if len(neighbours) < _MIN_NEIGHBOURS:
        return None

    idx, to_q = ctx["index"], ctx["asof_q"]
    adj_psf = [c["psf"] * (idx.factor(c["contract_ym"], to_q, "non-landed") if to_q else 1.0)
               for c in neighbours]

    psf = median(adj_psf)
    area = subject["area_sqft"]
    lo = hi = None
    if len(adj_psf) >= 4:
        lo = round(_pct(adj_psf, 0.25) * area, 0)
        hi = round(_pct(adj_psf, 0.75) * area, 0)
    same_dist = sum(1 for c in neighbours if c.get("district") == subj_district)
    return {"method": "A3_avm_knn", "psf": round(psf, 1), "price": round(psf * area, 0),
            "low": lo, "high": hi, "n_comps": len(neighbours),
            "note": f"kNN k={len(neighbours)} pool={len(pool)}@{radius_used:.0f}m "
                    f"same_dist={same_dist}"}


KNN_ANCHORS = {"A3_avm_knn": avm_knn}
