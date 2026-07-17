"""Landed comparables off official URA caveats — street set, land-size cohorts, trend.

Free and official: URA Data Service (a registered key; see researcher/sources/ura.py). For
LANDED rows URA's `area` is the LAND area and `psf` is therefore LAND psf, which is the
denominator landed pricing actually runs on.

    from researcher.landed.comps import street_comps, size_cohorts, trend, subject_cohort
    c = street_comps("SELETAR GREEN WALK")          # every caveat on the street
    size_cohorts(c)                                 # land psf by plot-size band
    subject_cohort(c, area_sqft=1615)               # the comps that actually price YOUR plot

CLI:  python -m researcher.landed.comps "SELETAR GREEN WALK" --area 1615

WHY COHORTS, NOT AN AVERAGE. Landed land-psf is strongly size-dependent: on one street, in one
period, on one tenure, small plots clear at a much higher land psf than big ones. Seletar Green
Walk 2021-2026: 1,615 sqft terraces run ~S$2,700-3,232/psf while 2,150-2,988 sqft plots run
~S$2,000-2,405/psf. A street "average psf" mixes those and describes no actual house — it is
also exactly how portal psf figures end up looking self-contradictory. Always price a subject
against its OWN size band.

WHAT THIS IS NOT. A caveat price is land+building bundled; it is not decomposable into a pure
land value by dividing by land area, and this module does not pretend otherwise. It gives you
observed transactions and their spread, not a valuation. Valuation is the L-track engine's job
(research/registry/01_roadmap.md); don't smuggle a fair value out of these numbers.

URA limits that shape every figure here (see researcher/sources/ura.py):
  - contractDate is MONTH granularity only -- no day.
  - Rolling ~5 years of caveats only.
  - Landed project names are anonymised to "LANDED HOUSING DEVELOPMENT", so the street is the
    only join key -- you cannot pin a caveat to a house number from URA alone.
  - **URA's `street` is a COARSE PARENT/LOCALITY LABEL, not the address street** (measured,
    EXP-0018): it merges adjacent roads of the same estate. Two consequences for every number
    below. (1) A street set can contain houses that are NOT on that road: URA's "LOYANG RISE"
    (135 caveats) is exactly IS's Loyang Rise (104) + IS's Loyang View (31), 0 unexplained.
    (2) An EMPTY result does not prove there were no sales -- the road may be filed under its
    parent: CARDIFF GROVE returns [] here while its houses sit in URA under "ALNWICK ROAD"
    (16 of 17 in-window sales matched on month+price+area). Investment Suite is the only
    source that resolves a caveat to a real address; whether splitting to the true address
    street helps or hurts a comp set is open (roadmap L2f) -- so this module keeps URA's
    definition and DECLARES it rather than guessing.
  - Caveats lag the transaction, so the most recent months are under-reported.
"""
from __future__ import annotations

import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TX = os.path.join(REPO, "researcher", "sources", "ura_transactions.json")

LANDED_TYPES = {"Terrace", "Semi-detached", "Detached",
                "Strata Terrace", "Strata Semi-detached", "Strata Detached"}
_tx_cache: list[dict] | None = None


def _load() -> list[dict]:
    global _tx_cache
    if _tx_cache is None:
        if not os.path.exists(TX):
            raise RuntimeError(
                f"No URA transactions at {TX}. Pull them first:\n"
                "    python -m researcher.sources.ura\n"
                "(needs a free URA_ACCESS_KEY — see researcher/sources/ura.py)")
        with open(TX, encoding="utf-8") as f:
            _tx_cache = json.load(f)
    return _tx_cache


def street_comps(street: str, landed_only: bool = True) -> list[dict]:
    """Every URA caveat on a street, oldest first. Matching is case-insensitive exact on
    URA's street name — pass the street as URA spells it.

    An EMPTY result means URA has no caveats filed UNDER THAT NAME. It does NOT prove the
    road had no sales: URA's street is a parent label (see the module docstring), so a small
    road can be filed under the estate's main road — CARDIFF GROVE returns [] here while its
    houses are in URA under "ALNWICK ROAD" (EXP-0018). On an empty result, look up the parent
    road before reporting "no transactions"; conversely, a non-empty set may include houses on
    adjacent roads."""
    s = street.strip().upper()
    rows = [t for t in _load() if (t.get("street") or "").upper() == s]
    if landed_only:
        rows = [t for t in rows if t.get("property_type") in LANDED_TYPES]
    return sorted(rows, key=lambda t: t["contract_ym"])


def size_cohorts(comps: list[dict], bands: tuple = (1800, 2500, 3500)) -> list[dict]:
    """Land psf grouped into plot-size bands. Exposes the size effect instead of averaging
    it away. Bands are upper bounds in sqft; the last cohort is everything above."""
    edges = list(bands) + [float("inf")]
    out = []
    lo = 0.0
    for hi in edges:
        rows = [c for c in comps if lo <= c["area_sqft"] < hi]
        if rows:
            psf = [c["psf"] for c in rows]
            out.append({
                "band": f"<{hi:,.0f}" if lo == 0 else
                        (f">={lo:,.0f}" if hi == float("inf") else f"{lo:,.0f}-{hi:,.0f}"),
                "lo_sqft": lo, "hi_sqft": None if hi == float("inf") else hi,
                "n": len(rows),
                "psf_min": round(min(psf)), "psf_med": round(statistics.median(psf)),
                "psf_max": round(max(psf)),
                "price_med": round(statistics.median([c["price"] for c in rows])),
                "area_med": round(statistics.median([c["area_sqft"] for c in rows])),
            })
        lo = hi
    return out


