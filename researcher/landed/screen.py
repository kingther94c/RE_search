"""Landed-listings screening (PropertyGuru payloads → scorecard → GO/CHECK ranking).

PropertyGuru blocks server-side fetches (WebFetch → HTTP 403), so listings are
gathered by **WebSearch** (which surfaces and summarises live PropertyGuru
listings) — see the `screen-landed-listings` skill for the exact queries and URL
patterns. The pulled listings live in `researcher/landed/<area>_listings.json`.

This module normalises each listing into the landed `scorecard` input, scores it
(quality), and flags **value** = land psf vs the area benchmark band, then ranks.
Run:  python -m researcher.landed.screen [area_slug]
"""
from __future__ import annotations

import json
import os
import sys

from researcher.landed.scorecard import fmt, score

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# portal/agent vocabulary → scorecard vocabulary (unknown values fall through to
# the scorecard's own middling defaults, but KNOWN synonyms must not be dropped)
_REBUILD_ALIASES = {"rebuilt_new": "rebuilt_recent", "renovated": "rebuilt_old",
                    "original": "original_good"}
_TIER_ALIASES = {"mid": "good"}
_TENURE_ALIASES = {"999_yr": "999", "999-year": "999", "99_yr": "99", "99-year": "99"}
_FLOOD_ALIASES = {"unverified": None, "unknown": None}


def normalize(lst: dict) -> dict:
    """PropertyGuru listing fields → scorecard input (omit unknowns → defaults)."""
    rebuild = lst.get("rebuild_status", "original_good")
    tier = lst.get("estate_tier", "prime")
    tenure = lst.get("tenure", "freehold")
    flood = lst.get("flood_risk", "none")
    flood = _FLOOD_ALIASES.get(flood, flood) or "none"
    out = {
        "name": f"{lst.get('street')} ({lst.get('type')})",
        "catchment": lst.get("catchment", "1km"),
        "estate_tier": _TIER_ALIASES.get(tier, tier),
        "zoning_risk": lst.get("zoning_risk", "none"),
        "hazards": lst.get("hazards", []),
        "flood_risk": flood,
        "future_risk": lst.get("future_risk", "none"),
        "rebuild_status": _REBUILD_ALIASES.get(rebuild, rebuild),
        "tenure": _TENURE_ALIASES.get(tenure, tenure),
        "foreign_eligible": lst.get("foreign_eligible", False),  # landed = restricted
    }
    for k in ("plot_shape", "frontage_m", "lw_ratio", "topography", "corner", "near_water"):
        if lst.get(k) is not None:
            out[k] = lst[k]
    return out


def value_flag(typ: str, psf, bench: dict) -> str:
    band = bench.get(typ)
    if not band or psf is None:
        return "?"
    lo, hi = band
    if psf < lo:
        return f"VALUE (<{lo})"
    if psf <= hi:
        return f"FAIR ({lo}-{hi})"
    if psf <= hi * 1.25:
        return f"RICH (>{hi})"
    return f"BUILD-PRICED (>>{hi})"


def screen_verdict(r: dict) -> str:
    """Final GO/CHECK call: quality score AND value band AND data completeness.

    The scorecard verdict alone is misleading in a shortlist — a high-quality plot
    asking build-level psf, or one with unconfirmed land area, must not read as an
    unqualified 'pursue'."""
    l, s, v = r["lst"], r["score"], r["value"]
    if l.get("land_sqft") is None or l.get("land_psf") is None or v == "?":
        return "VERIFY DATA - land size/psf unconfirmed"
    tenure = str(l.get("tenure") or "").lower()
    flood = str(l.get("flood_risk") or "").lower()
    # a S$10m+ decision cannot ride on an unknown tenure or unchecked flood record;
    # name exactly which field is unconfirmed so the caveat is actionable
    missing = [w for w, bad in (("tenure", tenure in ("", "unknown", "unverified")),
                                ("flood", flood in ("unknown", "unverified"))) if bad]
    if missing:
        return f"VERIFY DATA - {'/'.join(missing)} unconfirmed"
    band = v.split()[0]
    if band == "BUILD-PRICED":
        return "BUILD-PLAY - paying for the house, price as land+rebuild"
    if band == "RICH":
        return "NEGOTIATE - asking above the area band"
    if s.total >= 80:
        return "PURSUE"
    if s.total >= 65:
        return "CONSIDER"
    return "MARGINAL" if s.total >= 50 else "PASS"


def rank_listings(data: dict) -> list[dict]:
    """Score + rank a listings payload; pure (no printing) so reports can embed it."""
    bench = data.get("benchmark_land_psf", {})
    rows = []
    for lst in data.get("listings", []):
        s = score(normalize(lst))
        rows.append({
            "lst": lst,
            "score": s,
            "value": value_flag(lst.get("type"), lst.get("land_psf"), bench),
        })
    # rank: quality score first, then prefer better land value (FAIR/VALUE over RICH)
    val_rank = {"VALUE": 0, "FAIR": 1, "RICH": 2, "BUILD-PRICED": 3, "?": 4}
    rows.sort(key=lambda r: (-r["score"].total, val_rank.get(r["value"].split()[0], 4)))
    return rows


def screen(slug: str = "nanyang"):
    path = os.path.join(ROOT, "researcher", "landed", f"{slug}_listings.json")
    data = json.load(open(path, encoding="utf-8-sig"))
    rows = rank_listings(data)

    print(f"\n{data['area']}  —  {data['pulled']}")
    print(f"{'#':>2}  {'street / type':<42}{'price':>12}{'land':>8}{'psf':>7}  "
          f"{'value':<16}{'qual':>5}  verdict")
    print("-" * 110)

    def num(v, unit=""):  # listings scraped off portals routinely miss fields
        return (unit + format(v, ",")) if isinstance(v, (int, float)) else "?"

    for i, r in enumerate(rows, 1):
        l = r["lst"]
        label = f"{l.get('street', '?')} / {l.get('type', '?')}"
        print(f"{i:>2}  {label:<42}"
              f"{num(l.get('price'), 'S$'):>12}{num(l.get('land_sqft')):>8}"
              f"{num(l.get('land_psf')):>7}  {r['value']:<16}{r['score'].total:>5.0f}  {screen_verdict(r)}")
    print("\nTop picks — detail:")
    for r in rows[:3]:
        print("\n" + fmt(r["score"]))
        print(f"    land psf {r['lst'].get('land_psf', '?')} -> {r['value']}   | {r['lst'].get('notes','')}")
    return rows


if __name__ == "__main__":
    screen(sys.argv[1] if len(sys.argv) > 1 else "nanyang")
