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
    twin = [c for c in res["comps"] if (c["floor"], c["stack"]) == (18, "02")]
    assert twin and twin[0]["price"] == 1_730_900 and twin[0]["date"] == "2026-06-23"
    assert twin[0]["level"] == "B16 L18 #02"     # block picked up from the street field
    assert not [c for c in res["comps"] if (c["floor"], c["stack"]) == (18, "03")]
    # the subject's own history is returned separately (anchor material)
    assert any(r["date"] == "2021-05-07" and r["price"] == 1_500_000
               for r in res["subject_rows"])


def test_cross_surface_merge_is_fuzzy_on_date():
    # L18 #07: Sale says 2024-07-19, Tower View PP says 2024-07-23 — one caveat
    res = _spott()
    rows = [c for c in res["comps"] if (c["floor"], c["stack"]) == (18, "07")]
    assert len(rows) == 1 and "亦见于" in rows[0]["note"]


def test_multiblock_gallop_dedup_and_subject_block():
    def load(n):
        return json.load(open(os.path.join(ROOT, "research", n), encoding="utf-8"))

    res = rc.reconstruct(load("gallop_transactions.json"), load("gallop_profitability.json"),
                         load("gallop_towerview.json"), asof="2026-07-03", years=5,
                         subject="#03-04", subject_block="80")
    # scroll-artifact triplet (B72 L3 #03 $6.88m on 3 neighbouring dates) collapses to one
    b72 = [c for c in res["comps"] if c["price"] == 6_880_000]
    assert len(b72) == 1
    # subject exclusion is block-scoped: B82 #03-04 (same floor/stack, other block) stays
    assert all(r["block"] == "80" for r in res["subject_rows"])
    others = [c for c in res["comps"] if (c["floor"], c["stack"]) == (3, "04")]
    assert all(c["block"] != "80" for c in others)
    # stack numbers repeat across blocks — same-price fuzzy merge must stay block-scoped
    assert all(c["block"] for c in res["comps"])


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


def test_arithmetic_gate_and_same_day_conflict_resolution():
    sale = [{"date": "09 Mar 2026", "street": "1 Pearl Bank", "level": "17", "unit": "22",
             "unit_type": "2BR", "area_sqft": "893", "psf": "$2,665", "price": "$2,380,000",
             "sale_type": "Resale"}]
    tower = [  # same unit, same date, IMPOSSIBLE different price (misaligned twin)
        {"unit": "#17-22", "block": "1", "floor": 17, "stack": "22", "sqft": 893.0,
         "pp_date": "09 Mar 2026", "pp_price": 1_728_000, "pp_psf": 1935, "type": "2BR"},
        # and a row that flat-out fails price = psf x sqft
        {"unit": "#08-14", "block": "1", "floor": 8, "stack": "14", "sqft": 431.0,
         "pp_date": "19 Dec 2025", "pp_price": 2_830_000, "pp_psf": 2213, "type": "1BR"},
    ]
    res = rc.reconstruct(sale, {"meta": {}, "rows": []}, tower, asof="2026-07-08", years=5)
    assert res["meta"]["total"] == 1                    # only the sale row survives
    assert res["comps"][0]["surface"] == "sale" and res["comps"][0]["price"] == 2_380_000
    assert len(res["meta"]["quarantined"]) == 1         # the arithmetic-gate victim
    assert len(res["meta"]["price_conflicts"]) == 1     # sale wins the clash
    assert any("算术门" in g for g in res["meta"]["data_gaps"])


def test_fit_floor_premium_recovers_known_gradient():
    # synthetic tower: same-spec sales, same week, psf strictly +0.5%/floor
    comps = []
    for f in (2, 5, 8, 12, 15, 18, 21, 25, 28, 30):
        comps.append({"date": "2026-06-01", "floor": f, "stack": "05",
                      "size_sqft": 700, "beds": 2, "level": f"L{f} #05",
                      "psf": round(2300 * (1.005 ** f)), "price": 0,
                      "block": "1", "surface": "towerview", "note": ""})
    fit = rc.fit_floor_premium(comps, beds=2)
    assert fit["n_pairs"] >= 8
    assert abs(fit["rate_per_floor"] - 0.005) < 0.0005
    # too few pairs -> None
    assert rc.fit_floor_premium(comps[:3], beds=2)["rate_per_floor"] is None


def test_stale_panel_fingerprint_gate():
    # the Gallop review incident: one grid captured under many block names ->
    # identical (unit,sqft,pp_date,pp_price,est_val) across blocks
    base = {"unit": "#02-02", "sqft": 2669.0, "pp_date": "20 Nov 2024",
            "pp_price": 6_138_000, "pp_psf": 2299, "est_val": 6_500_000, "floor": 2,
            "stack": "02", "type": "4BR"}
    tower = [{**base, "block": b} for b in ("70", "72", "74", "76", "78", "80", "82")]
    tower.append({"unit": "#03-01", "sqft": 1733.0, "pp_date": "08 May 2025",
                  "pp_price": 4_080_000, "pp_psf": 2354, "est_val": 4_178_000,
                  "floor": 3, "stack": "01", "block": "78", "type": "3BR"})
    clean, warnings = rc.strip_stale_panel_artifacts(tower)
    assert len(clean) == 2                      # 7 phantoms -> 1 (+ the honest unit)
    kept = next(u for u in clean if u["unit"] == "#02-02")
    assert kept["block"] is None                # block identity is uncertain
    assert warnings and "stale-panel" in warnings[0]
    # two genuine records under two blocks must NOT be collapsed
    tower2 = [{**base, "block": "70"}, {**base, "block": "72"}]
    clean2, w2 = rc.strip_stale_panel_artifacts(tower2)
    assert len(clean2) == 2 and not w2
