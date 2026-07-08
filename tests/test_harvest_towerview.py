"""Tower View parser: pure-function tests, incl. a real-capture regression fixture."""
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.modules.setdefault("mbx", type(sys)("mbx"))  # stub the adb harness for offline import
spec = importlib.util.spec_from_file_location(
    "harvest_towerview", os.path.join(ROOT, "research", "harvest_towerview.py"))
htv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(htv)


def test_parses_full_cell():
    texts = ["#18-03", "743 sqft", "07 May 2021", "Est. SSD: Completed",
             "PP: $1,500,000 ($2,020 psf)", "Est. Val: $1,661,000 ($2,236 psf)",
             "Est. P/L: ▲$161,000 ($216 psf)", "Holding: 5yrs 1mos", "2 Caveats",
             "-", "3BR",
             "#17-03", "743 sqft", "Est. Val: $1,660,000 ($2,234 psf)"]
    units = htv.parse_towerview_texts(texts, block="16")
    assert len(units) == 2
    u = units[0]
    assert u["floor"] == 18 and u["stack"] == "03" and u["sqft"] == 743
    assert u["pp_price"] == 1_500_000 and u["pp_psf"] == 2020
    assert u["est_val"] == 1_661_000 and u["est_psf"] == 2236
    assert u["pp_date"] == "07 May 2021" and u["type"] == "3BR"
    assert units[1]["est_psf"] == 2234


def test_cell_without_avm_is_kept():
    units = htv.parse_towerview_texts(["#05-01", "1,130 sqft", "1 Caveats"])
    assert units[0]["sqft"] == 1130 and "est_psf" not in units[0]


def test_noise_between_cells_ignored():
    units = htv.parse_towerview_texts(
        ["UNIT 01", "UNIT 02", "#02-01", "999 sqft", "Est. Val: $2,000,000 ($2,002 psf)",
         "Back", "Market"])
    assert len(units) == 1 and units[0]["est_val"] == 2_000_000


def test_misaligned_cell_fields_are_quarantined():
    # wide-grid horizontal panning interleaves neighbouring cells' texts: this
    # cell claims 431 sqft but its PP string implies $3,560,000/$2,779 = 1,281 sqft
    # (real One Pearl Bank example caught by a hostile review)
    texts = ["#32-14", "431 sqft", "01 Mar 2021",
             "PP: $3,560,000 ($2,779 psf)", "Est. Val: $3,700,000 ($2,888 psf)", "3BR",
             "#02-15", "700 sqft", "22 Jun 2026",
             "PP: $1,626,100 ($2,323 psf)", "Est. Val: $1,664,000 ($2,378 psf)", "2BR"]
    units = htv.parse_towerview_texts(texts)
    bad = next(u for u in units if u["unit"] == "#32-14")
    good = next(u for u in units if u["unit"] == "#02-15")
    assert "pp_price" not in bad and "est_val" not in bad
    assert bad["misaligned"] == "pp est" and bad["sqft"] == 431
    assert good["pp_price"] == 1_626_100 and good["est_psf"] == 2378
    assert "misaligned" not in good


def test_real_gallop_capture_regression():
    cap = os.path.join(ROOT, "research", "captures", "gallop_twr_70_p0.json")
    nodes = json.load(open(cap, encoding="utf-8"))
    units = htv.parse_towerview_texts([n["text"] for n in nodes if n["text"]], "70")
    assert len(units) >= 8                       # block 70 first page shows >= 8 cells
    with_avm = [u for u in units if "est_psf" in u]
    assert with_avm, "no Est. Val parsed from a real capture"
    # the known first cell of block 70: #05-01, 2,691 sqft, Est. Val $6,310,000 ($2,345 psf)
    # (NB the app's Est. Val is LIVE — an earlier same-day capture of this unit showed
    # $6,224,000/$2,313; always pin the fixture to the exact capture file being parsed)
    u = next(u for u in units if u["unit"] == "#05-01")
    assert u["sqft"] == 2691 and u["est_psf"] == 2345 and u["est_val"] == 6_310_000
    assert u["pp_date"] == "20 Nov 2008" and u["pp_price"] == 3_202_290
