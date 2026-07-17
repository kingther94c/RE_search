"""全岛清单的覆盖测试 —— 这里锁的是一个**假阴性**,不是一个功能。

DD 链原本把 15 所小学 / 8 个 MRT 站硬编码在 dd.py 里(它第一次开发时那个片区的清单)。
换个地址它不报错,它**静默地**说「2.2km 内无小学」——385 LOYANG RISE 的报告就是这么出来的,
而那是假的。假阴性比缺失危险:缺失看得见,假阴性看不见。
"""
from __future__ import annotations

import pytest

amenities = pytest.importorskip("researcher.sources.amenities")


@pytest.fixture(scope="module")
def schools():
    try:
        return amenities.primary_schools()
    except RuntimeError as e:
        pytest.skip(str(e))


@pytest.fixture(scope="module")
def mrt():
    try:
        return amenities.mrt_stations()
    except RuntimeError as e:
        pytest.skip(str(e))


def test_school_list_is_island_wide_not_one_neighbourhood(schools):
    """新加坡有约 180 所招 P1 的学校。清单只要掉回几十所,就说明它又变成某个片区的清单了。"""
    assert len(schools) >= 150, f"只有 {len(schools)} 所 —— 清单不是全岛的"


def test_every_school_has_coordinates(schools):
    assert all(s.get("lat") and s.get("lon") for s in schools)


def test_the_east_is_covered(schools):
    """385 LOYANG RISE 的报告曾说「2.2km 内无小学」。东部必须有学校 —— 这条测试就是那次
    假阴性的锚。"""
    from researcher.sources.onemap import haversine_km
    lat, lon = 1.3705, 103.9702          # 385 Loyang Rise
    near = [s for s in schools if haversine_km(lat, lon, s["lat"], s["lon"]) <= 2.2]
    assert near, "Loyang 2.2km 内应当有小学 —— 假阴性回来了"


def test_the_northeast_still_works(schools):
    """原来那 15 所覆盖的片区不能因为换源而变差(Rosyth 在 Serangoon Garden 附近)。"""
    names = {s["name"].upper() for s in schools}
    assert "ROSYTH SCHOOL" in names
    assert "CHIJ OUR LADY OF GOOD COUNSEL" in names


def test_mrt_list_is_island_wide(mrt):
    """全岛 MRT+LRT 站约 170 个;原清单只有 8 个。"""
    assert len(mrt) >= 100, f"只有 {len(mrt)} 站 —— 清单不是全岛的"
    assert all(s.get("lat") and s.get("lon") for s in mrt)


def test_mrt_covers_both_ends_of_the_island(mrt):
    stations = {s["station"].upper() for s in mrt}
    assert any("PASIR RIS" in s for s in stations)      # 东
    assert any("JURONG EAST" in s for s in stations)    # 西


def test_cache_declares_when_it_was_built(schools):
    """学校会开会关、线路会通车 —— 报告要能印出清单的日期,否则「最近」是无期限的断言。"""
    import re
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", amenities.built_on())
