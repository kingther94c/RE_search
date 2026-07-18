"""Nearby-Properties parser: pure-function tests over real captures."""
import json
import os

from research.lib import harvest_nearby as hn

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _texts(name):
    cap = os.path.join(ROOT, "research", "captures", f"{name}.json")
    nodes = json.load(open(cap, encoding="utf-8"))
    return [n["text"] for n in nodes if n["text"]]


def test_gallop_nearby_page():
    out = hn.parse_nearby_texts(_texts("gallop_nearby_01"))
    rows = out["rows"]
    assert len(rows) == 4
    g = rows[0]
    assert g["project"] == "Gallop Gables" and g["tenure_type"] == "FH"
    assert g["top_year"] == 1997 and g["total_units"] == 140
    assert g["psf_low"] == 1923 and g["psf_high"] == 2421
    assert g["yield_avg_pct"] == 2.13 and g["rental_volume"] == 76
    pb = rows[3]
    assert pb["project"] == "Pollen & Bleu" and pb["tenure_type"] == "99y"
    assert pb["lease_start"] == 2012 and pb["yield_avg_pct"] == 2.81
    assert out["meta"]["radius"] == "200 Meters"
    assert out["meta"]["advertised_projects"] == 4
    # frozen Dist column: anchor = pin = 0
    assert rows[0]["dist_m"] == 0.0 and rows[1]["dist_m"] == 78.0


def test_spottiswoode_nearby_page():
    out = hn.parse_nearby_texts(_texts("spottiswoode_nearby_f0"))
    rows = out["rows"]
    assert rows, "no rows parsed from spottiswoode nearby capture"
    assert all(r["psf_low"] and r["psf_high"] and r["total_units"] for r in rows)


def test_landed_page_yields_no_condo_rows():
    # landed pages have NO condo-style Nearby table (they show a Tier-2 agency
    # panel instead) — the parser must return empty rather than mis-parse it
    out = hn.parse_nearby_texts(_texts("landed_kingsmead_nearby_01"))
    assert out["rows"] == []
