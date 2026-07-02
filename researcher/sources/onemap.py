"""OneMap (onemap.gov.sg) geocoding + distance checks — the authoritative way to
verify a Singapore school-catchment claim instead of trusting a portal's badge.

Pure stdlib (urllib). The public search endpoint needs no API key. Distances are
great-circle (haversine) from the best geocode match; for a STREET query the match
is a reference point on that street (a building/lot), so treat street-level results
as indicative (+/- the street's length) and re-check the exact address before an offer.

    from researcher.sources.onemap import distance_km, ring_check
    distance_km("ALNWICK ROAD", "ROSYTH SCHOOL")            # -> (km, match_a, match_b)
    ring_check(["ALNWICK ROAD", "BRIDPORT AVENUE"], "ROSYTH SCHOOL", limit_km=1.0)

CLI:  python -m researcher.sources.onemap "ALNWICK ROAD" --anchor "ROSYTH SCHOOL"

Gotcha: the search API chokes on apostrophes — "KING'S ROAD" finds nothing while
"KINGS ROAD" works; queries are sanitized here.
"""
from __future__ import annotations

import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://www.onemap.gov.sg/api/common/elastic/search"
_cache: dict[str, dict | None] = {}


def _fetch(url: str, tries: int = 4) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "RE_search/0.1"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < tries - 1:  # public API rate limit
                time.sleep(2.0 * (attempt + 1))
                continue
            raise
    raise RuntimeError("unreachable")


def _sanitize(q: str) -> str:
    return q.replace("'", "").replace("’", "").strip()


def geocode(query: str) -> dict | None:
    """Best OneMap match: {'match', 'lat', 'lon', 'postal'} or None. Cached; polite
    to the public API's rate limit (one request ~every 0.6s)."""
    key = _sanitize(query).upper()
    if key in _cache:
        return _cache[key]
    q = urllib.parse.quote(key)
    time.sleep(0.6)
    d = _fetch(f"{BASE}?searchVal={q}&returnGeom=Y&getAddrDetails=Y&pageNum=1")
    results = d.get("results") or []
    top = results[0] if results else None
    out = None if top is None else {
        "match": top.get("SEARCHVAL", ""),
        "lat": float(top["LATITUDE"]),
        "lon": float(top["LONGITUDE"]),
        "postal": top.get("POSTAL", ""),
    }
    _cache[key] = out
    return out


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = rlat2 - rlat1
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(a))


def distance_km(query: str, anchor: str) -> tuple[float, dict, dict] | None:
    """Great-circle km between the best matches for two queries."""
    a, b = geocode(query), geocode(anchor)
    if not a or not b:
        return None
    return haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]), a, b


def ring_check(queries: list[str], anchor: str, limit_km: float = 1.0) -> list[dict]:
    """Distance of each query point to the anchor, flagged against limit_km.

    within='margin' when the point is inside the limit but within 150m of it —
    a street reference point that close to the boundary cannot decide an exact
    address either way.
    """
    anc = geocode(anchor)
    out = []
    for q in queries:
        g = geocode(q)
        if not anc or not g:
            out.append({"query": q, "match": None, "km": None, "within": None})
            continue
        km = haversine_km(g["lat"], g["lon"], anc["lat"], anc["lon"])
        within = ("yes" if km <= limit_km - 0.15 else
                  "margin" if km <= limit_km + 0.15 else "no")
        out.append({"query": q, "match": g["match"], "km": round(km, 2), "within": within})
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    anchor = "NANYANG PRIMARY SCHOOL"
    for i, a in enumerate(sys.argv):
        if a == "--anchor" and i + 1 < len(sys.argv):
            anchor = sys.argv[i + 1]
    for row in ring_check(args, anchor):
        print(f"{row['query']:<36} -> {str(row['match']):<40} "
              f"{row['km'] if row['km'] is not None else '?':>6} km  within-1km: {row['within']}")
