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
import glob
import gzip
import json
import math
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_SOURCES = os.path.join(os.path.dirname(_HERE), "sources")
_DEFAULT = os.path.join(_SOURCES, "ura_transactions.json")
_SNAPSHOTS = os.path.join(_SOURCES, "snapshots")


def _newest_snapshot() -> str | None:
    """Newest committed frozen store, for a fresh clone with no local pull."""
    snaps = sorted(glob.glob(os.path.join(_SNAPSHOTS, "ura_transactions_*.json.gz")))
    return snaps[-1] if snaps else None

# Private-condo universe. EC (Executive Condominium) is deliberately EXCLUDED — it is a
# distinct HDB-hybrid sub-market that trades at a discount and would contaminate the
# segment pool (scope choice, logged in the experiment registry).
CONDO_TYPES = {"Condominium", "Apartment"}
# URA's real landed spellings vary: 'Terrace', 'Semi-detached', 'Detached', and strata
# variants 'Strata Terrace' / 'Strata Semi-detached' / 'Strata Detached'. Match on substring.
_LANDED_KEYS = ("terrace", "detached", "semi-detached")
# The L-track subject universe (L0 / EXP-0009): rows that are BOTH type_of_area='Land'
# AND one of these exact types. psf on these rows = LAND psf, area = LAND area.
# Strata-landed (cluster housing, trades on strata area) is a separate orphaned
# sub-market — in scope for NEITHER the condo nor the landed engine (routing note in the
# roadmap). 'Apartment' rows with Land area (walk-up / whole-building deals) are excluded
# by the type test.
PURE_LANDED_TYPES = {"Terrace", "Semi-detached", "Detached"}
# Land-psf sanity band (L0 / EXP-0009, percentile-verified): today's extremes are REAL —
# p0=107 psf is a ~8-years-left 70yr-lease terrace (Jalan Chempaka Kuning), p100=5,756 is
# an Emerald Hill conservation terrace. The band wraps the verified range to catch future
# data errors, NOT to trim the short-lease or conservation tails (cuts 0 rows today).
LANDED_PSF_BAND = (100.0, 6500.0)


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
        """Load the local pull if present, else the newest committed snapshot (so a fresh
        clone runs backtests without a URA key). Repull with `python -m researcher.sources.ura`."""
        if not os.path.exists(path):
            snap = _newest_snapshot()
            if not snap:
                raise FileNotFoundError(
                    f"no store at {path} and no snapshot in {_SNAPSHOTS}. "
                    "Run: python -m researcher.sources.ura")
            with gzip.open(snap, "rt", encoding="utf-8") as f:
                return cls(json.load(f))
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

    def is_pure_landed(self) -> "TransactionStore":
        """Land-titled landed homes only: type_of_area='Land' AND an exact landed type.
        Excludes strata-landed (different sub-market) and Apartment+Land whole-building
        rows. psf/area on every row returned = LAND psf / LAND area."""
        return self.where(lambda x: x["type_of_area"].lower() == "land"
                          and x["property_type"] in PURE_LANDED_TYPES)

    def is_strata_landed(self) -> "TransactionStore":
        """Cluster housing (Strata Terrace/Semi-detached/Detached) — trades on STRATA
        area. Orphaned sub-market: v1 scope of both engines DECLINES these with a routing
        note (condo backlog #4)."""
        return self.where(lambda x: x["type_of_area"].lower() != "land"
                          and any(k in x["property_type"].lower() for k in _LANDED_KEYS))

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

    # ------------------------------------------------------------- data hygiene (R0)
    def exclude_bulk(self) -> "TransactionStore":
        """Drop multi-unit / en-bloc caveats — non-market-rate as subject AND as comp."""
        return self.where(lambda t: t["no_of_units"] <= 1)

    def psf_band(self, lo: float = 500, hi: float = 6500) -> "TransactionStore":
        """Keep psf within a sanity band (audit: 107 caveats <500, 2 >6500 — data errors)."""
        return self.where(lambda t: lo <= t["psf"] <= hi)

    def sorted_by_ym(self, reverse: bool = True) -> list[dict]:
        return sorted(self.txs, key=lambda t: t["contract_ym"], reverse=reverse)

    # ------------------------------------------------------------- subject sampling
    def subjects(self, *, kind: str = "condo", sale_types=("Resale",),
                 min_ym: str | None = None, max_ym: str | None = None,
                 min_area_sqft: float | None = None,
                 max_area_sqft: float | None = None) -> list[dict]:
        """Candidate subjects to re-price out-of-sample.

        kind: 'condo' (strata Apt+Condo, EC excl) · 'pure-landed' (the L-track universe)
        · 'landed' (broad union incl. strata-landed — audits only, not a subject base).
        Area bounds default PER KIND — condo 300..6,000 sqft STRATA area; landed
        400..150,000 sqft LAND area (EXP-0009: p0.1=883 / p99.9=27,909 — the landed
        bounds are sanity guards against unit errors, not filters)."""
        if kind == "condo":
            base, lo, hi = self.is_condo(), 300.0, 6000.0
        elif kind == "pure-landed":
            base, lo, hi = self.is_pure_landed(), 400.0, 150000.0
        else:
            base, lo, hi = self.is_landed(), 400.0, 150000.0
        min_area_sqft = lo if min_area_sqft is None else min_area_sqft
        max_area_sqft = hi if max_area_sqft is None else max_area_sqft
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
