"""Landed DD tool chain: pure-logic tests (no network, no 190MB layer download).

These cover the parts that were wrong when done by hand — the size-cohort split, the
area/label distinction, and the flood list's evidential weight — plus the geometry the
zoning lookups stand on, and the URA street-label semantics an empty comp set must not
be read through (EXP-0018).
"""
import pytest

from researcher.landed import comps
from researcher.sources import mp_zoning, pub_flood


# ------------------------------------------- URA street semantics (EXP-0018 / R4a)
def test_empty_street_comps_does_not_mean_no_sales():
    """URA's `street` is a coarse PARENT label, so an empty comp set is a statement about
    the NAME, not about the road. Measured (EXP-0018): CARDIFF GROVE has no URA caveats
    under its own name, yet 16 of its 17 in-window sales are in URA under ALNWICK ROAD
    (matched on month+price+area). If this ever starts returning rows, URA changed its
    street convention and the DD chain's "none" wording should be revisited."""
    assert comps.street_comps("CARDIFF GROVE") == []
    parent = comps.street_comps("ALNWICK ROAD")
    assert len(parent) > 100                       # the parent road carries them
    # the exact print that proves it: 17 Cardiff Grove, 26 Jun 2026, 2,640sf, $4,698,000
    assert any(round(t["price"]) == 4_698_000 and abs(t["area_sqft"] - 2640) < 2
               and t["contract_ym"] == "2026-06" for t in parent)


def test_street_comps_can_include_adjacent_roads():
    """The other direction of the same fact: a street set may contain houses that are not
    on that road. URA's "LOYANG RISE" (135) = Investment Suite's Loyang Rise (104) + Loyang
    View (31), exactly — so any per-road claim built on a URA street set is approximate."""
    assert len(comps.street_comps("LOYANG RISE")) == 135


# --------------------------------------------------------------------- geometry
def test_in_ring_square():
    sq = [[0, 0], [0, 10], [10, 10], [10, 0]]
    assert mp_zoning._in_ring(5, 5, sq)
    assert not mp_zoning._in_ring(15, 5, sq)
    assert not mp_zoning._in_ring(5, 15, sq)


def test_in_ring_ignores_z_coordinate():
    """MP geometry ships [lon, lat, z] on some vintages — the extra dim must not break it."""
    sq = [[0, 0, 5], [0, 10, 5], [10, 10, 5], [10, 0, 5]]
    assert mp_zoning._in_ring(5, 5, sq)


def test_near_seg_distance_and_point():
    # segment from (3,-1) to (3,1): closest point to the origin is (3,0), distance 3
    d, p = mp_zoning._near_seg((3.0, -1.0), (3.0, 1.0))
    assert d == pytest.approx(3.0)
    assert p[0] == pytest.approx(3.0)
    assert p[1] == pytest.approx(0.0)


def test_near_seg_clamps_to_endpoint():
    """Beyond the segment the nearest point is an endpoint, not the infinite line's foot."""
    d, p = mp_zoning._near_seg((3.0, 4.0), (3.0, 8.0))
    assert d == pytest.approx(5.0)          # the (3,4) endpoint
    assert p == pytest.approx((3.0, 4.0))


def test_rings_polygon_and_multipolygon():
    assert len(mp_zoning._rings({"type": "Polygon", "coordinates": [[[0, 0]]]})) == 1
    assert len(mp_zoning._rings({"type": "MultiPolygon",
                                 "coordinates": [[[[0, 0]]], [[[1, 1]]]]})) == 2
    assert mp_zoning._rings({"type": "Point", "coordinates": [0, 0]}) == []


def test_clean_parses_html_table_properties():
    props = {"Description": "<table><tr><th>LU_DESC</th><td>RESIDENTIAL</td></tr>"
                            "<tr><th>GPR</th><td>LND</td></tr></table>"}
    assert mp_zoning._clean(props) == {"LU_DESC": "RESIDENTIAL", "GPR": "LND"}


def test_clean_passes_through_flat_properties():
    assert mp_zoning._clean({"LU_DESC": "PARK", "Description": ""}) == {"LU_DESC": "PARK"}


