"""Learned evidence-state ensemble (E1) -- the same C1<->A1 blend shape as E0, but
the point-estimate weight is TUNED from historical error instead of hand-set.

Calibration protocol (full runnable script + printed output: tune_e1.py):
  TRAIN = resale-condo subjects with contract_ym in 2023 ONLY (4,000 sampled,
          seed 42 -> 3,930 rows where BOTH C1 and A1 answered, the only
          population a blend weight actually governs).
  TEST  = subjects from 2024-01 onward (4,000 sampled, seed 42 -> 3,986 dual-
          estimate rows) -- NEVER used to pick a weight, evaluated only.

  w(recent) is grid-searched per same-project comp-count bucket (the identical
  1-2 / 3-5 / 6-15 / 16+ edges run.py already uses for its liquidity slice) on
  TRAIN, 0.05 steps, minimising the blended estimate's median APE. A further
  "does a STALE newest-comp deserve a discount?" delta is grid-searched ONCE
  globally on the pooled stale rows (rare: 90 of 3,930 TRAIN rows, and 66 of
  those 90 sit in the thinnest bucket alone) rather than as 4 separate per-cell
  fits -- an early per-cell attempt produced a NON-monotone table (a 66-row
  "stale" slice out-scored its own "recent" sibling by one grid step, almost
  certainly noise, not signal). The pooled search settled on delta=0.00: once
  n_comps is accounted for, "is the newest comp recent?" carried no further
  TRAIN signal here -- c1_grid_adapted itself already prefers the TIGHTEST
  comp window with >=3 comps before widening (candidates.py), so n_comps
  already partly encodes recency. Reported honestly rather than forcing an
  effect the training slice doesn't support; recency is still computed and
  surfaced (note field, and the `_STALE_DELTA` knob) so a future recalibration
  can pick up a nonzero discount if the pattern changes.

  TRAIN vs TEST median APE on the dual-estimate population (tune_e1.py output):
    TRAIN 2023   E1 4.25%   vs E0-equivalent-weight 4.53%
    TEST  2024+  E1 4.12%   vs E0-equivalent-weight 4.38%
  TEST does not degrade vs TRAIN (if anything it is slightly better) -- the
  8-value table is not overfit to 2023-specific quirks.

Like E0, the interval band is the UNION of the C1 and A1 bands (_blend_band),
independent of the point weight -- so E0's coverage win (44% -> 81%) carries
over unchanged no matter how aggressively the point estimate leans on C1.
"""
from __future__ import annotations

from .avm import avm_hedonic
from .candidates import c1_grid_adapted
from .store import months_between

RECENCY_EDGE_MONTHS = 12   # newest same-project comp within this many months = "recent"
MIN_W = 0.50               # floor: never blend below an even split
_STALE_DELTA = 0.00        # tuned on 2023 pooled-stale TRAIN rows (tune_e1.py); see docstring

# w(recent) per same-project comp-count bucket -- grid-searched on 2023 TRAIN subjects
# (tune_e1.py: W_GRID 0.05 steps, minimises blended median APE). Monotone non-decreasing
# by construction (more comps -> lean harder on C1), matching the task's requirement.
_NB_WEIGHTS = {
    "1-2": 0.85,
    "3-5": 0.90,
    "6-15": 0.95,
    "16+": 0.95,
}
_DEFAULT_W = 0.75   # defensive only: c1_grid_adapted never returns n_comps==0, so every
                    # real call matches a bucket above; this guards a future bucketing change.


def _n_bucket(n: int) -> str:
    return "1-2" if n <= 2 else "3-5" if n <= 5 else "6-15" if n <= 15 else "16+"


def _weight(n_comps: int, recency_months) -> float:
    """C1's share of the point-estimate blend for this evidence state: leans harder
    on C1 as same-project comps get more abundant (bucket ladder above), with an
    additional discount if the newest comp is stale (currently a calibrated no-op,
    delta=0 -- see module docstring)."""
    w = _NB_WEIGHTS.get(_n_bucket(n_comps), _DEFAULT_W)
    if recency_months is None or recency_months > RECENCY_EDGE_MONTHS:
        w -= _STALE_DELTA
    return max(MIN_W, min(1.0, w))


def _recency_months(subject, market, ctx):
    """Months since the newest same-project comp visible as-of ctx (or None if the
    project has no same-project comp at all -- only reachable when c1 is None)."""
    rows = market.same_project(subject["project"])
    if not rows:
        return None
    return months_between(rows[0]["contract_ym"], ctx["asof_ym"])


def _blend_band(a, b):
    los = [x for x in (a.get("low"), b.get("low")) if x is not None]
    his = [x for x in (a.get("high"), b.get("high")) if x is not None]
    return (min(los) if los else None), (max(his) if his else None)


