"""URA Master Plan 2025 zoning + Landed Housing Area lookup — free, official, scriptable.

This is the DD-1 planning check done as data instead of as a screenshot of URA SPACE.
Both layers are published by URA on data.gov.sg under the Open Data Licence and need no
account, no key and no login — so a zoning claim in a report can be reproduced by anyone.

    from researcher.sources.mp_zoning import zoning_at, landed_area_at, nearby_zones, transect
    zoning_at(1.379985, 103.874095)        # -> {'zone': 'RESIDENTIAL', 'gpr': 'LND', ...}
    landed_area_at(1.379985, 103.874095)   # -> {'type': 'MIXED LANDED', 'envelope': '3-STOREY ...'}
    nearby_zones(1.379985, 103.874095)     # -> nearest EDGE distance + area + bearing per zone
    transect(1.379985, 103.874095, 185)    # -> what actually lies between you and it

CLI:  python -m researcher.sources.mp_zoning 1.379985 103.874095

nearby_zones + transect are the highest-yield checks: the landed value-killer is usually an
adjacent parcel's zoning, not the house. But a zone LABEL plus a distance invents risks --
always read `area_sqm` and run a transect before rating one. Worked example: at 14 Seletar
Green Walk a `UTILITY` parcel 66m away looks alarming until its area (14.5 sqm) says feeder
pillar; a `BUSINESS 2` parcel at 151m looks fatal until the transect shows ~100m of zoned
park and a road in between.

Datasets (gazetted Master Plan 2025, in force 1 Dec 2025):
  Land Use            d_a8c3546b26712e35021f3a681d0353ae   (~190MB — cached on first use)
  Landed Housing Area d_70a5a4b67d9171dc0db6f6fd259a3215   (SDCP: type + storey envelope)

WHAT THIS DOES NOT SETTLE (keep these visible — they are the DD-2/DD-3 line):
  - The layer is URA's own words "indicative". It is NOT the legal boundary of your lot,
    and a plot near a zone edge cannot be decided from it. Lot geometry = SLA Certified Plan.
  - Zoning says what is permissible in principle on the land. It does NOT say what THIS lot
    can build: setbacks, nett site area after road reserve, sewer corridors, envelope
    interpretation and any waiver are a QP's call on a surveyed plan.
  - "3-STOREY ENVELOPE" is the control for the AREA. Whether a specific house can realise it
    is an architect's massing question, not a lookup.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CACHE = os.path.join(REPO, "research", "mp2025")

POLL = "https://api-open.data.gov.sg/v1/public/api/datasets/{ds}/poll-download"
DATASETS = {
    "land_use": "d_a8c3546b26712e35021f3a681d0353ae",
    "landed_housing_area": "d_70a5a4b67d9171dc0db6f6fd259a3215",
}
_UA = "RE_search/0.1"
SQM_TO_SQFT = 10.7639
_cache: dict[str, dict] = {}


# ------------------------------------------------------------------------------ fetch
def _download(name: str) -> str:
    """Cache the layer locally. data.gov.sg hands out a short-lived presigned S3 URL."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{name}.geojson")
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return path
    req = urllib.request.Request(POLL.format(ds=DATASETS[name]), headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        url = json.loads(r.read())["data"]["url"]
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=300) as r, open(path, "wb") as f:
        f.write(r.read())
    return path


def _layer(name: str) -> dict:
    if name not in _cache:
        with open(_download(name), encoding="utf-8") as f:
            _cache[name] = json.load(f)
    return _cache[name]


# --------------------------------------------------------------------------- geometry
def _rings(geom: dict) -> list[list]:
    """Outer rings of a Polygon/MultiPolygon. Inner rings (holes) are ignored: MP parcels
    are simple in practice, and a hole would only ever make us over-report a hit — which
    the caller sees as a zone that doesn't match the address, not as a silent wrong answer."""
    t, c = geom.get("type"), geom.get("coordinates") or []
    if t == "Polygon":
        return [c[0]] if c else []
    if t == "MultiPolygon":
        return [p[0] for p in c if p]
    return []


def _in_ring(lon: float, lat: float, ring: list) -> bool:
    """Ray casting. Ring coords are [lon, lat, (z)] — extra dims are ignored."""
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        if (y1 > lat) != (y2 > lat):
            xin = (x2 - x1) * (lat - y1) / (y2 - y1) + x1
            if lon < xin:
                inside = not inside
    return inside


def _hit(feature: dict, lat: float, lon: float) -> bool:
    return any(_in_ring(lon, lat, r) for r in _rings(feature.get("geometry") or {}))


