"""New-launch (新盘) screening scorecard.

Scores a Singapore new-launch condo 0-100 across the new-launch checklist, with
the weight where it belongs for new launches: **price positioning vs comps (22)**
and location (20) dominate, because the entry price and location decide most of
the return. Returns a category breakdown, red/amber flags, and a
BUY / SELECTIVE / WAIT / AVOID stance. Pure stdlib. Backs `new-launch-research`.

    from researcher.newlaunch.scorecard import score
    print(score({...}).stance)
"""
from __future__ import annotations

from dataclasses import dataclass, field

CATS = {
    "location_connectivity": 20,
    "developer": 8,
    "tenure_site": 10,
    "price_positioning": 22,
    "product": 10,
    "rental_demand": 12,
    "supply_competition": 10,
    "catalysts": 8,
}


def _pick(t, k, d=0):
    return t.get(k, d)


def _mrt(m):
    if m is None:
        return 6
    return 10 if m <= 5 else 8 if m <= 10 else 5 if m <= 15 else 2


def _tenure(p):
    if p.get("tenure") == "freehold":
        return 10
    yrs = p.get("lease_remaining", 99)
    return 8 if yrs >= 99 else 7 if yrs >= 90 else 5 if yrs >= 80 else 3


def _catalysts(c):
    n = len(c or [])
    return 2 if n == 0 else 4 if n == 1 else 6 if n == 2 else 8


@dataclass
class Score:
    name: str
    total: float
    breakdown: dict
    flags: list = field(default_factory=list)
    stance: str = ""


def score(p: dict) -> Score:
    b = {}
    b["location_connectivity"] = (
        _mrt(p.get("mrt_walk_min"))
        + (2 if p.get("expressway_access") else 0)
        + _pick({"excellent": 5, "good": 4, "average": 2}, p.get("amenities_tier"), 3)
        + (3 if p.get("nature_access") else 0)
    )
    b["developer"] = _pick({"top": 8, "established": 6, "mid": 4, "new": 2}, p.get("developer_tier"), 5)
    b["tenure_site"] = _tenure(p)
    b["price_positioning"] = _pick(
        {"discount": 22, "par": 16, "premium": 9, "steep_premium": 3}, p.get("price_vs_comps"), 12)
    b["product"] = (
        _pick({"efficient": 6, "average": 4, "inefficient": 2}, p.get("unit_efficiency"), 4)
        + _pick({"full": 4, "adequate": 3, "basic": 1}, p.get("facilities"), 3)
    )
    b["rental_demand"] = _pick({"strong": 12, "moderate": 8, "weak": 4}, p.get("rental_demand"), 8)
    b["supply_competition"] = _pick({"low": 10, "moderate": 6, "high": 2}, p.get("supply_risk"), 6)
    b["catalysts"] = _catalysts(p.get("catalysts"))

    total = round(sum(b.values()), 1)

    flags = []
    if p.get("price_vs_comps") == "steep_premium":
        flags.append(("red", "Priced well above comps - needs the area to re-rate before you break even"))
    elif p.get("price_vs_comps") == "premium":
        flags.append(("amber", "Above-comps pricing - thinner margin of safety"))
    elif p.get("price_vs_comps") == "discount":
        flags.append(("green", "Priced at/below comps - margin of safety"))
    if p.get("supply_risk") == "high":
        flags.append(("red", "Heavy supply pipeline in the belt - caps appreciation & rents"))
    if p.get("developer_tier") == "new":
        flags.append(("amber", "Unproven developer - execution & resale risk"))
    if p.get("rental_demand") == "weak":
        flags.append(("amber", "Weak rental catchment - low yield support"))
    if (p.get("mrt_walk_min") or 0) > 15:
        flags.append(("amber", "Far from MRT (>15 min) - weaker tenant/resale appeal"))
    if p.get("tenure") == "99":
        flags.append(("amber", f"99-yr leasehold ({p.get('lease_remaining', 99)} yrs) - lease decay vs freehold"))
    elif p.get("tenure") == "freehold":
        flags.append(("green", "Freehold"))

    stance = ("BUY" if total >= 80 else "SELECTIVE (right unit & price)" if total >= 68
              else "WAIT" if total >= 55 else "AVOID")
    # a steep premium caps the stance regardless of other strengths
    if p.get("price_vs_comps") == "steep_premium" and stance == "BUY":
        stance = "SELECTIVE (right unit & price)"
    return Score(p.get("name", "?"), total, b, flags, stance)


def fmt(s: Score) -> str:
    out = [f"{s.name}: {s.total}/100  ->  {s.stance}"]
    for k, v in s.breakdown.items():
        out.append(f"    {k:<22} {v:>4.1f} / {CATS[k]}")
    for lvl, t in s.flags:
        out.append(f"    [{ {'red':'X','amber':'!','green':'+'}[lvl] }] {t}")
    return "\n".join(out)


if __name__ == "__main__":
    examples = [
        {"name": "Well-priced, MRT-doorstep, top developer, low supply",
         "mrt_walk_min": 4, "expressway_access": True, "amenities_tier": "good", "nature_access": True,
         "developer_tier": "top", "tenure": "99", "lease_remaining": 99, "price_vs_comps": "par",
         "unit_efficiency": "efficient", "facilities": "full", "rental_demand": "strong",
         "supply_risk": "low", "catalysts": ["MRT interchange", "en-bloc-to-launch uplift", "area transformation"]},
        {"name": "Overpriced launch into heavy supply, mid developer",
         "mrt_walk_min": 12, "expressway_access": True, "amenities_tier": "average", "nature_access": False,
         "developer_tier": "mid", "tenure": "99", "lease_remaining": 99, "price_vs_comps": "steep_premium",
         "unit_efficiency": "average", "facilities": "adequate", "rental_demand": "moderate",
         "supply_risk": "high", "catalysts": []},
    ]
    for ex in examples:
        print(fmt(score(ex)))
        print()
