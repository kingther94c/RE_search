"""Assemble the factor-study cross-section panels from every Tier-1 surface
on disk — the bridge between raw harvests and the factor model.

Condo panel rows come from:
  * research/*_nearby.json        (harvest_nearby.py — psf range, yield, tenure,
                                   TOP, units, dist from anchor)
  * research/captures/<slug>_info.json   (anchor Property Info: region/district/
                                   subtown/plot ratio/land size)
  * research/tier1_comps.json     (prior study: 6 projects' info + sale bands)
  * researcher/legacy/valuation/*_digest.json   (deep studies: fitted trends, yields)

Landed panel rows (one per ADDRESS transaction) come from:
  * research/tier1_landed_*.json  (street transaction files)
  * research/captures/frankel_street_*.json (PP-panel shape) and
    frankel_hist_*/nearbyscope captures (8-col txn shape)

    python research/build_factor_panel.py
Outputs:
  researcher/factors/panel_condo.json   one row per project
  researcher/factors/panel_landed.json  street groups with per-address trades

Pure parsers, offline; no adb needed.
"""
from __future__ import annotations

import json
import os
import re
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.dirname(HERE)
DATA = os.path.join(RESEARCH, "data")
CAP = os.path.join(RESEARCH, "captures")
FACTORS = os.path.join(os.path.dirname(RESEARCH), "researcher", "factors")
VALUATION = os.path.join(os.path.dirname(RESEARCH), "researcher", "legacy", "valuation")

_ADDR = re.compile(r"^\d+[A-Z]? [A-Z' ]{3,}$")          # '23 FRANKEL AVENUE'
_PP = re.compile(r"PP: \$([\d,]+) \(\$([\d,]+) psf\)")
_DATE = re.compile(r"^\d{2} \w{3} \d{4}$")
_MONEY = re.compile(r"^\$[\d,]+$")


def _texts(path: str) -> list[str]:
    nodes = json.load(open(path, encoding="utf-8"))
    return [n["text"] for n in nodes if n.get("text")]


def _num(s) -> float:
    return float(re.sub(r"[^\d.]", "", str(s)))


# ── parsers ──────────────────────────────────────────────────────────────────

def parse_info_texts(texts: list[str]) -> dict:
    """'Type:' 'Condominium' 'Region:' 'RCR' ... -> {'type': ..., 'region': ...}"""
    out = {}
    keys = {"Type:": "type", "Region:": "region", "District:": "district",
            "Subtown:": "subtown", "TOP:": "top", "Tenure:": "tenure",
            "Land Size:": "land_size", "GFA:": "gfa", "Plot Ratio:": "plot_ratio",
            "Total Units:": "total_units", "Developer:": "developer"}
    for i, t in enumerate(texts):
        if t in keys and i + 1 < len(texts):
            out[keys[t]] = texts[i + 1]
    return out


def parse_landed_pp_texts(texts: list[str], street: str = "?") -> list[dict]:
    """Street-scope PP panel (landed Tower View): ADDRESS | type | tenure |
    land sqft | date | Est. SSD | PP: $X ($Y psf) | Holding | N Caveats."""
    rows = []
    i = 0
    while i < len(texts):
        t = (texts[i] or "").strip()
        if not _ADDR.match(t):
            i += 1
            continue
        rec = {"address": t.title(), "street": street}
        j = i + 1
        while j < len(texts) and not _ADDR.match((texts[j] or "").strip()):
            x = (texts[j] or "").strip()
            if x in ("Detached House", "Semi-Detached House", "Terrace House"):
                rec["type"] = x
            elif x in ("Freehold",) or re.match(r"^\d{2,4} yrs", x, re.I):
                rec["tenure"] = x
            elif re.match(r"^[\d,.]+ sqft$", x):
                rec["land_sqft"] = _num(x)
            elif _DATE.match(x):
                rec.setdefault("pp_date", x)
            elif m := _PP.search(x):
                rec["pp_price"] = int(m.group(1).replace(",", ""))
                rec["pp_psf"] = int(m.group(2).replace(",", ""))
            elif x.startswith("Holding:"):
                rec["holding"] = x.replace("Holding:", "").strip()
            j += 1
        if "pp_price" in rec:
            rows.append(rec)
        i = j
    return rows


