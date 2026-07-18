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

if __package__:
    from . import mbx
else:  # direct script run: python research/lib/<tool>.py
    import mbx

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

_TYPE = re.compile(r"^(\d(BR|Br)|-)$")            # unit type can be '-' (not disclosed)
_BAND = re.compile(r"^[\d,]+ - [\d,]+$")
_EXACT = re.compile(r"^[\d,]{3,}$")               # live-data rows carry exact sqft
_PSF = re.compile(r"^\$\d{1,2}(\.\d+)?$")         # '$7.82' but also '$6' (no cents)
_RENT = re.compile(r"^\$[\d,]{3,}$")
_MONYEAR = re.compile(r"^\w{3} \d{4}$")
_FULLDATE = re.compile(r"^\d{2} \w{3} \d{4}$")
_VIEWALL = re.compile(r"^View All \((\d+)\)$")


def _row_at(texts: list[str], i: int) -> dict | None:
    """Validate texts[i:i+5] as one rental row; None if not a row.
    Two row shapes share the layout: Past Rentals (Tier-1 contracts, AREA BAND)
    and realtime agency/live rows (Tier-2 listings, EXACT sqft) — tagged via
    'panel' so the caller can keep the tiers apart."""
    t = texts[i : i + 5]
    if len(t) < 5:
        return None
    ok = (
        t[0] and not t[0].startswith("$") and not _TYPE.match(t[0])
        and not _MONYEAR.match(t[0]) and not t[0][0].isdigit()   # street name
        and _TYPE.match(t[1])                                     # unit type (or '-')
        and (_BAND.match(t[2]) or _EXACT.match(t[2]))             # band | exact sqft
        and _PSF.match(t[3])                                      # $/sqft
        and _RENT.match(t[4])                                     # monthly rent
    )
    if not ok:
        return None
    return {
        "street": t[0],
        "type": t[1].upper() if t[1] != "-" else None,
        "area_band_sqft": t[2],
        "panel": "past" if _BAND.match(t[2]) else "live",
        "psf": float(t[3].lstrip("$").replace(",", "")),
        "monthly_rent": int(re.sub(r"[^\d]", "", t[4])),
    }


def parse_rent_texts(texts: list[str]) -> dict:
    """Pure parser: ordered visible texts of a Rent screen →
    {"rows": [...], "meta": {...}}. Cuts at the trailing aggregate/agency
    panels; live-listing rows inside the list are tagged panel='live'."""
    agency = False
    for marker in ("Realtime Agency Data", "Unit Mix Rentals"):
        if marker in texts:
            texts = texts[: texts.index(marker)]
            agency = True
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
    # frozen Contract-Date column: trailing month-year (contracts) or full-date
    # (live rows) tokens pair with rows in row order; 'live data' badges are
    # noise. Pair ONLY on an exact count match — a partial column (row half
    # scrolled off) would misalign every date below it.
    dates = [t for t in texts[last_field_idx:]
             if t and (_MONYEAR.match(t) or _FULLDATE.match(t))]
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
    live: dict[tuple, dict] = {}
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
            bucket = seen if r["panel"] == "past" else live
            if key not in bucket:
                gained += 1
                bucket[key] = r
        print(f"scroll {i:2}: +{gained} (contracts {len(seen)}, live {len(live)})")
        stale = stale + 1 if gained == 0 else 0
        if stale >= stale_stop:
            break
        mbx.swipe_region(1280, 1250, 1280, 700, 500)
        time.sleep(1.2)
    meta["dedup_note"] = ("rows have no unit identity — genuinely identical contracts "
                          "collapse; on high-volume devs treat counts as DISTINCT combos, "
                          "and read volume from the app band/advertised totals")
    return {"meta": meta, "rows": list(seen.values()),
            "live_rows_tier2": list(live.values())}


def save(data: dict, slug: str) -> None:
    if not data["rows"] and not data.get("live_rows_tier2"):
        print("no rows harvested — refusing to overwrite")
        return
    path = os.path.join(OUT, f"{slug}_rents.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"saved {len(data['rows'])} contracts (+{len(data.get('live_rows_tier2', []))} "
          f"Tier-2 live listings, kept separate) window={data['meta'].get('window')} "
          f"band={data['meta'].get('band', {}).get('avg')} -> {path}")


if __name__ == "__main__":
    _slug = sys.argv[1] if len(sys.argv) > 1 else "rents"
    save(harvest(), _slug)
