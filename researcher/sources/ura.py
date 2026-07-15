"""URA Data Service — private residential transactions (the backtest ground-truth base).

This is the ONLY realistic bulk, official, transaction-level, as-of-replayable source
for Singapore private residential caveats. It backs the walk-forward validation harness
(`researcher.backtest`). Investment Suite stays the live, richer, per-unit Tier-1 for
production single-property runs; URA is the base we backtest on and calibrate against.

Auth (you must do this once — I cannot register an account for you):
  1. Register a free Access Key at https://www.ura.gov.sg/maps/api/  (email-based).
  2. Put it in the environment:  setx URA_ACCESS_KEY "<key>"   (new shell after).
The daily Token is fetched automatically from the Access Key.

    python -m researcher.sources.ura --smoke      # verify key -> token -> 1 batch
    python -m researcher.sources.ura              # pull all 4 batches, normalize, persist

Output: researcher/sources/ura_transactions.json  (normalized, list[Transaction]).
Raw batches cache to research/ura_cache/batch_N.json (gitignored) so re-normalizing
is offline and free.

KNOWN LIMITS (these shape every downstream method — keep them visible):
  - contractDate granularity is MONTH only (MMYY). No transaction day. => as-of filtering
    must treat a whole month as one step, and same-unit dedup can't use day distance.
  - Rolling ~5 years of caveats only. Backtest window is bounded by what the API returns.
  - floorRange is a BAND ("06-10"), not an exact floor. typeOfArea 'Land' rows have no
    floor. No unit/stack id. => stack/exact-floor premium research needs Investment Suite,
    NOT URA. This is the concrete reason IS calibration matters.
  - Caveats are lodged with a LAG after the transaction. `as_of` in the store applies a
    conservative lag buffer so a backtest at date t cannot see a caveat that wasn't
    lodged yet (see researcher/backtest/store.py).

normalize() is pure and offline-testable. The raw->normalized field mapping is written
from URA's documented PMI_Resi_Transaction schema; the FIRST real pull must be checked
against it (run --smoke and eyeball a few rows) before trusting the base.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
RAW_CACHE = os.path.join(REPO, "research", "ura_cache")
OUT = os.path.join(HERE, "ura_transactions.json")
# Fallback for the Access Key when URA_ACCESS_KEY is unset: a GITIGNORED local file
# (research/.secrets/ is never committed). Persists the key without putting a secret in
# version control — the safe way to "save it in the repo".
KEY_FILE = os.path.join(REPO, "research", ".secrets", "ura_access_key")

TOKEN_URL = "https://eservice.ura.gov.sg/uraDataService/insertNewToken/v1"
DATA_URL = "https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1"
SERVICE = "PMI_Resi_Transaction"
BATCHES = (1, 2, 3, 4)  # URA splits the ~5y window into 4 batches
SQM_TO_SQFT = 10.7639

# URA's typeOfSale codes -> label (documented).
_SALE = {"1": "New Sale", "2": "Sub Sale", "3": "Resale"}
# UA matters: URA rejects the default urllib agent on some edges.
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RE_search/0.1"


# --------------------------------------------------------------------------- fetch
def _access_key() -> str:
    key = os.environ.get("URA_ACCESS_KEY", "").strip()
    if not key and os.path.exists(KEY_FILE):
        with open(KEY_FILE, encoding="utf-8") as f:
            key = f.read().strip()
    if not key:
        raise RuntimeError(
            "No URA access key. Register a free key at https://www.ura.gov.sg/maps/api/ "
            f"then either set URA_ACCESS_KEY, or write it into {KEY_FILE} "
            "(that path is gitignored)."
        )
    return key


def _get(url: str, headers: dict[str, str]) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, **headers})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:400]
        raise RuntimeError(f"URA HTTP {e.code} for {url}\n{body}") from e


def fetch_token(access_key: str | None = None) -> str:
    """Fetch a daily Token from the Access Key. Tokens are valid for the calendar day."""
    key = access_key or _access_key()
    d = _get(TOKEN_URL, {"AccessKey": key})
    if str(d.get("Status", "")).lower() != "success" or not d.get("Result"):
        raise RuntimeError(f"URA token refused: {d.get('Message') or d}")
    return d["Result"]


def fetch_batch(batch: int, token: str, access_key: str | None = None) -> list[dict]:
    """Raw project objects for one batch (each has a nested `transaction` list)."""
    key = access_key or _access_key()
    url = f"{DATA_URL}?service={SERVICE}&batch={batch}"
    d = _get(url, {"AccessKey": key, "Token": token})
    if str(d.get("Status", "")).lower() != "success":
        raise RuntimeError(f"URA batch {batch} refused: {d.get('Message') or d}")
    return d.get("Result") or []


def fetch_all(access_key: str | None = None, cache: bool = True) -> list[dict]:
    """All 4 batches merged into one list of raw project objects. Caches each batch."""
    key = access_key or _access_key()
    token = fetch_token(key)
    os.makedirs(RAW_CACHE, exist_ok=True)
    raw: list[dict] = []
    for b in BATCHES:
        rows = fetch_batch(b, token, key)
        if cache:
            with open(os.path.join(RAW_CACHE, f"batch_{b}.json"), "w",
                      encoding="utf-8", newline="\n") as f:
                json.dump(rows, f, ensure_ascii=False)
        raw.extend(rows)
    return raw


def load_cached_raw() -> list[dict]:
    """Re-load the last raw pull from disk (offline)."""
    raw: list[dict] = []
    for b in BATCHES:
        p = os.path.join(RAW_CACHE, f"batch_{b}.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                raw.extend(json.load(f))
    return raw


# ----------------------------------------------------------------------- normalize
def _contract_ym(mmyy: str) -> str | None:
    """'0625' -> '2025-06'. URA gives month-year only; day is unknown."""
    s = (mmyy or "").strip()
    if not re.fullmatch(r"\d{4}", s):
        return None
    mm, yy = int(s[:2]), int(s[2:])
    if not 1 <= mm <= 12:
        return None
    return f"{2000 + yy:04d}-{mm:02d}"


def _floor_band(fr: str) -> tuple[int | None, int | None]:
    """'06-10' -> (6, 10); '-' / 'B1-B5' / '' -> (None, None)."""
    m = re.fullmatch(r"\s*(\d{1,3})\s*-\s*(\d{1,3})\s*", fr or "")
    if not m:
        return (None, None)
    lo, hi = int(m.group(1)), int(m.group(2))
    return (lo, hi) if lo <= hi else (hi, lo)


def _tenure(raw: str) -> tuple[str, int | None]:
    """-> (tenure_type, lease_start_year). '999'/'9999' yrs treated as freehold-equiv."""
    s = (raw or "").strip()
    if not s:
        return ("unknown", None)
    if "freehold" in s.lower():
        return ("freehold", None)
    m = re.search(r"(\d+)\s*yr", s.lower())
    yrs = int(m.group(1)) if m else None
    m2 = re.search(r"from\s+(\d{4})", s.lower())
    start = int(m2.group(1)) if m2 else None
    if yrs is not None and yrs >= 900:
        return ("freehold_equiv", start)
    return ("leasehold", start)


def _f(v) -> float | None:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def normalize(raw_projects: list[dict]) -> list[dict]:
    """Flatten URA project objects into one clean transaction list. Pure — no I/O.

    Every output row carries its own project/street/segment/coords so a transaction is
    self-contained for the store. Rows with an unparseable price/area/date are dropped
    (counted by the caller via len difference).
    """
    out: list[dict] = []
    for proj in raw_projects:
        project = (proj.get("project") or "").strip()
        street = (proj.get("street") or "").strip()
        segment = (proj.get("marketSegment") or "").strip().upper()
        x, y = _f(proj.get("x")), _f(proj.get("y"))
        for i, tx in enumerate(proj.get("transaction") or []):
            price = _f(tx.get("price"))
            area_sqm = _f(tx.get("area"))
            ym = _contract_ym(tx.get("contractDate", ""))
            if not price or not area_sqm or not ym:
                continue
            area_sqft = area_sqm * SQM_TO_SQFT
            lo, hi = _floor_band(tx.get("floorRange", ""))
            ttype, lease_start = _tenure(tx.get("tenure", ""))
            fr = (tx.get("floorRange") or "").strip()
            rid = f"{project or street}|{ym}|{int(price)}|{round(area_sqm,1)}|{fr}|{i}"
            out.append({
                "id": rid,
                "project": project,
                "street": street,
                "market_segment": segment,           # CCR / RCR / OCR
                "district": (tx.get("district") or "").strip(),
                "property_type": (tx.get("propertyType") or "").strip(),
                "type_of_area": (tx.get("typeOfArea") or "").strip(),   # Strata / Land
                "type_of_sale": _SALE.get(str(tx.get("typeOfSale", "")).strip(),
                                          (tx.get("typeOfSale") or "").strip()),
                "tenure_raw": (tx.get("tenure") or "").strip(),
                "tenure_type": ttype,                # freehold / freehold_equiv / leasehold
                "lease_start": lease_start,
                "contract_ym": ym,                   # '2025-06'  (month granularity!)
                "area_sqm": round(area_sqm, 2),
                "area_sqft": round(area_sqft, 1),
                "price": price,
                "psf": round(price / area_sqft, 1),
                "floor_range": fr,                   # '06-10' or '' (landed)
                "floor_lo": lo,
                "floor_hi": hi,
                "x": x,
                "y": y,
                "no_of_units": int(_f(tx.get("noOfUnits")) or 1),
            })
    return out


# ------------------------------------------------------------------------------ CLI
def _coverage(txs: list[dict]) -> str:
    if not txs:
        return "0 transactions"
    yms = sorted(t["contract_ym"] for t in txs)
    segs: dict[str, int] = {}
    ptypes: dict[str, int] = {}
    for t in txs:
        segs[t["market_segment"] or "?"] = segs.get(t["market_segment"] or "?", 0) + 1
        ptypes[t["property_type"] or "?"] = ptypes.get(t["property_type"] or "?", 0) + 1
    lines = [f"{len(txs):,} transactions, {yms[0]}..{yms[-1]}",
             "  by segment: " + ", ".join(f"{k}={v}" for k, v in sorted(segs.items())),
             "  by type:    " + ", ".join(f"{k}={v}" for k, v in
                                          sorted(ptypes.items(), key=lambda kv: -kv[1]))]
    return "\n".join(lines)


def main(argv: list[str]) -> None:
    if "--smoke" in argv:
        key = _access_key()
        token = fetch_token(key)
        print(f"token OK ({token[:8]}...). fetching batch 1 ...")
        rows = fetch_batch(1, token, key)
        txs = normalize(rows)
        print(f"batch 1: {len(rows)} projects -> {len(txs)} transactions")
        print(_coverage(txs))
        for t in txs[:3]:
            print("  sample:", {k: t[k] for k in
                                ("project", "contract_ym", "psf", "area_sqft",
                                 "floor_range", "market_segment", "tenure_type")})
        return
    if "--from-cache" in argv:
        raw = load_cached_raw()
        print(f"loaded {len(raw)} cached projects")
    else:
        raw = fetch_all()
        print(f"fetched {len(raw)} projects across {len(BATCHES)} batches")
    txs = normalize(raw)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(txs, f, ensure_ascii=False)
    print(f"-> {OUT}")
    print(_coverage(txs))


if __name__ == "__main__":
    main(sys.argv[1:])
