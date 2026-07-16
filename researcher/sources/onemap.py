"""OneMap (onemap.gov.sg) geocoding + distance checks — a free, official, reproducible
distance figure instead of a portal's "within 1km" badge.

Pure stdlib (urllib). The public search endpoint needs no API key.

    from researcher.sources.onemap import distance_km, ring_check, geocode
    geocode("14 SELETAR GREEN WALK")     # -> {'blk_no': '14', 'road_name': 'SELETAR GREEN WALK', ...}
    distance_km("14 SELETAR GREEN WALK", "ROSYTH SCHOOL")   # -> (km, match_a, match_b)
    ring_check(["14 SELETAR GREEN WALK"], "ROSYTH SCHOOL", limit_km=1.0)

CLI:  python -m researcher.sources.onemap "14 SELETAR GREEN WALK" --anchor "ROSYTH SCHOOL"

THREE TRAPS, all of which have produced silently wrong answers here:

1. SILENT ROAD SUBSTITUTION. The search is fuzzy and never says "no match" — it hands
   back the closest thing it has. "SELETAR ROAD" returns SELETAR AEROSPACE ROAD 1 (3.7km
   away); "YIO CHU KANG ROAD" returns OLD YIO CHU KANG ROAD. A result is not evidence that
   the thing you asked for exists. ALWAYS read `road_name`/`blk_no` back, or call
   geocode(..., expect_road=...) which raises instead of quietly answering another
   question. This is why those fields are returned and not thrown away.

2. THE NAME MASKS THE HOUSE. `match` (OneMap's SEARCHVAL) is the BUILDING/estate name, so
   "14 SELETAR GREEN WALK" reports match='LUXUS HILLS' and looks like a fuzzy estate-level
   hit — but blk_no='14', postal='805248' show it resolved the exact house. Judge
   address-level precision on blk_no + postal, never on `match`.

3. THIS IS NOT MOE's MEASURE. Since the 2022 P1 exercise MOE computes home-school distance
   from the SCHOOL LAND BOUNDARY — the shortest distance from a point on the school's
   boundary to the home — via OneMap's SchoolQuery service. What we compute is haversine
   to the school's geocoded POINT, which is a conservative OVER-estimate (boundary is
   nearer than centre). Fine as a screen and safe when it says "inside"; it is NOT the
   official answer. Near the line, the deciding artifact is OneMap SchoolQuery for the
   exact address, in the relevant registration year (MOE refreshes it annually by June).

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


def geocode(query: str, expect_road: str | None = None) -> dict | None:
    """Best OneMap match, or None if nothing matched.

    Returns {'match', 'blk_no', 'road_name', 'postal', 'lat', 'lon'}. `match` is the
    building NAME and is the wrong field to judge precision by — use blk_no + postal
    (see trap 2 in the module docstring).

    expect_road: assert the match is on exactly this road (case/space-insensitive, but
    EQUALITY not substring — "YIO CHU KANG ROAD" must not be satisfied by OLD YIO CHU
    KANG ROAD, which a substring test happily accepts). Raises ValueError if OneMap
    substituted a different road (trap 1). Pass it whenever a wrong-road answer would be
    worse than no answer — which, for anything that lands in a report, is always.

    Cached; polite to the public API's rate limit (one request ~every 0.6s).
    """
    key = _sanitize(query).upper()
    if key not in _cache:
        q = urllib.parse.quote(key)
        time.sleep(0.6)
        d = _fetch(f"{BASE}?searchVal={q}&returnGeom=Y&getAddrDetails=Y&pageNum=1")
        results = d.get("results") or []
        top = results[0] if results else None
        _cache[key] = None if top is None else {
            "match": top.get("SEARCHVAL", ""),
            "blk_no": top.get("BLK_NO", ""),
            "road_name": top.get("ROAD_NAME", ""),
            "postal": top.get("POSTAL", ""),
            "lat": float(top["LATITUDE"]),
            "lon": float(top["LONGITUDE"]),
        }
    out = _cache[key]
    if expect_road is not None and out is not None:
        want = _sanitize(expect_road).upper().replace(" ", "")
        got = (out["road_name"] or "").upper().replace(" ", "")
        if want != got:
            raise ValueError(
                f"OneMap substituted a different road for {query!r}: matched "
                f"{out['road_name']!r} (postal {out['postal'] or 'NIL'}), expected "
                f"{expect_road!r}. The API is fuzzy and never reports 'no match' — "
                f"it returns the nearest thing it has."
            )
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

    within='margin' when the point is within 150m either side of the limit. Treat
    'margin' as UNDECIDED, not as a near-miss/near-hit: we measure to the anchor's
    geocoded point while MOE measures to the school land BOUNDARY, so inside the
    margin the two methods can disagree. Only OneMap SchoolQuery on the exact address
    settles it (module docstring, trap 3).
    """
    anc = geocode(anchor)
    out = []
    for q in queries:
        g = geocode(q)
        if not anc or not g:
            out.append({"query": q, "match": None, "addr": None, "km": None, "within": None})
            continue
        km = haversine_km(g["lat"], g["lon"], anc["lat"], anc["lon"])
        within = ("yes" if km <= limit_km - 0.15 else
                  "margin" if km <= limit_km + 0.15 else "no")
        # .get: a street-level match legitimately has no blk_no, and OneMap returns "".
        addr = " ".join(x for x in (g.get("blk_no"), g.get("road_name")) if x) or g["match"]
        out.append({"query": q, "match": g["match"], "addr": addr,
                    "postal": g["postal"], "km": round(km, 2), "within": within})
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    anchor = "NANYANG PRIMARY SCHOOL"
    for i, a in enumerate(sys.argv):
        if a == "--anchor" and i + 1 < len(sys.argv):
            anchor = sys.argv[i + 1]
    for row in ring_check(args, anchor):
        # print the resolved address, not just the building name: it is the only way to
        # see that OneMap answered the question you asked (traps 1 and 2).
        print(f"{row['query']:<30} -> {str(row['addr']):<34} "
              f"[{row['postal'] or 'NIL':>6}] {row['km'] if row['km'] is not None else '?':>6} km  "
              f"within-1km: {row['within']}")
    print(f"\nhaversine to {anchor}'s POINT. MOE measures to the school LAND BOUNDARY,")
    print("so this over-estimates. 'margin' = undecided; check OneMap SchoolQuery.")
