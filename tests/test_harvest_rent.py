"""Rent parser: pure-function tests over real captures + synthetics."""
import json
import os

from research.lib import harvest_rent as hr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _texts(name):
    cap = os.path.join(ROOT, "research", "captures", f"{name}.json")
    nodes = json.load(open(cap, encoding="utf-8"))
    return [n["text"] for n in nodes if n["text"]]


def test_first_page_rows_band_and_dates():
    out = hr.parse_rent_texts(_texts("spottiswoode_rent_f00"))
    rows = out["rows"]
    assert len(rows) == 5
    r = rows[0]
    assert r["street"] == "Spottiswoode Park Road" and r["type"] == "2BR"
    assert r["area_band_sqft"] == "500 - 600" and r["psf"] == 7.82 and r["monthly_rent"] == 4300
    assert r["contract_month"] == "May 2026" and rows[4]["contract_month"] == "Apr 2026"
    band = out["meta"]["band"]
    assert band["low"] == "$2,200" and band["avg"] == "$3,713" and band["high"] == "$7,000"
    assert band["avg_psf"] == "$6.65 PSF"
    assert out["meta"]["window"] == "5Y"


def test_scrolled_page_cuts_at_agency_panel():
    out = hr.parse_rent_texts(_texts("spottiswoode_rent_f02"))
    rows = out["rows"]
    assert len(rows) == 6                        # agency-panel headers must not parse as rows
    assert out["meta"]["agency_panel_present"] is True
    assert out["meta"]["advertised_total"] == 473
    assert all(r["contract_month"] == "Apr 2026" for r in rows)


def test_gallop_comma_area_bands():
    out = hr.parse_rent_texts(_texts("gallop_rent_02"))
    rows = out["rows"]
    assert len(rows) == 6
    assert rows[0]["street"] == "Farrer Road" and rows[0]["area_band_sqft"] == "1,700 - 1,800"
    assert rows[0]["psf"] == 4.69 and rows[0]["monthly_rent"] == 8200
    assert rows[5]["type"] == "4BR" and rows[5]["monthly_rent"] == 13_500


def test_partial_date_column_is_not_misaligned():
    texts = ["Spottiswoode Park Road", "2BR", "500 - 600", "$7.82", "$4,300",
             "Spottiswoode Park Road", "3BR", "700 - 800", "$6.13", "$4,600",
             "May 2026"]                          # 2 rows, 1 date -> skip pairing
    out = hr.parse_rent_texts(texts)
    assert len(out["rows"]) == 2
    assert all("contract_month" not in r for r in out["rows"])
    assert "skipped" in out["meta"]["date_pairing"]


def test_onepearl_shapes_dash_type_no_cents_and_live_panel():
    # One Pearl Bank realities: type '-', psf without cents ('$6'), live-data
    # rows with EXACT sqft + full dates + 'live data' badges, and the trailing
    # 'Unit Mix Rentals' aggregate panel
    texts = ["Past Rentals",
             "Pearl Bank", "-", "400 - 500", "$7.44", "$3,350",
             "Pearl Bank", "3BR", "1,200 - 1,300", "$6", "$7,500",
             "Pearl Bank", "2BR", "700", "$7.72", "$5,400",       # live (exact sqft)
             "May 2026", "May 2026", "live data", "12 Jun 2026",
             "View All (344)", "Unit Mix Rentals",
             "should", "not", "parse", "$9.99", "$9,999"]
    out = hr.parse_rent_texts(texts)
    rows = out["rows"]
    assert len(rows) == 3
    past = [r for r in rows if r["panel"] == "past"]
    live = [r for r in rows if r["panel"] == "live"]
    assert len(past) == 2 and len(live) == 1
    assert past[0]["type"] is None and past[1]["psf"] == 6.0
    assert live[0]["area_band_sqft"] == "700"
    assert [r["contract_month"] for r in rows] == ["May 2026", "May 2026", "12 Jun 2026"]
    assert out["meta"]["agency_panel_present"] is True
