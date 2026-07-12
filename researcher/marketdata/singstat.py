"""SingStat TableBuilder fetcher — official URA price/rental index series.

Tables used (both quarterly, official URA data republished by SingStat, no auth):
  M212261  Private Residential Property Price Index by Type (1Q2009=100)
           series: Residential Properties / Landed / Non-Landed, from 1975Q1
  M212311  Rental Index of Residential Properties (1Q2009=100), from ~2004

    python -m researcher.marketdata.singstat          # fetch + persist both
Output: researcher/marketdata/<table>.json  {"title", "series": {name: [[q, v], ...]}}

parse_tabledata() is pure — offline-testable. Quarters normalize to "YYYYQn".
"""
from __future__ import annotations

import json
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0 RE_search/0.1", "Accept": "application/json"}
TABLES = {"M212261": "price_index", "M212311": "rental_index"}


def fetch(table_id: str) -> dict:
    url = f"https://tablebuilder.singstat.gov.sg/api/table/tabledata/{table_id}?limit=5000"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _q(s: str) -> str:
    """'1975 1Q' -> '1975Q1'."""
    m = re.match(r"^(\d{4})\s+(\d)Q$", s.strip())
    if not m:
        raise ValueError(f"unrecognized quarter {s!r}")
    return f"{m.group(1)}Q{m.group(2)}"


def parse_tabledata(raw: dict) -> dict:
    data = raw.get("Data") or {}
    out = {"title": data.get("title", ""), "series": {}}
    for row in data.get("row") or []:
        name = (row.get("rowText") or "?").strip()
        pts = []
        for c in row.get("columns") or []:
            v = c.get("value")
            if v in (None, "", "na", "-"):
                continue
            pts.append([_q(c["key"]), float(v)])
        out["series"][name] = pts
    return out


def main() -> None:
    for tid, slug in TABLES.items():
        parsed = parse_tabledata(fetch(tid))
        parsed["source"] = (f"SingStat TableBuilder {tid} (official URA series), "
                            f"https://tablebuilder.singstat.gov.sg/table/TS/{tid}")
        p = os.path.join(HERE, f"{slug}.json")
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=1)
        spans = {k: f"{v[0][0]}..{v[-1][0]} (n={len(v)})" for k, v in parsed["series"].items()}
        print(f"{tid} -> {p}")
        for k, s in spans.items():
            print(f"   {k}: {s}")


if __name__ == "__main__":
    main()
