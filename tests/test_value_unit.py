"""condo-resale-valuation regression suite (R5 / G5) — structural assertions on real URA
archetype projects, rerun on every skill/engine change. Asserts BEHAVIOUR (confidence
tiers, hard-case flags, band ordering, guidance separation), not exact prices, so a data
refresh doesn't break it. Loads the committed snapshot, so it runs with no local pull."""
import pytest

from researcher.backtest.store import TransactionStore
from researcher.backtest.value_unit import value, SubjectSpec


@pytest.fixture(scope="module")
def store():
    return TransactionStore.load().exclude_bulk().psf_band(500, 6500)


def _v(store, project, area, floor):
    return value(SubjectSpec(project, area, floor=floor, asof="2026-07-01"), store)


# ---- invariants that must hold for EVERY valuation ------------------------------
@pytest.mark.parametrize("project,area,floor", [
    ("TREASURE AT TAMPINES", 936, 12),
    ("PARC CLEMATIS", 700, 20),
    ("THE FOLIAGE", 1100, 5),
])
def test_valuation_invariants(store, project, area, floor):
    v = _v(store, project, area, floor)
    fv = v["fair_value"]
    assert fv["low"] < fv["price"] < fv["high"]            # band brackets the point
    assert 0 < fv["confidence"] <= 100
    # buyer/seller guidance is DERIVED FROM the band and SEPARATE from fair value
    assert v["buyer_guidance"]["attractive_below"] == fv["low"]
    assert v["buyer_guidance"]["walk_away_above"] == fv["high"]
    assert v["seller_guidance"]["ask"] == fv["high"]
    assert v["seller_guidance"]["expected_clear"] == fv["price"]
    assert v["verify_before_offer"] and v["limitations"]


# ---- archetype behaviour --------------------------------------------------------
def test_liquid_project_is_high_confidence_and_anchors_agree(store):
    v = _v(store, "TREASURE AT TAMPINES", 936, 12)
    assert v["fair_value"]["confidence"] >= 80
    assert v["fair_value"]["n_same_project_comps"] >= 50
    assert v["anchor_disagreement"]["spread_rel"] < 0.06   # deep market -> methods converge
    assert not v["anchor_disagreement"]["hard_case"]


def test_boutique_project_flags_lower_confidence(store):
    v = _v(store, "THE FOLIAGE", 1100, 5)
    assert v["fair_value"]["confidence"] <= 72
    assert v["fair_value"]["n_same_project_comps"] < 20
    # a boutique freehold with mixed unit sizes is exactly where methods should diverge
    assert v["anchor_disagreement"]["hard_case"] or v["fair_value"]["confidence"] <= 62


def test_unknown_project_is_out_of_scope_not_a_guess(store):
    v = value(SubjectSpec("NO SUCH CONDO XYZ", 900, floor=10, asof="2026-07-01"), store)
    assert v.get("error") == "project_not_found"          # escalate, never fabricate


def test_thin_evidence_requests_investment_suite_corroboration(store):
    v = _v(store, "THE FOLIAGE", 1100, 5)
    if v["fair_value"]["n_same_project_comps"] < 3:
        assert any("Investment Suite" in s for s in v["verify_before_offer"])
