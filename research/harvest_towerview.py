"""Harvest the Tower View per-unit grid (the app's own Est. Val AVM) for a development.

The Tower View tab shows a floor x stack grid; each cell carries the unit's size,
last purchase (PP), the app's **Est. Val** (its AVM), Est. P/L, holding and caveat
count. This is the single most valuable Tier-1 benchmark in the app — harvest ALL
of it, not a hand-copied sample.

Navigation model (measured on the 2560x1600 tablet):
  * optional BLOCK tabs in a row near the top (y≈371) — tap each, and VERIFY the
    grid actually changed (first-unit + size signature) because naive taps can
    silently no-op;
  * the grid scrolls VERTICALLY (more floors) and HORIZONTALLY (more stacks);
    scroll only inside the content region (x≈1280, y 1250→700) — a centre swipe
    with a large fraction pulls down the Android notification shade;
  * stop each axis after 2 stale rounds (no new units parsed).

Usage:  python harvest_towerview.py <slug>
Output: research/<slug>_towerview.json   (one record per unit, deduped)

The parser (`parse_towerview_texts`) is a pure function — offline-testable against
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

_UNIT = re.compile(r"^#(\d{2})-(\d{2})$")


def parse_towerview_texts(texts: list[str], block: str = "?") -> list[dict]:
    """Pure parser: ordered visible texts of a Tower View screen → unit records.

    A cell reads like:  #18-03 / 743 sqft / 07 May 2021 / Est. SSD: Completed /
    PP: $1,500,000 ($2,020 psf) / Est. Val: $1,661,000 ($2,236 psf) /
    Est. P/L: ▲$161,000 ($216 psf) / Holding: 5yrs 1mos / 2 Caveats / - / 3BR
    Fields between cells never repeat, so scan forward until the next unit id.
    """
    units: list[dict] = []
    i = 0
    while i < len(texts):
        m = _UNIT.match(texts[i] or "")
        if not m:
            i += 1
            continue
        rec: dict = {"unit": texts[i], "floor": int(m.group(1)), "stack": m.group(2),
                     "block": block}
        j = i + 1
        while j < len(texts) and not _UNIT.match(texts[j] or ""):
            t = texts[j] or ""
            if t.endswith("sqft") and "sqft" not in rec:
                s = t.replace("sqft", "").replace(",", "").strip()
                if s.replace(".", "").isdigit():
                    rec["sqft"] = float(s)
            elif t.startswith("PP:"):
                rec["pp_raw"] = t
                pm = re.search(r"\$([\d,]+) \(\$([\d,]+) psf\)", t)
                if pm:
                    rec["pp_price"] = int(pm.group(1).replace(",", ""))
                    rec["pp_psf"] = int(pm.group(2).replace(",", ""))
            elif t.startswith("Est. Val:"):
                rec["est_raw"] = t
                em = re.search(r"\$([\d,]+) \(\$([\d,]+) psf\)", t)
                if em:
                    rec["est_val"] = int(em.group(1).replace(",", ""))
                    rec["est_psf"] = int(em.group(2).replace(",", ""))
            elif t.startswith("Est. P/L:"):
                rec["pl_raw"] = t
            elif t.startswith("Holding:"):
                rec["holding"] = t.replace("Holding:", "").strip()
            elif re.match(r"^\d{2} \w{3} \d{4}$", t) and "pp_date" not in rec:
                rec["pp_date"] = t
            elif t.endswith("Caveats") or t.endswith("Caveat"):
                rec["caveats"] = t
            elif re.match(r"^\d(BR|Br)$", t):
                rec["type"] = t.upper()
            j += 1
        _quarantine_misaligned(rec)
        units.append(rec)
        i = j
    return units


def _quarantine_misaligned(rec: dict) -> None:
    """Wide grids interleave neighbouring cells' texts during horizontal
    panning, pairing one unit's sqft with another's PP/Est strings (One Pearl
    Bank: 62/450 rows, caught by a hostile review as price != psf x sqft).
    Each money string carries its own psf, so price/psf = implied sqft — if it
    disagrees with the cell's sqft by >2%, the string belongs to another cell:
    drop those fields and flag the record."""
    sqft = rec.get("sqft")
    if not sqft:
        return
    for prefix in ("pp", "est"):
        price = rec.get(f"{prefix}_price") or rec.get(f"{prefix}_val")
        psf = rec.get(f"{prefix}_psf")
        if not (price and psf):
            continue
        if abs(price / psf - sqft) / sqft > 0.02:
            for k in list(rec):
                if k.startswith(prefix):
                    del rec[k]
            rec["misaligned"] = (rec.get("misaligned", "") + f" {prefix}").strip()


def _sig(units: list[dict]) -> tuple:
    """Grid signature: first two units + sizes (to verify a block/page actually changed)."""
    return tuple((u["unit"], u.get("sqft")) for u in units[:2])


def _grab(block: str) -> list[dict]:
    return parse_towerview_texts(
        [n["text"] for n in mbx.parse(mbx.dump_xml()) if n["text"]], block)


def _scroll_axis(seen: dict, block: str, swipe, max_pages: int = 40,
                 stale_stop: int = 2) -> None:
    stale = 0
    for _ in range(max_pages):
        gained = 0
        for u in _grab(block):
            key = (block, u["unit"])
            if key not in seen:
                gained += 1
                seen[key] = u
            else:
                seen[key] = {**seen[key], **u}  # new fields win (Est. Val is live)
        stale = stale + 1 if gained == 0 else 0
        if stale >= stale_stop:
            return
        swipe()
        time.sleep(1.4)


def harvest(slug: str) -> list[dict]:
    seen: dict[tuple, dict] = {}
    # seed from a previous run so repeated harvests ACCUMULATE coverage on big
    # grids (fields from the new run win — Est. Val is live, fresher is better)
    prev_path = os.path.join(OUT, f"{slug}_towerview.json")
    if os.path.exists(prev_path):
        with open(prev_path, encoding="utf-8") as f:
            for u in json.load(f):
                seen[(u.get("block", "?"), u["unit"])] = u
        print(f"seeded {len(seen)} units from previous run")
    nodes = mbx.parse(mbx.dump_xml())
    labels = [n["text"] for n in nodes if n["text"]]
    if "Tower View" not in labels:
        raise SystemExit("Not on an analysis page — open the development and try again.")
    # block tabs = short numeric labels in a row above the grid (absent for 1-block devs)
    tabs = {n["text"]: n["center"] for n in nodes
            if n["text"].isdigit() and len(n["text"]) <= 3 and n["center"]
            and 300 < n["center"][1] < 460}
    blocks = sorted(tabs) or ["(single)"]
    print(f"blocks: {blocks}")

    down = lambda: mbx.swipe_region(1280, 1250, 1280, 700, 500)    # noqa: E731
    up = lambda: mbx.swipe_region(1280, 700, 1280, 1250, 500)      # noqa: E731
    left = lambda: mbx.swipe_region(1800, 900, 600, 900, 500)      # noqa: E731
    for blk in blocks:
        if blk in tabs:
            before = _sig(_grab(blk))
            mbx.sh("shell", "input", "tap", str(tabs[blk][0]), str(tabs[blk][1]))
            time.sleep(2.5)
            if _sig(_grab(blk)) == before and len(blocks) > 1:
                print(f"  [warn] block {blk}: grid signature unchanged after tap")
        # normalize to the grid's top-left corner first — a mid-grid start
        # makes the leftward serpentine skip every column to its left
        for _ in range(3):
            mbx.swipe_region(600, 900, 1800, 900, 300)   # content right = view left
            time.sleep(0.6)
        for _ in range(4):
            mbx.swipe_region(1280, 700, 1280, 1300, 300)  # content down = view top
            time.sleep(0.6)
        # serpentine: walk the FULL vertical strip at each horizontal position
        # (big grids: a single vertical+horizontal pass leaves whole columns
        # unread — 774-unit One Pearl Bank proved it), alternating down/up so
        # the next column starts where this one ended; stop after 2 columns
        # with no new units.
        h_stale = 0
        for h in range(12):
            before_n = len(seen)
            _scroll_axis(seen, blk, down if h % 2 == 0 else up)
            h_stale = h_stale + 1 if len(seen) == before_n else 0
            if h_stale >= 2:
                break
            left()
            time.sleep(1.4)
        print(f"  block {blk}: {sum(1 for k in seen if k[0] == blk)} units")
    return sorted(seen.values(), key=lambda u: (u["block"], u["stack"], -u["floor"]))


def save(units: list[dict], slug: str) -> None:
    if not units:
        print("no units harvested — refusing to overwrite")
        return
    path = os.path.join(OUT, f"{slug}_towerview.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(units, f, ensure_ascii=False, indent=1)
    with_avm = sum(1 for u in units if "est_psf" in u)
    print(f"saved {len(units)} units ({with_avm} with Est. Val) -> {path}")


if __name__ == "__main__":
    _slug = sys.argv[1] if len(sys.argv) > 1 else "towerview"
    save(harvest(_slug), _slug)
