"""Address in, landed DD out — the whole free/official chain in one call.

    python -m researcher.landed.dd "14 SELETAR GREEN WALK" --slug seletar_green_walk_14
    python -m researcher.landed.dd "14 SELETAR GREEN WALK"           # print, don't write

Writes researcher/landed/<slug>_dd.json, which deliverables/build_landed_dd_report.py renders.

WHAT IT CHAINS (every source free, official, no account except URA's free key):
  onemap      exact address (blk+postal), schools, MRT, amenities, expressways
  mp_zoning   MP2025 zone + landed storey envelope; PLOT AREA off the containing parcel;
              neighbour scan by nearest parcel edge; transect toward anything material
  comps       URA caveats for the street: tenure, land-psf size cohorts, trend, subject cohort
  pub_flood   the flood-list name check, plus how little it means

WHY A TOOL AND NOT A CHECKLIST. Every number here was first produced by hand, and the hand
runs made mistakes a tool does not repeat: rating a `UTILITY` parcel as a substation when its
area said cable box; reading a street "average psf" that mixed two plot-size cohorts; trusting
a OneMap match that had silently substituted a different road. The tool encodes the checks that
caught those. It does NOT encode judgement.

VERIFY IT, DON'T TRUST IT. An agent using this must spot-check the output against the raw
source before putting it in a report — re-run one zoning point, re-read one caveat, confirm the
geocode's blk_no/postal is the actual house. `provenance` on every block tells you where to
look. A tool that is wrong in a way nobody checks is worse than no tool.

WHAT IT DELIBERATELY WILL NOT DO:
  - No valuation. Caveat prices bundle land+building and are not bulk-decomposable into land
    value; the AVM is the L-track engine's job (research/registry/01_roadmap.md).
  - No legal facts. Plot area here is an indicative zoning parcel, not a cadastral lot; owner,
    encumbrances and legal area come from INLIS (DD-2, S$16) — this chain cannot see them.
  - Nothing site-observable. Noise, ponding, light, the neighbour's dog: DD-3.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)

from researcher.landed import comps as comps_mod          # noqa: E402
from researcher.sources import mp_zoning, onemap, pub_flood  # noqa: E402

PRIMARIES = [
    "ROSYTH SCHOOL", "HOUGANG PRIMARY SCHOOL", "YIO CHU KANG PRIMARY SCHOOL",
    "FERNVALE PRIMARY SCHOOL", "XINMIN PRIMARY SCHOOL", "ANDERSON PRIMARY SCHOOL",
    "JING SHAN PRIMARY SCHOOL", "ZHONGHUA PRIMARY SCHOOL", "CHIJ OUR LADY OF GOOD COUNSEL",
    "PEI CHUN PUBLIC SCHOOL", "MARIS STELLA HIGH SCHOOL", "NAN CHIAU PRIMARY SCHOOL",
    "PALM VIEW PRIMARY SCHOOL", "SENGKANG GREEN PRIMARY SCHOOL", "CHIJ OUR LADY OF THE NATIVITY",
]
MRT = ["BUANGKOK MRT STATION", "HOUGANG MRT STATION", "SENGKANG MRT STATION",
       "ANG MO KIO MRT STATION", "YIO CHU KANG MRT STATION", "SERANGOON MRT STATION",
       "KOVAN MRT STATION", "LENTOR MRT STATION"]
AMENITIES = ["GREENWICH V", "THE SELETAR MALL", "MYVILLAGE AT SERANGOON GARDEN",
             "NEX SERANGOON", "HOUGANG MALL", "AMK HUB"]
EXPRESSWAYS = ["TAMPINES EXPRESSWAY", "CENTRAL EXPRESSWAY", "KALLANG PAYA LEBAR EXPRESSWAY",
               "SELETAR EXPRESSWAY", "PAN ISLAND EXPRESSWAY"]

# A zone this close is worth a transect: the label alone has misled before.
TRANSECT_ZONES = {"BUSINESS 1", "BUSINESS 2", "RESERVE SITE", "SPECIAL USE",
                  "TRANSPORT FACILITIES", "UTILITY", "CEMETERY", "HEALTH & MEDICAL CARE",
                  "PLACE OF WORSHIP"}
TRANSECT_WITHIN_M = 400


def _dists(lat: float, lon: float, names: list[str], cap_km: float) -> list[dict]:
    out = []
    for n in names:
        g = onemap.geocode(n)
        if not g:
            continue
        km = onemap.haversine_km(lat, lon, g["lat"], g["lon"])
        if km <= cap_km:
            out.append({"name": n, "km": round(km, 2),
                        "matched": " ".join(x for x in (g["blk_no"], g["road_name"]) if x)
                                   or g["match"],
                        "postal": g["postal"]})
    return sorted(out, key=lambda r: r["km"])


def run(address: str, expect_road: str | None = None) -> dict:
    # 1 — pin the address. Assert the road: OneMap substitutes silently and a wrong-road
    # answer would poison every distance below it.
    geo = onemap.geocode(address, expect_road=expect_road)
    if not geo:
        raise RuntimeError(f"OneMap has no match for {address!r}")
    lat, lon = geo["lat"], geo["lon"]
    street = geo["road_name"]

    # 2 — plot + planning
    plot = mp_zoning.plot_area_at(lat, lon)
    zoning = mp_zoning.zoning_at(lat, lon)
    landed = mp_zoning.landed_area_at(lat, lon)

    # 3 — neighbours, then a transect for anything material and close. Distance + label is
    # what invents risks; area and what lies between are what settle them.
    neighbours = mp_zoning.nearby_zones(lat, lon)
    transects = []
    for nb in neighbours:
        if nb["zone"] in TRANSECT_ZONES and nb["metres"] <= TRANSECT_WITHIN_M:
            t = mp_zoning.transect(lat, lon, nb["bearing_deg"],
                                   out_m=max(120, nb["metres"] + 120), step_m=20)
            steps, prev = [], object()
            for s in t:                      # collapse to transitions — the shape is the point
                key = (s["zone"], s["gpr"])
                if key != prev:
                    steps.append(s)
                    prev = key
            # The ray is aimed at the nearest EDGE point, which often sits on a boundary shared
            # with a road. A small parcel can be missed entirely — then the walk describes the
            # gap but never reaches the thing, and calling it "toward X" would oversell it.
            reaches = any(s["zone"] == nb["zone"] for s in t)
            transects.append({"toward": nb["zone"], "bearing_deg": nb["bearing_deg"],
                              "edge_m": nb["metres"], "steps": steps,
                              "reaches_target": reaches,
                              "note": None if reaches else
                              f"ray never lands in {nb['zone']} within "
                              f"{max(120, nb['metres'] + 120)}m — it is aimed at the nearest edge "
                              f"point, which lies on a shared boundary. The steps still show what "
                              f"separates you from it; they do not confirm arrival."})

    # 4 — comps off official caveats, cohorted to THIS plot's size
    try:
        cmp_ = comps_mod.summarise(street, plot["area_sqft"] if plot and plot["is_landed_zone"]
                                   else None)
    except RuntimeError as e:
        cmp_ = {"error": str(e), "n": 0}

    return {
        "address": address,
        "as_of": date.today().isoformat(),
        "geocode": geo,
        "street": street,
        "plot": plot,
        "zoning": {k: v for k, v in (zoning or {}).items() if k != "raw"},
        "landed_housing_area": {k: v for k, v in (landed or {}).items() if k != "raw"},
        "neighbours": neighbours,
        "transects": transects,
        "schools_primary": _dists(lat, lon, PRIMARIES, 2.2),
        "mrt": _dists(lat, lon, MRT, 4.0),
        "amenities": _dists(lat, lon, AMENITIES, 3.0),
        "expressways": _dists(lat, lon, EXPRESSWAYS, 6.0),
        "comps": cmp_,
        "flood": pub_flood.check(street),
        "provenance": {
            "geocode": "OneMap search API — free, no key. Road asserted.",
            "plot/zoning/neighbours": "URA Master Plan 2025 (gazetted 1 Dec 2025) Land Use + "
                                      "SDCP Landed Housing Area layers via data.gov.sg — free, "
                                      "no key. Indicative, not a legal boundary.",
            "comps": "URA Data Service caveats (free registered key). Landed `area` is LAND "
                     "area. Month granularity; ~5y rolling; caveats lag; landed project names "
                     "anonymised so STREET is the only join key.",
            "flood": "PUB flood-prone list (Nov 2025) by name + data.gov.sg national hectares.",
            "schools/mrt/amenities": "OneMap haversine to the target's POINT. For P1 the "
                                     "official measure is OneMap SchoolQuery (school LAND "
                                     "BOUNDARY to home) — ours over-estimates, so 'inside' is "
                                     "safe and near the line is undecided.",
        },
        "not_covered": [
            "Valuation — caveat prices bundle land+building; no fair value is derivable here.",
            "Legal: owner, encumbrances, legal land area, Certified Plan — INLIS (DD-2, S$16).",
            "Approved plans / unauthorised works — BCA, and SELLER-GATED (owner's signed "
            "authorisation required; a buyer cannot buy them).",
            "Anything site-observable: noise, ponding, light, traffic, condition — DD-3.",
        ],
    }


def _fmt(d: dict) -> str:
    g, p, z, lh = d["geocode"], d["plot"], d["zoning"], d["landed_housing_area"]
    L = [f"{d['address']}  ->  blk {g['blk_no']} {g['road_name']}, S({g['postal']})",
         f"  {g['lat']:.6f}, {g['lon']:.6f}   as of {d['as_of']}", ""]
    if p:
        L.append(f"PLOT      {p['area_sqm']:,.1f} sqm = {p['area_sqft']:,} sqft   "
                 f"[{p['caveat']}]")
    L.append(f"ZONING    {z.get('zone')}  GPR {z.get('gpr')}")
    if lh:
        L.append(f"LANDED    {lh.get('type')}   envelope: {lh.get('envelope')}")
    L.append("")
    L.append("NEIGHBOURS  (nearest parcel edge; read the area before rating anything)")
    for n in d["neighbours"][:12]:
        a = n["area_sqm"]
        a = f"{float(a):>9,.0f} sqm" if a else "        ?"
        L.append(f"  {n['metres']:>5} m  brg {n['bearing_deg']:>5}  {str(n['zone']):<40} "
                 f"GPR {str(n['gpr']):<5}{a}")
    for t in d["transects"]:
        hit = "" if t["reaches_target"] else "  [RAY MISSES IT — see note]"
        L.append(f"\n  transect toward {t['toward']} (brg {t['bearing_deg']}, edge {t['edge_m']}m){hit}:")
        L.append("    " + "  ->  ".join(f"{s['m']}m {s['zone'] or 'unzoned'}" for s in t["steps"]))

    c = d["comps"]
    L.append("")
    if c.get("n"):
        te = c["tenure"]
        L.append(f"COMPS     {c['street']}: {c['n']} landed caveats {c['first_ym']}..{c['last_ym']}")
        L.append(f"  tenure  {'UNANIMOUS ' if te['unanimous'] else 'MIXED '}"
                 + "; ".join(f"{k} (n={v})" for k, v in te["distinct"].items()))
        L.append("  land psf by plot size:")
        for b in c["cohorts"]:
            L.append(f"    {b['band']:<14} n={b['n']:<3} psf {b['psf_min']:>6,} / "
                     f"{b['psf_med']:>6,} / {b['psf_max']:>6,}   med price {b['price_med']:>11,}")
        s = c.get("subject")
        if s and s.get("n"):
            L.append(f"  subject cohort {s['area_sqft']:,.0f} sqft +/-{s['tol']:.0%}: n={s['n']}, "
                     f"land psf {s['psf_min']:,} / {s['psf_med']:,} / {s['psf_max']:,}")
            for r in s["recent"][-4:]:
                L.append(f"    {r['ym']}  ${r['price']:>10,.0f}  {r['area_sqft']:>5,} sqft  "
                         f"${r['psf']:>6,}/psf")
    else:
        # "no caveats on this street" is a claim we cannot make: URA's street is a PARENT
        # label, so a small road is often filed under the estate's main road (EXP-0018 —
        # CARDIFF GROVE's houses sit under ALNWICK ROAD). Report what we know: nothing is
        # filed under THIS NAME. Concluding "no sales here" from that is the error.
        L.append(f"COMPS     none ({c.get('error', 'no URA caveats filed under this street NAME '
                                        'in the ~5y window — URA files small roads under the '
                                        'estate parent road, so check the main road before '
                                        'concluding there were no sales')})")

    f = d["flood"]
    L.append("")
    L.append(f"FLOOD     on PUB list: {f['on_list']}" + (f"  {f['matches']}" if f["matches"] else ""))
    L.append(f"          {f['evidential_weight'][:150]}...")
    L.append("")
    L.append("NOT COVERED BY THIS CHAIN:")
    for n in d["not_covered"]:
        L.append(f"  - {n}")
    return "\n".join(L)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        raise SystemExit(2)
    slug = None
    road = None
    for i, a in enumerate(sys.argv):
        if a == "--slug" and i + 1 < len(sys.argv):
            slug = sys.argv[i + 1]
        if a == "--road" and i + 1 < len(sys.argv):
            road = sys.argv[i + 1]

    d = run(args[0], expect_road=road)
    print(_fmt(d))
    if slug:
        out = os.path.join(HERE, f"{slug}_dd_raw.json")
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        print(f"\n-> {out}")


if __name__ == "__main__":
    main()