def subject_cohort(comps: list[dict], area_sqft: float, tol: float = 0.06) -> dict:
    """The comps that actually price a subject of this plot size (within +/-tol).

    tol defaults to 6% — tight enough that a 1,615 sqft terrace is not priced off a 2,200 sqft
    one. If that leaves too few rows, WIDEN DELIBERATELY and say you did; do not quietly fall
    back to the street average, which is the error this module exists to prevent.
    """
    lo, hi = area_sqft * (1 - tol), area_sqft * (1 + tol)
    rows = [c for c in comps if lo <= c["area_sqft"] <= hi]
    if not rows:
        return {"n": 0, "area_sqft": area_sqft, "tol": tol, "rows": [],
                "note": f"no comps within +/-{tol:.0%} of {area_sqft:,.0f} sqft"}
    psf = [c["psf"] for c in rows]
    recent = rows[-6:]
    return {
        "n": len(rows), "area_sqft": area_sqft, "tol": tol,
        "psf_min": round(min(psf)), "psf_med": round(statistics.median(psf)),
        "psf_max": round(max(psf)),
        "first_ym": rows[0]["contract_ym"], "last_ym": rows[-1]["contract_ym"],
        "recent": [{"ym": r["contract_ym"], "price": r["price"], "psf": round(r["psf"]),
                    "area_sqft": round(r["area_sqft"]), "type": r["property_type"]}
                   for r in recent],
        "rows": rows,
    }


def trend(comps: list[dict], by: str = "year") -> list[dict]:
    """Median land psf and price per period. `by` = 'year' or 'ym'.

    Month buckets on a landed street are mostly n=1-2 — a 'trend' off single prints is noise.
    Default to years, and read n on every row before believing a move.
    """
    buckets: dict[str, list[dict]] = {}
    for c in comps:
        k = c["contract_ym"][:4] if by == "year" else c["contract_ym"]
        buckets.setdefault(k, []).append(c)
    return [{
        "period": k, "n": len(v),
        "psf_med": round(statistics.median([x["psf"] for x in v])),
        "price_med": round(statistics.median([x["price"] for x in v])),
        "area_med": round(statistics.median([x["area_sqft"] for x in v])),
    } for k, v in sorted(buckets.items())]


def tenure_summary(comps: list[dict]) -> dict:
    """What the caveats say the tenure is. Landed listings routinely round '999 yrs from 1879'
    to 'freehold'; the caveats are the free way to catch that before you offer."""
    raw: dict[str, int] = {}
    for c in comps:
        raw[c["tenure_raw"] or "?"] = raw.get(c["tenure_raw"] or "?", 0) + 1
    return {"distinct": raw, "n": len(comps),
            "unanimous": raw and len(raw) == 1}


def summarise(street: str, area_sqft: float | None = None) -> dict:
    c = street_comps(street)
    out = {"street": street.upper(), "n": len(c),
           "first_ym": c[0]["contract_ym"] if c else None,
           "last_ym": c[-1]["contract_ym"] if c else None,
           "tenure": tenure_summary(c), "cohorts": size_cohorts(c),
           "trend": trend(c), "types": {}}
    for t in c:
        out["types"][t["property_type"]] = out["types"].get(t["property_type"], 0) + 1
    if area_sqft:
        out["subject"] = subject_cohort(c, area_sqft)
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        raise SystemExit(2)
    area = None
    for i, a in enumerate(sys.argv):
        if a == "--area" and i + 1 < len(sys.argv):
            area = float(sys.argv[i + 1])

    d = summarise(args[0], area)
    print(f"{d['street']} — {d['n']} landed caveats, {d['first_ym']}..{d['last_ym']}")
    if not d["n"]:
        raise SystemExit(0)
    print("  types  :", ", ".join(f"{k}={v}" for k, v in sorted(d["types"].items())))
    t = d["tenure"]
    print(f"  tenure : {'UNANIMOUS ' if t['unanimous'] else 'MIXED '}"
          + "; ".join(f"{k} (n={v})" for k, v in t["distinct"].items()))

    print("\n  land psf by plot size — the size effect, not an average")
    print(f"    {'band (sqft)':<14}{'n':>4}{'psf min':>9}{'psf med':>9}{'psf max':>9}{'median price':>15}")
    for b in d["cohorts"]:
        print(f"    {b['band']:<14}{b['n']:>4}{b['psf_min']:>9,}{b['psf_med']:>9,}"
              f"{b['psf_max']:>9,}{b['price_med']:>15,}")

    print("\n  median land psf by year (read n — a landed street is thin)")
    for r in d["trend"]:
        print(f"    {r['period']}  n={r['n']:<3} psf {r['psf_med']:>6,}  "
              f"price {r['price_med']:>11,}  area {r['area_med']:>6,} sqft")

    if d.get("subject"):
        s = d["subject"]
        print(f"\n  subject cohort — {s['area_sqft']:,.0f} sqft +/-{s['tol']:.0%}")
        if not s["n"]:
            print("   ", s["note"])
        else:
            print(f"    n={s['n']}  {s['first_ym']}..{s['last_ym']}  "
                  f"land psf {s['psf_min']:,} / {s['psf_med']:,} / {s['psf_max']:,} (min/med/max)")
            print("    most recent:")
            for r in s["recent"]:
                print(f"      {r['ym']}  ${r['price']:>10,}  {r['area_sqft']:>5,} sqft  "
                      f"${r['psf']:>6,}/psf  {r['type']}")
    print("\n  caveat prices bundle land+building. These are observed transactions and their")
    print("  spread — not a valuation. Month granularity; recent months under-report (lag).")
