"""Normalize an Investment Suite street-caveat harvest — ONE parser for every consumer.

`harvest_street_sale.py` deliberately stores cell text AS PRINTED by the app
("$1,301", "1,615", "26 Jun 2026", "Terrace House"); analysis needs numbers.
This module is the single place that turns those strings into fields, so
`is_street_compare.py`, `reconcile_is_ura.py` and any future consumer cannot
drift apart on parsing rules.

Why IS street harvests matter at all (EXP-0018): URA anonymises landed addresses
to a PARENT street label, so a URA bucket can mix several real roads. IS carries
the true house number and road — `_road` on every row is the field that lets you
slice a mixed URA bucket into the road you are actually pricing.

Honesty notes carried by the data itself:
  - psf/price are the app's RAW bundle figures (land+building), UNADJUSTED —
    never compare them 1:1 with the engine's time+size-adjusted psf;
  - dates are day-granular (URA API is month-granular) — a day is a finding,
    never a join key (reconcile_is_ura matches on MONTH+area+price);
  - the harvester only reads the expanded CAVEAT table (agency panel refused),
    so rows here are caveats, not asking/agency data.
"""
from __future__ import annotations

import json
import os
import re
import statistics
from datetime import datetime

IS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "is_street")

# App vocabulary -> URA property_type vocabulary (store.PURE_LANDED_TYPES), so a
# road slice can be compared against the URA spine without a second mapping.
PTYPE = {
    "terrace house": "Terrace",
    "semi-detached house": "Semi-detached",
    "semi detached house": "Semi-detached",
    "detached house": "Detached",
    "cluster house": "Strata cluster",   # strata-landed: NEVER into a land-psf figure
}

_HOUSE_NO = re.compile(r"^\d+[A-Z]?\s+")


def _num(s) -> float | None:
    if s is None:
        return None
    t = re.sub(r"[^\d.]", "", str(s))
    return float(t) if t else None


def road_of(address: str) -> str:
    """'17 Cardiff Grove' -> 'CARDIFF GROVE' (the true road — the IS superpower)."""
    return _HOUSE_NO.sub("", (address or "").strip()).upper()


def parse_row(r: dict) -> dict:
    """Augment a raw harvest row with parsed fields (raw keys stay untouched)."""
    out = dict(r)
    try:
        dt = datetime.strptime(r.get("date", ""), "%d %b %Y")
        out["_date"], out["_ym"] = dt.date().isoformat(), dt.strftime("%Y-%m")
    except ValueError:
        out["_date"] = out["_ym"] = None
    out["_area"] = _num(r.get("area_sqft"))
    out["_psf"] = _num(r.get("psf"))
    out["_price"] = _num(r.get("price"))
    out["_road"] = road_of(r.get("address", ""))
    out["_ptype"] = PTYPE.get((r.get("type") or "").strip().lower())
    return out


def load_harvest(slug_or_path: str) -> dict:
    """Load research/data/is_street/<slug>_sale.json (or an explicit path)."""
    p = slug_or_path if slug_or_path.endswith(".json") else \
        os.path.join(IS_DIR, f"{slug_or_path}_sale.json")
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    d["rows"] = [parse_row(r) for r in d.get("rows", [])]
    return d


def by_road(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(r["_road"] or "?", []).append(r)
    return out


def cohort(rows: list[dict], area_sqft: float, tol: float = 0.06) -> list[dict]:
    lo, hi = area_sqft * (1 - tol), area_sqft * (1 + tol)
    return [r for r in rows if r["_area"] and lo <= r["_area"] <= hi]


def _ym_idx(ym: str) -> int:
    y, m = ym.split("-")
    return int(y) * 12 + int(m) - 1


def distribution(rows: list[dict]) -> dict | None:
    """RAW-psf distribution of a row set: n, p25/med/p75, price med, span,
    trailing-12m median and the last-3-print cluster. None if no usable rows."""
    rs = sorted((r for r in rows if r["_psf"] and r["_ym"]), key=lambda r: r["_ym"])
    if not rs:
        return None
    psf = [r["_psf"] for r in rs]
    if len(psf) >= 4:
        q = statistics.quantiles(psf, n=4, method="inclusive")
        p25, p75 = q[0], q[2]
    else:
        p25 = p75 = None
    end = _ym_idx(rs[-1]["_ym"])
    w12 = [r["_psf"] for r in rs if _ym_idx(r["_ym"]) > end - 12]
    return {
        "n": len(rs), "first_ym": rs[0]["_ym"], "last_ym": rs[-1]["_ym"],
        "psf_med": statistics.median(psf), "psf_p25": p25, "psf_p75": p75,
        "price_med": statistics.median(r["_price"] for r in rs if r["_price"]) if any(r["_price"] for r in rs) else None,
        "n12": len(w12), "med12_psf": statistics.median(w12) if w12 else None,
        "cluster": [(r["_ym"], r["_psf"]) for r in rs[-3:]],
        "cluster_med": statistics.median(r["_psf"] for r in rs[-3:]),
    }
