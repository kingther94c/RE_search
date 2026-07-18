"""Harvest the Nearby Properties table — the cross-section panel multiplier.

One anchor development's Nearby tab yields a row per surrounding project:

  Project | Tenure ("Freehold" / "99 yrs from 24/09/2012") | TOP | Total Units |
  Unit Type ("1, 2, 3") | Size Range | Sales Range ("$1.7M - $3.0M/PSF: $1,753 -
  $2,179") | Sales Volume | Rent Range ("$3,500 - $11,000/PSF: $4.10 - $6.59") |
  Rental Yield ("1.39% - 7.76%/AVG: 2.81%") | Rental Volume

plus a frozen Dist column (anchor row shows 📍, others "78m"/"1.2km") and a
"Radius: N Meters • K Projects" header. The driver tries to WIDEN the radius
(tap the radius control, pick the largest option) before harvesting, so each
anchor multiplies into 10-30 projects' summary stats — current psf range,
yield, tenure, TOP, units — exactly the factor-study cross-section.

Usage:  python harvest_nearby.py <slug>       (app on the Nearby Properties tab)
Output: research/<slug>_nearby.json  {"meta": {...}, "rows": [...]}

parse_nearby_texts() is pure — offline-testable against saved captures.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

if __package__:
    from . import mbx
else:  # direct script run: python research/lib/<tool>.py
    import mbx

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

_TENURE = re.compile(r"^(Freehold|\d{2,4} yrs from \d{2}/\d{2}/\d{4}|\d{2,4} Yrs.*|Leasehold)$", re.I)
_TOP = re.compile(r"^(\d{4}|-)$")
_UNITS = re.compile(r"^[\d,]+$")
_SALES = re.compile(r"^\$[\d,.]+[MK]? - \$[\d,.]+[MK]?\s*/?PSF: \$([\d,]+) - \$([\d,]+)$", re.S)
_RENT = re.compile(r"^\$[\d,]+ - \$[\d,]+\s*/?PSF: \$([\d.]+) - \$([\d.]+)$", re.S)
_YIELD = re.compile(r"^([\d.]+)% - ([\d.]+)%\s*/?AVG: ([\d.]+)%$", re.S)
_DIST = re.compile(r"^([\d,.]+)\s*(m|km)$")
_RADIUS = re.compile(r"^Radius: ([\d,]+) (Meters|KM|Kilometers?) • (\d+) Projects?$")
_VIEWALL = re.compile(r"^View All \((\d+)\)$")


def _num(s) -> int:
    return int(re.sub(r"[^\d]", "", str(s)))


def _tenure_fields(t: str) -> dict:
    tt = t.strip()
    if tt.lower() == "freehold":
        return {"tenure_type": "FH", "lease_start": None}
    m = re.match(r"^(\d{2,4}) yrs from (\d{2}/\d{2}/(\d{4}))", tt, re.I)
    if m:
        return {"tenure_type": f"{m.group(1)}y", "lease_start": int(m.group(3))}
    return {"tenure_type": tt, "lease_start": None}


def _row_at(texts: list[str], i: int) -> dict | None:
    t = [x.replace("\n", " ") if x else "" for x in texts[i : i + 11]]
    if len(t) < 11:
        return None
    ok = (
        t[0] and not t[0].startswith("$") and not _TOP.match(t[0])
        and not _TENURE.match(t[0]) and not _DIST.match(t[0])
        and _TENURE.match(t[1])
        and _TOP.match(t[2])
        and _UNITS.match(t[3])
        and _SALES.match(t[6])
    )
    if not ok:
        return None
    sm = _SALES.match(t[6])
    rm = _RENT.match(t[8])
    ym = _YIELD.match(t[9])
    rec = {"project": t[0], "tenure_raw": t[1], **_tenure_fields(t[1]),
           "top_year": None if t[2] == "-" else int(t[2]),
           "total_units": _num(t[3]), "unit_types": t[4], "size_range_sqft": t[5],
           "psf_low": _num(sm.group(1)), "psf_high": _num(sm.group(2)),
           "sales_range_raw": t[6],
           "sales_volume": _num(t[7]) if _UNITS.match(t[7]) else None,
           "rent_range_raw": t[8] if rm else None,
           "rent_psf_low": float(rm.group(1)) if rm else None,
           "rent_psf_high": float(rm.group(2)) if rm else None,
           "yield_low_pct": float(ym.group(1)) if ym else None,
           "yield_high_pct": float(ym.group(2)) if ym else None,
           "yield_avg_pct": float(ym.group(3)) if ym else None,
           "rental_volume": _num(t[10]) if _UNITS.match(t[10]) else None}
    return rec


def parse_nearby_texts(texts: list[str]) -> dict:
    """Pure parser: ordered visible texts of a Nearby Properties screen →
    {"rows": [...], "meta": {...}} with the frozen Dist column paired on an
    exact count match (anchor row = 📍 = 0m)."""
    rows: list[dict] = []
    meta: dict = {}
    last_field_idx = -1
    i = 0
    while i < len(texts):
        t = (texts[i] or "").replace("\n", " ")
        if m := _RADIUS.match(t):
            meta["radius"] = f"{m.group(1)} {m.group(2)}"
            meta["advertised_projects"] = int(m.group(3))
        elif m := _VIEWALL.match(t):
            meta["view_all"] = int(m.group(1))
        r = _row_at(texts, i)
        if r:
            rows.append(r)
            i += 11
            last_field_idx = i
            continue
        i += 1
    # frozen Dist column: 📍 for the anchor, then metric distances, row order
    tail = [x.replace("\n", " ") for x in texts[last_field_idx:] if x]
    dists: list[float | None] = []
    for x in tail:
        if x.strip() == "📍":
            dists.append(0.0)
        elif m := _DIST.match(x.strip()):
            v = float(m.group(1).replace(",", ""))
            dists.append(v * (1000 if m.group(2) == "km" else 1))
    if dists and len(dists) == len(rows):
        for r, dm in zip(rows, dists):
            r["dist_m"] = dm
    elif dists:
        meta["dist_pairing"] = f"skipped ({len(dists)} dists for {len(rows)} rows)"
    return {"rows": rows, "meta": meta}


def _grab() -> dict:
    return parse_nearby_texts(
        [n["text"] for n in mbx.parse(mbx.dump_xml()) if n["text"]])


def try_widen_radius() -> None:
    """Tap the radius header and pick the largest offered option, if a picker
    opens. If nothing opens, do NOTHING — never press Back on a probe (a blind
    Back exits the development page entirely; cost one navigation on Amber
    Park). Verify any picker actually appeared by looking for option rows."""
    node = mbx.find("Radius:")
    if not node or not node["center"]:
        return
    before = [n["text"] for n in mbx.parse(mbx.dump_xml()) if n["text"]]
    mbx.sh("shell", "input", "tap", str(node["center"][0]), str(node["center"][1]))
    time.sleep(1.5)
    texts = [n["text"] for n in mbx.parse(mbx.dump_xml()) if n["text"]]
    options = [t for t in texts if re.match(r"^[\d,]+ (Meters|KM|Kilometers?)$", t)
               and t not in before]
    if options:
        biggest = max(options, key=lambda t: _num(t) * (1000 if "K" in t.upper() else 1))
        mbx.tap_text(biggest)
        print(f"[radius] -> {biggest}")
        time.sleep(2.5)
    # else: leave the screen alone — the header tap is harmless by itself


def harvest(max_scrolls: int = 25, stale_stop: int = 3) -> dict:
    labels = [n["text"] for n in mbx.parse(mbx.dump_xml()) if n["text"]]
    if "Nearby Properties" not in labels:
        raise SystemExit("Not on an analysis page — open the development, tap "
                         "Nearby Properties, then re-run. If the app won't open, "
                         "run `python doctor.py`.")
    try_widen_radius()
    seen: dict[str, dict] = {}
    meta: dict = {}
    stale = 0
    for i in range(max_scrolls):
        parsed = _grab()
        meta.update(parsed["meta"])
        gained = 0
        for r in parsed["rows"]:
            if r["project"] not in seen:
                gained += 1
                seen[r["project"]] = r
            else:
                seen[r["project"]] = {**seen[r["project"]],
                                      **{k: v for k, v in r.items() if v is not None}}
        print(f"scroll {i:2}: +{gained} (total {len(seen)})")
        stale = stale + 1 if gained == 0 else 0
        if stale >= stale_stop:
            break
        mbx.swipe_region(1280, 1250, 1280, 700, 500)
        time.sleep(1.2)
    return {"meta": meta, "rows": list(seen.values())}


def save(data: dict, slug: str) -> None:
    if not data["rows"]:
        print("no rows harvested — refusing to overwrite")
        return
    path = os.path.join(OUT, f"{slug}_nearby.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"saved {len(data['rows'])} projects radius={data['meta'].get('radius')} -> {path}")


if __name__ == "__main__":
    _slug = sys.argv[1] if len(sys.argv) > 1 else "nearby"
    save(harvest(), _slug)
