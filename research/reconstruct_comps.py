"""Reconstruct a COMPLETE N-year comparable set from the three Tier-1 surfaces.

Why: the Sale tab's transaction table lazy-loads AND silently skips mid-window
rows (proven: #21-03 2024-05 fell inside its date range yet never rendered), so
no single surface is complete. The validated method (analyst-PASSed on the
#18-03 study) is a three-surface union:

    Sale table  ∪  Profitability sell-legs  ∪  Tower View PP fields

with fuzzy cross-surface dedup: the SAME caveat shows up on different surfaces
with date fields differing by a few days — treat same unit + same price within
31 days as one transaction. Surface priority sale > profitability > towerview
(the Sale table is the caveat-table canonical rendering).

Known residual gaps (declare them in the report, do not hide):
  * Tower View only exposes each unit's LAST transaction — an earlier in-window
    trade of a re-traded unit is invisible unless Sale/Profitability caught it;
  * Profitability may be harvested head-only (View All tail unexpanded) — check
    meta.advertised_total vs len(rows).

Inputs  (produced by the harvesters in this directory):
    research/<slug>_transactions.json    harvest_sale.py
    research/<slug>_profitability.json   harvest_profitability.py
    research/<slug>_towerview.json       harvest_towerview.py
Output:
    research/<slug>_comps.json  {"meta": ..., "comps": [...], "subject_rows": [...]}

Usage:
    python reconstruct_comps.py <slug> --asof YYYY-MM-DD [--years 5]
                                [--subject "#18-03"]

Also exposes fit_time_trend(): a deterministic project-fitted price trend from
cross-unit same-spec pairs (the method the accepted study used), with
repeat_sales_trend() from realised pairs as corroboration.

Pure functions throughout — offline-testable; no adb dependency.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import re
import statistics
from datetime import date, timedelta

OUT = os.path.dirname(os.path.abspath(__file__))

_MON = {m: i for i, m in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}


def iso(d: str) -> str:
    """'23 Jun 2026' -> '2026-06-23' (locale-independent)."""
    dd, mm, yy = d.split()
    return f"{yy}-{_MON[mm]:02d}-{int(dd):02d}"


def _num(s) -> int:
    return int(re.sub(r"[^\d]", "", str(s)))


def _beds(t) -> int | None:
    m = re.match(r"^(\d)BR$", str(t or "").upper())
    return int(m.group(1)) if m else None


def _blk_norm(b) -> str | None:
    """'(single)' / '?' / '' -> None (wildcard: single-block devs and legacy data)."""
    b = str(b or "").strip()
    return b if b and b not in ("(single)", "?") else None


def _blk_match(a: str | None, b: str | None) -> bool:
    return a is None or b is None or a == b


def _mk(dt: str, block: str | None, floor: int, stack: str, sqft: int, psf: int,
        price: int, beds: int | None, surface: str, note: str) -> dict:
    lvl = f"L{floor} #{stack}" if block is None else f"B{block} L{floor} #{stack}"
    return {"date": dt, "block": block, "floor": floor, "stack": stack,
            "level": lvl, "size_sqft": sqft, "psf": psf,
            "price": price, "beds": beds, "surface": surface, "note": note}


def rows_from_sale(sale: list[dict]) -> list[dict]:
    out = []
    for r in sale:
        m = re.match(r"^(\d+[A-Za-z]?)\s", r.get("street", ""))
        out.append(_mk(iso(r["date"]), _blk_norm(m.group(1) if m else None),
                       int(r["level"]), r["unit"],
                       _num(r["area_sqft"]), _num(r["psf"]), _num(r["price"]),
                       _beds(r.get("unit_type")), "sale",
                       f"{r.get('unit_type', '?')} · Sale caveat 表 · {r.get('sale_type', '')}".strip(" ·")))
    return out


def rows_from_profitability(profit: dict) -> list[dict]:
    out = []
    for r in profit.get("rows", []):
        out.append(_mk(iso(r["sell_date"]), _blk_norm(r.get("block")), r["level"],
                       r["stack"], r["sqft"], r["sell_psf"], r["sell_price"],
                       _beds(r.get("type")), "profitability",
                       f"{r.get('type', '?')} · Profitability 卖出腿（app caveat 口径）"))
    return out


def strip_stale_panel_artifacts(tower: list[dict], min_blocks: int = 3) -> tuple[list[dict], list[str]]:
    """Kill the stale-panel capture artifact: when a block-tab tap silently
    no-ops, the SAME grid gets captured under several block names — the
    fingerprint (unit, sqft, pp_date, pp_price) then repeats identically across
    blocks, and each phantom copy would enter the comp set as an 'independent'
    transaction (caught by a hostile review on Gallop Gables: one $6.138m sale
    counted 7x, +$62k on the point estimate). Identical fingerprint under
    >= min_blocks different blocks -> keep ONE copy with block=None (uncertain)
    and report it."""
    fp: dict[tuple, list[dict]] = {}
    for u in tower:
        key = (u.get("unit"), u.get("sqft"), u.get("pp_date"), u.get("pp_price"),
               u.get("est_val"))
        fp.setdefault(key, []).append(u)
    out, warnings = [], []
    for key, group in fp.items():
        blocks = {_blk_norm(u.get("block")) for u in group}
        if len(group) >= min_blocks and len(blocks) >= min_blocks:
            keep = dict(group[0])
            keep["block"] = None
            out.append(keep)
            warnings.append(f"{key[0]} ({key[1]}sf, PP {key[2]}): identical under "
                            f"{len(blocks)} blocks — stale-panel artifact, kept 1 "
                            f"copy with block=unknown")
        else:
            out.extend(group)
    return out, warnings


def rows_from_towerview(tower: list[dict]) -> list[dict]:
    out = []
    for u in tower:
        if not all(u.get(k) for k in ("pp_date", "pp_price", "pp_psf", "sqft")):
            continue
        out.append(_mk(iso(u["pp_date"]), _blk_norm(u.get("block")), u["floor"],
                       u["stack"], int(u["sqft"]), u["pp_psf"], u["pp_price"],
                       _beds(u.get("type")), "towerview",
                       f"{u.get('type', '?')} · Tower View PP 面（app caveat 口径）"))
    return out


def unit_beds_map(tower: list[dict]) -> dict[tuple, int]:
    """Tower View carries a type for most units — the primary beds source.
    Keyed (block, floor, stack); block None acts as wildcard for lookups."""
    return {(_blk_norm(u.get("block")), u["floor"], u["stack"]): b for u in tower
            if (b := _beds(u.get("type"))) is not None}


def _unit_beds_lookup(unit_map: dict, block: str | None, floor: int, stack: str) -> int | None:
    hits = {b for (bl, fl, st), b in unit_map.items()
            if fl == floor and st == stack and _blk_match(bl, block)}
    return next(iter(hits)) if len(hits) == 1 else None


def fill_beds(rows: list[dict], tower: list[dict]) -> list[str]:
    """Resolve beds for every row via a deterministic ladder:
       1. exact unit lookup in Tower View;
       2. size lookup — all typed rows of the SAME sqft agree on a bedroom count
          (within one development size->beds is near-deterministic);
       3. nearest typed size within ±15% (noted on the row).
    Returns warnings for rows still unresolved (caller reports them; the
    valuation pipeline must exclude beds-less rows from the engine grid)."""
    unit_map = unit_beds_map(tower)
    size_map: dict[int, set[int]] = {}
    for u in tower:
        if (b := _beds(u.get("type"))) is not None and u.get("sqft"):
            size_map.setdefault(int(u["sqft"]), set()).add(b)
    for r in rows:
        if r["beds"] is not None:
            size_map.setdefault(r["size_sqft"], set()).add(r["beds"])
    unanimous = {s: next(iter(bs)) for s, bs in size_map.items() if len(bs) == 1}
    warnings = []
    def _resolve(r, b, suffix=""):
        r["beds"] = b
        if r["note"].startswith("? · "):  # the surface had no type field
            r["note"] = f"{b}BR{suffix} · " + r["note"][4:]

    for r in rows:
        if r["beds"] is not None:
            continue
        if (b := _unit_beds_lookup(unit_map, r["block"], r["floor"], r["stack"])) is not None:
            _resolve(r, b, "（同单元他面口径）")
            continue
        if (b := unanimous.get(r["size_sqft"])) is not None:
            _resolve(r, b, "（同面积全体一致）")
            continue
        near = min(unanimous, default=None,
                   key=lambda s: abs(math.log(s / r["size_sqft"])))
        if near is not None and abs(math.log(near / r["size_sqft"])) <= math.log(1.15):
            _resolve(r, unanimous[near], f"（按面积就近推断，{r['size_sqft']}sf ≈ {near}sf）")
            continue
        warnings.append(f"{r['level']} {r['size_sqft']}sf @{r['date']}: beds unresolved")
    return warnings


def reconstruct(sale: list[dict], profit: dict, tower: list[dict],
                asof: str, years: int = 5, subject: str | None = None,
                fuzzy_days: int = 31, subject_block: str | None = None) -> dict:
    """Three-surface union -> deduped, windowed, provenance-tagged comps.
    Multi-block developments: pass subject_block (e.g. '80') — stack numbers
    repeat across blocks, and without it the exclusion would eat same-numbered
    units in OTHER blocks too."""
    a = date.fromisoformat(asof)
    start = (a - timedelta(days=round(years * 365.25))).isoformat()

    subj = None
    if subject:
        m = re.match(r"^#?(\d{2})-(\d{2})$", subject.strip())
        if not m:
            raise ValueError(f"subject must look like '#18-03', got {subject!r}")
        subj = (int(m.group(1)), m.group(2))
    subj_blk = _blk_norm(subject_block)

    tower, artifact_warnings = strip_stale_panel_artifacts(tower)
    for w in artifact_warnings:
        print(f"  [artifact] {w}")
    all_rows = (rows_from_sale(sale) + rows_from_profitability(profit)
                + rows_from_towerview(tower))
    beds_warnings = fill_beds(all_rows, tower)

    merged: list[dict] = []
    dropped: list[str] = []
    subject_rows: list[dict] = []
    merges: list[str] = []
    quarantined: list[str] = []
    conflicts: list[str] = []
    _prio = {"sale": 0, "profitability": 1, "towerview": 2}
    for row in all_rows:
        # hard arithmetic gate: price must equal psf x sqft (2%); a failing row
        # is a cross-cell misalignment, not a transaction
        if abs(row["price"] - row["psf"] * row["size_sqft"]) / row["price"] > 0.02:
            quarantined.append(f"{row['level']} {row['date']} {row['surface']}: "
                               f"${row['price']:,} != {row['psf']}psf x {row['size_sqft']}sf")
            continue
        if (subj and (row["floor"], row["stack"]) == subj
                and _blk_match(subj_blk, row["block"])):
            subject_rows.append(row)
            continue
        if not (start <= row["date"] <= asof):
            dropped.append(f"{row['date']} {row['level']} (outside {start}..{asof})")
            continue
        # same unit + same date but a DIFFERENT price = impossible pair; keep
        # the higher-priority surface (sale is the caveat-table canonical)
        clash = next((m2 for m2 in merged
                      if (m2["floor"], m2["stack"], m2["date"]) ==
                         (row["floor"], row["stack"], row["date"])
                      and _blk_match(m2["block"], row["block"])
                      and m2["price"] != row["price"]), None)
        if clash:
            keep, drop = ((clash, row) if _prio[clash["surface"]] <= _prio[row["surface"]]
                          else (row, clash))
            conflicts.append(f"{clash['level']} {clash['date']}: "
                             f"${clash['price']:,}({clash['surface']}) vs "
                             f"${row['price']:,}({row['surface']}) -> kept {keep['surface']}")
            if drop is clash:
                merged.remove(clash)
                merged.append(keep)
            keep["note"] += " · 同日冲突价已消解（保留高优先面，见 data_gaps）"
            continue
        dup = next((m2 for m2 in merged
                    if (m2["floor"], m2["stack"], m2["price"]) ==
                       (row["floor"], row["stack"], row["price"])
                    and _blk_match(m2["block"], row["block"])
                    and abs((date.fromisoformat(m2["date"])
                             - date.fromisoformat(row["date"])).days) <= fuzzy_days), None)
        if dup:
            dup["note"] += f" · 亦见于 {row['surface']} 面（{row['date']}，±{fuzzy_days}d 同价判同笔）"
            if dup["block"] is None and row["block"]:  # keep the more specific identity
                dup["block"] = row["block"]
                dup["level"] = f"B{row['block']} L{dup['floor']} #{dup['stack']}"
            if dup["beds"] is None and row["beds"]:
                dup["beds"] = row["beds"]
            merges.append(f"{dup['level']} {dup['price']}: {dup['surface']} + {row['surface']}")
            continue
        merged.append(row)

    merged.sort(key=lambda r: r["date"], reverse=True)
    counts = {s: sum(1 for r in merged if r["surface"] == s)
              for s in ("sale", "profitability", "towerview")}
    adv = profit.get("meta", {}).get("advertised_total")
    gaps = []
    if quarantined:
        gaps.append(f"算术门隔离 {len(quarantined)} 行（price≠psf×sqft>2%——跨列错位伪影，"
                    "非真实成交；明细见 meta.quarantined）")
    if conflicts:
        gaps.append(f"同单元同日冲突价 {len(conflicts)} 组——按面优先级（sale>profitability>"
                    "towerview）消解，明细见 meta.price_conflicts")
    if adv and len(profit.get("rows", [])) < adv:
        gaps.append(f"Profitability 采集 {len(profit['rows'])}/{adv} 对（View All 尾部未展开）——"
                    "残余不完整性方向上偏漏旧印")
    gaps.append("Tower View 只暴露每单元最后一笔——窗口内再交易单元的较早一笔仅当 Sale/Profitability "
                "捕获时可见")
    return {"meta": {"asof": asof, "window_years": years, "window_start": start,
                     "surface_counts": counts, "total": len(merged),
                     "cross_surface_merges": merges, "dropped_outside_window": len(dropped),
                     "subject_excluded": subject, "beds_warnings": beds_warnings,
                     "stale_panel_artifacts": artifact_warnings,
                     "quarantined": quarantined, "price_conflicts": conflicts,
                     "data_gaps": gaps},
            "comps": merged, "subject_rows": subject_rows}


# ── project-fitted time trend ────────────────────────────────────────────────

def fit_time_trend(comps: list[dict], floor_premium_pp: float = 0.003,
                   min_gap_years: float = 1.0, beds: int | None = None) -> dict:
    """Cross-unit same-spec pairs -> median annual psf growth (the accepted
    study's method, made deterministic). Pairs: same size_sqft AND same beds,
    date gap >= min_gap_years; each pair's rate is floor-adjusted
    ln(psf2/psf1)/yrs. Segments move differently (the #18-03 study found 1-2BR
    flat while 3BR rose), so pass beds= to fit the SUBJECT's segment only —
    a pooled median across segments dilutes toward the flattest one.
    Returns {'rate_pa', 'n_pairs', 'pairs'}; rate_pa is None when there are
    < 3 pairs (caller falls back down the choose_trend ladder)."""
    rates, pairs = [], []
    rows = sorted(comps, key=lambda r: r["date"])
    for a2, b in itertools.combinations(rows, 2):
        if a2["size_sqft"] != b["size_sqft"] or a2["beds"] != b["beds"] or not a2["beds"]:
            continue
        if beds is not None and a2["beds"] != beds:
            continue
        yrs = (date.fromisoformat(b["date"]) - date.fromisoformat(a2["date"])).days / 365.25
        if yrs < min_gap_years:
            continue
        floor_adj = (1 + floor_premium_pp) ** (a2["floor"] - b["floor"])  # bring b to a's floor
        rate = math.log((b["psf"] * floor_adj) / a2["psf"]) / yrs
        rates.append(rate)
        pairs.append(f"{a2['level']}@{a2['date']} -> {b['level']}@{b['date']}: "
                     f"{rate * 100:+.2f}%/yr")
    rate = statistics.median(rates) if len(rates) >= 3 else None
    return {"rate_pa": rate, "n_pairs": len(rates), "pairs": pairs}


def choose_trend(comps: list[dict], profit: dict, subject_beds: int,
                 default_pa: float = 0.018) -> dict:
    """Deterministic trend-selection ladder (no judgment left to the caller):
       1. subject-segment cross-unit median, if >= 5 pairs;
       2. repeat-sales median (holding >= 2y), if >= 3 pairs;
       3. the segment default (0.018).
    The chosen rate is clamped to [0%, 5%]. ALWAYS run the engine's
    sensitivities at 0% and chosen+2pp alongside — the estimate must be shown
    robust to this choice, whatever the ladder picked."""
    seg = fit_time_trend(comps, beds=subject_beds)
    rs = repeat_sales_trend(profit)
    if seg["rate_pa"] is not None and seg["n_pairs"] >= 5:
        rate, method = seg["rate_pa"], f"cross-unit {subject_beds}BR pairs (n={seg['n_pairs']}, median)"
    elif rs["rate_pa"] is not None:
        rate, method = rs["rate_pa"], f"repeat-sales median (n={rs['n_pairs']}, holding>=2y)"
    else:
        rate, method = default_pa, f"segment default {default_pa:.1%} (too few pairs to fit)"
    clamped = min(max(rate, 0.0), 0.05)
    return {"rate_pa": clamped, "method": method,
            "raw_rate_pa": rate, "clamped": clamped != rate,
            "segment_fit": {"rate_pa": seg["rate_pa"], "n_pairs": seg["n_pairs"]},
            "repeat_sales": rs}


def fit_floor_premium(comps: list[dict], beds: int | None = None,
                      max_gap_days: int = 90, min_dfloor: int = 3) -> dict:
    """Deterministic per-floor premium from same-spec pairs traded close in
    time at different floors: median of ln(psf_hi/psf_lo)/Δfloor. High-rise
    new-TOP towers price floors far steeper than the 0.3%/floor default
    (One Pearl Bank launch grid: ~0.5-1%/floor) — using the default there makes
    high-floor comps land too hot on a low-floor subject. rate is None when
    < 8 qualifying pairs (caller keeps the default and says so)."""
    rates = []
    rows = sorted(comps, key=lambda r: r["date"])
    for a2, b in itertools.combinations(rows, 2):
        if a2["size_sqft"] != b["size_sqft"] or a2["beds"] != b["beds"] or not a2["beds"]:
            continue
        if beds is not None and a2["beds"] != beds:
            continue
        days = abs((date.fromisoformat(b["date"]) - date.fromisoformat(a2["date"])).days)
        dfloor = b["floor"] - a2["floor"]
        if days > max_gap_days or abs(dfloor) < min_dfloor:
            continue
        rates.append(math.log(b["psf"] / a2["psf"]) / dfloor)
    rate = statistics.median(rates) if len(rates) >= 8 else None
    return {"rate_per_floor": rate, "n_pairs": len(rates)}


def repeat_sales_trend(profit: dict) -> dict:
    """Corroboration: median annualised return of realised same-unit pairs
    (holding >= 2y). Long holdings smooth over regimes — use as a cross-check,
    not the primary fit."""
    vals = [r["annualised_pct"] / 100 for r in profit.get("rows", [])
            if r.get("annualised_pct") is not None and r["holding"][0].isdigit()
            and int(re.match(r"(\d+)", r["holding"]).group(1)) >= 2]
    return {"rate_pa": statistics.median(vals) if len(vals) >= 3 else None,
            "n_pairs": len(vals)}


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slug")
    ap.add_argument("--asof", required=True, help="YYYY-MM-DD")
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--subject", default=None, help="e.g. '#18-03' — excluded (anchor, not comp)")
    ap.add_argument("--subject-block", default=None,
                    help="block of the subject (multi-block devs, e.g. '80')")
    ap.add_argument("--subject-beds", type=int, default=None,
                    help="subject bedroom count — fits the trend on that segment")
    args = ap.parse_args()

    def load(name, req=True):
        p = os.path.join(OUT, f"{args.slug}_{name}.json")
        if not os.path.exists(p):
            if req:
                raise SystemExit(
                    f"missing {p}\n  -> harvest it first (see read-investment-suite skill):\n"
                    f"     python doctor.py   # readiness gate\n"
                    f"     python harvest_{'sale' if name == 'transactions' else name}.py {args.slug}")
            return None
        return json.load(open(p, encoding="utf-8"))

    sale = load("transactions")
    profit = load("profitability") or {"meta": {}, "rows": []}
    tower = load("towerview")
    res = reconstruct(sale, profit, tower, args.asof, args.years, args.subject,
                      subject_block=args.subject_block)

    by_beds = {b: fit_time_trend(res["comps"], beds=b) for b in (1, 2, 3, 4)}
    res["meta"]["fitted_trend"] = {
        "by_beds": {b: {"rate_pa": t["rate_pa"], "n_pairs": t["n_pairs"]}
                    for b, t in by_beds.items() if t["n_pairs"]},
        "repeat_sales": repeat_sales_trend(profit),
        "note": "同规格跨单元对、楼层校正、按卧室数分段取中位——各段趋势可以不同（#18-03 研究中 "
                "1-2BR 持平、3BR 上行），估值管线用 choose_trend() 的阶梯规则选段"}
    if args.subject_beds:
        res["meta"]["chosen_trend"] = choose_trend(res["comps"], profit, args.subject_beds)

    path = os.path.join(OUT, f"{args.slug}_comps.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    m = res["meta"]
    print(f"{m['total']} comps = " + " ∪ ".join(f"{k} {v}" for k, v in m["surface_counts"].items())
          + f"  (window {m['window_start']}..{args.asof})")
    for msg in m["cross_surface_merges"]:
        print("  [merge]", msg)
    ft = res["meta"]["fitted_trend"]
    for b, t in ft["by_beds"].items():
        print(f"trend {b}BR: " + (f"{t['rate_pa'] * 100:+.2f}%/yr" if t["rate_pa"] is not None
                                  else "n/a") + f" (n={t['n_pairs']})")
    if ft["repeat_sales"]["rate_pa"] is not None:
        print(f"repeat-sales median {ft['repeat_sales']['rate_pa'] * 100:+.2f}%/yr "
              f"(n={ft['repeat_sales']['n_pairs']})")
    if "chosen_trend" in res["meta"]:
        c = res["meta"]["chosen_trend"]
        print(f"chosen trend {c['rate_pa'] * 100:+.2f}%/yr via {c['method']}"
              + ("  [clamped]" if c["clamped"] else ""))
    for g in m["data_gaps"]:
        print("  [gap]", g)
    print(f"-> {path}")


if __name__ == "__main__":
    main()
