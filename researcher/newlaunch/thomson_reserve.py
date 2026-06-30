"""Apply the new-launch scorecard + pricing to Thomson Reserve.

Inputs are derived from the VERIFIED research digest (2026-06; former Thomson View
redevelopment, D20, 99-yr LH, UOL/SingLand/CapitaLand). The project is PRE-LAUNCH —
all pricing here is the digest's *indicative* figure and is illustrative only, not
official launch pricing. Run:  python -m researcher.newlaunch.thomson_reserve
"""
from researcher.newlaunch.pricing import analyze
from researcher.newlaunch.pricing import fmt as pfmt
from researcher.newlaunch.scorecard import fmt as sfmt
from researcher.newlaunch.scorecard import score

SCORE_INPUT = {
    "name": "Thomson Reserve (former Thomson View redev, D20)",
    "mrt_walk_min": 7,                 # ~7-min walk to Upper Thomson MRT (TEL)
    "expressway_access": True,         # CTE/SLE
    "amenities_tier": "good",          # Thomson Plaza, established estate
    "nature_access": True,             # MacRitchie Reservoir adjacency
    "developer_tier": "top",           # UOL + SingLand + CapitaLand
    "tenure": "99", "lease_remaining": 99,
    "price_vs_comps": "premium",       # par-to-premium vs JadeScape resale; mid-upper vs Lentor cluster
    "unit_efficiency": "average",
    "facilities": "full",              # large ~1,240-unit site
    "rental_demand": "moderate",       # family/upgrader estate; owner-occupier skew
    "supply_risk": "moderate",         # first-mover D20, but Lentor + Upper-Thomson BTO pipeline looms
    "catalysts": ["Upper Thomson MRT (TEL)", "future Bright Hill CRL interchange ~2030",
                  "first big D20 launch since 2018 / scarcity", "Ai Tong School 1km + MacRitchie"],
}

# Indicative 2BR (~700 sqft @ ~S$2,250 psf) — pre-launch placeholder, NOT official.
PRICE_INPUT = {
    "name": "Thomson Reserve 2BR (indicative, pre-launch)",
    "psf": 2250, "size_sqft": 700,
    "absd_pct": 0,                     # Singaporean 1st property
    "holding_years": 6, "construction_years": 4,   # BUC: TOP ~2030-31, ~2 rented yrs
    "rent_psf_month": 4.5, "mortgage_rate": 0.03,
    "appreciation_scenarios": [0.0, 0.02, 0.04],
}

if __name__ == "__main__":
    print(sfmt(score(SCORE_INPUT)))
    print()
    print(pfmt(PRICE_INPUT, analyze(PRICE_INPUT)))
