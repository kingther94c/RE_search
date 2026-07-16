"""Backtest firewall + benchmarks. The load-bearing test is `test_as_of_excludes_future`:
if the as-of filter ever leaks a future caveat, every downstream metric is a lie."""
import datetime as dt

from researcher.backtest import metrics
from researcher.backtest.benchmarks import BENCHMARKS
from researcher.backtest.candidates import CANDIDATES, c1_grid_adapted
from researcher.backtest.harness import walk_forward, _prev_ym
from researcher.backtest.market import MarketView
from researcher.backtest.store import (TransactionStore, month_end, visible_from,
                                       months_between)


def _tx(project, ym, psf, area=1000, x=0.0, y=0.0, seg="RCR", sale="Resale",
        ptype="Condominium"):
    price = psf * area
    return {"id": f"{project}-{ym}-{int(price)}", "project": project, "street": "ST",
            "market_segment": seg, "district": "14", "property_type": ptype,
            "type_of_area": "Strata", "type_of_sale": sale, "tenure_raw": "Freehold",
            "tenure_type": "freehold", "lease_start": None, "contract_ym": ym,
            "area_sqm": area / 10.7639, "area_sqft": float(area), "price": float(price),
            "psf": float(psf), "floor_range": "06-10", "floor_lo": 6, "floor_hi": 10,
            "x": x, "y": y, "no_of_units": 1}


# ------------------------------------------------------------------- as-of firewall
def test_month_end_and_visible_from():
    assert month_end("2025-02") == dt.date(2025, 2, 28)
    assert month_end("2024-12") == dt.date(2024, 12, 31)
    assert visible_from("2025-06", 56) == dt.date(2025, 6, 30) + dt.timedelta(days=56)


def test_as_of_excludes_future():
    store = TransactionStore([_tx("A", "2024-06", 2000), _tx("A", "2024-10", 2200)])
    # value as of end of 2024-09: the June caveat is visible, the October one is NOT
    v = store.as_of(dt.date(2024, 9, 30), lag_days=56)
    yms = {t["contract_ym"] for t in v.txs}
    assert yms == {"2024-06"}


def test_as_of_respects_lag_buffer():
    store = TransactionStore([_tx("A", "2024-08", 2000)])
    # month-end 2024-08-31 + 56d ~= 2024-10-26; a valuation on 2024-10-01 can't see it
    assert len(store.as_of(dt.date(2024, 10, 1), 56)) == 0
    assert len(store.as_of(dt.date(2024, 11, 1), 56)) == 1


def test_months_between_and_within():
    assert months_between("2024-06", "2024-09") == 3
    assert months_between("2024-10", "2024-09") == -1
    store = TransactionStore([_tx("A", "2023-01", 2000), _tx("A", "2024-06", 2100)])
    assert len(store.within_months("2024-09", 12)) == 1  # only 2024-06 within 12mo


def test_prev_ym():
    assert _prev_ym("2024-01") == "2023-12"
    assert _prev_ym("2024-07") == "2024-06"


# ------------------------------------------------------------------------- metrics
def test_metrics_basic():
    rows = [{"pred": 110, "actual": 100}, {"pred": 90, "actual": 100},
            {"pred": None, "actual": 100}]
    s = metrics.summarise(rows)
    assert s["n"] == 2 and s["n_declined"] == 1
    assert s["median_ape"] == 0.10 and s["pct_over_10"] == 0.0
    assert s["signed_bias"] == 0.0


def test_metrics_interval_coverage():
    rows = [{"pred": 100, "actual": 100, "lo": 90, "hi": 110},
            {"pred": 100, "actual": 130, "lo": 90, "hi": 110}]
    s = metrics.summarise(rows)
    assert s["interval_coverage"] == 0.5


# ------------------------------------------------------------ benchmarks / harness
def _rising_project_store():
    """Project A with a monthly rising history, plus a nearby project B for B4/B5."""
    txs = []
    for i, ym in enumerate(["2024-01", "2024-02", "2024-03", "2024-04", "2024-05",
                            "2024-06"]):
        txs.append(_tx("A", ym, 2000 + i * 20, area=1000, x=0, y=0))
        txs.append(_tx("B", ym, 1900 + i * 20, area=1000, x=300, y=0))
    return TransactionStore(txs)


