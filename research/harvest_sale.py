"""Harvest the full 'Past Transactions' table from the Sale tab.

The table shows ~5-8 rows at a time; swiping the *data* columns scrolls it
(the Contract Date column on the left is frozen). We dump the tree, rebuild
each row by snapping cells to the nearest header column, scroll, and repeat
until no new rows appear.

Usage:  python harvest_sale.py [slug]        (default slug: spottiswoode)
Output: research/<slug>_transactions.json + .csv
Seeds:  captures/<slug>_sale*.json dumps already on disk are ingested first
        (legacy spottiswoode also seeds from the historical 08_/09_/10_ captures).
"""
from __future__ import annotations

import csv
import json
import os
import re
import time

import mbx

DATE_RE = re.compile(r"^\d\d \w{3} \d{4}$")

# header x-centers measured from the live header row
COLUMNS = [
    ("date", 91),
    ("street", 367),
    ("level", 609),
    ("unit", 886),
    ("unit_type", 1201),
    ("area_sqft", 1462),
    ("psf", 1737),
    ("price", 2028),
    ("sale_type", 2311),
]
DATA_COLS = COLUMNS[1:]  # everything except the frozen date column

OUT = os.path.dirname(os.path.abspath(__file__))


def nearest_col(x: int) -> str:
    return min(DATA_COLS, key=lambda c: abs(c[1] - x))[0]


def rows_from_nodes(nodes: list[dict]) -> list[dict]:
    dates = [n for n in nodes if n["center"] and DATE_RE.match(n["text"])]
    rows = []
    for d in dates:
        dy = d["center"][1]
        row = {"date": d["text"]}
        cells = [
            n
            for n in nodes
            if n["center"]
            and n["text"]
            and abs(n["center"][1] - dy) <= 30
            and n["center"][0] > 200
        ]
        for n in cells:
            col = nearest_col(n["center"][0])
            # area/psf/price/level/unit can collide on x if wrapped; keep first
            row.setdefault(col, n["text"])
        rows.append(row)
    return rows


def _ingest(seen: dict, nodes: list[dict]) -> int:
    before = len(seen)
    for r in rows_from_nodes(nodes):
        key = (r.get("date"), r.get("level"), r.get("unit"), r.get("price"))
        seen[key] = r
    return len(seen) - before


def harvest(slug: str = "spottiswoode", max_scrolls: int = 40, stop_after_stale: int = 6) -> list[dict]:
    seen: dict[tuple, dict] = {}
    # 1) recover rows from every Sale capture already on disk for THIS development
    prefixes = (f"{slug}_sale",)
    if slug == "spottiswoode":  # legacy capture naming from the first study
        prefixes += ("08_", "09_", "10_")
    cap_dir = os.path.join(OUT, "captures")
    if os.path.isdir(cap_dir):
        for fn in sorted(os.listdir(cap_dir)):
            if fn.endswith(".json") and fn.startswith(prefixes):
                with open(os.path.join(cap_dir, fn), encoding="utf-8") as f:
                    _ingest(seen, json.load(f))
    print(f"seeded {len(seen)} rows from existing captures")

    # 2) keep scrolling (gentle: short distance, slow = minimal fling)
    stale = 0
    for i in range(max_scrolls):
        gained = _ingest(seen, mbx.parse(mbx.dump_xml()))
        print(f"scroll {i:2}: +{gained} (total {len(seen)})")
        stale = stale + 1 if gained == 0 else 0
        if stale >= stop_after_stale:
            print("no new rows; stopping")
            break
        mbx.swipe_region(1300, 1300, 1300, 860, 450)
        time.sleep(0.85)
    return list(seen.values())


def _collapse_scroll_artifacts(rows: list[dict]) -> list[dict]:
    """During region-scrolls the frozen date column drifts against the data rows
    mid-animation, so one transaction can be keyed under 2-3 neighbouring dates.
    Collapse rows identical in (level, unit, area, psf, price) to a single row —
    genuine same-unit re-trades at the identical price inside one window are
    vanishingly rare; when collapsing, keep the row whose date is most common."""
    from collections import defaultdict
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r.get("level"), r.get("unit"), r.get("area_sqft"),
                r.get("psf"), r.get("price"))].append(r)
    out = []
    for g in groups.values():
        if len(g) > 1:
            print(f"  [dedup] collapsed {len(g)} scroll-artifact rows for "
                  f"L{g[0].get('level')} #{g[0].get('unit')} {g[0].get('price')} "
                  f"(dates: {sorted(set(r.get('date') for r in g))}) — verify the true "
                  f"date on a static re-read of the table top")
        out.append(g[0])
    return out


def save(rows: list[dict], slug: str = "spottiswoode") -> None:
    if not rows:
        # an adb hiccup must never overwrite the committed dataset with nothing
        print("no rows harvested — refusing to overwrite existing output files")
        return
    rows = _collapse_scroll_artifacts(rows)

    # newest-first by date already; sort by date desc for determinism
    def k(r):
        try:
            return time.strptime(r["date"], "%d %b %Y")
        except Exception:
            return time.gmtime(0)

    rows = sorted(rows, key=k, reverse=True)
    fields = [c[0] for c in COLUMNS]
    with open(os.path.join(OUT, f"{slug}_transactions.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUT, f"{slug}_transactions.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"\nsaved {len(rows)} transactions")
    for r in rows:
        print(
            f"  {r.get('date', ''):>11} | L{r.get('level', '?'):>2} #{r.get('unit', '?'):>2} | "
            f"{r.get('unit_type',''):>4} | {r.get('area_sqft',''):>4} sqft | "
            f"{r.get('psf',''):>7} | {r.get('price',''):>11} | {r.get('sale_type','')}"
        )


if __name__ == "__main__":
    import sys
    _slug = sys.argv[1] if len(sys.argv) > 1 else "spottiswoode"
    save(harvest(_slug), _slug)
