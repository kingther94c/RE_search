"""Landed-property screening scorecard.

Scores a Singapore landed house 0-100 against weighted criteria that mirror the
buyer value ordering - Location → Street → Land → Zoning → Neighbours → Future →
House - so the *land* dominates and renovation is ignored. Returns a category
breakdown, red/amber flags, and a go/no-go verdict. Pure stdlib; generalises to
any address. Backs the `landed-property-due-diligence` skill.

    from researcher.landed.scorecard import score
    r = score({"name": "12 King's Road", "catchment": "1km", "estate_tier": "prime",
               "plot_shape": "rectangular", "frontage_m": 11, "lw_ratio": 2.1,
               "topography": "above", "corner": True, "near_water": False,
               "zoning_risk": "none", "hazards": [], "flood_risk": "none",
               "future_risk": "none", "rebuild_status": "rebuilt_recent",
               "tenure": "freehold", "foreign_eligible": True})
    print(r.total, r.verdict)
"""
from __future__ import annotations

from dataclasses import dataclass, field

# category weights (sum = 100); land-heavy on purpose
CATS = {
    "location_street": 30,
    "land": 30,
    "zoning_neighbours": 18,
    "flood": 8,
    "future": 5,
    "house_rebuild": 9,
}


def _pick(table: dict, key, default=0):
    return table.get(key, default)


def _frontage_pts(m: float) -> float:
    if m is None:
        return 3
    return 6 if m >= 10 else 5 if m >= 8 else 3 if m >= 6 else 1


def _ratio_pts(r: float) -> float:
    if r is None:
        return 3
    if 1.5 <= r <= 2.5:
        return 5
    if 1.2 <= r < 1.5 or 2.5 < r <= 3.5:
        return 3
    return 1


def _hazard_pts(h) -> float:
    n = len(h or [])
    return 8 if n == 0 else 5 if n == 1 else 2 if n == 2 else 0


@dataclass
class Score:
    name: str
    total: float
    breakdown: dict
    flags: list = field(default_factory=list)   # (level, text): level in red/amber/green
    verdict: str = ""


def score(p: dict) -> Score:
    b: dict = {}

    # ── Location & street (30) ────────────────────────────────────────────────
    catch = {"1km": 14, "2km": 7, "outside": 0}
    tier = {"gcb": 16, "prime": 13, "good": 9, "average": 4}
    b["location_street"] = _pick(catch, p.get("catchment"), 7) + _pick(tier, p.get("estate_tier"), 9)

    # ── Land (30) ─────────────────────────────────────────────────────────────
    shape = {"rectangular": 9, "slightly_irregular": 6, "irregular": 2, "triangular": 0}
    topo = {"above": 6, "level": 4, "below": 0}
    land = (
        _pick(shape, p.get("plot_shape"), 6)
        + _frontage_pts(p.get("frontage_m"))
        + _ratio_pts(p.get("lw_ratio"))
        + _pick(topo, p.get("topography"), 4)
        + (2 if p.get("corner") else 0)
        + (0 if p.get("near_water") else 2)
    )
    b["land"] = land

    # ── Zoning & neighbours (18) ──────────────────────────────────────────────
    zr = {"none": 10, "high_plot_ratio_neighbour": 5, "adjacent_nonlanded": 3, "reserve_or_institution": 1}
    b["zoning_neighbours"] = _pick(zr, p.get("zoning_risk"), 7) + _hazard_pts(p.get("hazards"))

    # ── Flood (8) / Future (5) / House-rebuild (9) ────────────────────────────
    b["flood"] = _pick({"none": 8, "low": 4, "high": 0}, p.get("flood_risk"), 4)
    b["future"] = _pick({"none": 5, "some": 3, "material": 0}, p.get("future_risk"), 3)
    b["house_rebuild"] = _pick(
        {"rebuilt_recent": 9, "rebuilt_old": 6, "original_good": 4, "original_poor": 1},
        p.get("rebuild_status"), 4,
    )

    total = round(sum(b.values()), 1)

    # ── Flags ────────────────────────────────────────────────────────────────
    flags = []
    if p.get("topography") == "below":
        flags.append(("red", "Below road level - drainage / damp / ponding risk"))
    if p.get("flood_risk") == "high":
        flags.append(("red", "In/near a flood-prone area - verify ponding after heavy rain"))
    if p.get("plot_shape") in ("triangular", "irregular"):
        flags.append(("red", f"{p.get('plot_shape')} plot - future design/rebuild constrained"))
    if p.get("zoning_risk") in ("reserve_or_institution", "adjacent_nonlanded"):
        flags.append(("amber", f"Neighbour parcel risk ({p.get('zoning_risk')}) - check URA Master Plan"))
    if p.get("tenure") == "99":
        flags.append(("amber", "99-year landed - financing & resale implications; check remaining years"))
    elif p.get("tenure") == "999":
        flags.append(("green", "999-year tenure - near-freehold"))
    if p.get("foreign_eligible") is False:
        flags.append(("amber", "Restricted (foreign-ineligible) - narrower future-buyer pool"))
    if p.get("rebuild_status") in ("original_poor", "original_good"):
        flags.append(("amber", "Not rebuilt - price as land + rebuild cost, not as turnkey"))
    if p.get("near_water"):
        flags.append(("amber", "Beside canal/drain - confirm it doesn't pond"))
    if p.get("catchment") == "1km":
        flags.append(("green", "Within 1km school zone"))
    if p.get("tenure") == "freehold":
        flags.append(("green", "Freehold"))

    verdict = (
        "STRONG - pursue" if total >= 80
        else "CONSIDER - worth a viewing" if total >= 65
        else "MARGINAL - only at the right price" if total >= 50
        else "PASS"
    )
    return Score(p.get("name", "?"), total, b, flags, verdict)


def fmt(s: Score) -> str:
    lines = [f"{s.name}: {s.total}/100  ->  {s.verdict}"]
    for k, v in s.breakdown.items():
        lines.append(f"    {k:<20} {v:>4.1f} / {CATS[k]}")
    for lvl, t in s.flags:
        mark = {"red": "X", "amber": "!", "green": "+"}[lvl]
        lines.append(f"    [{mark}] {t}")
    return "\n".join(lines)


if __name__ == "__main__":
    examples = [
        {"name": "Rebuilt regular-plot terrace, 1km, prime st", "catchment": "1km",
         "estate_tier": "prime", "plot_shape": "rectangular", "frontage_m": 11, "lw_ratio": 2.1,
         "topography": "above", "corner": True, "near_water": False, "zoning_risk": "none",
         "hazards": [], "flood_risk": "none", "future_risk": "none",
         "rebuild_status": "rebuilt_recent", "tenure": "freehold", "foreign_eligible": True},
        {"name": "Original low-lying irregular plot near canal", "catchment": "1km",
         "estate_tier": "good", "plot_shape": "irregular", "frontage_m": 6, "lw_ratio": 3.6,
         "topography": "below", "corner": False, "near_water": True,
         "zoning_risk": "adjacent_nonlanded", "hazards": ["expressway", "construction"],
         "flood_risk": "high", "future_risk": "some", "rebuild_status": "original_poor",
         "tenure": "freehold", "foreign_eligible": True},
    ]
    for ex in examples:
        print(fmt(score(ex)))
        print()
