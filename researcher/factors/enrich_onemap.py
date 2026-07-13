"""OneMap factor enrichment — geospatial attributes for every panel row.

For each condo project / landed street, computes from official SLA OneMap
geocodes (great-circle km):
  * nearest MRT station (name + km)             — curated full station list
  * popular-primary schools within 1km / 2km    — curated oversubscribed list
  * nearest major park / nature reserve (+km)
  * nearest major mall (+km)                    — daily-convenience proxy
  * coast distance (km to nearest coastal reference point)
  * CCR/RCR/OCR segment from the app's district field (standard URA mapping)

Curated lists are PROXIES with documented limitations: station list excludes
LRT; school list is the market-relevant oversubscribed set, not every school;
mall list covers major/regional malls only. Distances are straight-line, not
walking. All coordinates come from OneMap (official), cached in
researcher/factors/onemap_cache.json so reruns are free.

    python -m researcher.factors.enrich_onemap
Outputs: researcher/factors/panel_condo_enriched.json, panel_landed_enriched.json
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

from researcher.sources import onemap  # noqa: E402

CACHE_PATH = os.path.join(HERE, "onemap_cache.json")

# ── curated reference layers (geocoded via OneMap at run time) ───────────────

MRT_STATIONS = [
    # NSL
    "Jurong East", "Bukit Batok", "Bukit Gombak", "Choa Chu Kang", "Yew Tee",
    "Kranji", "Marsiling", "Woodlands", "Admiralty", "Sembawang", "Canberra",
    "Yishun", "Khatib", "Yio Chu Kang", "Ang Mo Kio", "Bishan", "Braddell",
    "Toa Payoh", "Novena", "Newton", "Orchard", "Somerset", "Dhoby Ghaut",
    "City Hall", "Raffles Place", "Marina Bay", "Marina South Pier",
    # EWL
    "Pasir Ris", "Tampines", "Simei", "Tanah Merah", "Bedok", "Kembangan",
    "Eunos", "Paya Lebar", "Aljunied", "Kallang", "Lavender", "Bugis",
    "Tanjong Pagar", "Outram Park", "Tiong Bahru", "Redhill", "Queenstown",
    "Commonwealth", "Buona Vista", "Dover", "Clementi", "Chinese Garden",
    "Lakeside", "Boon Lay", "Pioneer", "Joo Koon", "Gul Circle", "Tuas Crescent",
    "Tuas West Road", "Tuas Link", "Expo", "Changi Airport",
    # NEL
    "HarbourFront", "Chinatown", "Clarke Quay", "Little India", "Farrer Park",
    "Boon Keng", "Potong Pasir", "Woodleigh", "Serangoon", "Kovan", "Hougang",
    "Buangkok", "Sengkang", "Punggol", "Punggol Coast",
    # CCL (incl. stage 6, opened 2026-07)
    "Bras Basah", "Esplanade", "Promenade", "Nicoll Highway", "Stadium",
    "Mountbatten", "Dakota", "MacPherson", "Tai Seng", "Bartley", "Lorong Chuan",
    "Marymount", "Caldecott", "Botanic Gardens", "Farrer Road", "Holland Village",
    "one-north", "Kent Ridge", "Haw Par Villa", "Pasir Panjang", "Labrador Park",
    "Telok Blangah", "Bayfront", "Keppel", "Cantonment", "Prince Edward Road",
    # DTL
    "Bukit Panjang", "Cashew", "Hillview", "Beauty World", "King Albert Park",
    "Sixth Avenue", "Tan Kah Kee", "Stevens", "Rochor", "Downtown", "Telok Ayer",
    "Fort Canning", "Bencoolen", "Jalan Besar", "Bendemeer", "Geylang Bahru",
    "Mattar", "Ubi", "Kaki Bukit", "Bedok North", "Bedok Reservoir",
    "Tampines West", "Tampines East", "Upper Changi",
    # TEL (through Bayshore, 2024)
    "Woodlands North", "Woodlands South", "Springleaf", "Lentor", "Mayflower",
    "Bright Hill", "Upper Thomson", "Mount Pleasant", "Napier", "Orchard Boulevard",
    "Great World", "Havelock", "Maxwell", "Shenton Way", "Gardens by the Bay",
    "Tanjong Rhu", "Katong Park", "Tanjong Katong", "Marine Parade", "Marine Terrace",
    "Siglap", "Bayshore",
]

POPULAR_PRIMARIES = [
    "Nanyang Primary School", "Raffles Girls' Primary School",
    "Anglo-Chinese School (Junior)", "Anglo-Chinese School (Primary)",
    "Tao Nan School", "CHIJ St Nicholas Girls' School", "Catholic High School",
    "Pei Hwa Presbyterian Primary School", "Henry Park Primary School",
    "Nan Hua Primary School", "Red Swastika School", "St Hilda's Primary School",
    "Kong Hwa School", "Ai Tong School", "Rosyth School", "Rulang Primary School",
    "Methodist Girls' School (Primary)", "Singapore Chinese Girls' Primary School",
    "St Joseph's Institution Junior", "Maris Stella High School",
    "Holy Innocents' Primary School", "Temasek Primary School",
    "Ngee Ann Primary School", "Maha Bodhi School", "Poi Ching School",
    "Gongshang Primary School", "St Andrew's Junior School",
    "Fairfield Methodist School (Primary)", "Anderson Primary School",
    "Chongfu School",
]

MAJOR_PARKS = [
    "Singapore Botanic Gardens", "East Coast Park", "Bishan-Ang Mo Kio Park",
    "MacRitchie Reservoir Park", "Bukit Timah Nature Reserve",
    "Gardens by the Bay", "Fort Canning Park", "Labrador Nature Reserve",
    "West Coast Park", "Pasir Ris Park", "Bedok Reservoir Park",
    "Mount Faber Park", "Telok Blangah Hill Park", "Kent Ridge Park",
    "Pearl's Hill City Park", "Dairy Farm Nature Park", "Zhenghua Nature Park",
    "Punggol Waterway Park", "Sengkang Riverside Park", "Jurong Lake Gardens",
    "Sungei Buloh Wetland Reserve", "Coney Island Park", "Tampines Eco Green",
    "Marina Barrage",
]

MAJOR_MALLS = [
    "ION Orchard", "Ngee Ann City", "Paragon Shopping Centre", "Plaza Singapura",
    "Raffles City Shopping Centre", "Suntec City Mall", "Marina Bay Sands",
    "VivoCity", "Great World City", "Tiong Bahru Plaza", "Chinatown Point",
    "100 AM", "Parkway Parade", "i12 Katong", "Kallang Wave Mall",
    "Paya Lebar Quarter", "KINEX", "Bedok Mall", "Tampines Mall", "Century Square",
    "Jewel Changi Airport", "White Sands", "NEX", "Compass One", "Waterway Point",
    "Hougang Mall", "AMK Hub", "Junction 8", "Thomson Plaza", "Causeway Point",
    "Northpoint City", "Bukit Panjang Plaza", "Hillion Mall", "Beauty World Centre",
    "Jem", "Westgate", "IMM Building", "Clementi Mall", "The Star Vista",
    "HillV2", "The Rail Mall", "Holland Village Shopping Centre",
]

COAST_REFS = [
    "East Coast Park", "Marina Barrage", "Labrador Nature Reserve",
    "West Coast Park", "Pasir Ris Park", "Changi Beach Park",
    "Sembawang Park", "Woodlands Waterfront Park", "Tanjong Rhu",
]

# standard URA market-segment mapping by postal district
CCR_DISTRICTS = {9, 10, 11, 1, 2, 6}          # D1/2/6 core downtown; D4 Sentosa part-CCR (treated RCR here, noted)
RCR_DISTRICTS = {3, 4, 5, 7, 8, 12, 13, 14, 15, 20}


# standard SG postal-sector (first 2 digits) -> postal district
_SECTOR_TO_DISTRICT = {}
for _d, _sectors in {
    1: (1, 2, 3, 4, 5, 6), 2: (7, 8), 3: (14, 15, 16), 4: (9, 10),
    5: (11, 12, 13), 6: (17,), 7: (18, 19), 8: (20, 21), 9: (22, 23),
    10: (24, 25, 26, 27), 11: (28, 29, 30), 12: (31, 32, 33),
    13: (34, 35, 36, 37), 14: (38, 39, 40, 41), 15: (42, 43, 44, 45),
    16: (46, 47, 48), 17: (49, 50, 81), 18: (51, 52), 19: (53, 54, 55, 82),
    20: (56, 57), 21: (58, 59), 22: (60, 61, 62, 63, 64),
    23: (65, 66, 67, 68), 24: (69, 70, 71), 25: (72, 73), 26: (77, 78),
    27: (75, 76), 28: (79, 80),
}.items():
    for _s in _sectors:
        _SECTOR_TO_DISTRICT[_s] = _d


def district_from_postal(postal: str | None) -> int | None:
    p = str(postal or "").strip()
    return _SECTOR_TO_DISTRICT.get(int(p[:2])) if p[:2].isdigit() and len(p) == 6 else None


def segment_from_district(d: str | int | None) -> str | None:
    if d in (None, ""):
        return None
    import re as _re
    m = _re.search(r"D?(\d+)", str(d))
    if not m:
        return None
    n = int(m.group(1))
    return "CCR" if n in CCR_DISTRICTS else "RCR" if n in RCR_DISTRICTS else "OCR"


# ── cached geocoding ─────────────────────────────────────────────────────────

def _load_cache() -> dict:
    if os.path.exists(CACHE_PATH):
        return json.load(open(CACHE_PATH, encoding="utf-8"))
    return {}


def _save_cache(c: dict) -> None:
    json.dump(c, open(CACHE_PATH, "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, indent=0)


def geocode_cached(cache: dict, query: str) -> dict | None:
    k = query.strip().upper()
    if k in cache:
        return cache[k]
    g = onemap.geocode(query)
    cache[k] = g
    return g


ALT_NAMES = {
    "St Hilda's Primary School": "ST HILDA PRIMARY",
    "St Joseph's Institution Junior": "ST JOSEPH INSTITUTION JUNIOR",
    "St Andrew's Junior School": "SAINT ANDREW JUNIOR SCHOOL",
    "Pearl's Hill City Park": "PEARL BANK",              # park sits on Pearl's Hill
    "Paragon Shopping Centre": "PARAGON",
    "i12 Katong": "112 EAST COAST ROAD",                  # i12 Katong's address
    "Holland Village Shopping Centre": "HOLLAND ROAD SHOPPING CENTRE",
    "Pollen & Bleu": "FARRER DRIVE",                      # its street
}


def build_layer(cache: dict, names: list[str], suffix: str = "") -> list[dict]:
    layer = []
    for n in names:
        g = geocode_cached(cache, n + suffix)
        if not g and n in ALT_NAMES:
            g = geocode_cached(cache, ALT_NAMES[n])
        if g:
            layer.append({"name": n, "lat": g["lat"], "lon": g["lon"]})
        else:
            print(f"  [miss] {n + suffix!r} not geocoded")
    return layer


def nearest(lat: float, lon: float, layer: list[dict]) -> dict | None:
    if not layer:
        return None
    best = min(layer, key=lambda p: onemap.haversine_km(lat, lon, p["lat"], p["lon"]))
    return {"name": best["name"],
            "km": round(onemap.haversine_km(lat, lon, best["lat"], best["lon"]), 2)}


def within(lat: float, lon: float, layer: list[dict], km: float) -> list[str]:
    return [p["name"] for p in layer
            if onemap.haversine_km(lat, lon, p["lat"], p["lon"]) <= km]


def enrich_point(lat: float, lon: float, layers: dict) -> dict:
    s1 = within(lat, lon, layers["schools"], 1.0)
    s2 = within(lat, lon, layers["schools"], 2.0)
    coast = nearest(lat, lon, layers["coast"])
    return {"nearest_mrt": nearest(lat, lon, layers["mrt"]),
            "popular_pri_1km": s1, "n_popular_pri_1km": len(s1),
            "n_popular_pri_2km": len(s2),
            "nearest_park": nearest(lat, lon, layers["parks"]),
            "nearest_mall": nearest(lat, lon, layers["malls"]),
            "coast_km": coast["km"] if coast else None}


def main() -> None:
    cache = _load_cache()
    print("building POI layers via OneMap (cached)...")
    layers = {"mrt": build_layer(cache, MRT_STATIONS, " MRT STATION"),
              "schools": build_layer(cache, POPULAR_PRIMARIES),
              "parks": build_layer(cache, MAJOR_PARKS),
              "malls": build_layer(cache, MAJOR_MALLS),
              "coast": build_layer(cache, COAST_REFS)}
    _save_cache(cache)
    print({k: len(v) for k, v in layers.items()})

    condo = json.load(open(os.path.join(HERE, "panel_condo.json"), encoding="utf-8"))
    for r in condo["projects"]:
        g = geocode_cached(cache, r["project"])
        if not g and r["project"] in ALT_NAMES:
            g = geocode_cached(cache, ALT_NAMES[r["project"]])
        if not g:
            r["onemap"] = None
            print(f"  [nogeo] {r['project']}")
            continue
        r["onemap"] = {"match": g["match"], "postal": g.get("postal")}
        r.update(enrich_point(g["lat"], g["lon"], layers))
        d = r.get("district") or district_from_postal(g.get("postal"))
        r["district_no"] = (district_from_postal(g.get("postal"))
                            if not r.get("district") else None) or d
        # the app's Region field is Tier-1 (URA planning-region based) and beats
        # the postal-district heuristic — districts straddle regions (D21 Beauty
        # World is RCR; D2 Spottiswoode side is Bukit Merah = RCR). Review-caught.
        r["segment"] = r.get("region") or segment_from_district(d)
        if r.get("region") and segment_from_district(d) and r["region"] != segment_from_district(d):
            r["segment_note"] = (f"app Region={r['region']}（采用）；邮政区启发式={segment_from_district(d)}")
    _save_cache(cache)
    p1 = os.path.join(HERE, "panel_condo_enriched.json")
    json.dump(condo, open(p1, "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, indent=1)
    print(f"-> {p1}")

    landed = json.load(open(os.path.join(HERE, "panel_landed.json"), encoding="utf-8"))
    STREET_GEO = {"Alnwick (rosyth)": "ALNWICK ROAD",
                  "Frankel Avenue": "FRANKEL AVENUE",
                  "Kingsmead (nanyang)": "KINGSMEAD ROAD",
                  "Nearby (nanyang)": "KINGSMEAD ROAD",
                  "Nearby (rosyth)": "ALNWICK ROAD"}
    for s in landed["streets"]:
        q = STREET_GEO.get(s["street"], s["street"])
        g = geocode_cached(cache, q)
        if not g:
            s["onemap"] = None
            continue
        s["onemap"] = {"match": g["match"], "postal": g.get("postal")}
        s.update(enrich_point(g["lat"], g["lon"], layers))
    _save_cache(cache)
    p2 = os.path.join(HERE, "panel_landed_enriched.json")
    json.dump(landed, open(p2, "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, indent=1)
    print(f"-> {p2}")

    for r in condo["projects"]:
        if r.get("nearest_mrt"):
            print(f"  {r['project']:32s} {(r.get('segment') or '?'):>3} "
                  f"mrt {r['nearest_mrt']['km']:>5.2f} "
                  f"({r['nearest_mrt']['name'][:18]:18s}) pri1k {r['n_popular_pri_1km']} "
                  f"mall {r['nearest_mall']['km']:>5.2f} park {r['nearest_park']['km']:>5.2f} "
                  f"coast {r['coast_km']:>5.2f}")


if __name__ == "__main__":
    main()
