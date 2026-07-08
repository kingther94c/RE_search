"""Profitability parser: pure-function tests over real captures + synthetics."""
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.modules.setdefault("mbx", type(sys)("mbx"))  # stub the adb harness for offline import
spec = importlib.util.spec_from_file_location(
    "harvest_profitability", os.path.join(ROOT, "research", "harvest_profitability.py"))
hp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hp)


def _texts(name):
    cap = os.path.join(ROOT, "research", "captures", f"{name}.json")
    nodes = json.load(open(cap, encoding="utf-8"))
    return [n["text"] for n in nodes if n["text"]]


def test_spottiswoode_first_page():
    out = hp.parse_profitability_texts(_texts("spottiswoode_profit_f0"))
    rows = out["rows"]
    assert len(rows) == 5
    r = rows[0]
    assert (r["block"], r["level"], r["stack"], r["sqft"]) == ("16", 17, "01", 581)
    assert r["buy_month"] == "Apr 2021" and r["buy_psf"] == 2130 and r["buy_price"] == 1_238_000
    assert r["sell_date"] == "15 Oct 2024" and r["sell_psf"] == 2581 and r["sell_price"] == 1_500_000
    assert r["profit_amt"] == 262_000 and r["annualised_pct"] == 5.69
    assert r["section"] == "profitable" and r["type"] == "2BR"
    assert rows[4]["type"] == "1BR"
    assert out["meta"]["window"] == "5Y"


def test_scrolled_page_with_stray_date_in_type_column():
    # f1 has a leaked '26 May 2023' fragment right before the frozen type column
    out = hp.parse_profitability_texts(_texts("spottiswoode_profit_f1"))
    rows = out["rows"]
    assert len(rows) == 9                       # headers gone after scroll; rows still parse
    assert [r["type"] for r in rows] == ["2BR", "2BR", "2BR", "2BR", "1BR",
                                          "3BR", "2BR", "3BR", "3BR"]


def test_view_all_and_unprofitable_markers():
    out = hp.parse_profitability_texts(_texts("spottiswoode_profit_f2"))
    assert len(out["rows"]) == 6
    assert all(r["section"] == "profitable" for r in out["rows"])
    assert out["meta"]["view_all"] == {"profitable": 26}


def test_gallop_single_digit_levels():
    out = hp.parse_profitability_texts(_texts("gallop_profit_01"))
    rows = out["rows"]
    assert len(rows) == 5
    assert rows[0]["level"] == 1 and rows[0]["block"] == "82"   # 'Level 1' is one digit
    assert rows[0]["sell_psf"] == 1923 and rows[0]["holding"] == "20y 3m 26d"
    assert [r["type"] for r in rows] == ["2BR", "2BR", "4BR", "4BR", "3BR"]
    assert out["meta"]["view_all"] == {"profitable": 6}
    assert out["meta"]["window"] == "2Y"        # gallop capture was on the 2Y window


def test_unprofitable_rows_get_negative_amounts():
    texts = ["Unprofitable Transactions",
             "16", "08", "05", "743", "Jan 2013", "$2,258", "$1,678,000",
             "10 Mar 2023", "$2,100", "$1,560,000", "▼$158", "▼$118,000",
             "10y 2m 0d", "-0.72%",
             "Unit Type", "3BR"]
    out = hp.parse_profitability_texts(texts)
    r = out["rows"][0]
    assert r["section"] == "unprofitable" and r["profit_amt"] == -118_000
    assert r["type"] == "3BR" and r["annualised_pct"] == -0.72


def test_partial_type_column_is_not_misaligned():
    # 2 rows but only 1 trailing type token -> pairing skipped entirely
    row = ["16", "17", "01", "581", "Apr 2021", "$2,130", "$1,238,000",
           "15 Oct 2024", "$2,581", "$1,500,000", "▲$451", "▲$262,000",
           "3y 5m 18d", "5.69%"]
    row2 = ["16", "10", "01", "581", "Oct 2019", "$2,121", "$1,233,000",
            "25 Mar 2025", "$2,581", "$1,500,000", "▲$460", "▲$267,000",
            "5y 5m 16d", "3.65%"]
    out = hp.parse_profitability_texts(row + row2 + ["2BR"])
    assert len(out["rows"]) == 2
    assert all("type" not in r for r in out["rows"])
    assert "skipped" in out["meta"]["type_pairing"]
