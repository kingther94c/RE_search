"""Valuation engine: identity adjustment, direction of adjustments, guards."""
import pytest

from researcher.legacy.valuation.engine import Comp, Params, Subject, adjust, value

P = Params(asof="2026-06-30", time_trend_pa=0.02, floor_premium_pp=0.003,
           size_elasticity=-0.08, compact3br_discount=0.03)
SUBJ = Subject(name="subject", size_sqft=743, floor=18, bedrooms=3)


def identical_comp(psf=2000.0) -> Comp:
    return Comp("identical", P.asof, SUBJ.floor, SUBJ.bedrooms, SUBJ.size_sqft, psf)


def test_identical_comp_needs_no_adjustment():
    a = adjust(identical_comp(), SUBJ, P)
    assert a.adj_psf == pytest.approx(a.raw_psf)
    for f in (a.time_adj, a.floor_adj, a.size_adj, a.type_adj):
        assert f == pytest.approx(1.0)


def test_older_comp_adjusts_upward_in_rising_market():
    old = Comp("old", "2024-06-30", SUBJ.floor, SUBJ.bedrooms, SUBJ.size_sqft, 2000)
    assert adjust(old, SUBJ, P).adj_psf > 2000


def test_lower_floor_comp_adjusts_upward():
    low = Comp("low", P.asof, 5, SUBJ.bedrooms, SUBJ.size_sqft, 2000)
    assert adjust(low, SUBJ, P).adj_psf > 2000


def test_smaller_comp_adjusts_downward():
    # negative elasticity: smaller units carry higher psf, so a smaller comp's
    # psf must come DOWN to fit the (larger) subject
    small = Comp("small", P.asof, SUBJ.floor, 2, 500, 2400)
    assert adjust(small, SUBJ, P).adj_psf < 2400


def test_estimate_within_band_and_price_consistent():
    comps = [
        Comp("a", "2026-01-15", 12, 3, 750, 2100),
        Comp("b", "2025-11-01", 20, 3, 700, 2250),
        Comp("c", "2026-04-01", 8, 2, 550, 2350),
        Comp("d", "2025-08-20", 22, 3, 760, 2150),
    ]
    v = value(SUBJ, comps, P)
    assert v.low_psf <= v.estimate_psf <= v.high_psf
    assert v.estimate_price == pytest.approx(v.estimate_psf * SUBJ.size_sqft)


def test_anchor_pulls_estimate():
    comps = [Comp("a", P.asof, SUBJ.floor, SUBJ.bedrooms, SUBJ.size_sqft, 2000)]
    anchor = Comp("anchor", P.asof, SUBJ.floor, SUBJ.bedrooms, SUBJ.size_sqft, 2600)
    v_no = value(SUBJ, comps, P)
    v_yes = value(SUBJ, comps, P, same_line_anchor=anchor, anchor_weight=2.0)
    assert v_yes.estimate_psf > v_no.estimate_psf


def test_no_comps_raises_cleanly():
    with pytest.raises(ValueError):
        value(SUBJ, [], P)


def test_default_asof_is_not_frozen_in_2026_06():
    assert Params().asof >= "2026-07"  # today() — catches a re-hardcoded date
