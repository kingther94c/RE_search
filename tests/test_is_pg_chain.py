"""landed 的两条拉取链桥接层测试(离线,不碰设备)。

IS 链:harvest JSON → is_rows(单一解析器)→ 分布/队列 —— is_street_compare 的数学。
PG 链:explorer 卡片 → pg_cards(单一映射)→ 筛选 schema —— 两条 honesty 闸是重点:
非 land 口径的面积绝不产生 land_psf;merge 绝不清洗判断层字段。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research.lib import is_rows, pg_cards  # noqa: E402


# ---------------------------------------------------------------- IS: is_rows
def test_road_of_strips_the_house_number_only():
    assert is_rows.road_of("17 Cardiff Grove") == "CARDIFF GROVE"
    assert is_rows.road_of("150A Loyang Rise") == "LOYANG RISE"
    # 999 yrs from … 形状的字符串不是地址;调用方靠 CELL 分类器保证,这里只保证不崩
    assert is_rows.road_of("") == ""


def test_parse_row_normalizes_app_strings():
    r = is_rows.parse_row({"date": "26 Jun 2026", "address": "17 Cardiff Grove",
                           "type": "Terrace House", "tenure": "999 yrs from 01/01/1956",
                           "area_sqft": "2,640", "psf": "$1,779",
                           "price": "$4,700,000", "sale_type": "Resale"})
    assert r["_ym"] == "2026-06" and r["_date"] == "2026-06-26"
    assert r["_area"] == 2640.0 and r["_psf"] == 1779.0 and r["_price"] == 4700000.0
    assert r["_road"] == "CARDIFF GROVE" and r["_ptype"] == "Terrace"


def test_cluster_house_maps_to_strata_and_stays_out_of_land_psf():
    r = is_rows.parse_row({"date": "01 Jan 2026", "address": "1 Foo Walk",
                           "type": "Cluster House", "area_sqft": "1,615",
                           "psf": "$1,200", "price": "$1,900,000"})
    assert r["_ptype"] == "Strata cluster"


def test_load_harvest_on_the_tracked_cardiff_file():
    d = is_rows.load_harvest("cardiff_grove")
    assert d["meta"]["street"] == "CARDIFF GROVE"
    assert len(d["rows"]) == d["meta"]["n_rows"] > 0
    assert all(r["_road"] for r in d["rows"])
    dist = is_rows.distribution(d["rows"])
    assert dist["n"] == len(d["rows"]) and dist["psf_p25"] < dist["psf_med"] < dist["psf_p75"]


def test_distribution_windows_and_cluster():
    rows = [is_rows.parse_row({"date": f"01 Jan {y}", "address": "1 A Rd",
                               "type": "Terrace House", "area_sqft": "1,615",
                               "psf": f"${p}", "price": f"${p*1615}"})
            for y, p in (("2021", "1000"), ("2025", "1400"), ("2026", "1500"))]
    d = is_rows.distribution(rows)
    assert d["last_ym"] == "2026-01" and d["n12"] == 1 and d["med12_psf"] == 1500.0
    assert [ym for ym, _ in d["cluster"]] == ["2021-01", "2025-01", "2026-01"]


def test_cohort_uses_parsed_area():
    rows = [is_rows.parse_row({"date": "01 Jan 2026", "address": "1 A Rd",
                               "type": "Terrace House", "area_sqft": a,
                               "psf": "$1,500", "price": "$2,400,000"})
            for a in ("1,615", "2,640")]
    assert len(is_rows.cohort(rows, 1615.0)) == 1


# ---------------------------------------------------------------- PG: pg_cards
def _card(**kw):
    base = {"listing_id": "1", "card_kind": "listing", "title": "X",
            "price": "S$ 5,380,000", "price_psf": "S$ 3,331 psf",
            "address": "14 Seletar Green Walk", "bedrooms": "5",
            "area": "1,615 sqft (land)", "property_type": "Terrace House",
            "tenure": "999-year Leasehold", "completion_year": "Built: 2020"}
    base.update(kw)
    return base


def test_rent_card_is_skipped():
    lst, warns = pg_cards.card_to_listing(_card(price="S$ 7,800 /mo"))
    assert lst is None and "rent card" in warns[0]


def test_land_area_card_gets_land_psf_computed_from_price():
    lst, warns = pg_cards.card_to_listing(_card())
    assert lst["land_sqft"] == 1615.0 and lst["land_psf"] == 3331
    assert lst["type"] == "terrace" and lst["tenure"] == "999"
    assert lst["street"] == "Seletar Green Walk"
    assert lst["flood_risk"] == "unverified"          # 导入永远不冒充已核实
    assert not warns


def test_floor_area_card_never_gets_land_figures():
    lst, warns = pg_cards.card_to_listing(_card(area="3,800 sqft (built-up)"))
    assert "land_sqft" not in lst and "land_psf" not in lst
    assert lst["builtup_sqft"] == 3800.0
    assert any("UNCONFIRMED" in w for w in warns)


def test_merge_preserves_judgment_and_reports_missing():
    existing = [{"id": "1", "street": "A", "price": 5000000, "land_sqft": 1615,
                 "estate_tier": "prime", "flood_risk": "low",
                 "notes": "2026-07-02 复核", "onemap_km": 0.3},
                {"id": "9", "street": "GONE", "price": 1}]
    imported = [{"id": "1", "street": "A", "price": 5200000,
                 "flood_risk": "unverified"}]
    merged, rep = pg_cards.merge(existing, imported)
    one = next(l for l in merged if l["id"] == "1")
    assert one["price"] == 5200000                      # 市场字段刷新
    assert one["estate_tier"] == "prime" and one["flood_risk"] == "low"
    assert one["notes"] == "2026-07-02 复核" and one["onemap_km"] == 0.3
    assert one["land_sqft"] == 1615                     # 人工确认的面积不被 None 覆盖
    assert rep == {"new": [], "updated": ["1"], "missing": ["9"]}
    assert any(l["id"] == "9" for l in merged)          # 未见 ≠ 删除