def parse_band_head(texts: list[str], label: str = "LOWEST SALE") -> dict | None:
    """The app's own low/avg/high band above a table: 3 $ values + 3 $PSF values
    before the LOWEST/AVERAGE/HIGHEST labels."""
    if label not in texts:
        return None
    i = texts.index(label)
    head = [t.replace("\n", " ").strip() for t in texts[max(0, i - 7):i]]
    money = [t for t in head if t.startswith("$") and "PSF" not in t]
    psf = [t for t in head if t.endswith("PSF")]
    if len(money) >= 3 and len(psf) >= 3:
        return {"low": money[-3], "avg": money[-2], "high": money[-1],
                "low_psf": int(_num(psf[-3])), "avg_psf": int(_num(psf[-2])),
                "high_psf": int(_num(psf[-1]))}
    return None


def parse_landed_txn_texts(texts: list[str], street: str = "?") -> list[dict]:
    """8-col street/history table: Address | Type | Tenure | TOP | Area | PSF |
    Price | Sale Type, with a frozen Contract Date column trailing."""
    rows, i, last = [], 0, -1
    while i < len(texts):
        t = [(x or "").replace("\n", " ").strip() for x in texts[i : i + 8]]
        if len(t) < 8:
            break
        ok = (_ADDR.match(t[0].upper())
              and t[1] in ("Detached House", "Semi-Detached House", "Terrace House")
              and (t[2] == "Freehold" or re.match(r"^\d{2,4} yrs", t[2], re.I) or t[2] == "-")
              and re.match(r"^(\d{4}|-|0)$", t[3])
              and re.match(r"^[\d,.]+$", t[4])
              and (t[5].startswith("$") or t[5] == "-")
              and _MONEY.match(t[6]))
        if ok:
            rows.append({"address": t[0].title(), "street": street, "type": t[1],
                         "tenure": t[2], "top": t[3], "area_sqft": _num(t[4]),
                         "psf": None if t[5] == "-" else int(_num(t[5])),
                         "price": int(_num(t[6])), "sale_type": t[7]})
            i += 8
            last = i
            continue
        i += 1
    dates = [x for x in texts[last:] if x and _DATE.match(x.strip())]
    if dates and len(dates) == len(rows):
        for r, d in zip(rows, dates):
            r["date"] = d
    return rows


# ── assembly ─────────────────────────────────────────────────────────────────

CONDO_ANCHORS = ["amberpark", "treasure", "dairyfarm", "sengkanggrand", "parcesta",
                 "onepearl", "spottiswoode", "gallop"]


