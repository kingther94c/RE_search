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


def test_lease_parse_does_not_collide_with_the_year():
    """A substring scan for '999' matches the YEAR in '...from 1999', turning a 99yr lease
    into quasi-freehold and re-arming the 232% failure. Anchored parse only."""
    t = _tx("leasehold", 1999, "99 yrs lease commencing from 1999")
    assert remaining_lease(t, "2026-01") == pytest.approx(72.0)     # NOT ~800
    assert remaining_lease(_tx("freehold_equiv", 1885,
                               "999 yrs lease commencing from 1885"), "2026-01") >= 800
    # and such a plot must never be priced off a freehold comp
    assert not lease_compatible(_tx("freehold"), t, "2026-01")


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
    # Guidance is EITHER derived from the band and separate from fair value, OR suppressed
    # with a reason when the engine has declared itself unreliable — never invented.
    bg, sg = v["buyer_guidance"], v["seller_guidance"]
    if sg["ask"] is None:
        assert "SUPPRESSED" in sg["note"] and bg["walk_away_above"] is None
    else:
        assert bg["attractive_below"] < bg["walk_away_above"]
        assert sg["expected_clear"] == fv["price"]
    # the fair-value band is ALWAYS disclosed, and always as the engine's uncertainty
    assert bg["fair_value_band"] == [fv["low"], fv["high"]]
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


def test_wide_band_suppresses_guidance_instead_of_quoting_an_ask(store):
    """The conformal band is the ENGINE'S predictive error, not achievable price dispersion.
    Quoting its top as a seller 'ask' turned ignorance into aggression (review blocker:
    ask S$21.8M on a plot that printed S$14.0M). When the engine says 'indicative only',
    it must emit NO ask."""
    v = _v(store, "BOWMONT GARDENS", 9225, "Detached")       # >=8k -> scope-limited
    assert v["seller_guidance"]["ask"] is None
    assert v["buyer_guidance"]["walk_away_above"] is None
    assert "SUPPRESSED" in v["seller_guidance"]["note"]
    # a confident, well-evidenced subject still gets real (evidence-derived) guidance
    ok = _v(store, "LOYANG RISE", 1635, "Terrace")
    assert ok["seller_guidance"]["ask"] is not None
    assert ok["seller_guidance"]["ask"] != ok["fair_value"]["high"]   # NOT the band top


def test_condition_is_honest_not_a_dead_input(store):
    """Review blocker: `condition` was echoed while the report claimed it widened the band —
    it did nothing. The engine is condition-BLIND; it must say so and give DIRECTION only,
    never a fabricated magnitude or a fake widening."""
    base = value_landed(LandedSpec("ALNWICK ROAD", 2800, "Terrace", asof="2026-07-01"), store)
    rebuilt = value_landed(LandedSpec("ALNWICK ROAD", 2800, "Terrace", condition="rebuilt",
                                      asof="2026-07-01"), store)
    # the point is identical BECAUSE the engine is condition-blind — and it now admits it
    assert rebuilt["fair_value"]["price"] == base["fair_value"]["price"]
    assert "FLOOR" in rebuilt["condition_note"]
    assert "NOT quantified" in rebuilt["condition_note"]
    assert "NOT supplied and NOT inferred" in base["condition_note"]
    assert any("CONDITION-BLIND" in s for s in base["limitations"])


def test_displayed_comps_are_lease_matched(store):
    """Review blocker: the comps exhibit filtered on type only while captioned
    'lease-matched', displaying FH prints against a leasehold subject — the exact pairing
    the 232% guard forbids."""
    v = _v(store, "LOYANG RISE", 1635, "Terrace")           # leasehold street
    assert v["subject"]["tenure_type"] == "leasehold"
    assert v["comps"], "expected street comps"
    assert all(c["tenure"] == "leasehold" for c in v["comps"])


def test_leasehold_without_lease_start_refuses_rather_than_freehold_pricing(store):
    """Review blocker: `remaining_lease` returns quasi-FH when lease_start is unknown —
    correct for a COMP (dropped), catastrophic for the SUBJECT (a real leasehold gets priced
    off freehold comps; a measured 42% swing). It must REFUSE, not guess."""
    v = value_landed(LandedSpec("FABER AVENUE", 3000, "Semi-detached",
                                tenure_type="leasehold", asof="2026-07-01"), store)
    assert v.get("error") == "lease_start_required"
    assert "232%" in v["message"]
    # supplying the lease start makes it valuable again
    ok = value_landed(LandedSpec("FABER AVENUE", 3000, "Semi-detached",
                                 tenure_type="leasehold", lease_start=1995,
                                 asof="2026-07-01"), store)
    assert "error" not in ok or ok.get("error") != "lease_start_required"


