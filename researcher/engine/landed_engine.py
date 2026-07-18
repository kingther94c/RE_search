"""L3: the landed engine (LV1) — the architecture the condo line proved, transposed.

  POINT    = LC2 (lease-matched same-street grid + fitted size curve) wherever the street
             answers — L1/EXP-0010 showed even 1-2 street comps beat every cross-street
             pool (the condo thin-comp reversal, transposed), so we do NOT blend an anchor
             into it. Else fall back to LA1 (lease-matched pooled anchor) purely for COVERAGE.
  INTERVAL = split-conformal per (street-liquidity x type) cell, calibrated on an earlier
             time slice (`research/analyze_landed.py`), fingerprinted against the code that
             produced its residuals so drift is a red test, not a silent skew.
  SCOPE    = >=8k sqft plots ride a widened band and route to the case protocol: EXP-0011
             showed the size curve is worst-identified exactly where the error is largest.

Everything here is the SAME shape as `engine_v2.py` for condo. That is deliberate: the
architecture ("best method where it applies + fallback + calibrated band", NOT an ensemble
blend) is the thing the condo programme actually validated.

TIME ADJUSTMENT (EXP-0017): comps ride the published landed PPI to the last published
quarter PLUS an observed bridge (fitted local trend, `local_trend.py`) from that quarter's
midpoint to the newest visible caveat month — closing ~2 of the ~4.5 months of publication
staleness with observations, never forecasts. `shipped_time_ctx` is the ONE constructor of
that configuration; production (`value_landed`), the harness default (`run_landed`) and the
regression tests all call it, so the shipped point IS the backtested point by construction
(the EXP-0015 P1 lesson, enforced structurally).
"""
from __future__ import annotations

import json
import os

from researcher.backtest.landed_candidates import la1_pooled_anchor, lc2_fitted_curve
from researcher.backtest.landed_size_curve import is_big_plot
from researcher.backtest.local_trend import fit_landed_trend


def shipped_time_ctx(view_txs, asof_ym: str) -> dict:
    """The SHIPPED time-adjustment configuration (EXP-0017 verdict: V2 "lt_tail").
    Fit ONLY on an as-of view — the caller guarantees visibility."""
    return {"ltrend": fit_landed_trend(view_txs, asof_ym), "tadj_mode": "lt_tail"}

_TABLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "landed_conformal_table.json")
_TABLE: dict | None = None
BIG_PLOT_WIDEN = 1.6      # extra half-width multiplier for >=8k sqft (curve poorly identified)


def _table() -> dict:
    global _TABLE
    if _TABLE is None:
        try:
            with open(_TABLE_PATH, encoding="utf-8") as f:
                _TABLE = json.load(f)
        except FileNotFoundError:
            _TABLE = {"_global": [0.80, 1.25]}   # inert default until calibrated
    return _TABLE


def liq_bucket(n: int) -> str:
    return "0" if not n else "1-2" if n <= 2 else "3-5" if n <= 5 else "6-15" if n <= 15 else "16+"


def _band(price: float, n_comps: int, ptype: str, area: float) -> tuple[float, float]:
    t = _table()
    lohi = (t.get(f"{liq_bucket(n_comps)}|{ptype}") or t.get(f"_type|{ptype}")
            or t["_global"])
    lo_r, hi_r = lohi[0], lohi[1]
    if is_big_plot(area):
        # widen symmetrically around 1.0: the curve is not reliably identified >=8k sqft
        lo_r = 1.0 - (1.0 - lo_r) * BIG_PLOT_WIDEN
        hi_r = 1.0 + (hi_r - 1.0) * BIG_PLOT_WIDEN
    return round(price * lo_r, 0), round(price * hi_r, 0)


def landed_engine(subject, market, ctx):
    """LV1: LC2 point where the street answers, else LA1 pooled fallback; conformal band."""
    est = lc2_fitted_curve(subject, market, ctx)
    if est is not None:
        psf, n, src = est["psf"], est["n_comps"], "LC2-street"
    else:
        a = la1_pooled_anchor(subject, market, ctx)
        if a is None:
            return None
        psf, n, src = a["psf"], 0, "LA1-pooled-fallback"
    area = subject["area_sqft"]
    price = round(psf * area, 0)
    lo, hi = _band(price, n, subject["property_type"], area)
    note = f"{src}, conformal band"
    if is_big_plot(area):
        note += f" (>={int(8000)}sqft: widened x{BIG_PLOT_WIDEN}, case-tier)"
    return {"method": "LV1_landed_engine", "psf": round(psf, 1), "price": price,
            "low": lo, "high": hi, "n_comps": n, "note": note}


LANDED_ENGINE = {"LV1_landed_engine": landed_engine}
