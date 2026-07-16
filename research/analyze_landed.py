"""L3: calibrate + validate the landed split-conformal band (research/analyze_landed.py).

    python -m researcher.backtest.run_landed --dump <p> && python research/analyze_landed.py <p>

Same protocol as the condo conformal (EXP-0006/0007), so the numbers are comparable:
  - CALIBRATE on subjects before CUTOFF, VALIDATE on subjects at/after it — calibration
    strictly precedes evaluation, so the coverage number is honest;
  - per (street-liquidity x property-type) cell, asymmetric ratio quantiles (actual/pred);
  - a NOMINAL sweep, because temporal drift makes nominal != actual;
  - the saved table is FINGERPRINTED with sha1 of the code whose residuals it calibrates
    (landed_candidates.py + landed_size_curve.py), so a change without recalibration turns
    tests/test_landed.py::test_landed_conformal_table_matches_code RED instead of silently
    skewing every band.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
BT = os.path.join(os.path.dirname(HERE), "researcher", "backtest")
TABLE_OUT = os.path.join(BT, "landed_conformal_table.json")
CUTOFF = "2025-01"
MIN_CELL_N = 40
POINT_METHOD = "LV1_landed_engine"


def _liq(n):
    return "0" if not n else "1-2" if n <= 2 else "3-5" if n <= 5 else "6-15" if n <= 15 else "16+"


def _q(vals, p):
    s = sorted(vals)
    if not s:
        return None
    pos = p * (len(s) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        rows = json.load(f)
    pts = [r for r in rows if r["method"] == POINT_METHOD and r.get("pred")]
    cal = [r for r in pts if r["contract_ym"] < CUTOFF]
    test = [r for r in pts if r["contract_ym"] >= CUTOFF]
    print(f"{POINT_METHOD}: {len(pts):,} scored  (cal<{CUTOFF} {len(cal):,} / "
          f"test>={CUTOFF} {len(test):,})")

    def cell(r):
        return f"{_liq(r['n_comps'])}|{r.get('property_type')}"

    by_cell, by_type, allr = defaultdict(list), defaultdict(list), []
    for r in cal:
        ratio = r["actual"] / r["pred"]
        by_cell[cell(r)].append(ratio)
        by_type[r.get("property_type")].append(ratio)
        allr.append(ratio)

    # NOMINAL IS FIXED A PRIORI at p10/p90 = the 80% target. It is NOT selected by the sweep
    # below: choosing the nominal by minimising |coverage-0.80| ON THE TEST SET and then
    # publishing that same test coverage as "held-out" is selection bias (a reviewer caught
    # exactly this). The sweep is printed as a DIAGNOSTIC only.
    NOM_LO, NOM_HI = 0.10, 0.90
    print(f"\n=== nominal sweep — DIAGNOSTIC ONLY (shipped nominal is fixed a priori "
          f"at p{NOM_LO}/p{NOM_HI}) ===")
    for plo, phi in ((0.10, 0.90), (0.075, 0.925), (0.05, 0.95), (0.035, 0.965),
                     (0.025, 0.975)):
        gl, gh = _q(allr, plo), _q(allr, phi)
        cov = wsum = 0
        for r in test:
            v = by_cell.get(cell(r), [])
            lohi = ([_q(v, plo), _q(v, phi)] if len(v) >= MIN_CELL_N else [gl, gh])
            lo, hi = r["pred"] * lohi[0], r["pred"] * lohi[1]
            cov += lo <= r["actual"] <= hi
            wsum += (hi - lo) / r["actual"]
        c, w = cov / len(test), wsum / len(test)
        print(f"  nominal {int((phi-plo)*100)}% (p{plo}/p{phi}): coverage {c:.3f}  width {w:.3f}")
        if (plo, phi) == (NOM_LO, NOM_HI):
            cov, wid = c, w
    print(f"\n-> SHIPPED nominal p{NOM_LO}/p{NOM_HI} (fixed a priori): held-out coverage "
          f"{cov:.3f}, width {wid:.3f}")

    table = {"_global": [_q(allr, NOM_LO), _q(allr, NOM_HI)],
             "_meta": {"point_method": POINT_METHOD, "cutoff": CUTOFF, "n_cal": len(cal),
                       "nominal": [NOM_LO, NOM_HI], "heldout_coverage": round(cov, 4),
                       "heldout_width": round(wid, 4)}}
    for c, v in by_cell.items():
        if len(v) >= MIN_CELL_N:
            table[c] = [_q(v, NOM_LO), _q(v, NOM_HI)]
    for ty, v in by_type.items():
        table[f"_type|{ty}"] = [_q(v, NOM_LO), _q(v, NOM_HI)]

    h = hashlib.sha1()
    for f in ("landed_candidates.py", "landed_size_curve.py"):
        with open(os.path.join(BT, f), "rb") as fh:
            h.update(fh.read())
    table["_meta"]["code_sha1"] = h.hexdigest()

    with open(TABLE_OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(table, f, ensure_ascii=False, indent=1)
    print(f"-> SAVED {TABLE_OUT} "
          f"({len([k for k in table if not k.startswith('_')])} cells, fingerprinted)")


if __name__ == "__main__":
    main()
