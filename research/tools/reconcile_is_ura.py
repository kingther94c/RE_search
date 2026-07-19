"""EXP-0018 / R4a — reconcile Investment Suite street caveats against the URA API spine.

Answers the four PRE-REGISTERED questions (registry EXP-0018), per street:
  F1 FRESHNESS   — is IS's newest caveat newer than URA's newest? (the claim L2b left in
                   the roadmap: "only fresher observations can shrink the residual bias")
  D1 DEPTH       — does IS reach back before the URA window opens? (the CARDIFF class)
  A1 AGREEMENT   — on matched rows, do price and area agree?
  C1 COMPLETENESS— what does each source have that the other does not?

Matching is on (contract MONTH, area, price): URA publishes contractDate at MONTH
granularity while IS gives the exact DAY, so the day cannot be a key — it is a FINDING
(see the report's freshness section), not a join field. Area is compared as a rounded
integer because IS renders '2,153' where URA carries 2152.8.

    python research/reconcile_is_ura.py [STREET ...]      # default: everything harvested
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.lib import is_rows as is_lib  # noqa: E402
from researcher.backtest.store import LANDED_PSF_BAND, TransactionStore  # noqa: E402

AREA_TOL = 1.5          # sqft — absorbs IS's rounding of URA's decimals

# Parsing lives in research/lib/is_rows.py — the ONE normalizer every IS-harvest
# consumer shares (is_street_compare.py uses the same load).
load_is = is_lib.load_harvest


def load_ura(street: str) -> list[dict]:
    st = (TransactionStore.load().is_pure_landed().exclude_bulk()
          .psf_band(*LANDED_PSF_BAND))
    return [t for t in st.txs if (t["street"] or "").strip().upper() == street.upper()]


def match(is_rows: list[dict], ura_rows: list[dict]) -> dict:
    """Greedy 1-1 match on (month, price) then verify area — price is near-unique per
    month on a street, so it carries the join and area becomes an AGREEMENT test rather
    than part of the key (otherwise an area disagreement would masquerade as a miss)."""
    pool: dict[tuple, list[dict]] = defaultdict(list)
    for u in ura_rows:
        pool[(u["contract_ym"], round(u["price"]))].append(u)
    matched, is_only, area_bad = [], [], []
    for r in is_rows:
        key = (r["_ym"], round(r["_price"]))
        cands = pool.get(key)
        if cands:
            # Pair by NEAREST AREA inside the (month, price) group. Popping an arbitrary
            # member crossed two same-price sales on one street-month and then reported the
            # crossing as an area DISAGREEMENT — a self-inflicted 98.1% that would have been
            # published as "IS and URA disagree on area". They agree; the matcher was wrong.
            u = min(cands, key=lambda c: abs(c["area_sqft"] - r["_area"]))
            cands.remove(u)
            matched.append((r, u))
            if abs(u["area_sqft"] - r["_area"]) > AREA_TOL:
                area_bad.append((r, u))
        else:
            is_only.append(r)
    ura_only = [u for rest in pool.values() for u in rest]
    return {"matched": matched, "is_only": is_only, "ura_only": ura_only,
            "area_bad": area_bad}


def report(street: str, slug: str) -> dict:
    d = load_is(slug)
    is_rows, ura_rows = d["rows"], load_ura(street)
    if not ura_rows:
        print(f"\n### {street}: URA has NO caveats (the CARDIFF class) — IS has "
              f"{len(is_rows)} rows {min(r['_date'] for r in is_rows)}.."
              f"{max(r['_date'] for r in is_rows)}")
        return {"street": street, "ura_n": 0, "is_n": len(is_rows), "cardiff_class": True}
    m = match(is_rows, ura_rows)
    is_max, ura_max = max(r["_ym"] for r in is_rows), max(u["contract_ym"] for u in ura_rows)
    is_min, ura_min = min(r["_ym"] for r in is_rows), min(u["contract_ym"] for u in ura_rows)
    n_match = len(m["matched"])
    out = {
        "street": street, "is_n": len(is_rows), "ura_n": len(ura_rows),
        "matched": n_match, "is_only": len(m["is_only"]), "ura_only": len(m["ura_only"]),
        "is_newest": is_max, "ura_newest": ura_max, "is_oldest": is_min,
        "ura_oldest": ura_min,
        "F1_is_fresher": is_max > ura_max,
        "D1_is_deeper": is_min < ura_min,
        "A1_area_agree": round(1 - len(m["area_bad"]) / n_match, 4) if n_match else None,
        "C1_ura_only_share": round(len(m["ura_only"]) / len(ura_rows), 4),
    }
    print(f"\n### {street}")
    print(f"  rows: IS {out['is_n']} | URA {out['ura_n']} | matched {n_match} "
          f"| IS-only {out['is_only']} | URA-only {out['ura_only']}")
    print(f"  window: IS {is_min}..{is_max} | URA {ura_min}..{ura_max}")
    print(f"  F1 IS fresher? {out['F1_is_fresher']}   D1 IS deeper? {out['D1_is_deeper']}   "
          f"A1 area agree {out['A1_area_agree']}   C1 URA-only {out['C1_ura_only_share']:.1%}")
    for r, u in m["area_bad"][:3]:
        print(f"    [area!] {r['_date']} ${r['_price']:,.0f}: IS {r['_area']:,.0f} "
              f"vs URA {u['area_sqft']:,.1f}")
    for r in sorted(m["is_only"], key=lambda x: x["_date"], reverse=True)[:3]:
        print(f"    [IS-only] {r['_date']} {r.get('address','')} {r['_area']:,.0f}sf "
              f"${r['_price']:,.0f} {r.get('sale_type')}")
    for u in sorted(m["ura_only"], key=lambda x: x["contract_ym"], reverse=True)[:3]:
        print(f"    [URA-only] {u['contract_ym']} {u['area_sqft']:,.0f}sf "
              f"${u['price']:,.0f} {u['type_of_sale']}")
    return out


def main() -> None:
    want = sys.argv[1:]
    files = sorted(f for f in os.listdir(is_lib.IS_DIR) if f.endswith("_sale.json"))
    rows = []
    for f in files:
        slug = f[:-len("_sale.json")]
        street = slug.replace("_", " ").upper()
        if want and street not in [w.upper() for w in want]:
            continue
        rows.append(report(street, slug))
    scored = [r for r in rows if not r.get("cardiff_class")]
    if scored:
        print("\n=== EXP-0018 pre-registered verdict ===")
        f1 = sum(r["F1_is_fresher"] for r in scored) / len(scored)
        d1 = sum(r["D1_is_deeper"] for r in scored) / len(scored)
        print(f"  F1 IS fresher on {f1:.0%} of streets (gate: >=50% AND >=30d median)")
        print(f"  D1 IS deeper on {d1:.0%} of streets (gate: >=50%)")
        a1 = [r["A1_area_agree"] for r in scored if r["A1_area_agree"] is not None]
        print(f"  A1 area agreement: min {min(a1):.1%} (gate: >=95%)" if a1 else "  A1 n/a")
        c1 = max(r["C1_ura_only_share"] for r in scored)
        print(f"  C1 worst URA-only share: {c1:.1%} (gate: <10% for 'IS is complete')")


if __name__ == "__main__":
    main()
