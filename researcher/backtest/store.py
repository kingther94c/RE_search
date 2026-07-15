"""As-of-queryable transaction store — the leakage firewall of the backtest.

The one job: given a valuation date t, hand back ONLY the caveats a valuer could
actually have seen at t. Two subtleties URA forces on us, both handled here:

  1. contractDate is month-only. We treat a transaction as occurring at its month-END
     (the latest possible day) so we never reveal it too early.
  2. Caveats are lodged AFTER the transaction and published later still. `as_of` adds a
     conservative lag buffer (default 56 days) on top of month-end before a caveat is
     considered visible. Tune with lag_days; document any change in the experiment log.

Everything is a cheap immutable view: filters return a new TransactionStore over a
sub-list, so `store.as_of(t).is_condo().same_project(p)` chains without mutating.
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT = os.path.join(os.path.dirname(_HERE), "sources", "ura_transactions.json")

# Private-condo universe. EC (Executive Condominium) is deliberately EXCLUDED — it is a
# distinct HDB-hybrid sub-market that trades at a discount and would contaminate the
# segment pool (scope choice, logged in the experiment registry).
CONDO_TYPES = {"Condominium", "Apartment"}
# URA's real landed spellings vary: 'Terrace', 'Semi-detached', 'Detached', and strata
# variants 'Strata Terrace' / 'Strata Semi-detached' / 'Strata Detached'. Match on substring.
_LANDED_KEYS = ("terrace", "detached", "semi-detached")


def _as_date(t) -> _dt.date:
    if isinstance(t, _dt.date):
        return t
    return _dt.date.fromisoformat(str(t)[:10])


def month_end(ym: str) -> _dt.date:
    """'2025-06' -> date(2025, 6, 30)."""
    y, m = (int(x) for x in ym.split("-"))
    nxt = _dt.date(y + (m == 12), (m % 12) + 1, 1)
    return nxt - _dt.timedelta(days=1)


def visible_from(ym: str, lag_days: int) -> _dt.date:
    """Earliest date a caveat dated `ym` is assumed knowable = month-end + lag."""
    return month_end(ym) + _dt.timedelta(days=lag_days)


def months_between(a_ym: str, b_ym: str) -> int:
    """Whole months from a_ym to b_ym (b - a). Negative if b precedes a."""
    ay, am = (int(x) for x in a_ym.split("-"))
    by, bm = (int(x) for x in b_ym.split("-"))
    return (by - ay) * 12 + (bm - am)


class TransactionStore:
    def __init__(self, transactions: list[dict]):
        self.txs = transactions

    @classmethod
    def load(cls, path: str = _DEFAULT) -> "TransactionStore":
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    def __len__(self) -> int:
        return len(self.txs)

    # --------------------------------------------------------------- as-of firewall
    def as_of(self, t, lag_days: int = 56) -> "TransactionStore":
        """Caveats visible at date t (month-end + lag_days <= t). THE leakage guard."""
        t = _as_date(t)
        return TransactionStore([x for x in self.txs
                                 if visible_from(x["contract_ym"], lag_days) <= t])

    # ----------------------------------------------------------------------- filters
    def where(self, pred) -> "TransactionStore":
        return TransactionStore([x for x in self.txs if pred(x)])

    def same_project(self, project: str) -> "TransactionStore":
        key = (project or "").strip().casefold()
        return self.where(lambda x: x["project"].strip().casefold() == key)

    def segment(self, seg: str) -> "TransactionStore":
        s = seg.strip().upper()
        return self.where(lambda x: x["market_segment"] == s)

    def is_condo(self) -> "TransactionStore":
        return self.where(lambda x: x["property_type"] in CONDO_TYPES
                          and x["type_of_area"].lower() != "land")

    def is_landed(self) -> "TransactionStore":
        def ok(x):
            pt = x["property_type"].lower()
            return x["type_of_area"].lower() == "land" or any(k in pt for k in _LANDED_KEYS)
        return self.where(ok)

    def property_type(self, pt: str) -> "TransactionStore":
        return self.where(lambda x: x["property_type"] == pt)

    def near(self, x: float, y: float, radius_m: float) -> "TransactionStore":
        """Within radius_m of SVY21 point (x, y). SVY21 units are metres, so plane
        distance ~= ground metres. Rows without coords are dropped."""
        def ok(t):
            if t.get("x") is None or t.get("y") is None:
                return False
            return math.hypot(t["x"] - x, t["y"] - y) <= radius_m
        return self.where(ok)

    def within_months(self, before_ym: str, months: int) -> "TransactionStore":
        """Caveats in the `months` months up to and including before_ym."""
        return self.where(lambda t: 0 <= months_between(t["contract_ym"], before_ym) < months)

    def sorted_by_ym(self, reverse: bool = True) -> list[dict]:
        return sorted(self.txs, key=lambda t: t["contract_ym"], reverse=reverse)

    # ------------------------------------------------------------- subject sampling
    def subjects(self, *, kind: str = "condo", sale_types=("Resale",),
                 min_ym: str | None = None, max_ym: str | None = None,
                 min_area_sqft: float = 300, max_area_sqft: float = 6000) -> list[dict]:
        """Candidate subjects to re-price out-of-sample. Defaults to resale condos with
        a sane area; narrow by date window for a quick run."""
        base = self.is_condo() if kind == "condo" else self.is_landed()
        st = {s.lower() for s in sale_types}

        def ok(t):
            if t["type_of_sale"].lower() not in st:
                return False
            if not (min_area_sqft <= t["area_sqft"] <= max_area_sqft):
                return False
            if min_ym and t["contract_ym"] < min_ym:
                return False
            if max_ym and t["contract_ym"] > max_ym:
                return False
            return True
        return [t for t in base.txs if ok(t)]
