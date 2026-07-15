"""URA normalize(): the one raw->clean mapping that needs real-data verification.
These lock the parsing rules against URA's documented PMI_Resi_Transaction schema."""
from researcher.sources.ura import normalize, _contract_ym, _floor_band, _tenure

RAW = [{
    "street": "SOME ROAD", "project": "SOME CONDO", "marketSegment": "RCR",
    "x": "28983.5", "y": "31112.3",
    "transaction": [
        {"area": "100", "floorRange": "06-10", "noOfUnits": "1", "contractDate": "0625",
         "typeOfSale": "3", "price": "2000000", "propertyType": "Condominium",
         "district": "14", "typeOfArea": "Strata",
         "tenure": "99 yrs lease commencing from 2015"},
        {"area": "120", "floorRange": "-", "noOfUnits": "1", "contractDate": "1124",
         "typeOfSale": "1", "price": "3600000", "propertyType": "Detached",
         "district": "14", "typeOfArea": "Land", "tenure": "Freehold"},
        {"area": "bad", "floorRange": "01-05", "contractDate": "0625",
         "price": "1", "propertyType": "Condominium", "typeOfArea": "Strata"},
    ],
}]


def test_flattens_and_computes():
    txs = normalize(RAW)
    assert len(txs) == 2  # the "bad" area row is dropped
    a = txs[0]
    assert a["project"] == "SOME CONDO" and a["market_segment"] == "RCR"
    assert a["contract_ym"] == "2025-06"
    assert a["area_sqft"] == round(100 * 10.7639, 1)
    assert a["psf"] == round(2000000 / (100 * 10.7639), 1)
    assert (a["floor_lo"], a["floor_hi"]) == (6, 10)
    assert a["type_of_sale"] == "Resale"
    assert a["tenure_type"] == "leasehold" and a["lease_start"] == 2015
    assert a["x"] == 28983.5 and a["y"] == 31112.3


def test_landed_and_freehold_row():
    b = normalize(RAW)[1]
    assert b["property_type"] == "Detached" and b["type_of_area"] == "Land"
    assert (b["floor_lo"], b["floor_hi"]) == (None, None)
    assert b["tenure_type"] == "freehold" and b["type_of_sale"] == "New Sale"


def test_contract_ym_parsing():
    assert _contract_ym("0625") == "2025-06"
    assert _contract_ym("1299") == "2099-12"
    assert _contract_ym("1325") is None   # month 13
    assert _contract_ym("") is None


def test_floor_band_and_tenure():
    assert _floor_band("11-15") == (11, 15)
    assert _floor_band("-") == (None, None)
    assert _tenure("Freehold") == ("freehold", None)
    assert _tenure("999 yrs lease commencing from 1885") == ("freehold_equiv", 1885)
    assert _tenure("99 yrs lease commencing from 2018") == ("leasehold", 2018)
