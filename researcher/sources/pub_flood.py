"""PUB flood exposure — what the free public sources CAN and cannot tell you about a plot.

    from researcher.sources.pub_flood import check
    check("SELETAR GREEN WALK", "SELETAR")   # -> {'on_list': False, 'evidential_weight': ...}

CLI:  python -m researcher.sources.pub_flood "SELETAR GREEN WALK" SELETAR

READ THIS BEFORE USING THE RESULT. `on_list: False` is very close to NO INFORMATION about a
specific house, and the module returns it that way on purpose:

  - PUB's flood-prone designation is a list of ~36 NAMED LOCATIONS for the whole country. It
    marks known public flooding hotspots; it is not a per-property flood risk assessment.
  - PUB's own national figure: total flood-prone area in Singapore is 23.3 HECTARES (2025),
    down from 27 ha (2022). Singapore is roughly 73,000 ha. So under 0.05% of the country is
    on this designation. Almost every address on the island is "not flood-prone" by it,
    including addresses that pond.
  - There is NO free geospatial flood layer. The data.gov.sg "Flood Prone Areas" dataset is
    the hectares time-series above, not polygons. The list itself is a PDF of road names, so
    matching is by NAME, not geometry — a neighbouring road that floods will not match.

So: use this to catch the loud case (your street IS named), never to clear a plot. Whether a
particular plot ponds is settled on site, in rain, and by asking neighbours — DD-3.

Vintage: list as at Nov 2025; hectares series through 2025. Re-fetch before relying on it:
  https://www.pub.gov.sg/Public/KeyInitiatives/Flood-Resilience/About-Floods
"""
from __future__ import annotations

import json
import sys
import urllib.request

HECTARES_DS = "d_c4aed98f1533eb3a66f65dbb1a30da46"
_UA = "RE_search/0.1"

# PUB, "List of Flood Prone Areas in Singapore (as of Nov 2025)", extracted verbatim.
# 36 entries for the entire country -- that is the whole designation, not a sample.
FLOOD_PRONE_NOV_2025 = [
    "Prince Philip Avenue / Jervois Road",
    "Admiralty Road West (from Sembawang Drive to Dock Road West)",
    "St John's Headquarters at junction of Beach Road and Java Road",
    "Bedok South Rd (slip road to Bedok South Ave 1)",
    "Service road off Changi Road (near Chin Cheng Ave)",
    "Junction of Commonwealth Drive and Commonwealth Ave",
    "CTE (slip road to Moulmein Road)",
    "Derbyshire Road / Cambridge Road / Farrer Park Field",
    "Hong Kah Area",
    "Indus Road (from Havelock Road to Ganges Avenue)",
    "Jalan Benaan Kapal",
    "Jalan Besar Area",
    "Jalan Mashor",
    "Jalan Mat Jambol",
    "Jalan Taman",
    "People's Association HQ at King George's Avenue",
    "Langsat Road Area (from Lor 102 Changi to Lor 106 Changi)",
    "Lorong Buangkok Area",
    "Lorong H Telok Kurau (near canal)",
    "State Land at junction of Alexandra Road and Lower Delta Road",
    "Margaret Drive / Tanglin Road",
    "Meyer Road Area (from Fort Road to Broadrick Road)",
    "Mimosa Walk (near canal)",
    "Mindef's Changi Camp at junction of Changi Village Road and Farnborough Road",
    "Service Road off Mountbatten Rd (near Jalan Seaview)",
    "Junction of Neo Pee Teck Lane and Pasir Panjang Road",
    "State Land at junction of New Upper Changi Road and Tanah Merah Kechil Avenue",
    "Rose Lane",
    "Second Chin Bee Road",
    "Sennett Estate (Siang Kuang Avenue / Puay Hee Avenue / Wan Tho Avenue / Jalan Kemboja "
    "from Siang Kuang Avenue to Lorong Kembang / Mulberry Avenue from Jalan Wangi to Angsana Avenue)",
    "Service road off Tampines Road (near Jalan Teliti)",
    "Junction of Stevens Road and Balmoral Road",
    "South Bridge Road / Upper Hokien Street / Upper Pickering Street",
    "Upper East Coast Road (near Parbury Avenue)",
    "Waterloo Street / Bencoolen Street / Prinsep Street",
    "Former Boys' Brigade HQ at Zion Road",
]
LIST_VINTAGE = "Nov 2025"
SG_LAND_HA = 73_000  # approx; used only to size the designation, not for any calculation


