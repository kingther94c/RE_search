"""Harvest the Rent tab (recent rental contracts + the app's rent band) for a
development.

Screen anatomy (measured on the 2560x1600 tablet):
  * a band head — 3 monthly-$ values + 3 $psf values labelled
    LOWEST RENT / AVERAGE / HIGHEST RENT — the app's own aggregate over the
    selected window (record it; do NOT recompute it from the visible rows);
  * "Past Rentals" rows, each a strict 5-field tuple:
      street | unit type (2BR) | area band ("500 - 600") | $psf | monthly $rent
    with the Contract-Date column FROZEN on the right — its month-year values
    arrive as a trailing list pairing with the visible rows in order;
  * a "View All (N)" footer and then a **Realtime Agency Data** panel.
    Everything after the "Realtime Agency Data" marker is agency LISTING data
    (Tier-2, asking not contracted) — the parser cuts the text stream there.
    Do NOT auto-tap "View All" here: it sits between the two panels and its
    ownership is ambiguous (the View-All trap).

Rows have no unit numbers, so cross-screen dedup keys on the full tuple —
two genuinely identical contracts in the same month would collapse into one;
the app's own band head + advertised total (meta) keep the aggregate honest.
Scope: this harvests the RECENT contracts (a few screens, stale-stop), which
is what yield analysis needs, plus the app's full-window band. It does not
chase all N contracts.

Usage:  python harvest_rent.py <slug>
Output: research/<slug>_rents.json   {"meta": {...}, "rows": [...]}

Precondition: app on the development's Rent tab, window selected (the selected
window tab renders right after the "..." token — recorded in meta.window).

The parser (`parse_rent_texts`) is a pure function — offline-testable against
saved captures.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

import mbx

OUT = os.path.dirname(os.path.abspath(__file__))

_TYPE = re.compile(r"^\d(BR|Br)$")
_BAND = re.compile(r"^[\d,]+ - [\d,]+$")
_PSF = re.compile(r"^\$[\d.]+$")
_RENT = re.compile(r"^\$[\d,]+$")
_MONYEAR = re.compile(r"^\w{3} \d{4}$")
_VIEWALL = re.compile(r"^View All \((\d+)\)$")


def _row_at(texts: list[str], i: int) -> dict | None:
    """Validate texts[i:i+5] as one Past-Rentals row; None if not a row."""
    t = texts[i : i + 5]
    if len(t) < 5:
        return None
    ok = (
        t[0] and not t[0].startswith("$") and not _TYPE.match(t[0])
        and not _MONYEAR.match(t[0]) and not t[0][0].isdigit()   # street name
        and _TYPE.match(t[1])                                     # unit type
        and _BAND.match(t[2])                                     # area band
        and _PSF.match(t[3]) and "." in t[3]                      # $/sqft has cents
        and _RENT.match(t[4])                                     # monthly rent
    )
    if not ok:
        return None
    return {
        "street": t[0], "type": t[1].upper(), "area_band_sqft": t[2],
        "psf": float(t[3].lstrip("$").replace(",", "")),
        "monthly_rent": int(re.sub(r"[^\d]", "", t[4])),
    }


def parse_rent_texts(texts: list[str]) -> dict:
    """Pure parser: ordered visible texts of a Rent screen →
    {"rows": [...], "meta": {...}}. Cuts at the Realtime Agency Data panel."""
    if "Realtime Agency Data" in texts:
        cut = texts.index("Realtime Agency Data")
        texts, agency = texts[:cut], True
    else:
        agency = False
    rows: list[dict] = []
    meta: dict = {"agency_panel_present": agency}
    last_field_idx = -1
    i = 0
    while i < len(texts):
        t = texts[i] or ""
        if t == "...":
            if i + 1 < len(texts):
                meta["window"] = texts[i + 1]  # selected window tab renders after "..."
            i += 2
            continue
        if t.endswith("Bedrooms"):
            meta["bedrooms_filter"] = t
        elif t == "AVERAGE" and i >= 5 and "band" not in meta:
            # band head: $low $avg $high, $low-psf $avg-psf $high-psf, then labels
            head = texts[max(0, i - 7):i + 2]
            money = [x for x in head if x.startswith("$") and "PSF" not in x]
            psf = [x for x in head if x.endswith("PSF")]
            if len(money) >= 3 and len(psf) >= 3:
                meta["band"] = {"low": money[-3], "avg": money[-2], "high": money[-1],
                                "low_psf": psf[-3], "avg_psf": psf[-2], "high_psf": psf[-1]}
        elif m := _VIEWALL.match(t):
            meta["advertised_total"] = int(m.group(1))
        r = _row_at(texts, i)
        if r:
            rows.append(r)
            i += 5
            last_field_idx = i
            continue
        i += 1
    # frozen Contract-Date column: trailing month-year tokens pair with rows in
    # row order. Pair ONLY on an exact count match — a partial column (row half
    # scrolled off) would misalign every date below it.
    dates = [t for t in texts[last_field_idx:] if t and _MONYEAR.match(t)]
    if dates and len(dates) == len(rows):
        for r, dt in zip(rows, dates):
            r["contract_month"] = dt
    elif dates:
        meta["date_pairing"] = f"skipped ({len(dates)} dates for {len(rows)} rows)"
    return {"rows": rows, "meta": meta}


def _grab() -> dict:
    return parse_rent_texts(
        [n["text"] for n in mbx.parse(mbx.dump_xml()) if n["text"]])


def harvest(max_scrolls: int = 12, stale_stop: int = 3) -> dict:
    labels = [n["text"] for n in mbx.parse(mbx.dump_xml()) if n["text"]]
    if "Rent" not in labels:
        raise SystemExit(
            "Not on an analysis page — open the development, tap the Rent tab and "
            "select the window (5Y default), then re-run. "
            "If the app itself won't open, run `python doctor.py` and follow it.")
    seen: dict[tuple, dict] = {}
    meta: dict = {}
    stale = 0
    for i in range(max_scrolls):
        parsed = _grab()
        for k, v in parsed["meta"].items():
            meta.setdefault(k, v)
        gained = 0
        for r in parsed["rows"]:
            key = (r["street"], r["type"], r["area_band_sqft"], r["psf"],
                   r["monthly_rent"], r.get("contract_month"))
            if key not in seen:
                gained += 1
                seen[key] = r
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
    path = os.path.join(OUT, f"{slug}_rents.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"saved {len(data['rows'])} contracts window={data['meta'].get('window')} "
          f"band={data['meta'].get('band', {}).get('avg')} -> {path}")


if __name__ == "__main__":
    _slug = sys.argv[1] if len(sys.argv) > 1 else "rents"
    save(harvest(), _slug)
