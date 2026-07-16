"""MarketView — an as-of caveat set with indexes built ONCE per valuation month.

The harness groups subjects by valuation month, so all subjects in a month share one
MarketView. Without this, every benchmark rescans ~100k rows per subject (61k subjects ->
~10^10 ops). With it: same-project is a dict lookup, nearest-project is a 3x3 spatial-grid
scan, segment pools are memoized. Indexes build lazily so a method that isn't used costs
nothing.
"""
from __future__ import annotations

import math

from .store import CONDO_TYPES, PURE_LANDED_TYPES, months_between

_CELL = 1000.0  # spatial grid cell = the nearest-project search radius (metres, SVY21)


class MarketView:
    def __init__(self, txs: list[dict], asof_ym: str):
        self.txs = txs
        self.asof_ym = asof_ym
        self._proj: dict[str, list[dict]] | None = None
        self._condo: list[dict] | None = None
        self._grid: dict[tuple[int, int], list[dict]] | None = None
        self._seg_recent: dict[tuple[str, int], list[dict]] = {}
        self._landed: list[dict] | None = None
        self._landed_street: dict[str, list[dict]] | None = None
        self._landed_grid: dict[tuple[int, int], list[dict]] | None = None
        # generic per-month memo for fitted models (e.g. the hedonic AVM fit once/month)
        self.cache: dict = {}

    def same_project(self, project: str) -> list[dict]:
        """Same-project caveats, newest-first. O(1) lookup after the first call."""
        if self._proj is None:
            d: dict[str, list[dict]] = {}
            for t in self.txs:
                d.setdefault(t["project"].strip().casefold(), []).append(t)
            for v in d.values():
                v.sort(key=lambda t: t["contract_ym"], reverse=True)
            self._proj = d
        return self._proj.get((project or "").strip().casefold(), [])

    def condo(self) -> list[dict]:
        if self._condo is None:
            self._condo = [t for t in self.txs if t["property_type"] in CONDO_TYPES
                           and t["type_of_area"].lower() != "land"]
        return self._condo

    def condo_near(self, x: float, y: float, radius_m: float = _CELL) -> list[dict]:
        """Condo caveats within radius_m of (x, y) via a 3x3 grid scan (cell = radius)."""
        if self._grid is None:
            g: dict[tuple[int, int], list[dict]] = {}
            for t in self.condo():
                if t.get("x") is None or t.get("y") is None:
                    continue
                g.setdefault((int(t["x"] // _CELL), int(t["y"] // _CELL)), []).append(t)
            self._grid = g
        cx, cy = int(x // _CELL), int(y // _CELL)
        out = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for t in self._grid.get((cx + dx, cy + dy), ()):
                    if math.hypot(t["x"] - x, t["y"] - y) <= radius_m:
                        out.append(t)
        return out

    def segment_recent(self, seg: str, months: int) -> list[dict]:
        """Condo caveats in `seg` within `months` of the valuation month (memoized)."""
        key = (seg, months)
        if key not in self._seg_recent:
            self._seg_recent[key] = [
                t for t in self.condo()
                if t["market_segment"] == seg
                and 0 <= months_between(t["contract_ym"], self.asof_ym) < months]
        return self._seg_recent[key]

    # ------------------------------------------------------------ landed (L0 mirrors)
    def landed(self) -> list[dict]:
        """Pure-landed pool (Land-titled Terrace/Semi-D/Detached; land psf/area)."""
        if self._landed is None:
            self._landed = [t for t in self.txs
                            if t["type_of_area"].lower() == "land"
                            and t["property_type"] in PURE_LANDED_TYPES]
        return self._landed

    def landed_on_street(self, street: str) -> list[dict]:
        """Pure-landed caveats on a street, newest-first — the landed analogue of
        same_project (streets are the finest grouping URA gives landed)."""
        if self._landed_street is None:
            d: dict[str, list[dict]] = {}
            for t in self.landed():
                d.setdefault(t["street"].strip().casefold(), []).append(t)
            for v in d.values():
                v.sort(key=lambda t: t["contract_ym"], reverse=True)
            self._landed_street = d
        return self._landed_street.get((street or "").strip().casefold(), [])

    def landed_near(self, x: float, y: float, radius_m: float = _CELL) -> list[dict]:
        """Pure-landed caveats within radius_m of (x, y) — own grid, mirrors condo_near."""
        if self._landed_grid is None:
            g: dict[tuple[int, int], list[dict]] = {}
            for t in self.landed():
                if t.get("x") is None or t.get("y") is None:
                    continue
                g.setdefault((int(t["x"] // _CELL), int(t["y"] // _CELL)), []).append(t)
            self._landed_grid = g
        cx, cy = int(x // _CELL), int(y // _CELL)
        out = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for t in self._landed_grid.get((cx + dx, cy + dy), ()):
                    if math.hypot(t["x"] - x, t["y"] - y) <= radius_m:
                        out.append(t)
        return out
