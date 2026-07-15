"""Evidence-state ensemble (E0) — the mandate's mixture-of-experts, simplest form.

Blend the same-project grid (C1) with the independent hedonic anchor (A1), weighting by
evidence state: when same-project comps are many, trust C1; when they are thin/absent,
lean on the AVM. This is the direct test of the R3 hypothesis that an independent anchor
fixes the tail and the thin-comp cases that same-project methods can't.

Weights here are a HAND-SET starting point (n_comps only). R3 replaces them with weights
learned from historical anchor error — but only if the learned version beats this baseline.
"""
from __future__ import annotations

from .avm import avm_hedonic
from .candidates import c1_grid_adapted


def _blend_band(a, b, area):
    los = [x for x in (a.get("low"), b.get("low")) if x is not None]
    his = [x for x in (a.get("high"), b.get("high")) if x is not None]
    return (min(los) if los else None), (max(his) if his else None)


def ensemble_v0(subject, market, ctx):
    """E0: C1 (grid) and A1 (AVM) blended by same-project comp count."""
    c1 = c1_grid_adapted(subject, market, ctx)
    avm = avm_hedonic(subject, market, ctx)
    if c1 is None and avm is None:
        return None
    if c1 is None:
        return {**avm, "method": "E0_ensemble", "note": "AVM only (no same-project comp)"}
    if avm is None:
        return {**c1, "method": "E0_ensemble", "note": "grid only (AVM declined)"}

    n = c1["n_comps"]
    w_c1 = 0.5 + 0.5 * min(n, 10) / 10        # n=1 -> 0.55, n>=10 -> 1.00
    psf = w_c1 * c1["psf"] + (1 - w_c1) * avm["psf"]
    area = subject["area_sqft"]
    lo, hi = _blend_band(c1, avm, area)
    return {"method": "E0_ensemble", "psf": round(psf, 1), "price": round(psf * area, 0),
            "low": lo, "high": hi, "n_comps": n,
            "note": f"blend w_c1={w_c1:.2f} (n={n})"}


ENSEMBLES = {"E0_ensemble": ensemble_v0}