# ------------------------------------------------------------------------- properties
def _clean(props: dict) -> dict:
    """MP layers ship attributes as an HTML <table> inside a Description field on some
    vintages, and as flat keys on others. Return flat keys either way."""
    desc = props.get("Description") or ""
    if "<th>" in desc or "<td>" in desc:
        pairs = re.findall(r"<th>(.*?)</th>\s*<td>(.*?)</td>", desc, re.S | re.I)
        out = {k.strip(): re.sub(r"<[^>]+>", "", v).strip() for k, v in pairs}
        if out:
            return out
    return {k: v for k, v in props.items() if k != "Description"}


# ----------------------------------------------------------------------------- lookup
def zoning_at(lat: float, lon: float) -> dict | None:
    """MP2025 land-use zone containing the point, or None if the point is in no parcel
    (roads and waterbodies are genuinely unzoned — None is a real answer, not a failure).

    `area_sqm`/`area_sqft` are the CONTAINING PARCEL's area. In landed areas the layer is cut
    per plot, so for a landed address this is effectively a free, official read of the plot
    size — see plot_area_at().
    """
    for f in _layer("land_use")["features"]:
        if _hit(f, lat, lon):
            p = _clean(f.get("properties") or {})
            area = p.get("SHAPE.AREA") or p.get("SHAPE_Area")
            try:
                area = float(area)
            except (TypeError, ValueError):
                area = None
            return {
                "zone": p.get("LU_DESC") or p.get("lu_desc") or p.get("LU_TEXT"),
                "gpr": p.get("GPR") or p.get("gpr"),
                "gpr_num": p.get("GPR_NUM"),
                "area_sqm": round(area, 1) if area else None,
                "area_sqft": round(area * SQM_TO_SQFT) if area else None,
                "objectid": p.get("OBJECTID"),
                "updated": p.get("FMEL_UPD_D"),
                "raw": p,
            }
    return None


def plot_area_at(lat: float, lon: float) -> dict | None:
    """Plot area for a LANDED address, free and official, from the containing MP2025 parcel.

    In landed housing areas the Land Use layer is cut per plot, so the containing parcel is
    the house's own plot. Verified on Seletar Green Walk: the parcels come out at 150.0 sqm
    (1,615 sqft) for the intermediate terraces and ~200-203 sqm (2,158/2,180 sqft) for the
    wider ones, and those figures match the LAND areas on URA's caveats for the same street
    exactly. Two independent official sources agreeing is why this is usable.

    IT IS STILL NOT THE LEGAL AREA. URA labels the layer indicative; this is a ZONING parcel,
    not a cadastral lot. Use it to pick the comp cohort and sanity-check a listing; confirm
    with INLIS Property Title Information (S$16, DD-2) before offering, and with an SLA
    Certified Plan + surveyor if the boundary is ever contested (DD-3).

    Returns None if the point is not in a zoned parcel, and `is_landed_zone` False if the
    containing parcel is not landed residential — in which case the area is a zoning block,
    NOT a plot, and must not be read as one.
    """
    z = zoning_at(lat, lon)
    if not z or z["area_sqm"] is None:
        return None
    is_landed = (z["zone"] or "").upper() == "RESIDENTIAL" and (z["gpr"] or "").upper() == "LND"
    return {
        "area_sqm": z["area_sqm"],
        "area_sqft": z["area_sqft"],
        "is_landed_zone": is_landed,
        "objectid": z["objectid"],
        "zone": z["zone"],
        "gpr": z["gpr"],
        "caveat": ("indicative zoning parcel, not a cadastral lot — confirm with INLIS PTI"
                   if is_landed else
                   "NOT a landed plot: the containing parcel is a zoning block, not a house's plot"),
    }


def landed_area_at(lat: float, lon: float) -> dict | None:
    """MP2025 SDCP Landed Housing Area at the point: the landed TYPE and the storey
    ENVELOPE control for the area. None = the point is not inside a designated landed
    housing area (which is itself a material finding — different rebuild rules apply)."""
    for f in _layer("landed_housing_area")["features"]:
        if _hit(f, lat, lon):
            p = _clean(f.get("properties") or {})
            return {
                "classification": p.get("CLASSIFCTN"),
                "type": p.get("TYPE"),
                "envelope": p.get("PERM_ENV"),
                "name": p.get("NAME"),
                "updated": p.get("FMEL_UPD_D"),
                "raw": p,
            }
    return None


# ------------------------------------------------------- neighbours (the value-killer)
M_LAT = 110574.0


def _m_lon(lat: float) -> float:
    return 111320.0 * math.cos(math.radians(lat))