def test_walk_forward_predicts_and_excludes_subject():
    store = _rising_project_store()
    subject = _tx("A", "2024-10", 2200, area=1000, x=0, y=0)  # the row we re-price
    store_all = TransactionStore(store.txs + [subject])
    res = walk_forward(store_all, [subject], BENCHMARKS, lag_days=56)
    by = res.by_method()
    b1 = by["B1_latest_same_project"][0]
    # B1 uses the latest visible A caveat (2024-06 @ 2100 psf) -> ~2.1M, NOT the
    # subject's own 2200 psf: proves the subject is excluded from its own comp set.
    assert b1["pred"] is not None
    assert abs(b1["pred_psf"] - 2100) < 1e-6
    assert b1["actual"] == 2200 * 1000


def test_benchmarks_all_runnable():
    store = _rising_project_store()
    subject = _tx("A", "2024-10", 2200, area=1000, x=0, y=0)
    store_all = TransactionStore(store.txs + [subject])
    res = walk_forward(store_all, [subject], BENCHMARKS, lag_days=56)
    methods = {r["method"] for r in res.rows}
    assert methods == set(BENCHMARKS)
    # B4 (nearest OTHER project) should find project B
    b4 = [r for r in res.rows if r["method"] == "B4_nearest_project_psf"][0]
    assert b4["pred"] is not None


# ---------------------------------------------------------------------- MarketView
def test_marketview_indexes():
    txs = [_tx("A", "2024-01", 2000, x=0, y=0), _tx("A", "2024-03", 2100, x=0, y=0),
           _tx("B", "2024-02", 1900, x=300, y=0), _tx("C", "2024-02", 1800, x=9000, y=0)]
    mkt = MarketView(txs, "2024-06")
    sp = mkt.same_project("A")
    assert [r["contract_ym"] for r in sp] == ["2024-03", "2024-01"]  # newest first
    assert len(mkt.condo()) == 4
    near = mkt.condo_near(0, 0, 1000)                # A(0) and B(300) in, C(9000) out
    assert {c["project"] for c in near} == {"A", "B"}
    assert len(mkt.segment_recent("RCR", 12)) == 4   # all within 12mo of 2024-06


def test_marketview_excludes_far_and_old():
    txs = [_tx("A", "2020-01", 2000, x=0, y=0), _tx("A", "2024-05", 2100, x=0, y=0)]
    mkt = MarketView(txs, "2024-06")
    assert len(mkt.segment_recent("RCR", 12)) == 1   # 2020-01 is >12mo out


# ------------------------------------------------------------------------- C1 grid
def test_c1_runs_and_is_reasonable():
    store = _rising_project_store()
    subject = _tx("A", "2024-10", 2200, area=1000, x=0, y=0)
    store_all = TransactionStore(store.txs + [subject])
    res = walk_forward(store_all, [subject], CANDIDATES, lag_days=56)
    c1 = res.by_method()["C1_grid_adapted"][0]
    assert c1["pred"] is not None
    # A's visible history tops out at 2100 psf; C1 shouldn't wildly exceed it
    assert 1900 <= c1["pred_psf"] <= 2300


def test_c1_declines_without_same_project():
    mkt = MarketView([_tx("OTHER", "2024-05", 2000, x=999, y=999)], "2024-09")
    subject = _tx("LONELY", "2024-10", 2200, x=0, y=0)
    ctx = {"asof_ym": "2024-09", "asof_q": None, "index": None}
    assert c1_grid_adapted(subject, mkt, ctx) is None


