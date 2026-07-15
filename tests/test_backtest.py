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
