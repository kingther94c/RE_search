"""Three-surface reconstruction: regression against the analyst-PASSed #18-03
digest (its 37-row comps_table was built by hand from the same inputs) plus
unit tests for windowing, dedup, subject exclusion and the trend ladder."""
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.modules.setdefault("mbx", type(sys)("mbx"))
spec = importlib.util.spec_from_file_location(
    "reconstruct_comps", os.path.join(ROOT, "research", "reconstruct_comps.py"))
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)


def _load(name):
    return json.load(open(os.path.join(ROOT, "research", name), encoding="utf-8"))


def _spott():
    return rc.reconstruct(_load("spottiswoode_transactions.json"),
                          _load("spottiswoode_profitability.json"),
                          _load("spottiswoode_towerview.json"),
                          asof="2026-07-03", years=5, subject="#18-03")


def test_regression_reproduces_the_passed_digest_comps():
    res = _spott()
    assert res["meta"]["surface_counts"] == {"sale": 16, "profitability": 6, "towerview": 15}
    assert res["meta"]["total"] == 37
    digest = json.load(open(os.path.join(
        ROOT, "researcher", "valuation", "spottiswoode_1803_digest.json"), encoding="utf-8"))
    want = sorted((c["date"], int(c["price"])) for c in digest["comps_table"])
    got = sorted((c["date"], c["price"]) for c in res["comps"])
    assert got == want, "tool must reproduce the hand-built, analyst-PASSed 37-row set"


def test_twin_print_is_in_and_subject_is_out():
    res = _spott()
    twin = [c for c in res["comps"] if c["level"] == "L18 #02"]
    assert twin and twin[0]["price"] == 1_730_900 and twin[0]["date"] == "2026-06-23"
    assert not [c for c in res["comps"] if c["level"] == "L18 #03"]
    # the subject's own history is returned separately (anchor material)
    assert any(r["date"] == "2021-05-07" and r["price"] == 1_500_000
               for r in res["subject_rows"])


def test_cross_surface_merge_is_fuzzy_on_date():
    # L18 #07: Sale says 2024-07-19, Tower View PP says 2024-07-23 — one caveat
    res = _spott()
    rows = [c for c in res["comps"] if c["level"] == "L18 #07"]
    assert len(rows) == 1 and "亦见于" in rows[0]["note"]


def test_beds_filled_for_every_row():
    res = _spott()
    missing = [c for c in res["comps"] if c["beds"] is None]
    assert not missing, f"beds ladder should resolve every row: {missing[:3]}"
    assert res["meta"]["beds_warnings"] == []
    # 538 sf carried no type in Tower View — resolved via the size ladder to 2BR
    r538 = [c for c in res["comps"] if c["size_sqft"] == 538]
    assert r538 and all(c["beds"] == 2 for c in r538)


def test_window_filter_drops_old_prints():
    res = rc.reconstruct(_load("spottiswoode_transactions.json"),
                         _load("spottiswoode_profitability.json"),
                         _load("spottiswoode_towerview.json"),
                         asof="2026-07-03", years=1, subject="#18-03")
    assert res["meta"]["total"] < 37
    assert all(c["date"] >= res["meta"]["window_start"] for c in res["comps"])


def test_head_only_profitability_declared_as_gap():
    res = _spott()
    assert any("10/26" in g for g in res["meta"]["data_gaps"])


def test_trend_ladder_segments_and_clamps():
    res = _spott()
    profit = _load("spottiswoode_profitability.json")
    seg3 = rc.fit_time_trend(res["comps"], beds=3)
    assert seg3["n_pairs"] >= 5 and 0.0 < seg3["rate_pa"] < 0.03
    chosen = rc.choose_trend(res["comps"], profit, subject_beds=3)
    assert chosen["rate_pa"] == seg3["rate_pa"] and "cross-unit 3BR" in chosen["method"]
    # too few pairs in a fake segment -> falls back to repeat-sales
    chosen4 = rc.choose_trend(res["comps"], profit, subject_beds=4)
    assert "repeat-sales" in chosen4["method"]
    # no pairs at all -> default, clamped to >= 0
    empty = rc.choose_trend([], {"rows": []}, subject_beds=3, default_pa=-0.02)
    assert empty["rate_pa"] == 0.0 and empty["clamped"]


def test_iso_date_helper():
    assert rc.iso("07 May 2021") == "2021-05-07"
    assert rc.iso("23 Jun 2026") == "2026-06-23"
