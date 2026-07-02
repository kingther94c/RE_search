"""Landed scorecard: weights, boundaries, flags, verdict thresholds."""
from researcher.landed.scorecard import CATS, fmt, score

PERFECT = {
    "name": "perfect", "catchment": "1km", "estate_tier": "gcb",
    "plot_shape": "rectangular", "frontage_m": 12, "lw_ratio": 2.0,
    "topography": "above", "corner": True, "near_water": False,
    "zoning_risk": "none", "hazards": [], "flood_risk": "none",
    "future_risk": "none", "rebuild_status": "rebuilt_recent",
    "tenure": "freehold", "foreign_eligible": True,
}


def test_weights_sum_to_100():
    assert sum(CATS.values()) == 100


def test_perfect_input_hits_100():
    s = score(PERFECT)
    assert s.total == 100
    for cat, pts in s.breakdown.items():
        assert pts == CATS[cat], f"{cat} not at max for a perfect input"


def test_category_never_exceeds_its_weight():
    s = score(PERFECT)
    for cat, pts in s.breakdown.items():
        assert 0 <= pts <= CATS[cat]


def test_empty_input_is_mid_range_not_crash():
    s = score({})
    assert 0 < s.total < 100  # unknowns default to middling, never max/min


def test_worst_input_scores_low_and_flags_red():
    s = score({
        "catchment": "outside", "estate_tier": "average", "plot_shape": "triangular",
        "frontage_m": 4, "lw_ratio": 5.0, "topography": "below", "corner": False,
        "near_water": True, "zoning_risk": "reserve_or_institution",
        "hazards": ["a", "b", "c"], "flood_risk": "high", "future_risk": "material",
        "rebuild_status": "original_poor", "tenure": "99", "foreign_eligible": False,
    })
    assert s.total < 25
    assert s.verdict == "PASS"
    assert any(lvl == "red" for lvl, _ in s.flags)


def test_verdict_thresholds():
    assert score(PERFECT).verdict.startswith("STRONG")
    assert score({}).verdict != ""


def test_fmt_renders_every_category():
    out = fmt(score(PERFECT))
    for cat in CATS:
        assert cat in out
