"""Harvest a LANDED STREET's caveat table from Investment Suite (R4a / EXP-0018).

The four existing harvesters all drive a *condo development* screen. Landed has no
project id — the app is ADDRESS-first — so this one drives a different path and a
differently-shaped table, and it is the first harvester that must deal with a table
WIDER than the screen (the reference device was a 2560x1600 tablet where every column
fit; this emulator is a 1080x2400 phone, where a row's cells are never all visible at
once).

Navigation contract (verified 2026-07-17 on emulator-5554, 1080x2400 / density 420):
  Property Analysis -> tap the search bar -> type the STREET name -> tap any address
  result -> [Sale] tab -> window tab (5Y matches the URA API's rolling window) ->
  scope defaults to [Street] -> scroll to "View All (N)" under *Street Transactions*
  -> tap it -> a full-screen "Street Transactions" table opens. Run this script there.

TWO PANELS, ONLY ONE IS CAVEATS — the trap this script exists to avoid:
the Sale screen stacks *Street Transactions* (URA caveats: real Tenure values) ABOVE
*Realtime Agency Data* (Tier-2 agency-reported rows: Tenure renders as "-"). The agency
panel carries dates the caveat panel does not (e.g. Loyang Rise showed 30 Jun 2026 and
10 Jun 2026 there, absent from caveats) — reading "the newest date on the Sale screen"
would have scored IS as FRESHER than URA on Tier-2 asking data. This script only ever
runs inside the expanded caveat table, and `assert_caveat_table()` refuses otherwise.

Row assembly: the "Contract Date" column is FROZEN — measured: its nodes keep byte-identical
y-centres across a horizontal swipe — so each screen is dumped twice (left half: address /
type / tenure; right half: completion / area / psf / price / sale type) and the halves are
joined on the frozen date column's y-band. That join is exact, unlike joining two full
vertical passes on the date text (a street can print twice on one day).

    python harvest_street_sale.py "LOYANG RISE" [--window 5Y]
Output: research/is_street/<slug>_sale.json  (rows + provenance meta)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time

if __package__:
    from . import mbx
else:  # direct script run: python research/lib/<tool>.py
    import mbx

DATE_RE = re.compile(r"^\d\d \w{3} \d{4}$")
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "is_street")

# Cells are classified by FORMAT, never by x-coordinate. Three things defeated coordinate
# snapping here, and this design answers all of them at once:
#   1. hardcoded x-centres are device-specific (both harvest skills warn: "re-derive");
#   2. the horizontal swipe lands on a DIFFERENT offset each time (measured: the area column
#      sat at x=460 on one pass and x=296 on the next), so even a per-device map shifted
#      28/125 rows by one column — tenure parsed as area, the real price pushed off the end
#      and LOST;
#   3. the header row is NOT sticky — it scrolls away after the first screen, so reading the
#      map from the live header only works on screen 0.
# This table's columns have mutually exclusive formats, so a cell says what it is:
#   "150 Loyang Rise" | "Terrace House" | "99 yrs from 01/05/1993" | "1996" | "1,615"
#   | "$1,301" | "$2,100,000" | "Resale"
# psf vs price are both money and are separated by MAGNITUDE — landed psf tops out in the
# low thousands while a landed price starts at ~$500k; the gap is two orders of magnitude.
PSF_MAX = 20_000
# ORDER MATTERS — most specific first. A tenure string ("99 yrs from 01/05/1993") also
# satisfies a loose "<number> <word>" address pattern, so tenure is tested before address;
# the test suite pins this.
CELL = [
    ("tenure", re.compile(r"^(\d+ yrs? from .+|Freehold.*|999.*)$", re.I)),
    ("type", re.compile(r"^(Terrace|Semi-?Detached|Detached|Cluster).*House$", re.I)),
    ("sale_type", re.compile(r"^(Resale|New Sale|Sub[- ]Sale)$", re.I)),
    ("completion", re.compile(r"^(19|20)\d\d$")),
    ("address", re.compile(r"^\d+[A-Z]? [A-Za-z].*$")),
    ("area_sqft", re.compile(r"^\d{1,3}(,\d{3})*(\.\d+)?$")),
]
MONEY = re.compile(r"^\$[\d,]+$")
Y_TOL = 30
DATE_X_MAX = 240          # the frozen date column never leaves the left edge


def classify(text: str) -> str | None:
    """Which column does this cell belong to? Format alone decides."""
    t = (text or "").strip()
    if MONEY.match(t):
        v = int(t[1:].replace(",", ""))
        return "psf" if v <= PSF_MAX else "price"
    for col, pat in CELL:
        if pat.match(t):
            return col
    return None


def _rows_at(nodes: list[dict], want: tuple[str, ...]) -> dict[int, dict]:
    """{date_y: {col: text}} for whatever half of the table is currently visible.

    Keyed by the FROZEN date column's y — measured to be byte-identical across a horizontal
    swipe, which is what makes joining the two halves exact (joining two full vertical passes
    on the date TEXT would collide whenever a street prints twice on one day)."""
    anchors = [n for n in nodes if n["center"] and DATE_RE.match(n["text"] or "")
               and n["center"][0] <= DATE_X_MAX]
    out: dict[int, dict] = {}
    for a in anchors:
        ay = a["center"][1]
        row = {"date": a["text"]}
        for n in nodes:
            if not (n["center"] and n["text"]):
                continue
            nx, ny = n["center"]
            if abs(ny - ay) > Y_TOL or nx <= DATE_X_MAX:
                continue
            col = classify(n["text"])
            if col and col in want:
                row.setdefault(col, n["text"].strip())
        out[ay] = row
    return out


def assert_caveat_table(nodes: list[dict]) -> None:
    """Refuse to harvest anything but the expanded CAVEAT table (see the two-panel trap).

    Guards, in order: the screen must be the full-screen 'Street Transactions' view, and
    its rows must carry real tenure strings — the agency panel renders tenure as '-'."""
    texts = [n["text"] or n["desc"] for n in nodes]
    if not any("Street Transactions" in (t or "") for t in texts):
        raise RuntimeError(
            "not on the expanded 'Street Transactions' table — open the Sale tab, scroll to "
            "'View All (N)' UNDER 'Street Transactions' and tap it. (Do NOT harvest the "
            "'Realtime Agency Data' panel below it: Tier-2 agency rows, not caveats.)")
    if any("Realtime Agency Data" in (t or "") for t in texts):
        raise RuntimeError("the Realtime Agency Data panel is on screen — that is Tier-2 "
                           "agency data, never caveats. Open the caveat table's View All.")
    tenures = [t for t in texts if t and re.match(r"^\d+ yrs from|^Freehold", t)]
    dashes = [n for n in nodes if (n["text"] or "") == "-" and n["center"]
              and n["center"][0] > 900]
    if not tenures and dashes:
        raise RuntimeError("rows show '-' tenure and no lease strings — this looks like the "
                           "agency panel, not the caveat table. Refusing to harvest.")


def _edit_text() -> str:
    for n in mbx.parse(mbx.dump_xml()):
        if n["cls"].endswith("EditText"):
            return n["text"] or ""
    return ""


def _set_search(street: str, tries: int = 3) -> None:
    """Put exactly `street` in the search box, VERIFIED by reading the field back.

    Blind `clear_field` + `type` is not safe here: a residual character survived a clear and
    the app searched for 'ELOYANG RISE', which returns nothing — a typo that would look
    exactly like "this street has no data" and could be mis-scored as a coverage gap."""
    for _ in range(tries):
        cur = _edit_text()
        if cur.strip().upper() == street.upper():
            return
        if cur:
            mbx.sh("shell", "input", "keyevent", "123")           # MOVE_END
            for _ in range(len(cur) + 5):
                mbx.sh("shell", "input", "keyevent", "67")        # DEL, one at a time
            time.sleep(0.6)
        mbx.type_text(street)
        time.sleep(3.0)
    got = _edit_text()
    if got.strip().upper() != street.upper():
        raise RuntimeError(f"search box holds {got!r}, wanted {street!r} — refusing to "
                           f"search on a corrupted query (an empty result would look like "
                           f"'no data for this street').")


def open_street_sale(street: str, window: str = "5Y") -> None:
    """Property Analysis -> search STREET -> first address -> Sale tab -> window.

    Always navigate from the bottom-nav, never from wherever the app happens to be: the
    Sale tab is NOT one screen. Re-entering it via Back can land on a 'Type Summary'
    rendering (aggregate by type + charts) that has NO scope selector and NO Street
    Transactions section at all — the state that silently defeated an earlier attempt to
    'just tap Sale again'. A full walk from Property Analysis is the only reset that is
    known to produce the scoped Street Transactions view.

    5Y is the default window because it is the one that matches the URA API's rolling
    ~5-year pull, which is what EXP-0018 compares against.
    """
    mbx.tap_text("Property Analysis")
    time.sleep(2.5)
    mbx.tap_xy(540, 222)                      # the search bar (top of Property Analysis)
    time.sleep(1.5)
    _set_search(street)
    nodes = mbx.parse(mbx.dump_xml())
    hits = [n for n in nodes if n["center"]
            and re.match(rf"^\d+[A-Z]? {re.escape(street)}\b", (n["text"] or ""), re.I)]
    if not hits:
        raise RuntimeError(f"no address result for {street!r} — check the URA/app spelling "
                           f"(saw: {[n['text'] for n in nodes[:8]]})")
    mbx.tap_xy(*hits[0]["center"])
    time.sleep(4)
    mbx.tap_text("Sale")
    time.sleep(4)
    mbx.tap_text(window)
    time.sleep(3)
    nodes = mbx.parse(mbx.dump_xml())
    if not any((n["text"] or "") == "Street Transactions" for n in nodes):
        # the scope selector defaults to Street; if a previous run left it elsewhere, set it
        if any((n["text"] or "") == "Street" for n in nodes):
            mbx.tap_text("Street")
            time.sleep(3)


def open_caveat_view_all(max_steps: int = 8) -> None:
    """From the Sale tab, open the CAVEAT table's 'View All (N)' — never the agency one.

    `mbx.tap("View All")` is a trap: it taps the FIRST match, and both panels have a
    'View All' footer. Which one is first depends purely on the current scroll offset —
    measured live: the same tap opened 'Street Transactions' at one offset and 'Realtime
    Agency Data' at another (the guard below caught it).

    Two facts make it deterministic. (1) The Sale page's section order is fixed: window
    tabs -> Street Transactions (+footer) -> Realtime Agency Data (+footer) -> Type Summary
    -> charts. So walking DOWN FROM THE TOP, the first 'View All' reached is the caveat one.
    (2) The walk must be gentle: a 600px/500ms swipe is a FLING — it sailed past the whole
    agency section in one step (observed: the page landed on 'Type Summary'), which is why
    an anchor-based search kept missing. 300px over 900ms scrolls without throwing.

    The caller is expected to have just tapped a window tab, which resets the page to top;
    `assert_caveat_table` is the backstop if any of this is ever wrong."""
    for _ in range(max_steps):
        nodes = mbx.parse(mbx.dump_xml())
        va = [n for n in nodes if n["center"] and (n["text"] or "").startswith("View All")]
        if any((n["text"] or "") == "Realtime Agency Data" for n in nodes) and not va:
            raise RuntimeError("scrolled past the Street Transactions footer (its 'View All' "
                               "is above the agency panel) — re-tap the window tab to reset "
                               "the page to the top and retry.")
        if va:
            mbx.tap_xy(*min(va, key=lambda n: n["center"][1])["center"])
            time.sleep(3)
            assert_caveat_table(mbx.parse(mbx.dump_xml()))
            return
        # Measured on this build: 300px/900ms does not scroll at all (below the touch-slop
        # /velocity threshold — the page did not move across 8 attempts), while 600px/500ms
        # flings. 500px/650ms scrolls ~one section per step.
        mbx.swipe_region(540, 1700, 540, 1200, 650)
        time.sleep(1.4)
    raise RuntimeError("could not locate the Street Transactions 'View All (N)' footer — "
                       "is the Sale tab open with the Street scope selected?")


def _h_swipe(to_right: bool, times: int = 1) -> None:
    for _ in range(times):
        if to_right:
            mbx.swipe_region(900, 900, 150, 900, 500)   # reveal right-hand columns
        else:
            mbx.swipe_region(150, 900, 950, 900, 500)   # back to the left edge
        time.sleep(1.0)


def harvest(street: str, max_scrolls: int = 30, stop_after_stale: int = 4) -> dict:
    seen: dict[tuple, dict] = {}
    stale = 0
    for i in range(max_scrolls):
        _h_swipe(to_right=False, times=2)               # idempotent at the left edge
        nodes = mbx.parse(mbx.dump_xml())
        if i == 0:
            assert_caveat_table(nodes)
        left = _rows_at(nodes, ("address", "type", "tenure"))
        _h_swipe(to_right=True, times=2)                # 2: one swipe can stop mid-table
        right = _rows_at(mbx.parse(mbx.dump_xml()),
                         ("area_sqft", "psf", "price", "sale_type"))

        gained = 0
        for y, lrow in left.items():
            rrow = right.get(y)
            if not rrow or rrow["date"] != lrow["date"]:
                continue                                # half-scrolled row: re-read later
            row = {**lrow, **rrow}
            # a row enters the set only when COMPLETE — a partial read must never be
            # persisted as if the missing fields did not exist
            if not all(row.get(c) for c in ("address", "area_sqft", "psf", "price",
                                            "sale_type")):
                continue
            key = (row.get("date"), row.get("address"), row.get("price"))
            if key not in seen:
                gained += 1
            seen[key] = row
        print(f"  screen {i:2}: +{gained} (total {len(seen)})")
        stale = stale + 1 if gained == 0 else 0
        if stale >= stop_after_stale:
            print("  no new rows; stopping")
            break
        _h_swipe(to_right=False, times=2)
        mbx.swipe_region(540, 1900, 540, 800, 600)      # vertical scroll
        time.sleep(1.1)

    rows = list(seen.values())
    return {
        "meta": {
            "source": "investment_suite",
            "screen": "Street Transactions (expanded View All) — CAVEATS, not agency data",
            "street": street,
            "harvested_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "device": f"{mbx.SERIAL} {'x'.join(map(str, mbx.screen_size()))}",
            "n_rows": len(rows),
        },
        "rows": rows,
    }


def save(data: dict, street: str) -> None:
    if not data["rows"]:
        print("no rows harvested — refusing to write an empty file")
        return
    os.makedirs(OUT_DIR, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", street.lower()).strip("_")
    path = os.path.join(OUT_DIR, f"{slug}_sale.json")
    data["rows"].sort(key=lambda r: time.strptime(r["date"], "%d %b %Y"), reverse=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"-> {path}: {len(data['rows'])} rows "
          f"({data['rows'][-1]['date']} .. {data['rows'][0]['date']})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("street")
    ap.add_argument("--max-scrolls", type=int, default=30)
    ap.add_argument("--window", default="5Y")
    ap.add_argument("--here", action="store_true",
                    help="already on the expanded caveat table; skip navigation")
    args = ap.parse_args()
    if not args.here:
        open_street_sale(args.street, args.window)
        open_caveat_view_all()
    save(harvest(args.street, args.max_scrolls), args.street)