# ----------------------------------------------------------------- comps: cohorts
def _c(area, psf, ym="2025-01", ptype="Terrace", tenure="999 yrs lease commencing from 1879"):
    return {"area_sqft": area, "psf": psf, "price": area * psf, "contract_ym": ym,
            "property_type": ptype, "tenure_raw": tenure, "street": "TEST STREET"}


def test_size_cohorts_separate_the_size_effect():
    """The whole point: small plots clear at a higher land psf. An average would hide it."""
    rows = [_c(1615, 2700), _c(1615, 2900), _c(2200, 2100), _c(2200, 2200)]
    got = comps.size_cohorts(rows)
    small = next(b for b in got if b["lo_sqft"] == 0)
    big = next(b for b in got if b["lo_sqft"] == 1800)
    assert small["n"] == 2 and big["n"] == 2
    assert small["psf_med"] == 2800
    assert big["psf_med"] == 2150
    assert small["psf_med"] > big["psf_med"]


def test_subject_cohort_excludes_other_size_bands():
    """A 1,615 sqft house must not be priced off a 2,200 sqft print."""
    rows = [_c(1615, 2900), _c(1644, 2840), _c(2200, 2100)]
    s = comps.subject_cohort(rows, 1615, tol=0.06)
    assert s["n"] == 2                       # 1615 and 1644 (+1.8%), not 2200 (+36%)
    assert all(r["area_sqft"] < 1800 for r in s["rows"])


def test_subject_cohort_reports_empty_rather_than_widening():
    """No comps in band is a real answer. Silently falling back to the street average is the
    error this module exists to prevent."""
    s = comps.subject_cohort([_c(2200, 2100)], 1615, tol=0.06)
    assert s["n"] == 0
    assert "no comps" in s["note"]


def test_tenure_summary_flags_unanimous_vs_mixed():
    same = [_c(1615, 2700), _c(1615, 2800)]
    assert comps.tenure_summary(same)["unanimous"] is True
    mixed = same + [_c(1615, 2800, tenure="Freehold")]
    assert comps.tenure_summary(mixed)["unanimous"] is False
    assert len(comps.tenure_summary(mixed)["distinct"]) == 2


def test_trend_carries_n_so_thin_years_are_visible():
    rows = [_c(1615, 2000, "2021-03"), _c(1615, 2100, "2021-09"), _c(1615, 2900, "2025-04")]
    t = comps.trend(rows, by="year")
    assert [r["period"] for r in t] == ["2021", "2025"]
    assert t[0]["n"] == 2 and t[1]["n"] == 1
    assert t[0]["psf_med"] == 2050


# ------------------------------------------------------------------- pub_flood
def test_flood_check_matches_a_listed_area():
    d = pub_flood.check("Jalan Besar")
    assert d["on_list"] is True
    assert any("Jalan Besar" in m for m in d["matches"])


def test_flood_check_absence_is_reported_as_near_zero_evidence():
    """`on_list: False` must never read as 'not flood-prone' — the designation covers ~0.03%
    of Singapore, so almost every address is off it, including ones that pond."""
    d = pub_flood.check("SELETAR GREEN WALK")
    assert d["on_list"] is False
    assert "near-zero evidence" in d["evidential_weight"]
    assert "DD-3" in d["evidential_weight"]


def test_flood_list_is_the_whole_designation_not_a_sample():
    assert len(pub_flood.FLOOD_PRONE_NOV_2025) == 36


def test_flood_check_is_name_matching_and_says_so():
    d = pub_flood.check("SELETAR GREEN WALK")
    assert "NAME match" in d["method"]
    assert "not geospatial" in d["method"]


def test_flood_check_survives_a_dead_datagov(monkeypatch):
    """Regression: the national hectares figure is CONTEXT. When data.gov.sg was unreachable
    the verdict string formatted a None pct and raised TypeError, killing the whole DD run
    over a stat that decorates the answer rather than making it."""
    monkeypatch.setattr(pub_flood, "_series_cache", None)
    monkeypatch.setattr(pub_flood, "hectares_series",
                        lambda: (_ for _ in ()).throw(OSError("data.gov.sg down")))
    d = pub_flood.check("SELETAR GREEN WALK")
    assert d["on_list"] is False
    assert d["national_hectares"] is None
    assert "near-zero evidence" in d["evidential_weight"]   # verdict still stands
    d2 = pub_flood.check("Jalan Besar")
    assert d2["on_list"] is True                            # positive path too
