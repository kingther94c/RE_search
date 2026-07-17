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

    # NOTE: a `drift_factor` (index-momentum extrapolation beyond the last published
    # quarter) used to live here. REJECTED — GY-0003: sliced by regime it broke the four
    # already-unbiased half-years while worsening the one it targeted. Deleted so nobody
    # rediscovers it from this file; the record lives in the method graveyard.

    def as_of_quarter(self, t, pub_lag_days: int = 35) -> str | None:
        """Latest quarter whose index was published by date t (quarter-end + lag <= t)."""
        t = t if isinstance(t, _dt.date) else _dt.date.fromisoformat(str(t)[:10])
        s = self._series("non-landed") or self._series("residential")
        cands = [q for q in s if quarter_end(q) + _dt.timedelta(days=pub_lag_days) <= t]
        return max(cands) if cands else None
