"""Harvest the Profitability tab (realised buy->sell pairs) for a development.

The tab lists matched buy->sell transactions in TWO sections — "Profitable
Transactions" and "Unprofitable Transactions" — each with a band head
(lowest / average / highest). Every row is a strict 14-field tuple:

  block | level | stack | sqft | buy month-year | buy $psf | buy $price |
  sell full-date | sell $psf | sell $price | profit ±$psf | profit ±$amt |
  holding ("3y 5m 18d") | annualised ("5.69%")

and the Unit-Type column is FROZEN on the right: its values arrive as a
trailing list of "2BR"-style tokens that pair with the visible rows in order
(scroll artifacts can leak stray date fragments into that region — filter to
\\dBR tokens only). Column headers disappear once the list is scrolled, so the
parser detects rows by the 14-field pattern, not by headers.

Why this matters: the SELL legs are one of the three Tier-1 surfaces used to
reconstruct a complete 5Y comp set (Sale table ∪ Profitability sell-legs ∪
Tower View PP) — the Sale table alone lazy-loads AND skips rows. The pairs are
also a repeat-sales trend sample (see reconstruct_comps.fit_time_trend).

Usage:  python harvest_profitability.py <slug>
Output: research/<slug>_profitability.json   {"meta": {...}, "rows": [...]}

Precondition: the app is on the development's Profitability tab with the time
window you want selected (the selected window tab renders right after the
"..." token — recorded in meta.window; pick 5Y for valuation work).
If a "View All (N)" footer is present and the embedded list yielded fewer
rows, the harvester taps it, harvests the expanded list, then Backs out.

The parser (`parse_profitability_texts`) is a pure function — offline-testable
against saved captures.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

import mbx

OUT = os.path.dirname(os.path.abspath(__file__))

_MONEY = re.compile(r"^[▲▼\-−]?\$[\d,]+$")
_SIGNED = re.compile(r"^(?:[▲▼\-−]\$[\d,]+|\$0)$")  # break-even rows print an unsigned $0
_FULLDATE = re.compile(r"^\d{2} \w{3} \d{4}$")
_MONYEAR = re.compile(r"^\w{3} \d{4}$")
_SQFT = re.compile(r"^[\d,]+$")
_HOLD = re.compile(r"^(?=.)(\d+y ?)?(\d+m ?)?(\d+d)?$")
_PCT = re.compile(r"^-?[\d.]+%$")
_TYPE = re.compile(r"^\d(BR|Br)$")
_VIEWALL = re.compile(r"^View All \((\d+)\)$")


def _num(s: str) -> int:
    return int(re.sub(r"[^\d]", "", s))


def _row_at(texts: list[str], i: int) -> dict | None:
    """Validate texts[i:i+14] as one profitability row; None if not a row."""
    t = texts[i : i + 14]
    if len(t) < 14:
        return None
    ok = (
        re.match(r"^\d{1,3}[A-Z]?$", t[0])              # block (can carry a letter: 10A)
        and t[1].isdigit() and 1 <= len(t[1]) <= 2      # level
        and t[2].isdigit() and len(t[2]) == 2           # stack
        and _SQFT.match(t[3])                            # area sqft
        and _MONYEAR.match(t[4])                         # purchase month-year
        and _MONEY.match(t[5]) and _MONEY.match(t[6])    # buy psf / price
        and _FULLDATE.match(t[7])                        # sale full date
        and _MONEY.match(t[8]) and _MONEY.match(t[9])    # sell psf / price
        and _SIGNED.match(t[10]) and _SIGNED.match(t[11])  # profit psf / amt
        and _HOLD.match(t[12])                           # holding period
        and _PCT.match(t[13])                            # annualised
    )
    if not ok:
        return None
    return {
        "block": t[0], "level": int(t[1]), "stack": t[2], "sqft": _num(t[3]),
        "buy_month": t[4], "buy_psf": _num(t[5]), "buy_price": _num(t[6]),
        "sell_date": t[7], "sell_psf": _num(t[8]), "sell_price": _num(t[9]),
        "profit_psf_raw": t[10], "profit_amt_raw": t[11],
        "profit_amt": _num(t[11]) * (-1 if t[11][0] in "▼-−" else 1),
        "holding": t[12], "annualised_pct": float(t[13].rstrip("%")),
    }


def parse_profitability_texts(texts: list[str]) -> dict:
    """Pure parser: ordered visible texts of a Profitability screen →
    {"rows": [...], "meta": {...}}. Rows carry section=profitable|unprofitable
    and, when the frozen Unit-Type column is on screen, a "type" field."""
    rows: list[dict] = []
    meta: dict = {}
    section = "profitable"
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
        elif t == "Unprofitable Transactions":
            section = "unprofitable"
        elif m := _VIEWALL.match(t):
            # a View All footer belongs to the section of the rows ABOVE it; on a
            # scrolled screen the section header may be gone, so trust the last
            # parsed row over the header-tracked state
            sec = rows[-1]["section"] if rows else section
            meta.setdefault("view_all", {})[sec] = int(m.group(1))
        r = _row_at(texts, i)
        if r:
            r["section"] = section
            rows.append(r)
            i += 14
            last_field_idx = i
            continue
        i += 1
    # frozen Unit-Type column: trailing \dBR tokens after the last row, in row
    # order. Pair ONLY on an exact count match — a partial column (row half
    # scrolled off) would misalign every type below it.
    types = [t for t in texts[last_field_idx:] if t and _TYPE.match(t)]
    if types and len(types) == len(rows):
        for r, ty in zip(rows, types):
            r["type"] = ty.upper()
    elif types:
        meta["type_pairing"] = f"skipped ({len(types)} types for {len(rows)} rows)"
    return {"rows": rows, "meta": meta}


def _grab() -> dict:
    return parse_profitability_texts(
        [n["text"] for n in mbx.parse(mbx.dump_xml()) if n["text"]])


def _merge(seen: dict, rows: list[dict]) -> int:
    gained = 0
    for r in rows:
        key = (r["block"], r["level"], r["stack"], r["sell_date"], r["sell_price"])
        if key not in seen:
            gained += 1
            seen[key] = r
        else:  # keep the richer record (e.g. one of them has the frozen type column)
            seen[key] = {**r, **{k: v for k, v in seen[key].items() if v is not None}}
    return gained


def _scroll_harvest(seen: dict, max_scrolls: int = 30, stale_stop: int = 3) -> dict:
    meta: dict = {}
    stale = 0
    for i in range(max_scrolls):
        parsed = _grab()
        meta.update(parsed["meta"])
        gained = _merge(seen, parsed["rows"])
        print(f"scroll {i:2}: +{gained} (total {len(seen)})")
        stale = stale + 1 if gained == 0 else 0
        if stale >= stale_stop:
            break
        mbx.swipe_region(1280, 1250, 1280, 700, 500)
        time.sleep(1.2)
    return meta


def harvest() -> dict:
    labels = [n["text"] for n in mbx.parse(mbx.dump_xml()) if n["text"]]
    if "Profitability" not in labels:
        raise SystemExit(
            "Not on an analysis page — open the development, tap the Profitability "
            "tab and select the window (5Y for valuation), then re-run. "
            "If the app itself won't open, run `python doctor.py` and follow it.")
    seen: dict[tuple, dict] = {}
    meta = _scroll_harvest(seen)

    # expand "View All (N)" if the embedded list held rows back
    expected = sum(meta.get("view_all", {}).values())
    if expected and len(seen) < expected:
        node = mbx.find("View All (")
        if node and node["center"]:
            print(f"expanding View All ({expected} expected, {len(seen)} so far)")
            mbx.sh("shell", "input", "tap", str(node["center"][0]), str(node["center"][1]))
            time.sleep(2.0)
            expanded = _scroll_harvest(seen, max_scrolls=60)
            meta = {**expanded, **meta}
            mbx.back()
            time.sleep(1.5)
    if expected and len(seen) < expected:
        print(f"[warn] harvested {len(seen)} of {expected} advertised pairs — "
              "the tail may be unexpanded; note this as a data gap")
    meta["advertised_total"] = expected or None
    return {"meta": meta, "rows": sorted(
        seen.values(), key=lambda r: (r["section"], r["sell_date"]), reverse=False)}


def save(data: dict, slug: str) -> None:
    if not data["rows"]:
        print("no rows harvested — refusing to overwrite")
        return
    path = os.path.join(OUT, f"{slug}_profitability.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    n = len(data["rows"])
    typed = sum(1 for r in data["rows"] if "type" in r)
    print(f"saved {n} pairs ({typed} with unit type) window={data['meta'].get('window')} -> {path}")


if __name__ == "__main__":
    _slug = sys.argv[1] if len(sys.argv) > 1 else "profitability"
    save(harvest(), _slug)