# --------------------------------------------------------------------- hedonic AVM
def test_hedonic_recovers_known_coefficients():
    import math
    import random
    from researcher.backtest.avm import HedonicAVM
    rng = random.Random(1)
    txs = []
    for _ in range(2000):
        area = rng.choice([500, 700, 900, 1200])
        seg = rng.choice(["CCR", "RCR", "OCR"])
        ym = f"2023-{rng.randint(1, 12):02d}"
        t = months_between("2021-07", ym)
        logpsf = 8.0 - 0.1 * math.log(area) + (0.15 if seg == "CCR" else 0.0) \
            + 0.02 * (t / 12) + rng.gauss(0, 0.03)
        txs.append({"area_sqft": float(area), "psf": math.exp(logpsf), "market_segment": seg,
                    "district": "10", "tenure_type": "freehold", "lease_start": None,
                    "floor_lo": 6, "floor_hi": 10, "contract_ym": ym})
    m = HedonicAVM.fit(txs, "2024-01")
    test = {"area_sqft": 700.0, "market_segment": "CCR", "district": "10",
            "tenure_type": "freehold", "lease_start": None, "floor_lo": 6, "floor_hi": 10,
            "contract_ym": "2024-01"}
    t = months_between("2021-07", "2024-01")
    expect = math.exp(8.0 - 0.1 * math.log(700) + 0.15 + 0.02 * (t / 12))
    assert abs(m.predict_psf(test) / expect - 1.0) < 0.03   # recovers truth within 3%


def test_ensemble_grid_only_when_avm_declines():
    from researcher.backtest.ensemble import ensemble_v0
    # small market: AVM can't fit (<200 rows) so E0 falls back to the grid, still answers
    store = _rising_project_store()
    mkt = MarketView(store.txs, "2024-09")
    subject = _tx("A", "2024-10", 2200, area=1000, x=0, y=0)
    ctx = {"asof_ym": "2024-09", "asof_q": None, "index": None}
    est = ensemble_v0(subject, mkt, ctx)
    assert est is not None and est["price"] is not None
    assert "grid only" in est["note"]