def assemble_condo() -> dict:
    panel: dict[str, dict] = {}

    def merge(name: str, rec: dict) -> None:
        key = name.strip().lower()
        panel.setdefault(key, {"project": name.strip()})
        panel[key].update({k: v for k, v in rec.items() if v is not None})

    # 1) nearby tables
    for slug in CONDO_ANCHORS:
        p = os.path.join(DATA, f"{slug}_nearby.json")
        if not os.path.exists(p):
            continue
        data = json.load(open(p, encoding="utf-8"))
        for r in data["rows"]:
            merge(r["project"], {**{k: v for k, v in r.items() if k != "project"},
                                 "seen_from_anchor": slug})
    # 2) anchor info captures + 5Y sale-band backfill (the anchor's own row can
    #    drop out of the nearby table mid-load — the band is the honest fallback)
    for slug in CONDO_ANCHORS:
        p = os.path.join(CAP, f"{slug}_info.json")
        if not os.path.exists(p):
            continue
        info = parse_info_texts(_texts(p))
        name = {"amberpark": "Amber Park", "treasure": "Treasure At Tampines",
                "dairyfarm": "Dairy Farm Residences", "sengkanggrand":
                "Sengkang Grand Residences", "parcesta": "Parc Esta",
                "onepearl": "One Pearl Bank", "spottiswoode": "Spottiswoode Suites",
                "gallop": "Gallop Gables"}[slug]
        rec = {**info, "is_anchor": True, "anchor_slug": slug}
        pb = os.path.join(CAP, f"{slug}_sale_band.json")
        if os.path.exists(pb):
            band = parse_band_head(_texts(pb))
            if band:
                rec["sale_band_5y"] = band
                key = name.strip().lower()
                cur = panel.get(key, {})
                if not cur.get("psf_low"):
                    rec["psf_low"], rec["psf_high"] = band["low_psf"], band["high_psf"]
                    rec["psf_source"] = "5Y sale band (anchor backfill)"
        merge(name, rec)
    # 3) prior-study tier1 comps
    t1 = os.path.join(DATA, "tier1_comps.json")
    if os.path.exists(t1):
        for slug, rec in json.load(open(t1, encoding="utf-8")).items():
            info = rec.get("info") or {}
            name = {"royalgreen": "Royalgreen", "leedongreen": "Leedon Green",
                    "sixthave": "Sixth Avenue Residences", "wattenhouse": "Watten House",
                    "reserve": "The Reserve Residences", "8atbt": "8@BT"}.get(slug, slug)
            band = rec.get("sale_band") or {}
            extra = {}
            if band.get("low_psf") or band.get("low"):
                lo = band.get("low_psf") or band.get("low")
                hi = band.get("high_psf") or band.get("high")
                try:
                    extra = {"psf_low": int(_num(lo)), "psf_high": int(_num(hi)),
                             "psf_source": f"sale band ({band.get('window', '?')} window)"}
                except (ValueError, TypeError):
                    pass
            merge(name, {**info, "sale_band": band or None,
                         "tier1_comps_slug": slug, **extra})
    # 4) deep digests: reviewed trends/yields
    for fn in os.listdir(VALUATION):
        if not fn.endswith("_digest.json"):
            continue
        d = json.load(open(os.path.join(VALUATION, fn), encoding="utf-8"))
        dev = (d.get("subject") or {}).get("development")
        if not dev:
            continue
        pip = d.get("pipeline") or {}
        merge(dev, {"deep_digest": fn,
                    "fitted_trend_pa": (pip.get("trend") or {}).get("rate_pa"),
                    "fitted_floor_premium": (pip.get("floor_premium") or {}).get("rate_per_floor"),
                    "review_overall": (d.get("review") or {}).get("overall")})
    return {"meta": {"n": len(panel), "sources": ["nearby tables", "anchor info caps",
            "tier1_comps", "deep digests"]}, "projects": sorted(
            panel.values(), key=lambda r: r["project"])}


LANDED_CAP_SETS = {
    "Frankel Avenue": (["frankel_street_%d" % i for i in range(5)]
                       + ["frankel_nearbyscope_%d" % i for i in range(3)], "pp"),
    "Kingsmead Road": (["landed_kingsmead_sale", "landed_kingsmead_sale_b"], "txn"),
    "Alnwick Road": (["landed_alnwick_street_00", "landed_alnwick_street_01"], "txn"),
}


