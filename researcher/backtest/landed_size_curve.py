"""L2a: the fitted landed land-size curve (EXP-0011) — replaces LC1's ported -0.877.

WHY: `landed_benchmarks.CRAFT_SIZE_ELASTICITY = -0.877` came from ONE street's two
cross-size legs in the Cardiff craft valuation (guardrail-#5). L1 showed size is the
dominant error axis (LC1: 8.8% median APE at 1.5-3k sqft -> 41.2% at 15k+, monotone).

WHAT THE DATA SAYS (research/fit_land_size_curve.py — within-street FIXED-EFFECTS slope of
ln(psf) on ln(area), so street prestige/location cannot contaminate it; n=10,399 rows in
1,027 street-type groups; near-simultaneous pairs cross-check agrees at -0.575):
  - global elasticity is **-0.50**, not -0.877 — the craft constant over-corrects ~1.7x;
  - a SINGLE log-log constant is inadequate — the slope COLLAPSES with size:
        <3k -0.53 | 3-5k -0.60 | 5-8k -0.59 | 8-15k -0.01 | 15k+ +0.05
    Economically: small terrace plots trade on QUANTUM (an extra sqft is worth ~nothing, so
    psf falls steeply with size); big detached plots trade on LAND (each sqft carries ~full
    marginal value, so psf is ~flat in size).
  - TYPE is NOT an independent axis: within a size band, Detached is as steep as Terrace
    (3-5k: Terr -0.73 / Semi -0.56 / Deta -0.63). The global "Detached -0.24" was a size
    composition artifact. So the curve is keyed on SIZE ALONE.

LEAKAGE: the backtest subject window starts 2023-01, so shipped values are anchored on the
PRE-2023 fit and cross-checked against full history (they agree where identified):
  <3k pre -0.509 / full -0.526 · 3-5k pre -0.685 / full -0.596 · 5-8k pre -0.547 / full -0.585.
The constants are structural (stable across periods), not a price signal.

HONEST SCOPE LIMIT (>=8k sqft): the two periods DISAGREE (8-15k: pre -0.349 vs full -0.006)
on n=14-51 street groups. The big-plot regime — exactly where L1 measured 24-41% median APE
— is where URA identifies the curve WORST. We ship a conservative flat-ish -0.20 there and
the engine must treat >=8k as wide-band / case-tier (L3/L4), never as a precise curve.
"""
from __future__ import annotations

import math

# (lo_sqft, hi_sqft, elasticity) — piecewise-constant d ln(psf) / d ln(area)
BANDS: list[tuple[float, float, float]] = [
    (1000.0, 3000.0, -0.51),     # quantum regime: extra land ~free
    (3000.0, 5000.0, -0.64),
    (5000.0, 8000.0, -0.56),
    (8000.0, 1e9, -0.20),        # land regime — POORLY IDENTIFIED, scope-limited (see docstring)
]
BIG_PLOT_SQFT = 8000.0           # at/above this the curve is low-confidence: widen + case-tier
_FLOOR = 1000.0                  # clamp: landed p25 is ~1,880 sqft; below this is not a plot


def _F(area: float) -> float:
    """Antiderivative of the elasticity in ln(area) space. Piecewise-LINEAR in ln(area), so
    exp(F(b) - F(a)) is CONTINUOUS across band breaks — no price jump at 3k/5k/8k sqft."""
    a = max(float(area), _FLOOR)
    total = 0.0
    for lo, hi, e in BANDS:
        if a <= lo:
            break
        total += e * (math.log(min(a, hi)) - math.log(lo))
    return total


def size_factor(area_from: float, area_to: float) -> float:
    """Multiply a comp's land-psf by this to move it from `area_from` to `area_to`.

    Integrates the fitted piecewise elasticity, so a 2,000->10,000 sqft move correctly
    crosses the quantum->land regimes instead of applying one constant to both.
    """
    if area_from <= 0 or area_to <= 0:
        return 1.0
    return math.exp(_F(area_to) - _F(area_from))


def is_big_plot(area: float) -> bool:
    """>=8k sqft: the curve is not reliably identified here (see docstring) — the engine
    must widen the band and route to the case protocol rather than trust a point."""
    return float(area) >= BIG_PLOT_SQFT