_series_cache: list[dict] | None = None


def hectares_series() -> list[dict]:
    """PUB's national flood-prone area by year, from data.gov.sg. This is what the
    'Flood Prone Areas' dataset actually contains — a CSV of Year,Hectares. Cached per
    process: it is a 4-row national statistic, not worth re-fetching per call."""
    global _series_cache
    if _series_cache is not None:
        return _series_cache
    req = urllib.request.Request(
        f"https://api-open.data.gov.sg/v1/public/api/datasets/{HECTARES_DS}/poll-download",
        headers={"User-Agent": _UA})
    url = json.loads(urllib.request.urlopen(req, timeout=60).read())["data"]["url"]
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    text = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
    rows = []
    for line in text.strip().splitlines()[1:]:
        y, h = line.split(",")[:2]
        rows.append({"year": int(y), "hectares": float(h)})
    _series_cache = rows
    return rows


def check(street: str, *extra_terms: str) -> dict:
    """Name-match a street (and any extra area terms) against the flood-prone list.

    Returns on_list plus the honest weight of that answer. `matches` is fuzzy on purpose --
    read them, don't just trust the boolean.
    """
    terms = [t.strip().upper() for t in (street,) + extra_terms if t and t.strip()]
    matches = [loc for loc in FLOOD_PRONE_NOV_2025
               if any(t in loc.upper() for t in terms)]
    try:
        ha = hectares_series()
        latest = ha[-1] if ha else None
    except Exception:
        ha, latest = [], None

    pct = (latest["hectares"] / SG_LAND_HA * 100) if latest else None
    # The national figure is context, not the finding. If data.gov.sg is unreachable the
    # verdict must still stand on the list itself — a DD run must not die here.
    ha_txt = f"{latest['hectares']} ha" if latest else "~23 ha (last known)"
    pct_txt = f" ({pct:.3f}% of the country)" if pct is not None else ""
    return {
        "terms": terms,
        "on_list": bool(matches),
        "matches": matches,
        "list_vintage": LIST_VINTAGE,
        "list_size": len(FLOOD_PRONE_NOV_2025),
        "national_hectares": latest,
        "national_series": ha,
        "national_pct_of_land": round(pct, 3) if pct else None,
        "method": "NAME match against a PDF list — not geospatial. A flooding road next to "
                  "yours will not match.",
        "evidential_weight": (
            "ON THE LIST — this is a real, named PUB flooding hotspot. Treat as material."
            if matches else
            f"NOT on the list — near-zero evidence for this plot. The designation covers "
            f"{ha_txt} of ~{SG_LAND_HA:,} ha of Singapore{pct_txt} across "
            f"{len(FLOOD_PRONE_NOV_2025)} named locations. Almost every address is 'not on it', "
            f"including ones that pond. Whether THIS plot ponds is a site question (DD-3): "
            f"visit in rain, check plot-vs-road level, ask neighbours."),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    d = check(sys.argv[1], *sys.argv[2:])
    print(f"terms         : {', '.join(d['terms'])}")
    print(f"on PUB list   : {d['on_list']}   (list of {d['list_size']}, {d['list_vintage']})")
    if d["matches"]:
        for m in d["matches"]:
            print(f"   MATCH      : {m}")
    n = d["national_hectares"]
    if n:
        print(f"national      : {n['hectares']} ha flood-prone in {n['year']} "
              f"({d['national_pct_of_land']}% of Singapore's land)")
        print("   series     : " + ", ".join(f"{r['year']}={r['hectares']}ha"
                                             for r in d["national_series"]))
    print(f"\nmethod        : {d['method']}")
    print(f"weight        : {d['evidential_weight']}")
