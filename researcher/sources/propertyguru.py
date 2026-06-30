"""PropertyGuru landed-listings source → screening.

PropertyGuru blocks server-side fetches (WebFetch → HTTP 403), so listings are
gathered by **WebSearch** (which surfaces and summarises live PropertyGuru
listings) — see the `screen-landed-listings` skill for the exact queries and URL
patterns. The pulled listings live in `researcher/landed/<area>_listings.json`.

This module normalises each listing into the landed `scorecard` input, scores it
(quality), and flags **value** = land psf vs the area benchmark band, then ranks.
Run:  python -m researcher.sources.propertyguru [area_slug]
"""
from __future__ import annotations

import json
import os
import sys

from researcher.landed.scorecard import fmt, score

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def normalize(lst: dict) -> dict:
    """PropertyGuru listing fields → scorecard input (omit unknowns → defaults)."""
    out = {
        "name": f"{lst.get('street')} ({lst.get('type')})",
        "catchment": lst.get("catchment", "1km"),
        "estate_tier": lst.get("estate_tier", "prime"),
        "zoning_risk": lst.get("zoning_risk", "none"),
        "hazards": lst.get("hazards", []),
        "flood_risk": lst.get("flood_risk", "none"),
        "future_risk": lst.get("future_risk", "none"),
        "rebuild_status": lst.get("rebuild_status", "original_good"),
        "tenure": lst.get("tenure", "freehold"),
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


def screen(slug: str = "nanyang"):
    path = os.path.join(ROOT, "researcher", "landed", f"{slug}_listings.json")
    data = json.load(open(path, encoding="utf-8-sig"))
    bench = data["benchmark_land_psf"]
    rows = []
    for lst in data["listings"]:
        s = score(normalize(lst))
        rows.append({
            "lst": lst,
            "score": s,
            "value": value_flag(lst.get("type"), lst.get("land_psf"), bench),
        })
    # rank: quality score first, then prefer better land value (FAIR/VALUE over RICH)
    val_rank = {"VALUE": 0, "FAIR": 1, "RICH": 2, "BUILD": 3, "?": 4}
    rows.sort(key=lambda r: (-r["score"].total, val_rank.get(r["value"].split()[0], 4)))

    print(f"\n{data['area']}  —  {data['pulled']}")
    print(f"{'#':>2}  {'street / type':<42}{'price':>12}{'land':>8}{'psf':>7}  "
          f"{'value':<16}{'qual':>5}  verdict")
    print("-" * 110)
    for i, r in enumerate(rows, 1):
        l = r["lst"]
        print(f"{i:>2}  {(l['street'] + ' / ' + l['type']):<42}"
              f"{'S$' + format(l['price'], ','):>12}{format(l['land_sqft'], ','):>8}"
              f"{l['land_psf']:>7}  {r['value']:<16}{r['score'].total:>5.0f}  {r['score'].verdict}")
    print("\nTop picks — detail:")
    for r in rows[:3]:
        print("\n" + fmt(r["score"]))
        print(f"    land psf {r['lst']['land_psf']} -> {r['value']}   | {r['lst'].get('notes','')}")
    return rows


if __name__ == "__main__":
    screen(sys.argv[1] if len(sys.argv) > 1 else "nanyang")
