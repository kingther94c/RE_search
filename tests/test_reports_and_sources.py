"""Report builder + listings screening: robustness to partial data, ranking."""
import importlib.util
import io
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

spec = importlib.util.spec_from_file_location(
    "build_landed_report", os.path.join(ROOT, "deliverables", "build_landed_report.py"))
blr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(blr)

from researcher.sources.propertyguru import (  # noqa: E402
    normalize, rank_listings, screen, value_flag,
)


def test_render_minimal_digest_no_crash():
    html = blr.render({"area_name": "X", "summary": "s"})
    assert "X" in html and "<html" in html


def test_render_uses_digest_asof_not_hardcoded():
    html = blr.render({"area_name": "X", "asof": "2031-01-02"})
    assert "2031-01-02" in html and "2026-06-30" not in html


def test_render_escapes_html_in_data():
    html = blr.render({"area_name": "<script>alert(1)</script>"})
    assert "<script>alert(1)" not in html


def test_txn_dict_rows_render_as_table():
    html = blr.render({
        "area_name": "X",
        "price_structure": [{"segment": "terrace", "land_psf": "2000", "quantum": "5m", "note": ""}],
        "example_transactions": [{
            "date": "2026-05", "street": "Kings Rd", "type": "terrace",
            "price": "S$5.2m", "land_sqft": 1800, "land_psf": 2889,
            "note": "rebuilt", "source": "EdgeProp",
        }],
    })
    assert "Kings Rd" in html and "EdgeProp" in html and "2889" in html


def test_legacy_string_txns_still_render():
    html = blr.render({
        "area_name": "X",
        "price_structure": [{"segment": "terrace", "land_psf": "2000", "quantum": "5m", "note": ""}],
        "example_transactions": ["a deal happened"],
    })
    assert "a deal happened" in html


def test_value_flag_bands():
    bench = {"terrace": (2000, 2800)}
    assert value_flag("terrace", 1900, bench).startswith("VALUE")
    assert value_flag("terrace", 2400, bench).startswith("FAIR")
    assert value_flag("terrace", 3000, bench).startswith("RICH")
    assert value_flag("terrace", 4000, bench).startswith("BUILD-PRICED")
    assert value_flag("gcb", 2000, bench) == "?"


def test_rank_listings_orders_by_quality_then_value():
    data = {
        "benchmark_land_psf": {"terrace": (2000, 2800)},
        "listings": [
            {"street": "worse", "type": "terrace", "land_psf": 2100,
             "flood_risk": "high", "topography": "below", "rebuild_status": "original_poor"},
            {"street": "better", "type": "terrace", "land_psf": 2100,
             "plot_shape": "rectangular", "frontage_m": 11, "rebuild_status": "rebuilt_recent"},
        ],
    }
    rows = rank_listings(data)
    assert rows[0]["lst"]["street"] == "better"


def test_build_priced_ranks_below_fair_at_equal_quality():
    base = {"type": "terrace", "plot_shape": "rectangular", "frontage_m": 11}
    data = {
        "benchmark_land_psf": {"terrace": (2000, 2800)},
        "listings": [
            {**base, "street": "expensive", "land_psf": 4000},
            {**base, "street": "fair", "land_psf": 2400},
        ],
    }
    rows = rank_listings(data)
    assert rows[0]["lst"]["street"] == "fair"  # BUILD-PRICED must sort below FAIR


def test_screen_tolerates_missing_fields(tmp_path, monkeypatch, capsys):
    data = {
        "area": "T", "pulled": "now", "benchmark_land_psf": {"terrace": (2000, 2800)},
        "listings": [{"street": "NoNumbers Rd", "type": "terrace"}],  # no price/land/psf
    }
    landed = tmp_path / "researcher" / "landed"
    landed.mkdir(parents=True)
    (landed / "t_listings.json").write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr("researcher.sources.propertyguru.ROOT", str(tmp_path))
    rows = screen("t")
    out = capsys.readouterr().out
    assert len(rows) == 1 and "NoNumbers Rd" in out and "?" in out


def test_normalize_defaults_are_conservative():
    n = normalize({"street": "s", "type": "terrace"})
    assert n["foreign_eligible"] is False  # landed default: restricted
