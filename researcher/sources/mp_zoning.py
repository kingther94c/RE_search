"""URA Master Plan 2025 zoning + Landed Housing Area lookup — free, official, scriptable.

This is the DD-1 planning check done as data instead of as a screenshot of URA SPACE.
Both layers are published by URA on data.gov.sg under the Open Data Licence and need no
account, no key and no login — so a zoning claim in a report can be reproduced by anyone.

    from researcher.sources.mp_zoning import zoning_at, landed_area_at
    zoning_at(1.379985, 103.874095)        # -> {'zone': 'RESIDENTIAL', 'gpr': '1.4', ...}
    landed_area_at(1.379985, 103.874095)   # -> {'type': 'MIXED LANDED', 'envelope': '3-STOREY ...'}

CLI:  python -m researcher.sources.mp_zoning 1.379985 103.874095

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
    (roads and waterbodies are genuinely unzoned — None is a real answer, not a failure)."""
    for f in _layer("land_use")["features"]:
        if _hit(f, lat, lon):
            p = _clean(f.get("properties") or {})
            return {
                "zone": p.get("LU_DESC") or p.get("lu_desc") or p.get("LU_TEXT"),
                "gpr": p.get("GPR") or p.get("gpr"),
                "gpr_num": p.get("GPR_NUM"),
                "updated": p.get("FMEL_UPD_D"),
                "raw": p,
            }
    return None


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
    print("\nindicative layer — not a legal boundary; lot geometry = SLA Certified Plan,")
    print("buildability = a QP on a surveyed plan.")
