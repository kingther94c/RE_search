"""L2/L3/L4 landed suite — size curve, lease matching, engine, and the production
`landed-valuation` regression cases (structural asserts on real URA streets, so a data
refresh doesn't break them). Rerun on every landed engine/skill change."""
import math

import pytest

from researcher.backtest.landed_candidates import (lease_compatible, remaining_lease)
from researcher.backtest.landed_size_curve import BANDS, is_big_plot, size_factor
from researcher.backtest.store import TransactionStore
from researcher.backtest.value_landed import LandedSpec, value_landed


# ---------------------------------------------------------------- L2a size curve
def test_size_curve_is_continuous_across_band_breaks():
    """The curve integrates a PIECEWISE elasticity in ln(area); if it were applied as a
    step constant the price surface would jump at 3k/5k/8k sqft. Guard the continuity."""
    for b in (3000.0, 5000.0, 8000.0):
        below = size_factor(2000.0, b - 1.0)
        above = size_factor(2000.0, b + 1.0)
        assert abs(above / below - 1.0) < 0.001      # no jump at the break


def test_size_curve_direction_and_regimes():
    # bigger plot -> lower land-psf everywhere (all bands are negative elasticities)
    assert size_factor(2000.0, 4000.0) < 1.0
    assert all(e < 0 for _, _, e in BANDS)
    # SMALL plots are the quantum regime (steep); BIG plots the land regime (flat).
    # Doubling 2k->4k must cut psf far harder than doubling 10k->20k.
    small = 1.0 - size_factor(2000.0, 4000.0)
    big = 1.0 - size_factor(10000.0, 20000.0)
    assert small > big * 1.5


def test_size_factor_identity_and_inverse():
    assert size_factor(2500.0, 2500.0) == pytest.approx(1.0)
    assert size_factor(2000.0, 6000.0) * size_factor(6000.0, 2000.0) == pytest.approx(1.0)


def test_big_plot_flag():
    assert not is_big_plot(7999) and is_big_plot(8000)


# ------------------------------------------------------- L2c lease matching (the 232% fix)
def _tx(tenure, start=None, raw=""):
    return {"tenure_type": tenure, "lease_start": start, "tenure_raw": raw}


def test_quasi_freehold_never_matches_real_leasehold():
    """The decisive L1 failure: spatial kNN priced ~20-yr-left 99yr terraces off freehold
    neighbours at 6-10x (median APE 232%). A quasi-FH comp must NEVER price a leasehold."""
    subj = _tx("leasehold", 1947, "99 yrs lease commencing from 1947")
    assert not lease_compatible(_tx("freehold"), subj, "2026-01")
    assert not lease_compatible(_tx("freehold_equiv", 1885), subj, "2026-01")


def test_leasehold_matches_only_similar_remaining_lease():
    subj = _tx("leasehold", 1990, "99 yrs lease commencing from 1990")   # ~63y left
    near = _tx("leasehold", 1995, "99 yrs lease commencing from 1995")   # ~68y left
    far = _tx("leasehold", 1947, "99 yrs lease commencing from 1947")    # ~20y left
    assert lease_compatible(near, subj, "2026-01")
    assert not lease_compatible(far, subj, "2026-01")


def test_remaining_lease_reads_the_tenure_string():
    t = _tx("leasehold", 1947, "99 yrs lease commencing from 1947")
    assert remaining_lease(t, "2026-01") == pytest.approx(20.0)
    assert remaining_lease(_tx("freehold"), "2026-01") >= 800
    # unknown lease start must NOT be fabricated into a short lease
    assert remaining_lease(_tx("leasehold", None), "2026-01") >= 800


def test_conformal_table_matches_landed_code():
    """The band multipliers are calibrated on LC2/curve residuals. If that code changes
    without recalibration the bands silently skew — make it a red test."""
    import hashlib
    import json
    import os
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "researcher", "backtest")
    with open(os.path.join(base, "landed_conformal_table.json"), encoding="utf-8") as f:
        meta = json.load(f).get("_meta", {})
    stored = meta.get("code_sha1")
    assert stored, "landed conformal table has no fingerprint — run research/analyze_landed.py"
    h = hashlib.sha1()
    for fn in ("landed_candidates.py", "landed_size_curve.py"):
        with open(os.path.join(base, fn), "rb") as fh:
            h.update(fh.read())
    assert h.hexdigest() == stored, (
        "landed point code changed since calibration — re-run "
        "`python -m researcher.backtest.run_landed --dump <p>` then "
        "`python research/analyze_landed.py <p>`")


# --------------------------------------------------- L4 production regression cases
@pytest.fixture(scope="module")
def store():
    return TransactionStore.load()


def _v(store, street, area, ptype):
    return value_landed(LandedSpec(street, area, ptype, asof="2026-07-01"), store)


@pytest.mark.parametrize("street,area,ptype", [
    ("ALNWICK ROAD", 2800, "Terrace"),
    ("LOYANG RISE", 1635, "Terrace"),
    ("BOWMONT GARDENS", 5016, "Detached"),
])
def test_landed_valuation_invariants(store, street, area, ptype):
    v = _v(store, street, area, ptype)
    fv = v["fair_value"]
    assert fv["low"] < fv["price"] < fv["high"]
    assert 0 < fv["confidence"] <= 100
    # guidance is derived from the band and separate from fair value
    assert v["buyer_guidance"]["attractive_below"] == fv["low"]
    assert v["seller_guidance"]["expected_clear"] == fv["price"]
    # every landed report must carry the bundle/geometry honesty
    assert any("geometry" in s.lower() for s in v["verify_before_offer"])
    assert any("bundle" in s.lower() for s in v["limitations"])


def test_leasehold_street_is_lease_matched_and_confident(store):
    """LOYANG RISE is 99yr: remaining lease must be surfaced and the methods should AGREE
    once lease-matched (this is the slice that used to be 232% wrong)."""
    v = _v(store, "LOYANG RISE", 1635, "Terrace")
    assert v["subject"]["tenure_type"] == "leasehold"
    assert 40 < v["subject"]["remaining_lease_years"] < 90
    assert v["method_disagreement"]["spread_rel"] < 0.15


def test_big_plot_is_scope_limited(store):
    """>=8k sqft: EXP-0011 showed the curve is worst-identified exactly where error is
    largest — the engine must cap confidence, widen, and route to the case protocol."""
    v = _v(store, "BOWMONT GARDENS", 9225, "Detached")
    fv = v["fair_value"]
    assert fv["confidence"] <= 45
    assert any("8k sqft" in s or ">=8k" in s for s in v["verify_before_offer"])
    assert (fv["high"] - fv["low"]) / fv["price"] > 0.4        # genuinely wide
    assert "indicative" in fv["confidence_label"]


def test_unknown_street_escalates_not_fabricates(store):
    """Cardiff Grove is a real street with a PASS-8.5 craft valuation, but URA's rolling
    5y window carries no caveats there — the engine must route to Investment Suite."""
    v = value_landed(LandedSpec("CARDIFF GROVE", 1839.57, "Terrace", asof="2026-07-01"),
                     store)
    assert v.get("error") == "street_not_found"
    assert "Investment Suite" in v["message"]