# ------------------------------------------------- team methods (A2 pooled, A3 kNN, E1)
def _big_condo_market(n=260, asof_ym="2024-09"):
    """>=200 condo caveats so A3's scaler and A1 fit; spread over projects/segments."""
    from researcher.backtest.index import PriceIndex
    txs = []
    for i in range(n):
        proj = f"P{i % 20}"
        seg = ("CCR", "RCR", "OCR")[i % 3]
        ym = f"2024-{(i % 8) + 1:02d}"
        txs.append(_tx(proj, ym, 1800 + (i % 20) * 10, area=700 + (i % 5) * 100,
                       x=float(i % 10) * 200, y=float(i // 10) * 200, seg=seg))
    mkt = MarketView(txs, asof_ym)
    ctx = {"asof_ym": asof_ym, "asof_date": None, "index": PriceIndex({}), "asof_q": None}
    return mkt, ctx


def test_avm_pooled_answers_and_falls_back_to_segment():
    from researcher.backtest.avm_pooled import avm_pooled
    mkt, ctx = _big_condo_market()
    onproj = avm_pooled(_tx("P3", "2024-10", 2000, area=800, x=0, y=0), mkt, ctx)
    assert onproj and onproj["psf"] > 0 and "pooled" in onproj["note"]
    # unknown project -> no same-project comp -> segment-anchor fallback, still answers
    lonely = avm_pooled(_tx("NOWHERE", "2024-10", 2000, area=800, x=0, y=0, seg="CCR"),
                        mkt, ctx)
    assert lonely and "segment anchor" in lonely["note"]


def test_avm_knn_answers_with_pool_and_declines_without_scaler():
    from researcher.backtest.avm_knn import avm_knn
    mkt, ctx = _big_condo_market()
    est = avm_knn(_tx("P3", "2024-10", 2000, area=800, x=100, y=100), mkt, ctx)
    assert est and est["psf"] > 0 and est["n_comps"] >= 5
    # too little history -> scaler declines rather than guessing
    tiny = MarketView(_rising_project_store().txs, "2024-09")
    assert avm_knn(_tx("A", "2024-10", 2200, x=0, y=0), tiny, ctx) is None


def test_ensemble_learned_blends_and_beats_nothing_without_avm():
    from researcher.backtest.ensemble_learned import ensemble_learned
    # big market: both C1 and A1 answer -> E1 blends, weight recorded in the note
    mkt, ctx = _big_condo_market()
    est = ensemble_learned(_tx("P3", "2024-10", 2000, area=800, x=100, y=100), mkt, ctx)
    assert est and est["price"] is not None and "w_c1=" in est["note"]


def test_ensemble_pooled_e2_blends():
    from researcher.backtest.ensemble_learned import ensemble_pooled
    mkt, ctx = _big_condo_market()
    est = ensemble_pooled(_tx("P3", "2024-10", 2000, area=800, x=100, y=100), mkt, ctx)
    assert est and est["price"] is not None and est["method"] == "E2_ensemble_pooled"


# ----------------------------------------------------- landed L0 (EXP-0009 foundation)
def _ltx(street, ym, price, area_sqm, ptype="Terrace", type_of_area="Land",
         sale="Resale", units=1, x=0.0, y=0.0):
    area_sqft = area_sqm * 10.7639
    return {"id": f"L|{street}|{ym}|{int(price)}|{area_sqm}", "project": "LANDED HOUSING",
            "street": street, "market_segment": "OCR", "district": "19",
            "property_type": ptype, "type_of_area": type_of_area, "type_of_sale": sale,
            "tenure_raw": "Freehold", "tenure_type": "freehold", "lease_start": None,
            "contract_ym": ym, "area_sqm": area_sqm, "area_sqft": round(area_sqft, 1),
            "price": float(price), "psf": round(price / area_sqft, 1),
            "floor_range": "", "floor_lo": None, "floor_hi": None,
            "x": x, "y": y, "no_of_units": units}


def test_pure_landed_classification():
    txs = [_ltx("AIDA ST", "2024-01", 3_000_000, 150.0),                    # pure
           _ltx("AIDA ST", "2024-02", 2_000_000, 120.0, ptype="Strata Terrace",
                type_of_area="Strata"),                                     # strata-landed
           _ltx("JOO AVE", "2024-03", 1_800_000, 140.0, ptype="Apartment"), # walk-up stray
           _tx("CONDO", "2024-04", 2000)]                                   # condo
    store = TransactionStore(txs)
    assert [t["street"] for t in store.is_pure_landed().txs] == ["AIDA ST"]
    assert [t["property_type"] for t in store.is_strata_landed().txs] == ["Strata Terrace"]
    # the broad landed universe keeps all three landed-ish rows (audit view)
    assert len(store.is_landed()) == 3
    # and the condo universe is untouched by any of them
    assert [t["project"] for t in store.is_condo().txs] == ["CONDO"]


def test_landed_subjects_use_land_area_defaults():
    # 743 sqm ~= 8,000 sqft: a normal landed plot that condo defaults (<=6,000) would cut
    store = TransactionStore([_ltx("BIG PLOT WAY", "2024-05", 9_000_000, 743.0)])
    assert len(store.subjects(kind="pure-landed")) == 1
    assert store.subjects(kind="condo") == []


def test_marketview_landed_indexes():
    from researcher.backtest.market import MarketView
    txs = [_ltx("AIDA ST", "2024-01", 3_000_000, 150.0, x=0, y=0),
           _ltx("AIDA ST", "2024-03", 3_200_000, 160.0, x=100, y=0),
           _ltx("FAR RD", "2024-02", 2_500_000, 140.0, x=9000, y=0),
           _ltx("AIDA ST", "2024-02", 2_000_000, 120.0, ptype="Strata Terrace",
                type_of_area="Strata"),                       # not in the pure pool
           _tx("CONDO", "2024-02", 2000, x=0, y=0)]           # nor condos
    mkt = MarketView(txs, "2024-06")
    assert len(mkt.landed()) == 3
    street = mkt.landed_on_street("aida st")                  # casefolded lookup
    assert [r["contract_ym"] for r in street] == ["2024-03", "2024-01"]  # newest first
    near = mkt.landed_near(0, 0, 1000)
    assert {r["street"] for r in near} == {"AIDA ST"}         # FAR RD is 9km out


def test_same_plot_matcher_rules():
    from researcher.backtest.landed_pairs import repeat_pairs, same_plot_groups
    txs = [
        # plot A: 3 clean trades -> 2 consecutive pairs
        _ltx("AIDA ST", "2022-01", 3_000_000, 150.0),
        _ltx("AIDA ST", "2023-01", 3_300_000, 150.0),
        _ltx("AIDA ST", "2024-01", 3_600_000, 150.0),
        # plot B: exact copy (same month+price) collapses to ONE trade -> no pair
        _ltx("BEDOK WALK", "2023-05", 2_800_000, 200.0),
        _ltx("BEDOK WALK", "2023-05", 2_800_000, 200.0),
        # plot C: same month, DIFFERENT price = twin plots -> key dropped
        _ltx("CHUAN DR", "2023-06", 2_000_000, 180.0),
        _ltx("CHUAN DR", "2023-06", 2_100_000, 180.0),
        # plot D: 5 distinct trades = cookie-cutter development -> key dropped
        *[_ltx("DEV ROW", f"2023-{m:02d}", 1_500_000 + m, 170.0) for m in range(1, 6)],
        # plot E: two New Sales months apart = mirror units -> key dropped
        _ltx("MIRROR LANE", "2022-10", 6_400_000, 278.4, sale="New Sale"),
        _ltx("MIRROR LANE", "2022-12", 6_000_000, 278.4, sale="New Sale"),
        # plot F: Resale -> New Sale = redevelopment pair, KEPT
        _ltx("REBUILD AVE", "2022-03", 3_000_000, 210.0),
        _ltx("REBUILD AVE", "2024-03", 6_000_000, 210.0, sale="New Sale"),
    ]
    groups = same_plot_groups(txs)
    assert set(groups) == {("AIDA ST", 150.0, "Terrace"),
                           ("REBUILD AVE", 210.0, "Terrace")}
    pairs = repeat_pairs(txs)
    assert len(pairs) == 3
    aida = [p for p in pairs if p["street"] == "AIDA ST"]
    assert aida[0]["gap_months"] == 12 and abs(aida[0]["ratio"] - 1.1) < 1e-9
    assert abs(aida[0]["annualized"] - 0.1) < 1e-9
    rebuild = [p for p in pairs if p["street"] == "REBUILD AVE"][0]
    assert (rebuild["a_sale"], rebuild["b_sale"]) == ("Resale", "New Sale")
    # sub-3-month gaps are not annualized (too short to be honest)
    short = repeat_pairs([_ltx("E ST", "2024-01", 1_000_000, 90.0),
                          _ltx("E ST", "2024-02", 1_050_000, 90.0)])
    assert short[0]["annualized"] is None


def test_landed_benchmarks_behaviour():
    from researcher.backtest.index import PriceIndex
    from researcher.backtest.landed_benchmarks import (lb1_same_street,
        lb2_street_district_pooled, lb3_type_tenure_segment, lb4_spatial_knn,
        lb5_district_median_price, lc1_craft_landed)
    from researcher.backtest.market import MarketView
    ctx = {"asof_ym": "2024-09", "asof_date": None, "index": PriceIndex({}), "asof_q": None}
    txs = [_ltx("AIDA ST", f"2024-0{m}", 3_000_000 + m * 10_000, 150.0, x=0, y=0)
           for m in range(1, 6)] + [
        _ltx("AIDA ST", "2024-06", 5_000_000, 300.0, x=0, y=0),      # bigger plot, street
        _ltx("ELSEWHERE RD", "2024-05", 2_600_000, 150.0, x=400, y=0),
        _ltx("FAR AWAY", "2024-05", 9_900_000, 150.0, x=50_000, y=0)]
    mkt = MarketView(txs, "2024-09")
    subj = _ltx("AIDA ST", "2024-10", 3_100_000, 150.0, x=0, y=0)

    est = lb1_same_street(subj, mkt, ctx)
    assert est and est["n_comps"] == 6          # type-matched street comps, ALL sizes
    # LB1 declines with no street history at all
    assert lb1_same_street(_ltx("NO ST", "2024-10", 1, 150.0), mkt, ctx) is None
    # LB2 pools to district when the street is thin
    thin = _ltx("ELSEWHERE RD", "2024-10", 2_600_000, 150.0)
    pooled = lb2_street_district_pooled(thin, mkt, ctx)
    assert pooled and "district pool" in pooled["note"]
    assert lb3_type_tenure_segment(subj, mkt, ctx) is not None
    knn = lb4_spatial_knn(subj, mkt, ctx)
    assert knn and knn["n_comps"] >= 3          # size gate keeps the 300sqm plot out
    q = lb5_district_median_price(subj, mkt, ctx)
    assert q and q["price"] == 3_035_000        # naive district median PRICE
    craft = lc1_craft_landed(subj, mkt, ctx)
    assert craft and "same-spec grid" in craft["note"]


def test_lc1_size_prior_only_when_needed():
    """LC1 falls back to the ported area^-0.877 prior ONLY when <3 same-spec comps —
    and the adjustment moves psf the right way (bigger subject -> lower psf)."""
    from researcher.backtest.index import PriceIndex
    from researcher.backtest.landed_benchmarks import lc1_craft_landed
    from researcher.backtest.market import MarketView
    ctx = {"asof_ym": "2024-09", "asof_date": None, "index": PriceIndex({}), "asof_q": None}
    # street has only SMALL plots (150 sqm, psf ~1860); subject is 300 sqm
    txs = [_ltx("AIDA ST", f"2024-0{m}", 3_000_000, 150.0) for m in range(1, 4)]
    mkt = MarketView(txs, "2024-09")
    big = _ltx("AIDA ST", "2024-10", 6_000_000, 300.0)
    est = lc1_craft_landed(big, mkt, ctx)
    assert est and "size-adjusted" in est["note"]
    small_psf = txs[0]["psf"]
    assert est["psf"] < small_psf               # negative elasticity: bigger -> lower psf
    assert abs(est["psf"] - small_psf * 0.5 ** 0.877) < 1.0   # 2x size at e=-0.877


def test_conformal_table_matches_current_c1():
    """The conformal table is calibrated on C1 residuals. If candidates.py changes without
    a recalibration (run.py --dump -> analyze_r3.py), the band multipliers silently drift
    from the code that produced them — this guard makes that a red test, not a silent skew."""
    import hashlib
    import json
    import os
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "researcher", "backtest")
    with open(os.path.join(base, "conformal_table.json"), encoding="utf-8") as f:
        meta = json.load(f).get("_meta", {})
    stored = meta.get("candidates_sha1")
    assert stored, "conformal table has no fingerprint — recalibrate via analyze_r3.py"
    with open(os.path.join(base, "candidates.py"), "rb") as f:
        current = hashlib.sha1(f.read()).hexdigest()
    assert current == stored, (
        "candidates.py changed since the conformal table was calibrated — re-run "
        "`python -m researcher.backtest.run --sample 8000 --dump <p>` then "
        "`python research/analyze_r3.py <p>`")


def test_engine_v2_point_band_and_fallback():
    from researcher.backtest.engine_v2 import engine_v2
    mkt, ctx = _big_condo_market()
    # C1 available -> V2 point comes from C1, with a conformal band around it
    est = engine_v2(_tx("P3", "2024-10", 2000, area=800, x=100, y=100), mkt, ctx)
    assert est and est["method"] == "V2_engine" and est["note"].startswith("C1")
    assert est["low"] < est["price"] < est["high"]        # conformal band brackets the point
    # unknown project -> C1 declines -> anchor fallback keeps V2 answering (100% coverage)
    fb = engine_v2(_tx("NOWHERE", "2024-10", 2000, area=800, x=0, y=0, seg="CCR"), mkt, ctx)
    assert fb is not None and "fallback" in fb["note"]
