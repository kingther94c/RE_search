"""The simple benchmarks every complex method must beat (mandate: Benchmark Discipline).

Each benchmark has the signature (subject, store, ctx) -> estimate | None, where:
  - `store` is ALREADY as-of filtered by the harness (leakage handled in one place),
  - `ctx`   carries the valuation month/date, published index quarter and the PriceIndex,
  - returns {"method","psf","price","low","high","n_comps","note"} or None to decline.

An estimate's psf is the driver; price = psf * subject area. Bands (when n>=4) are the
inter-quartile psf spread — rough, but enough to score interval coverage even here.
"""
from __future__ import annotations

import math
from statistics import median

from .store import TransactionStore


def _pct(vals: list[float], q: float) -> float:
    s = sorted(vals)
    if len(s) == 1:
        return s[0]
    pos = q * (len(s) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def _est(method: str, psf: float, subject: dict, comps: list[dict],
         note: str = "") -> dict:
    area = subject["area_sqft"]
    psfs = [c["psf"] for c in comps]
    lo = hi = None
    if len(psfs) >= 4:
        lo = round(_pct(psfs, 0.25) * area, 0)
        hi = round(_pct(psfs, 0.75) * area, 0)
    return {"method": method, "psf": round(psf, 1), "price": round(psf * area, 0),
            "low": lo, "high": hi, "n_comps": len(comps), "note": note}


# ------------------------------------------------------------------- the benchmarks
def latest_same_project(subject, store, ctx):
    """B1: psf of the most recent same-project caveat(s)."""
    sp = store.same_project(subject["project"])
    if not len(sp):
        return None
    rows = sp.sorted_by_ym(reverse=True)
    top_ym = rows[0]["contract_ym"]
    latest = [r for r in rows if r["contract_ym"] == top_ym]
    return _est("latest_same_project", median(c["psf"] for c in latest),
                subject, latest, f"latest month {top_ym}")


def median_last3_same_project(subject, store, ctx):
    """B2: median psf of the 3 most recent same-project caveats."""
    sp = store.same_project(subject["project"]).sorted_by_ym(reverse=True)
    if not sp:
        return None
    last3 = sp[:3]
    return _est("median_last3_same_project", median(c["psf"] for c in last3),
                subject, last3, "last 3 same-project")


def same_project_filtered(subject, store, ctx):
    """B3: same project, +/-30% size, last 12 months -> median psf."""
    area = subject["area_sqft"]
    sp = store.same_project(subject["project"]).within_months(ctx["asof_ym"], 12)
    comps = [c for c in sp.txs if 0.7 * area <= c["area_sqft"] <= 1.3 * area]
    if not comps:
        return None
    return _est("same_project_filtered", median(c["psf"] for c in comps),
                subject, comps, "same project, +/-30% size, 12mo")


def nearest_project_psf(subject, store, ctx):
    """B4: nearest OTHER project within 1km with a caveat in the last 12mo -> its median psf."""
    if subject.get("x") is None or subject.get("y") is None:
        return None
    near = store.is_condo().near(subject["x"], subject["y"], 1000).within_months(
        ctx["asof_ym"], 12)
    key = subject["project"].strip().casefold()
    others = [c for c in near.txs if c["project"].strip().casefold() != key
              and c.get("x") is not None]
    if not others:
        return None
    # closest distinct project, then that project's recent median psf
    def dist(c):
        return math.hypot(c["x"] - subject["x"], c["y"] - subject["y"])
    nearest_proj = min(others, key=dist)["project"]
    comps = [c for c in others if c["project"] == nearest_proj]
    return _est("nearest_project_psf", median(c["psf"] for c in comps),
                subject, comps, f"nearest project '{nearest_proj}'")


def segment_time_adjusted(subject, store, ctx):
    """B5: segment (CCR/RCR/OCR) median psf, each comp time-adjusted to the as-of quarter."""
    seg = subject["market_segment"]
    if not seg:
        return None
    idx = ctx["index"]
    to_q = ctx["asof_q"]  # published quarter as of the valuation date, or None
    pool = store.is_condo().segment(seg).within_months(ctx["asof_ym"], 12)
    if not pool.txs:
        return None
    adj = []
    for c in pool.txs:
        f = idx.factor(c["contract_ym"], to_q, "non-landed") if to_q else 1.0
        adj.append(c["psf"] * f)
    comps = pool.txs
    note = f"segment {seg}, time-adj to {to_q or 'n/a'}"
    return _est("segment_time_adjusted", median(adj), subject, comps, note)


BENCHMARKS = {
    "B1_latest_same_project": latest_same_project,
    "B2_median_last3_same_project": median_last3_same_project,
    "B3_same_project_filtered": same_project_filtered,
    "B4_nearest_project_psf": nearest_project_psf,
    "B5_segment_time_adjusted": segment_time_adjusted,
}