def ensemble_learned(subject, market, ctx):
    """E1: C1 (grid) and A1 (AVM) blended by an evidence-state weight TUNED on a
    2023 held-out slice and validated on 2024+ (see tune_e1.py) -- replacing E0's
    hand-set n-only ramp with one fit from historical error."""
    c1 = c1_grid_adapted(subject, market, ctx)
    avm = avm_hedonic(subject, market, ctx)
    if c1 is None and avm is None:
        return None
    if c1 is None:
        return {**avm, "method": "E1_ensemble_learned", "note": "AVM only (no same-project comp)"}
    if avm is None:
        return {**c1, "method": "E1_ensemble_learned", "note": "grid only (AVM declined)"}

    n_comps = c1["n_comps"]
    recency = _recency_months(subject, market, ctx)
    w_c1 = _weight(n_comps, recency)
    psf = w_c1 * c1["psf"] + (1 - w_c1) * avm["psf"]
    area = subject["area_sqft"]
    lo, hi = _blend_band(c1, avm)
    return {"method": "E1_ensemble_learned", "psf": round(psf, 1), "price": round(psf * area, 0),
            "low": lo, "high": hi, "n_comps": n_comps,
            "note": f"blend w_c1={w_c1:.2f} (n={n_comps}, recency={recency}mo)"}


def ensemble_pooled(subject, market, ctx):
    """E2: same evidence-state blend as E1 but pairs C1 with the pooled anchor A2 (median
    5.46%) instead of the hedonic A1 (10.3%). Tests whether a stronger — but same-project-
    correlated — anchor makes a better ensemble than a weaker but more independent one."""
    from .avm_pooled import avm_pooled
    c1 = c1_grid_adapted(subject, market, ctx)
    a2 = avm_pooled(subject, market, ctx)
    if c1 is None and a2 is None:
        return None
    if c1 is None:
        return {**a2, "method": "E2_ensemble_pooled", "note": "A2 only (no same-project comp)"}
    if a2 is None:
        return {**c1, "method": "E2_ensemble_pooled", "note": "grid only (A2 declined)"}
    n_comps = c1["n_comps"]
    w_c1 = _weight(n_comps, _recency_months(subject, market, ctx))
    psf = w_c1 * c1["psf"] + (1 - w_c1) * a2["psf"]
    area = subject["area_sqft"]
    lo, hi = _blend_band(c1, a2)
    return {"method": "E2_ensemble_pooled", "psf": round(psf, 1), "price": round(psf * area, 0),
            "low": lo, "high": hi, "n_comps": n_comps, "note": f"C1+A2 blend w_c1={w_c1:.2f}"}


def ensemble_multi(subject, market, ctx):
    """E3: blend C1 with the MEDIAN of all three anchors (A1 hedonic, A2 pooled, A3 kNN).
    The anchor median is robust to any single anchor being off, and — unlike E2's lone A2 —
    it carries genuine cross-method diversity (A1/A3 do not use same-project comps). Tests
    whether a robust anchor consensus beats a single anchor in the ensemble."""
    from statistics import median
    from .avm import avm_hedonic
    from .avm_knn import avm_knn
    from .avm_pooled import avm_pooled
    c1 = c1_grid_adapted(subject, market, ctx)
    anchors = [f(subject, market, ctx) for f in (avm_hedonic, avm_pooled, avm_knn)]
    anchors = [a for a in anchors if a]
    apsf = [a["psf"] for a in anchors]
    if c1 is None and not apsf:
        return None
    area = subject["area_sqft"]
    if c1 is None:
        psf = median(apsf)
        lo, hi = _blend_band(anchors[0], anchors[-1]) if len(anchors) > 1 else (None, None)
        return {"method": "E3_ensemble_multi", "psf": round(psf, 1), "price": round(psf * area, 0),
                "low": lo, "high": hi, "n_comps": 0, "note": "anchor-median only (no C1)"}
    if not apsf:
        return {**c1, "method": "E3_ensemble_multi", "note": "grid only (anchors declined)"}
    n_comps = c1["n_comps"]
    w_c1 = _weight(n_comps, _recency_months(subject, market, ctx))
    consensus = median(apsf)
    psf = w_c1 * c1["psf"] + (1 - w_c1) * consensus
    los = [x for x in [c1.get("low")] + [a.get("low") for a in anchors] if x is not None]
    his = [x for x in [c1.get("high")] + [a.get("high") for a in anchors] if x is not None]
    return {"method": "E3_ensemble_multi", "psf": round(psf, 1), "price": round(psf * area, 0),
            "low": min(los) if los else None, "high": max(his) if his else None,
            "n_comps": n_comps, "note": f"C1+median(A1,A2,A3) w_c1={w_c1:.2f}"}


ENSEMBLES_LEARNED = {"E1_ensemble_learned": ensemble_learned,
                     "E2_ensemble_pooled": ensemble_pooled,
                     "E3_ensemble_multi": ensemble_multi}
