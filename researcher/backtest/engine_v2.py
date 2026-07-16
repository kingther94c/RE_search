"""Condo engine v2 (V2) — the R3 outcome. Simpler than the blend ensembles, because the
evidence (EXP-0006 thin-comp matrix) showed blending an anchor into C1 HURTS the point
wherever same-project data exists — even at 1-2 comps. So:

  POINT     = C1 (same-project grid) wherever it answers (best on every liquidity bucket);
              else fall back to the best independent anchor (A2 pooled -> A3 kNN -> A1)
              purely to keep coverage at 100% for the ~0.6% no-same-project-comp cases.
  INTERVAL  = split-conformal per (liquidity x segment) cell (conformal_table.json,
              calibrated on an early slice, validated ~82% coverage held-out) — ~30-57%
              sharper than the union band the E-series used.

The E0-E3 ensembles were the necessary experiments that proved the blend doesn't help the
point; they are superseded by this. The anchors survive as the fallback + interval inputs.
"""
from __future__ import annotations

import json
import os

from .avm import avm_hedonic
from .avm_knn import avm_knn
from .avm_pooled import avm_pooled
from .candidates import c1_grid_adapted

_TABLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conformal_table.json")
_TABLE: dict | None = None


def _table() -> dict:
    global _TABLE
    if _TABLE is None:
        try:
            with open(_TABLE_PATH, encoding="utf-8") as f:
                _TABLE = json.load(f)
        except FileNotFoundError:
            _TABLE = {"_global": [0.90, 1.10]}   # inert default until the table is built
    return _TABLE


def _liq(n: int) -> str:
    return "0" if not n else "1-2" if n <= 2 else "3-5" if n <= 5 else "6-15" if n <= 15 else "16+"


def _conformal_band(price: float, n_comps: int, seg: str) -> tuple[float, float]:
    t = _table()
    lohi = t.get(f"{_liq(n_comps)}|{seg}") or t.get(f"_seg|{seg}") or t["_global"]
    return round(price * lohi[0], 0), round(price * lohi[1], 0)


def engine_v2(subject, market, ctx):
    """V2: C1 point wherever available, else best-anchor fallback; conformal interval."""
    c1 = c1_grid_adapted(subject, market, ctx)
    if c1 is not None:
        psf, n, src = c1["psf"], c1["n_comps"], "C1"
    else:
        for fn, tag in ((avm_pooled, "A2"), (avm_knn, "A3"), (avm_hedonic, "A1")):
            a = fn(subject, market, ctx)
            if a is not None:
                psf, n, src = a["psf"], 0, tag + "-fallback"
                break
        else:
            return None
    area = subject["area_sqft"]
    price = round(psf * area, 0)
    lo, hi = _conformal_band(price, n, subject.get("market_segment") or "")
    return {"method": "V2_engine", "psf": round(psf, 1), "price": price,
            "low": lo, "high": hi, "n_comps": n, "note": f"{src}, conformal band"}


ENGINE_V2 = {"V2_engine": engine_v2}
