"""URA Property Price Index adapter for time adjustment — with as-of publication lag.

Reads the SingStat-fetched series (researcher/marketdata/price_index.json). Two rules
keep it leakage-safe inside a backtest:

  - `factor(from_ym, to_ym, kind)` = index(to)/index(from): move a comp's psf from its
    quarter to the target quarter.
  - `as_of_quarter(t)` = the latest quarter whose index was PUBLISHED by date t. URA
    releases the flash estimate ~4 weeks after quarter-end; default pub lag is 35 days.
    A backtest at date t must target this quarter, never a later (unknowable) one.

If the index file is absent (no fetch yet) every factor is 1.0 and `available` is False,
so a benchmark degrades to "no time adjustment" rather than crashing.
"""
from __future__ import annotations

import datetime as _dt
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_INDEX = os.path.join(os.path.dirname(_HERE), "marketdata", "price_index.json")

_Q_END = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


def q_of_ym(ym: str) -> str:
    """'2025-06' -> '2025Q2'."""
    y, m = (int(x) for x in ym.split("-"))
    return f"{y}Q{(m - 1) // 3 + 1}"


def quarter_end(q: str) -> _dt.date:
    y, qq = q.split("Q")
    mm, dd = _Q_END[int(qq)]
    return _dt.date(int(y), mm, dd)


class PriceIndex:
    def __init__(self, series: dict[str, dict[str, float]]):
        self.series = series  # {kind: {quarter: value}}
        self.available = bool(series)

    @classmethod
    def load(cls, path: str = _INDEX) -> "PriceIndex":
        if not os.path.exists(path):
            return cls({})
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        out: dict[str, dict[str, float]] = {"non-landed": {}, "landed": {},
                                            "residential": {}}
        for name, pts in (raw.get("series") or {}).items():
            low = name.lower()
            kind = ("non-landed" if "non-landed" in low or "non landed" in low
                    else "landed" if "landed" in low
                    else "residential" if "residential" in low else None)
            if kind:
                out[kind] = {q: v for q, v in pts}
        return cls(out)

    def _series(self, kind: str) -> dict[str, float]:
        k = kind.lower()
        k = "non-landed" if k in ("condo", "non-landed", "nonlanded") else \
            "landed" if k == "landed" else "residential"
        return self.series.get(k) or self.series.get("residential") or {}

    def value(self, ym_or_q: str, kind: str = "non-landed") -> float | None:
        """Index value at a quarter (accepts 'YYYY-MM' or 'YYYYQn'); falls back to the
        latest earlier quarter that exists."""
        q = ym_or_q if "Q" in ym_or_q else q_of_ym(ym_or_q)
        s = self._series(kind)
        if not s:
            return None
        if q in s:
            return s[q]
        earlier = [k for k in s if k <= q]
        return s[max(earlier)] if earlier else None

    def factor(self, from_ym: str, to_ym: str, kind: str = "non-landed") -> float:
        """Multiplier to move a value from from_ym's quarter to to_ym's quarter."""
        a, b = self.value(from_ym, kind), self.value(to_ym, kind)
        if not a or not b:
            return 1.0
        return b / a

    def drift_factor(self, from_q: str, to_ym: str, kind: str = "non-landed",
                     lookback_q: int = 4, cap: float = 0.06) -> float:
        """Extrapolate the index from the last PUBLISHED quarter `from_q` to `to_ym`.

        Adjusting a comp only to the last published quarter leaves the estimate structurally
        1-2 quarters stale: at as-of 2026-07 the newest published quarter is 2026Q1, so in a
        market running ~7.6%/yr the point is ~1.2pp low — a one-directional bias measured on
        the landed engine (actual exceeded the point 63% of the time). This projects the
        gap forward at the recent PUBLISHED trend, so no unpublished data is used (the
        drift is estimated only from quarters already visible at the valuation date).

        Capped: an extrapolation is a forecast, not an observation. Returns 1.0 when the
        series is too short to establish a trend.
        """
        s = self._series(kind)
        if not s or from_q not in s:
            return 1.0
        hist = sorted(q for q in s if q <= from_q)
        if len(hist) < lookback_q + 1:
            return 1.0
        base, prior = s[hist[-1]], s[hist[-1 - lookback_q]]
        if prior <= 0:
            return 1.0
        per_q = (base / prior) ** (1.0 / lookback_q) - 1.0      # avg quarterly growth
        y, m = (int(x) for x in to_ym.split("-"))
        fy, fq = int(from_q[:4]), int(from_q[-1])
        q_gap = (y - fy) * 4 + ((m - 1) // 3 + 1 - fq)
        if q_gap <= 0:
            return 1.0
        f = (1.0 + per_q) ** q_gap
        return min(max(f, 1.0 - cap), 1.0 + cap)

    def as_of_quarter(self, t, pub_lag_days: int = 35) -> str | None:
        """Latest quarter whose index was published by date t (quarter-end + lag <= t)."""
        t = t if isinstance(t, _dt.date) else _dt.date.fromisoformat(str(t)[:10])
        s = self._series("non-landed") or self._series("residential")
        cands = [q for q in s if quarter_end(q) + _dt.timedelta(days=pub_lag_days) <= t]
        return max(cands) if cands else None