def test_mixed_tenure_street_refuses_when_tenure_not_supplied(store):
    """The lease guard's other half. Refusing only on DECLARED-leasehold-without-lease_start
    left the undeclared case open: on a mixed street the tenure MODE silently makes a
    leasehold plot freehold. Measured swing on JALAN RINDU (14 FH / 11 LH): +69.8%
    (S$5.34M inferred-FH vs S$3.14M declared-LH) — at confidence 70 with a live ask."""
    v = value_landed(LandedSpec("JALAN RINDU", 2656, "Terrace", asof="2026-07-01"), store)
    assert v.get("error") == "tenure_required"
    assert "MIXED-TENURE" in v["message"]
    # supplying tenure resolves it
    ok = value_landed(LandedSpec("JALAN RINDU", 2656, "Terrace", tenure_type="leasehold",
                                 lease_start=1993, asof="2026-07-01"), store)
    assert ok.get("error") != "tenure_required"
    # a single-tenure street still values without a tenure input
    plain = value_landed(LandedSpec("LOYANG RISE", 1635, "Terrace", asof="2026-07-01"), store)
    assert "error" not in plain


def test_no_momentum_extrapolation_in_time_adjustment():
    """GY-0003: a trailing-trend drift was tried to close the index publication lag and is
    REJECTED — sliced by regime it broke the already-unbiased periods (2023H2 sign 47.6%
    -> 37.6%) while worsening the one it targeted. _tadj_psf must not extrapolate."""
    import inspect
    from researcher.backtest import landed_benchmarks as lb
    src = inspect.getsource(lb._tadj_psf)
    assert "drift_factor" not in src.split('"""')[-1], \
        "momentum extrapolation reintroduced into the landed time adjustment (see GY-0003)"


def test_hard_case_suppresses_guidance(store):
    """Review blocker: the gate keyed on band_rel, which is a per-CELL constant from the
    conformal table and therefore BLIND to a subject-level hard case — ALNWICK (hard_case,
    18% spread) still emitted an ask above every comp on its own page."""
    v = _v(store, "ALNWICK ROAD", 2800, "Terrace")
    assert v["method_disagreement"]["hard_case"] is True
    assert v["seller_guidance"]["ask"] is None
    assert "hard case" in v["seller_guidance"]["note"]


def test_guidance_comes_from_observed_prints_not_the_error_bar(store):
    """The blocker that survived TWO patch rounds: thresholds were read off the conformal
    band — the engine's PREDICTIVE error — so 72% of asks landed above every comp on their
    own page. Guidance must come from the lease-matched adjusted comp distribution, and an
    ask must therefore never exceed the dearest comparable print."""
    from researcher.backtest.value_landed import _adjusted_comp_psfs, _infer, _landed_store
    from researcher.backtest.index import PriceIndex
    from researcher.backtest.market import MarketView
    import datetime as dt
    v = _v(store, "LOYANG RISE", 1635, "Terrace")
    sg = v["seller_guidance"]
    assert sg["ask"] is not None, "this subject should get live guidance"
    ls = _landed_store(store)
    subj = _infer(LandedSpec("LOYANG RISE", 1635, "Terrace", asof="2026-07-01"), ls)
    t = dt.date.fromisoformat("2026-07-01")
    idx = PriceIndex.load()
    ctx = {"asof_ym": "2026-07", "asof_date": t, "index": idx, "asof_q": idx.as_of_quarter(t)}
    mkt = MarketView(ls.as_of(t, lag_days=56).txs, "2026-07")
    adj = _adjusted_comp_psfs(subj, mkt, ctx)
    ask_psf = sg["ask"] / 1635
    assert ask_psf <= max(adj) + 1e-6, "ask must not exceed the dearest comparable print"
    assert min(adj) - 1e-6 <= sg["quick_sale"] / 1635, "quick sale must sit inside the evidence"
    assert "ACTUALLY printed" in sg["note"]
    # the EXHIBIT must carry the adjusted column the numbers live on, or a correct ask looks
    # like it sits above every comp (raw psf) on its own page
    assert all("adj_land_psf" in c for c in v["comps"])
    assert ask_psf <= max(c["adj_land_psf"] for c in v["comps"]) + 1e-6


def test_live_mode_sees_the_current_partial_month(store):
    """The DEFAULT path (no asof) was untested — every other test uses a past asof. LIVE
    claims lag 0, but as_of's month-END convention silently dropped the current month's
    prints (the EXP-0008 defect, fixed for condo, reintroduced here)."""
    import datetime as dt
    from researcher.backtest.market import MarketView
    from researcher.backtest.value_landed import _landed_store
    ls = _landed_store(store)
    ym = dt.date.today().strftime("%Y-%m")
    n_this_month = sum(1 for t in ls.txs if t["contract_ym"] == ym)
    if not n_this_month:
        pytest.skip("no caveats dated this month in the snapshot")
    live = ls.where(lambda x: x["contract_ym"] <= ym)
    assert sum(1 for t in live.txs if t["contract_ym"] == ym) == n_this_month
    # the backtest convention would hide them all — that's why LIVE must not use it
    assert sum(1 for t in ls.as_of(dt.date.today(), lag_days=0).txs
               if t["contract_ym"] == ym) < n_this_month


def test_unknown_street_escalates_not_fabricates(store):
    """Cardiff Grove is a real street with a PASS-8.5 craft valuation, but URA's rolling
    5y window carries no caveats there — the engine must route to Investment Suite."""
    v = value_landed(LandedSpec("CARDIFF GROVE", 1839.57, "Terrace", asof="2026-07-01"),
                     store)
    assert v.get("error") == "street_not_found"
    assert "Investment Suite" in v["message"]
