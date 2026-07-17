"""Offline tests for the IS landed-street harvester's parser (R4a / EXP-0018).

The UI drive can't be tested offline, but the parse can — and the parse is where the
first version silently corrupted 28 of 125 rows (a one-column shift that swallowed the
real price). These lock the format-based classifier against exactly that.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))

import pytest  # noqa: E402

from harvest_street_sale import _rows_at, assert_caveat_table, classify  # noqa: E402


def _n(text, x, y):
    return {"text": text, "desc": "", "id": "", "full_id": "", "cls": "TextView",
            "clickable": False, "bounds": "", "center": (x, y)}


@pytest.mark.parametrize("text,want", [
    ("150 Loyang Rise", "address"),
    ("2A Cardiff Grove", "address"),
    ("Terrace House", "type"),
    ("Semi-Detached House", "type"),
    ("Detached House", "type"),
    ("99 yrs from 01/05/1993", "tenure"),
    ("Freehold", "tenure"),
    ("1996", "completion"),
    ("1,615", "area_sqft"),
    ("1,645.82", "area_sqft"),
    ("$1,301", "psf"),
    ("$2,100,000", "price"),
    ("Resale", "sale_type"),
    ("New Sale", "sale_type"),
    ("", None),
    ("View All (104)", None),
])
def test_classify(text, want):
    assert classify(text) == want


def test_psf_and_price_split_on_magnitude():
    """The one genuinely ambiguous pair: both are '$...'. Landed psf lives in the low
    thousands, a landed price starts around half a million — never adjacent."""
    assert classify("$1,709") == "psf"          # the dearest Loyang Rise psf on record
    assert classify("$683") == "psf"            # the cheapest
    assert classify("$1,500,000") == "price"    # the cheapest sale on that street
    assert classify("$14,000,000") == "price"


def test_row_assembly_is_offset_independent():
    """The same row, dumped at two DIFFERENT horizontal offsets (measured live: the area
    column sat at x=460 on one pass and x=296 on the next), must parse identically. This
    is what the coordinate-snapping version got wrong."""
    far = [_n("19 Jun 2026", 113, 516), _n("99 yrs from 01/05/1993", 93, 516),
           _n("1995", 254, 516), _n("2,153", 463, 516), _n("$1,231", 658, 516),
           _n("$2,650,000", 876, 516), _n("Resale", 1064, 516)]
    near = [_n("19 Jun 2026", 113, 516), _n("99 yrs from 01/05/1993", 9, 516),
            _n("1,682", 296, 516), _n("$1,379", 490, 516),
            _n("$2,320,000", 708, 516), _n("Resale", 937, 516)]
    want = ("area_sqft", "psf", "price", "sale_type")
    a = _rows_at(far, want)[516]
    assert a == {"date": "19 Jun 2026", "area_sqft": "2,153", "psf": "$1,231",
                 "price": "$2,650,000", "sale_type": "Resale"}
    b = _rows_at(near, want)[516]
    assert b["area_sqft"] == "1,682" and b["price"] == "$2,320,000"


def test_frozen_date_column_is_not_read_as_a_cell():
    """The date column is the join key and sits left of DATE_X_MAX; a tenure string that
    slides under it must not be picked up as a data cell."""
    nodes = [_n("19 Jun 2026", 113, 516), _n("99 yrs from 01/05/1993", 93, 516),
             _n("2,153", 463, 516)]
    row = _rows_at(nodes, ("tenure", "area_sqft"))[516]
    assert "tenure" not in row          # x=93 is inside the frozen column
    assert row["area_sqft"] == "2,153"


def test_rows_only_pair_within_their_y_band():
    nodes = [_n("19 Jun 2026", 113, 516), _n("2,153", 463, 516),
             _n("29 May 2026", 113, 642), _n("1,618", 463, 642)]
    rows = _rows_at(nodes, ("area_sqft",))
    assert rows[516]["area_sqft"] == "2,153"
    assert rows[642]["area_sqft"] == "1,618"


def test_guard_refuses_the_agency_panel():
    """THE trap this harvester exists for: 'Realtime Agency Data' is Tier-2 agency rows
    (tenure renders as '-') carrying dates the caveat table does not have. Harvesting it
    as caveats would score IS as 'fresher than URA' on asking data."""
    agency = [_n("Realtime Agency Data", 351, 211), _n("30 Jun 2026", 113, 516),
              _n("-", 1014, 516)]
    with pytest.raises(RuntimeError, match="Street Transactions"):
        assert_caveat_table(agency)


def test_guard_accepts_the_caveat_table():
    caveat = [_n("Street Transactions", 351, 211), _n("19 Jun 2026", 113, 516),
              _n("99 yrs from 01/05/1993", 1044, 516)]
    assert_caveat_table(caveat)          # must not raise


def test_guard_refuses_dash_tenure_rows_even_if_titled_street_transactions():
    dash = [_n("Street Transactions", 351, 211), _n("30 Jun 2026", 113, 516),
            _n("-", 1014, 516)]
    with pytest.raises(RuntimeError, match="agency"):
        assert_caveat_table(dash)