def _near_seg(a: tuple, b: tuple) -> tuple[float, tuple]:
    """Distance from the ORIGIN to segment a-b, and the closest point. Inputs are local
    metres with the subject at (0,0), so the origin is the subject."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(ax, ay), (ax, ay)
    t = max(0.0, min(1.0, (-ax * dx - ay * dy) / (dx * dx + dy * dy)))
    px, py = ax + t * dx, ay + t * dy
    return math.hypot(px, py), (px, py)


def nearby_zones(lat: float, lon: float, radius_m: float = 1000.0) -> list[dict]:
    """Nearest parcel EDGE per (zone, gpr) within radius_m, sorted nearest-first.

    Each row: zone, gpr, metres, bearing_deg (0=N, 90=E), area_sqm of that parcel, objectid.

    `metres` is distance to the parcel BOUNDARY. For the zone you are standing in that is the
    distance to your own parcel's edge, not a separation — only rows for zones you are OUTSIDE
    are true separations. `area_sqm` is not decoration: it is what stops you rating a 14 sqm
    cable box as a substation.
    """
    mlon = _m_lon(lat)
    best: dict[tuple, dict] = {}
    for f in _layer("land_use")["features"]:
        rings = _rings(f.get("geometry") or {})
        if not rings:
            continue
        # bbox reject on any vertex — cheap, and a polygon with no vertex near us cannot
        # have an edge near us at these scales.
        if not any(abs(c[1] - lat) * M_LAT < radius_m * 1.5
                   and abs(c[0] - lon) * mlon < radius_m * 1.5
                   for r in rings for c in r):
            continue
        dmin, pmin = 1e9, None
        for r in rings:
            pts = [((c[0] - lon) * mlon, (c[1] - lat) * M_LAT) for c in r]
            for i in range(len(pts)):
                d, p = _near_seg(pts[i], pts[(i + 1) % len(pts)])
                if d < dmin:
                    dmin, pmin = d, p
        if dmin > radius_m:
            continue
        pr = _clean(f.get("properties") or {})
        key = (pr.get("LU_DESC") or pr.get("LU_TEXT") or "?", pr.get("GPR") or "")
        if key not in best or dmin < best[key]["metres"]:
            best[key] = {
                "zone": key[0], "gpr": key[1], "metres": round(dmin),
                "bearing_deg": round((math.degrees(math.atan2(pmin[0], pmin[1])) + 360) % 360, 1),
                "area_sqm": pr.get("SHAPE.AREA"), "objectid": pr.get("OBJECTID"),
            }
    return sorted(best.values(), key=lambda r: r["metres"])


def transect(lat: float, lon: float, bearing_deg: float,
             out_m: float = 400.0, step_m: float = 20.0) -> list[dict]:
    """Walk a straight line on `bearing_deg` and report the zone at each step.

    This is what turns "BUSINESS 2 at 151m" from a verdict into a fact: it tells you whether
    the gap is a zoned park or a fence. Returns [{m, zone, gpr}] with `zone: None` for
    unzoned gaps (roads and water are genuinely unzoned in the layer).
    """
    brg = math.radians(bearing_deg)
    mlon = _m_lon(lat)
    out = []
    for d in range(0, int(out_m) + 1, int(step_m)):
        la = lat + (d * math.cos(brg)) / M_LAT
        lo = lon + (d * math.sin(brg)) / mlon
        z = zoning_at(la, lo)
        out.append({"m": d, "zone": (z or {}).get("zone"), "gpr": (z or {}).get("gpr")})
    return out


def describe(lat: float, lon: float) -> dict:
    return {"lat": lat, "lon": lon,
            "zoning": zoning_at(lat, lon),
            "landed_housing_area": landed_area_at(lat, lon)}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(2)
    la, lo = float(sys.argv[1]), float(sys.argv[2])
    d = describe(la, lo)
    z, lh = d["zoning"], d["landed_housing_area"]
    print(f"point            : {la}, {lo}")
    print(f"MP2025 zone      : {z['zone'] if z else 'NOT IN ANY ZONED PARCEL'}"
          + (f"   GPR {z['gpr']}" if z and z.get("gpr") else ""))
    if lh:
        print(f"landed housing   : {lh['type']}   envelope: {lh['envelope']}")
    else:
        print("landed housing   : NOT in a designated Landed Housing Area")

    print("\nnearest parcel edge per zone within 1km  (bearing 0=N, 90=E)")
    print("  read the parcel area before rating anything: a 14 sqm UTILITY is a cable box.")
    for r in nearby_zones(la, lo):
        a = r["area_sqm"]
        a = f"{float(a):,.0f} sqm" if a not in (None, "") else "?"
        print(f"  {r['metres']:>5} m  brg {r['bearing_deg']:>5}  {str(r['zone']):<40} "
              f"GPR {str(r['gpr']):<5} parcel {a}")

    print("\nindicative layer - not a legal boundary; lot geometry = SLA Certified Plan,")
    print("buildability = a QP on a surveyed plan.")