def assemble_landed() -> dict:
    streets: dict[str, dict] = {}

    def add(street: str, kind: str, rows: list[dict]) -> str:
        # normalize so 'Alnwick (rosyth)' and 'Alnwick Road' merge into one group
        def _base(x):
            x = re.sub(r"\s*\((nanyang|rosyth)\)$", "", x).strip().lower()
            return x if x.endswith("road") or x.endswith("avenue") else x + " road"
        for full in list(streets):
            # merge real street names across sources; 'Nearby' groups are
            # area-scoped and must stay separate per area
            if (full != street and "nearby" not in _base(street)
                    and _base(full) == _base(street)):
                street = full
                break
        s = streets.setdefault(street, {"street": street, "pp_panel": [], "transactions": []})
        bucket = s["pp_panel"] if kind == "pp" else s["transactions"]
        seenk = {(r.get("address"), r.get("pp_date") or r.get("date"),
                  r.get("pp_price") or r.get("price")) for r in bucket}
        for r in rows:
            k = (r.get("address"), r.get("pp_date") or r.get("date"),
                 r.get("pp_price") or r.get("price"))
            if k not in seenk:
                bucket.append(r)
                seenk.add(k)
        return street

    # prior tier1 landed files (already-clean transaction rows)
    for fn, label in (("tier1_landed_nanyang.json", "nanyang"),
                      ("tier1_landed_rosyth.json", "rosyth")):
        p = os.path.join(DATA, fn)
        if not os.path.exists(p):
            continue
        for street_key, rows in json.load(open(p, encoding="utf-8")).items():
            if not isinstance(rows, list):
                continue
            street = street_key.replace("street_", "").title() + f" ({label})"
            norm = [{"address": r.get("address"), "street": street, "type": r.get("type"),
                     "tenure": r.get("tenure"), "top": r.get("top"),
                     "area_sqft": _num(r.get("area_sqft", 0)) or None,
                     "psf": int(_num(r["psf"])) if r.get("psf") not in (None, "-") else None,
                     "price": int(_num(r["price"])) if r.get("price") else None,
                     "sale_type": r.get("sale_type"), "date": r.get("date")}
                    for r in rows if r.get("price")]
            add(street, "txn", norm)
    # street captures (PP panels + 8-col transaction tables, + the app's band)
    for street, (names, kind) in LANDED_CAP_SETS.items():
        for nm in names:
            p = os.path.join(CAP, f"{nm}.json")
            if not os.path.exists(p):
                continue
            ts = _texts(p)
            rows = (parse_landed_pp_texts(ts, street) if kind == "pp"
                    else parse_landed_txn_texts(ts, street))
            resolved = add(street, kind, rows)
            band = parse_band_head(ts)
            if band:
                streets[resolved]["street_band"] = band
    for s in streets.values():
        pts = [r for r in s["pp_panel"] if r.get("pp_psf")]
        s["n_pp"] = len(pts)
        s["n_txn"] = len(s["transactions"])
        if pts:
            s["pp_psf_span"] = [min(r["pp_psf"] for r in pts), max(r["pp_psf"] for r in pts)]
    return {"meta": {"streets": len(streets)}, "streets": sorted(
        streets.values(), key=lambda s: s["street"])}


def main() -> None:
    os.makedirs(FACTORS, exist_ok=True)
    condo = assemble_condo()
    p1 = os.path.join(FACTORS, "panel_condo.json")
    json.dump(condo, open(p1, "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, indent=1)
    print(f"condo panel: {condo['meta']['n']} projects -> {p1}")
    for r in condo["projects"]:
        print(f"   {r['project']:34s} {r.get('tenure_type') or r.get('tenure', '?'):>10} "
              f"TOP {r.get('top_year') or r.get('top', '?')} units {r.get('total_units', '?')} "
              f"psf {r.get('psf_low', '?')}-{r.get('psf_high', '?')} yld {r.get('yield_avg_pct', '?')}")
    landed = assemble_landed()
    p2 = os.path.join(FACTORS, "panel_landed.json")
    json.dump(landed, open(p2, "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, indent=1)
    print(f"landed panel: {landed['meta']['streets']} street groups -> {p2}")
    for s in landed["streets"]:
        print(f"   {s['street']:34s} pp {s['n_pp']:2d}  txn {s['n_txn']:2d}  "
              f"psf span {s.get('pp_psf_span')}")


if __name__ == "__main__":
    main()
