"""New-launch scorecard weights + pricing math (BSD, SSD, breakeven identity)."""
import math

from researcher.newlaunch.pricing import analyze, bsd, ssd_rate
from researcher.newlaunch.scorecard import CATS, score

BEST = {
    "name": "best", "mrt_walk_min": 3, "expressway_access": True,
    "amenities_tier": "excellent", "nature_access": True, "developer_tier": "top",
    "tenure": "freehold", "price_vs_comps": "discount", "unit_efficiency": "efficient",
    "facilities": "full", "rental_demand": "strong", "supply_risk": "low",
    "catalysts": ["a", "b", "c"],
}


def test_weights_sum_to_100_and_best_hits_100():
    assert sum(CATS.values()) == 100
    s = score(BEST)
    assert s.total == 100
    for cat, pts in s.breakdown.items():
        assert pts == CATS[cat]


def test_steep_premium_caps_stance():
    s = score({**BEST, "price_vs_comps": "steep_premium"})
    assert not s.stance.startswith("BUY")


def test_bsd_known_values():
    # 1% x 180k + 2% x 180k + 3% x 640k = 24,600 exactly at S$1.0m
    assert bsd(1_000_000) == 24_600
    assert bsd(180_000) == 1_800
    # 3.0m: 24,600 + 4% x 500k + 5% x 1.5m = 24,600 + 20,000 + 75,000
    assert bsd(3_000_000) == 119_600


def test_ssd_schedule():
    assert ssd_rate(0.5) == 0.16
    assert ssd_rate(2) == 0.12
    assert ssd_rate(3.5) == 0.04
    assert ssd_rate(4) == 0.04
    assert ssd_rate(5) == 0.0


def test_breakeven_is_actually_breakeven():
    p = {"psf": 2200, "size_sqft": 700, "absd_pct": 0, "holding_years": 5,
         "construction_years": 3, "rent_psf_month": 5.0, "mortgage_rate": 0.03}
    r = analyze(p)
    # selling exactly at the breakeven exit price must net ~zero profit
    appr = (r.breakeven_exit_psf * p["size_sqft"] / r.price) ** (1 / 5) - 1
    r2 = analyze({**p, "appreciation_scenarios": [appr]})
    _, _, profit, _, _ = r2.scenarios[0]
    assert abs(profit) < 1.0  # dollars, rounding only


def test_ssd_bites_inside_4_years():
    base = {"psf": 2200, "size_sqft": 700, "absd_pct": 0, "construction_years": 3,
            "rent_psf_month": 5.0, "appreciation_scenarios": [0.03]}
    hold3 = analyze({**base, "holding_years": 3})
    hold5 = analyze({**base, "holding_years": 5})
    # inside the SSD window the required breakeven appreciation must be higher
    assert hold3.breakeven_appreciation_pct > hold5.breakeven_appreciation_pct + 0.05


def test_absd_pct_accepts_percent_or_fraction():
    a = analyze({"psf": 2000, "size_sqft": 800, "absd_pct": 5})
    b = analyze({"psf": 2000, "size_sqft": 800, "absd_pct": 0.05})
    assert math.isclose(a.stamp_total, b.stamp_total)
