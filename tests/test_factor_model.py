"""Factor model stats helpers + panel integration checks."""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from researcher.factors import factor_model as fm  # noqa: E402


def test_spearman_known():
    assert abs(fm.spearman([1, 2, 3, 4, 5], [2, 4, 6, 8, 10]) - 1.0) < 1e-9
    assert abs(fm.spearman([1, 2, 3, 4, 5], [10, 8, 6, 4, 2]) + 1.0) < 1e-9
    assert fm.spearman([1, 2, 3], [1, 2, 3]) is None  # too few


def test_ols_recovers_coefficients():
    # y = 3 + 2*x1 - 1*x2
    x1 = [1, 2, 3, 4, 5, 6, 7, 8.0]
    x2 = [2, 1, 4, 3, 6, 5, 8, 7.0]
    y = [3 + 2 * a - b for a, b in zip(x1, x2)]
    b0, b1, b2 = fm.ols(y, [x1, x2])
    assert abs(b0 - 3) < 1e-9 and abs(b1 - 2) < 1e-9 and abs(b2 + 1) < 1e-9
    assert abs(fm.r_squared(y, [x1, x2]) - 1.0) < 1e-9


def test_bootstrap_flags_a_real_effect():
    import random
    rng = random.Random(7)
    x = [rng.gauss(0, 1) for _ in range(60)]
    noise = [rng.gauss(0, 0.1) for _ in range(60)]
    y = [2.0 * a + e for a, e in zip(x, noise)]
    out = fm.bootstrap_ols(y, [x], n_boot=300)
    assert out[0]["sig"] and 1.8 < out[0]["coef"] < 2.2


def test_condo_rows_from_committed_panel():
    rows = fm.condo_rows()
    assert len(rows) >= 20
    assert all(r["segment"] in ("CCR", "RCR", "OCR") for r in rows)
    assert all(r["mid_psf"] > 500 for r in rows)


def test_landed_cagr_pairs_need_same_type_and_gap():
    # synthetic: detached at t0 psf 400, detached at t0+20y psf 1600 -> ~+7.2%/yr
    panel = {"streets": [{"street": "T", "pp_panel": [
        {"address": "1 T", "type": "Detached House", "pp_psf": 400, "pp_date": "01 Jan 2005"},
        {"address": "2 T", "type": "Detached House", "pp_psf": 1600, "pp_date": "01 Jan 2025"},
        {"address": "3 T", "type": "Semi-Detached House", "pp_psf": 9999, "pp_date": "01 Jan 2025"},
    ], "transactions": []}]}
    import json
    p = os.path.join(ROOT, "researcher", "factors", "_tmp_landed.json")
    json.dump(panel, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    try:
        orig = fm._load
        fm._load = lambda n: panel if n == "panel_landed_enriched.json" else orig(n)  # noqa
        out = fm.landed_street_cagr()
        fm._load = orig
        s = out[0]
        assert s["n_pairs"] == 1                     # semi never pairs with detached
        assert abs(s["cagr_range"][0] - math.log(4) / 20) < 1e-6
    finally:
        os.remove(p)
