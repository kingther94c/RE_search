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

    def fake_geocode(q):
        c = coords.get(q)
        return {"match": q, "lat": c[0], "lon": c[1], "postal": ""} if c else None

    monkeypatch.setattr(onemap, "geocode", fake_geocode)
    rows = onemap.ring_check(["NEAR", "EDGE", "FAR", "NOWHERE"], "ANCHOR", limit_km=1.0)
    assert [r["within"] for r in rows] == ["yes", "margin", "no", None]
    assert rows[0]["km"] == pytest.approx(0.33, abs=0.03)
