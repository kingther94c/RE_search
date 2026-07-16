"""OneMap module: pure-math + parsing tests (network mocked)."""
import pytest

from researcher.sources import onemap


def test_haversine_known_distance():
    # Nanyang Primary (1.320847, 103.807750) to Raffles Place MRT (1.284001, 103.851463)
    km = onemap.haversine_km(1.320847, 103.807750, 1.284001, 103.851463)
    assert 6.0 < km < 7.0  # ~6.3 km


def test_haversine_zero():
    assert onemap.haversine_km(1.3, 103.8, 1.3, 103.8) == 0


def test_sanitize_strips_apostrophes():
    assert onemap._sanitize("KING'S ROAD") == "KINGS ROAD"


def test_ring_check_classification(monkeypatch):
    coords = {
        "ANCHOR": (1.3200, 103.8000),
        "NEAR": (1.3230, 103.8000),      # ~0.33 km -> yes
        "EDGE": (1.3285, 103.8000),      # ~0.95 km -> margin (within 150m of limit)
        "FAR": (1.3350, 103.8000),       # ~1.67 km -> no
        "NOWHERE": None,
    }

    def fake_geocode(q, expect_road=None):
        # Mirror the real geocode's full return shape. A double that drifts from the
        # contract stops testing the caller and starts testing the double.
        c = coords.get(q)
        return {"match": q, "blk_no": "", "road_name": q, "postal": "",
                "lat": c[0], "lon": c[1]} if c else None

    monkeypatch.setattr(onemap, "geocode", fake_geocode)
    rows = onemap.ring_check(["NEAR", "EDGE", "FAR", "NOWHERE"], "ANCHOR", limit_km=1.0)
    assert [r["within"] for r in rows] == ["yes", "margin", "no", None]
    assert rows[0]["km"] == pytest.approx(0.33, abs=0.03)


def test_ring_check_tolerates_geocode_without_address_fields(monkeypatch):
    """A street-level match has no blk_no. ring_check must not hard-require it."""
    def fake_geocode(q, expect_road=None):
        return {"match": q, "lat": 1.32, "lon": 103.80, "postal": ""}

    monkeypatch.setattr(onemap, "geocode", fake_geocode)
    rows = onemap.ring_check(["X"], "ANCHOR")
    assert rows[0]["addr"] == "X"          # falls back to the building name


def test_expect_road_catches_silent_substitution(monkeypatch):
    """OneMap is fuzzy and never says 'no match' — it substitutes. Real cases:
    SELETAR ROAD -> SELETAR AEROSPACE ROAD 1, YIO CHU KANG ROAD -> OLD YIO CHU KANG ROAD.
    The second is why the check is equality, not substring."""
    def fake_fetch(url, tries=4):
        return {"results": [{"SEARCHVAL": "OLD YIO CHU KANG ROAD", "BLK_NO": "",
                             "ROAD_NAME": "OLD YIO CHU KANG ROAD", "POSTAL": "NIL",
                             "LATITUDE": "1.38", "LONGITUDE": "103.87"}]}

    monkeypatch.setattr(onemap, "_fetch", fake_fetch)
    monkeypatch.setattr(onemap.time, "sleep", lambda *_: None)
    onemap._cache.clear()

    with pytest.raises(ValueError, match="substituted a different road"):
        onemap.geocode("YIO CHU KANG ROAD", expect_road="YIO CHU KANG ROAD")

    onemap._cache.clear()
    g = onemap.geocode("OLD YIO CHU KANG ROAD", expect_road="old yio chu kang road")
    assert g["road_name"] == "OLD YIO CHU KANG ROAD"   # exact match, case-insensitive


def test_geocode_returns_address_fields(monkeypatch):
    """blk_no + postal are how you prove a house-level hit: `match` is the estate NAME
    ('LUXUS HILLS' for 14 Seletar Green Walk) and makes an exact hit look fuzzy."""
    def fake_fetch(url, tries=4):
        return {"results": [{"SEARCHVAL": "LUXUS HILLS", "BLK_NO": "14",
                             "ROAD_NAME": "SELETAR GREEN WALK", "POSTAL": "805248",
                             "LATITUDE": "1.379985", "LONGITUDE": "103.874095"}]}

    monkeypatch.setattr(onemap, "_fetch", fake_fetch)
    monkeypatch.setattr(onemap.time, "sleep", lambda *_: None)
    onemap._cache.clear()

    g = onemap.geocode("14 SELETAR GREEN WALK", expect_road="SELETAR GREEN WALK")
    assert g["match"] == "LUXUS HILLS"      # the name alone would look like a fuzzy hit
    assert g["blk_no"] == "14"              # but this proves the exact house
    assert g["postal"] == "805248"
