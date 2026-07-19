"""PropertyGuru explorer cards → landed screening listings — the PG chain's bridge.

mobile_bridge's PG explorer (`scripts/propertyguru.ps1 listings … --property-type Landed`)
writes de-duplicated listing cards to `<run>/listings.json`. The landed screening
(`researcher/landed/screen.py`) reads `researcher/landed/<slug>_listings.json` in a
different, judgment-bearing schema. This module is the ONE mapping between them;
`research/tools/pg_listings_import.py` is its CLI.

Two honesty rules are load-bearing:
  1. `land_psf` is computed ONLY from a land-labelled area ("… sqft (land)"). A card
     whose area says "(floor)"/"(built-up)" gets `builtup_sqft`, no land figures —
     screen_verdict then correctly reports "VERIFY DATA - land size/psf unconfirmed"
     instead of ranking on a floor psf that looks like a bargain land psf.
  2. Imported rows carry `flood_risk: "unverified"` and (absent a card value)
     `tenure: "unknown"` — both trip screen_verdict's VERIFY-DATA gate. An import
     must never make a listing LOOK vetted; vetting is the analyst's judgment layer,
     preserved across re-imports by `merge`.
"""
from __future__ import annotations

import re

# Judgment-layer fields the analyst fills by hand — merge() must never clobber these.
JUDGMENT_FIELDS = ("estate_tier", "catchment", "zoning_risk", "hazards", "flood_risk",
                   "future_risk", "rebuild_status", "notes", "onemap_km", "url",
                   "plot_shape", "frontage_m", "lw_ratio", "topography", "corner",
                   "near_water")

TYPE_MAP = {
    "terrace house": "terrace", "terraced house": "terrace", "corner terrace": "terrace",
    "semi-detached house": "semi_d", "semi detached house": "semi_d",
    "detached house": "detached", "bungalow": "bungalow",
    "good class bungalow": "gcb", "cluster house": "cluster",
    "land only": "land", "landed": "terrace",
}

_AREA = re.compile(r"([\d,.]+)\s*sqft(?:\s*\((land|floor|built[\s-]?up)\))?", re.I)
_HOUSE_NO = re.compile(r"^\d+[A-Z]?\s+")
_YEAR = re.compile(r"(19|20)\d\d")


def _num(s) -> float | None:
    if s is None:
        return None
    t = re.sub(r"[^\d.]", "", str(s))
    return float(t) if t else None


def tenure_of(s) -> str:
    t = (s or "").lower()
    if "freehold" in t:
        return "freehold"
    if "999" in t:
        return "999"
    if "99" in t:
        return "99"
    return "unknown"


def card_to_listing(card: dict) -> tuple[dict | None, list[str]]:
    """One explorer card → one screening listing. (None, [reason]) when skipped."""
    warns: list[str] = []
    if card.get("card_kind") not in (None, "listing"):
        return None, [f"skip {card.get('listing_id')}: card_kind={card.get('card_kind')}"]
    price_raw = card.get("price") or ""
    if "/mo" in price_raw:
        return None, [f"skip {card.get('listing_id')}: rent card ({price_raw.strip()})"]

    area_kind, area_val = None, None
    m = _AREA.search(card.get("area") or "")
    if m:
        area_val = _num(m.group(1))
        area_kind = (m.group(2) or "").lower().replace("-", "").replace(" ", "") or None

    price = _num(price_raw)
    lst: dict = {
        "id": str(card.get("listing_id") or ""),
        "street": _HOUSE_NO.sub("", (card.get("address") or "").strip()) or card.get("title"),
        "address": card.get("address"),
        "type": TYPE_MAP.get((card.get("property_type") or "").strip().lower(),
                             (card.get("property_type") or "").strip().lower() or None),
        "price": price,
        "tenure": tenure_of(card.get("tenure")),
        "beds": int(card["bedrooms"]) if str(card.get("bedrooms") or "").isdigit() else None,
        "mrt": card.get("mrt"),
        "listed": card.get("listed_at"),
        "flood_risk": "unverified",
    }
    y = _YEAR.search(card.get("completion_year") or "")
    if y:
        lst["built_year"] = int(y.group(0))

    if area_kind == "land":
        lst["land_sqft"] = area_val
        if price and area_val:
            lst["land_psf"] = round(price / area_val)
    elif area_val:
        lst["builtup_sqft"] = area_val
        psf = _num(card.get("price_psf"))
        if psf:
            lst["floor_psf"] = psf
        warns.append(f"{lst['id']}: area is {area_kind or 'unlabelled'} "
                     f"({area_val:,.0f} sqft) — land size/psf UNCONFIRMED, listing will "
                     f"rank as VERIFY DATA until the land area is established")
    else:
        warns.append(f"{lst['id']}: no parsable area — VERIFY DATA")
    if lst["tenure"] == "unknown":
        warns.append(f"{lst['id']}: tenure unknown on the card — confirm via caveats "
                     f"(portals round 999-yr to freehold; the caveat is the free catch)")
    return lst, warns


def merge(existing: list[dict], imported: list[dict]) -> tuple[list[dict], dict]:
    """Refresh market fields, PRESERVE judgment fields, report what changed.

    Returns (merged_listings, {new, updated, missing}) where `missing` are ids present
    in the existing file but absent from this pull — candidates for stale_ids, decided
    by the analyst (a listing can drop off page 1 without being sold)."""
    by_id = {str(l.get("id")): l for l in existing}
    seen, out = set(), []
    report = {"new": [], "updated": [], "missing": []}
    for imp in imported:
        i = imp["id"]
        seen.add(i)
        if i in by_id:
            old = dict(by_id[i])
            for k in JUDGMENT_FIELDS:
                if k in old:
                    imp = {**imp, k: old[k]}
            # a hand-set land area beats a card-parsed one (INLIS/agent-confirmed)
            for k in ("land_sqft", "land_psf", "builtup_sqft"):
                if old.get(k) is not None and imp.get(k) is None:
                    imp[k] = old[k]
            out.append(imp)
            report["updated"].append(i)
        else:
            out.append(imp)
            report["new"].append(i)
    for i, old in by_id.items():
        if i not in seen:
            out.append(old)
            report["missing"].append(i)
    return out, report
