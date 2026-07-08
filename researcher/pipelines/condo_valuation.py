"""End-to-end condo valuation pipeline — deterministic numbers, model narrative.

One command takes the three harvest files to a validated digest + rendered
report. Everything numeric (comp reconstruction, trend choice, adjustment
grid, sensitivities, AVM cohort, cost stack, yield) is computed HERE, the same
way every time; the model's job is only the narrative sections (summary,
risks, catalysts, advisory stance, verification claims) — and the validation
gates refuse to ship while TODO placeholders remain or any number disagrees.

    python -m researcher.pipelines.condo_valuation <harvest_slug>
           --digest-slug <digest_slug> --asof YYYY-MM-DD [--years 5]
           [--init] [--no-report]

    harvest_slug  names research/<slug>_{transactions,profitability,towerview,rents}.json
    digest_slug   names researcher/valuation/<digest_slug>_digest.json (and the report)

Typical first run for a new subject:
    python research/doctor.py                       # readiness gate
    python research/harvest_sale.py mydev           # on the Sale tab (5Y window)
    python research/harvest_profitability.py mydev  # on the Profitability tab (5Y)
    python research/harvest_rent.py mydev           # on the Rent tab (5Y)
    python research/harvest_towerview.py mydev      # on the Tower View tab
    python -m researcher.pipelines.condo_valuation mydev --digest-slug mydev_0503 \
           --asof 2026-07-08 --init      # writes a skeleton digest; fill subject + TODOs
    python -m researcher.pipelines.condo_valuation mydev --digest-slug mydev_0503 \
           --asof 2026-07-08             # compute + validate + render

The pipeline REFUSES to guess: missing inputs stop it with the exact command
to run next; a missing/ambiguous subject stops it with the fields to fill.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

from researcher.newlaunch.pricing import bsd  # noqa: E402
from researcher.valuation import validate_digest  # noqa: E402
from researcher.valuation.engine import Comp, Params, Subject, value  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "reconstruct_comps", os.path.join(ROOT, "research", "reconstruct_comps.py"))
rc = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("mbx", type(sys)("mbx"))  # rc imports nothing from mbx, but be safe
_spec.loader.exec_module(rc)

RESEARCH = os.path.join(ROOT, "research")
VALUATION = os.path.join(ROOT, "researcher", "valuation")

MORTGAGE_LTV, MORTGAGE_RATE, MORTGAGE_YEARS = 0.75, 0.014, 30

SKELETON_NARRATIVE = {
    "subtitle": "TODO：一句话副标题（方法 + 关键锚 + 验收状态）",
    "summary": "TODO：中文摘要——结论先行（点估/区间/谈判带），然后是三角依据与关键风险。",
    "development_facts": ["TODO：楼盘事实（地址/区/权属/TOP/户数）——来自 Property Info tab，标注口径"],
    "market_context": ["TODO：URA 季度指数/成交量背景（官方 pr 编号）。本轮若未采集官方源，"
                       "如实写『数据缺口：本轮未采集』——绝不编造数字"],
    "catchment": ["TODO：学区/交通/配套（OneMap/LTA/MOE 口径）。未采集则如实声明缺口，勿编造"],
    "risks": ["TODO：风险（数据面/市场面/政策面/个体面）"],
    "catalysts": ["TODO：催化剂（交通开通/供给/政策）"],
    "yield_analysis": ["（管线会自动写入第 1 条收益率计算行）", "TODO：租赁市场解读"],
    "market_comps": [],
    "verification": [{"claim": "TODO：抽 3 条载重数字做核查", "status": "model-input",
                      "note": "TODO"}],
    "sources": ["PropNex Investment Suite（Tier-1，capture 留痕于 research/captures/）"],
    "advisory": {"stance": "TODO：买方/卖方立场一句话", "detail": "TODO：给能明天行动的建议",
                 "cost_stack": []},
}


def die(msg: str) -> None:
    raise SystemExit(f"\n[STOP] {msg}")


def load_inputs(slug: str) -> tuple[list, dict, list, dict | None]:
    def path(n):
        return os.path.join(RESEARCH, f"{slug}_{n}.json")

    def need(n, harvester):
        p = path(n)
        if not os.path.exists(p):
            die(f"missing {p}\n  harvest it first:\n"
                f"    python research/doctor.py\n"
                f"    python research/{harvester} {slug}   # app on the right tab, 5Y window")
        return json.load(open(p, encoding="utf-8"))

    sale = need("transactions", "harvest_sale.py")
    tower = need("towerview", "harvest_towerview.py")
    profit_p = path("profitability")
    profit = (json.load(open(profit_p, encoding="utf-8")) if os.path.exists(profit_p)
              else None)
    if profit is None:
        print(f"[warn] no {profit_p} — sell-leg surface missing; the comp set may be "
              f"incomplete. Strongly recommended:\n"
              f"    python research/harvest_profitability.py {slug}")
        profit = {"meta": {}, "rows": []}
    rents_p = path("rents")
    rents = json.load(open(rents_p, encoding="utf-8")) if os.path.exists(rents_p) else None
    if rents is None:
        print(f"[warn] no {rents_p} — yield section will be skipped. To include it:\n"
              f"    python research/harvest_rent.py {slug}")
    return sale, profit, tower, rents


def subject_from_digest(d: dict) -> tuple[Subject, str]:
    s = d.get("subject") or {}
    missing = [k for k in ("size_sqft", "floor", "bedrooms") if not s.get(k)]
    if missing:
        die(f"digest.subject is incomplete (missing {missing}) — fill it, then re-run")
    unit = s.get("unit")
    if not unit:
        m = re.search(r"#\d{2}-\d{2}", s.get("name", ""))
        if not m:
            die("digest.subject needs a 'unit' field like '#18-03' "
                "(or a name containing it)")
        unit = m.group(0)
    return Subject(name=s.get("name", unit), size_sqft=float(s["size_sqft"]),
                   floor=int(s["floor"]), bedrooms=int(s["bedrooms"]),
                   tenure=s.get("tenure", "Freehold")), unit


def to_engine_comps(comps: list[dict]) -> tuple[list[Comp], list[str]]:
    out, skipped = [], []
    for c in comps:
        if c["beds"] is None:
            skipped.append(f"{c['level']} {c['size_sqft']}sf (beds unresolved)")
            continue
        out.append(Comp(f"{c['date']} {c['level']} {c['beds']}BR {c['size_sqft']}sf",
                        c["date"], c["floor"], c["beds"], float(c["size_sqft"]),
                        float(c["psf"]), float(c["price"])))
    return out, skipped


def avm_cohort(tower: list[dict], subj: Subject) -> list[dict]:
    rows = [u for u in tower if u.get("est_psf") and u.get("sqft")
            and abs(u["sqft"] - subj.size_sqft) / subj.size_sqft <= 0.02]
    rows.sort(key=lambda u: -u["floor"])
    return [{"blk": u.get("block", "?"), "unit": u["unit"], "sqft": f"{int(u['sqft'])}",
             "est_val": f"${u['est_val']:,}", "est_psf": u["est_psf"]} for u in rows]


def profit_digest_rows(profit: dict) -> list[dict]:
    rows = sorted(profit.get("rows", []), key=lambda r: -r["annualised_pct"])
    return [{"unit": f"#{r['level']:02d}-{r['stack']} ({r['sqft']:,} sqft)",
             "bought": f"{r['buy_month']} @ ${r['buy_price']:,} (${r['buy_psf']:,})",
             "sold": f"{r['sell_date']} @ ${r['sell_price']:,} (${r['sell_psf']:,})",
             "profit": f"{r['profit_amt_raw']} ({r['profit_psf_raw']} psf)",
             "holding": r["holding"], "annualised": f"{r['annualised_pct']}%"}
            for r in rows]


def rent_digest_rows(rents: dict, cap: int = 12) -> list[dict]:
    rows = rents.get("rows", [])
    rows = sorted(rows, key=lambda r: r.get("contract_month", ""), reverse=True)[:cap]
    return [{"unit_type": r["type"], "monthly_rent": f"${r['monthly_rent']:,}",
             "note": f"{r['area_band_sqft']} sqft · ${r['psf']}/sqft · "
                     f"{r.get('contract_month', '?')} · Investment Suite（租约）"}
            for r in rows]


def run(args: argparse.Namespace) -> int:
    digest_path = os.path.join(VALUATION, f"{args.digest_slug}_digest.json")

    # ── init mode: write a skeleton and stop ─────────────────────────────────
    if args.init:
        if os.path.exists(digest_path) and not args.force:
            die(f"{digest_path} already exists — edit it, or pass --force to overwrite")
        skel = {"subject": {"name": "TODO：#NN-SS 楼盘名（面积 户型）", "development": "TODO",
                            "address": "TODO", "district": "TODO", "tenure": "TODO",
                            "top_year": 0, "size_sqft": 0, "floor": 0, "bedrooms": 0,
                            "unit": "#NN-SS"},
                "asof": args.asof, "report_basename": f"{args.digest_slug}_Condo_Valuation_Report.html",
                **SKELETON_NARRATIVE,
                "data_gaps": [], "review": {}}
        json.dump(skel, open(digest_path, "w", encoding="utf-8", newline="\n"),
                  ensure_ascii=False, indent=2)
        print(f"skeleton written -> {digest_path}\n"
              "fill subject (size/floor/beds/unit/tenure from Property Info + Tower View) "
              "and the TODO narrative, then re-run without --init")
        return 0

    if not os.path.exists(digest_path):
        die(f"no digest at {digest_path} — run with --init first, fill the skeleton, re-run")
    d = json.load(open(digest_path, encoding="utf-8"))
    subj, unit = subject_from_digest(d)

    # ── 1. reconstruct the three-surface comp set ────────────────────────────
    sale, profit, tower, rents = load_inputs(args.slug)
    window_gaps = []
    for label, data in (("Profitability", profit), ("Rent", rents or {})):
        w = (data.get("meta") or {}).get("window")
        m = re.match(r"(\d+)Y$", str(w or ""))
        if m and int(m.group(1)) < args.years:
            msg = (f"{label} 面在 {w} 窗口下采集，短于重构窗 {args.years}Y——"
                   f"该面早于 {w} 的记录缺失；建议在 app 选 {args.years}Y 后重采")
            window_gaps.append(msg)
            print(f"[warn] {msg}")
    res = rc.reconstruct(sale, profit, tower, args.asof, args.years, subject=unit,
                         subject_block=d.get("subject", {}).get("block"))
    comps_rows = res["comps"]
    if not comps_rows:
        die("0 comps in window — widen --years or check the harvests")
    for c in comps_rows:  # deterministic like-for-like markers
        if (c["floor"] == subj.floor and c["size_sqft"] == int(subj.size_sqft)
                and c["beds"] == subj.bedrooms):
            c["note"] = "⭐同层同规格（最强直接可比） · " + c["note"]
        elif c["size_sqft"] == int(subj.size_sqft) and c["beds"] == subj.bedrooms:
            c["note"] = "⭐同规格 cohort · " + c["note"]

    # ── 2. trend + anchor ────────────────────────────────────────────────────
    trend = rc.choose_trend(comps_rows, profit, subj.bedrooms, default_pa=args.default_trend)
    if args.trend is not None:
        # explicit analyst override (e.g. out of a review round) — recorded, on the record
        trend = {**trend, "rate_pa": args.trend,
                 "method": (f"人工覆写 {args.trend:.2%}（阶梯缺省为 "
                            f"{trend['rate_pa'] * 100:+.2f}%/yr via {trend['method']}；"
                            f"覆写依据必须写进 summary/风险节）"),
                 "clamped": False, "override": True}
    anchor = None
    own = sorted(res["subject_rows"], key=lambda r: r["date"])
    if own:
        a = own[-1]
        anchor = Comp(f"{unit} own {a['date']}", a["date"], a["floor"],
                      subj.bedrooms, float(a["size_sqft"]), float(a["psf"]), float(a["price"]))

    # floor premium: fitted from same-spec close-in-time cross-floor pairs when
    # the data supports it (high-rise towers are far steeper than the 0.3%
    # default); else the segment default
    ffit = rc.fit_floor_premium(comps_rows, beds=subj.bedrooms)
    if ffit["rate_per_floor"] is None:
        ffit = rc.fit_floor_premium(comps_rows)  # all segments pooled
    floor_pp = ffit["rate_per_floor"] if ffit["rate_per_floor"] is not None else 0.003
    floor_pp = min(max(floor_pp, 0.0), 0.02)  # clamp to [0%, 2%]/floor
    floor_method = (f"拟合 {floor_pp:.2%}/层（同规格 ±90 天跨楼层对 n={ffit['n_pairs']}，中位）"
                    if ffit["rate_per_floor"] is not None else "缺省 0.30%/层（可拟合对不足）")

    # ── 3. engine + sensitivities ────────────────────────────────────────────
    engine_comps, skipped = to_engine_comps(comps_rows)
    if skipped:
        print(f"[warn] {len(skipped)} rows excluded from the grid (beds unresolved): {skipped}")

    def _value(tr, use_anchor=True):
        p = Params(asof=args.asof, time_trend_pa=tr, floor_premium_pp=floor_pp,
                   size_elasticity=-0.08, compact3br_discount=0.03)
        return value(subj, engine_comps, p,
                     same_line_anchor=anchor if use_anchor else None, anchor_weight=2.0)

    v = _value(trend["rate_pa"])
    sens = {"trend_0pc": round(_value(0.0).estimate_psf),
            "trend_plus2pp": round(_value(trend["rate_pa"] + 0.02).estimate_psf),
            "no_anchor": round(_value(trend["rate_pa"], use_anchor=False).estimate_psf)}
    est_price = round(v.estimate_price, -3)

    # triangulation (the accepted #18-03 read): app AVM cohort as one leg, the
    # freshest same-spec print as the other, the model in between. The
    # negotiation band spans model∪AVM∪freshest — a deterministic rendering of
    # "AVM lags fresh prints; never price outside what the market just proved".
    cohort = avm_cohort(tower, subj)
    avm_med = round(statistics.median(u["est_psf"] for u in cohort)) if cohort else None
    fresh = next((c for c in comps_rows
                  if c["size_sqft"] == int(subj.size_sqft) and c["beds"] == subj.bedrooms),
                 None)  # comps_rows is date-desc
    tri_vals = [x for x in (avm_med, round(v.estimate_psf),
                            fresh["psf"] if fresh else None) if x]
    triangulation = {
        "avm_cohort_median_psf": avm_med,
        "model_psf": round(v.estimate_psf),
        "freshest_same_spec": ({"psf": fresh["psf"], "date": fresh["date"],
                                "level": fresh["level"]} if fresh else None),
        "negotiation_band_psf": [min(tri_vals), max(tri_vals)] if tri_vals else None,
        "note": "谈判带 = AVM cohort 中位 ∪ 模型点估 ∪ 最新同规格成交 的包络（AVM 滞后新成交，"
                "最新直接成交为上锚；三值任何一个缺失时带宽相应收窄——按脚注读）",
    }

    # ── 4. deterministic digest sections ────────────────────────────────────
    d["asof"] = args.asof
    d["comps_table"] = [{"date": c["date"], "size_sqft": c["size_sqft"], "level": c["level"],
                         "psf": c["psf"], "price": c["price"], "beds": c["beds"],
                         "note": c["note"]} for c in comps_rows]
    counts = res["meta"]["surface_counts"]
    anchor_txt = (f"自身上次成交锚：{anchor.label}（${anchor.psf:,.0f} psf，趋势前推后权重 2.0；"
                  f"分位集合计 1 次）" if anchor else "无自身成交锚（subject 无历史成交记录）")
    d["valuation"] = {
        "estimate_psf": round(v.estimate_psf), "estimate_price": est_price,
        "low_psf": round(v.low_psf), "high_psf": round(v.high_psf),
        "low_price": round(v.low_price, -3), "high_price": round(v.high_price, -3),
        "sensitivity": sens, "triangulation": triangulation,
        "params_note": (
            f"模型输入：{len(d['comps_table'])} 笔 {args.years}Y 三面重构集 = "
            f"Sale 表 {counts['sale']} ∪ Profitability 卖出腿 {counts['profitability']} ∪ "
            f"Tower View PP 面 {counts['towerview']}（app/URA caveat 口径，逐笔可溯源；"
            f"跨面同价 ±31 天判同笔）。Sale 表 UI 懒加载且可跳行——三面互补是采集方法论。"
            f"{anchor_txt}。时间趋势 {trend['rate_pa'] * 100:+.2f}%/yr（{trend['method']}"
            f"{'，超界截断' if trend['clamped'] else ''}）；"
            f"敏感性：趋势 0% → {sens['trend_0pc']:,}；+2pp → {sens['trend_plus2pp']:,}；"
            f"去锚 → {sens['no_anchor']:,}（psf）。楼层 {floor_method}；面积弹性 -0.08；"
            f"紧凑 3BR（≤800sf）折价 3%；权重 = 1/(1+|ln(面积比)|×3+楼层差/25+年差/2+异卧室数 0.6)。"
            f"区间 = 调整后值的四分位距（exclusive/type-6，含前推锚共 "
            f"{len(engine_comps) + (1 if anchor else 0)} 个值），点估恒在区间内。"),
        "grid": [{"label": g.label, "raw_psf": g.raw_psf, "time_adj": g.time_adj,
                  "floor_adj": g.floor_adj, "size_adj": g.size_adj, "type_adj": g.type_adj,
                  "adj_psf": g.adj_psf, "weight": g.weight} for g in v.grid],
    }
    d["avm_crosscheck"] = avm_cohort(tower, subj)
    if profit.get("rows"):
        d["profitability"] = profit_digest_rows(profit)
    if rents:
        d["rentals"] = rent_digest_rows(rents)
        same_type = [r["monthly_rent"] for r in rents["rows"]
                     if r["type"] == f"{subj.bedrooms}BR"]
        if same_type:
            med = statistics.median(same_type)
            gy = med * 12 / est_price * 100
            band = rents.get("meta", {}).get("band", {})
            line = (f"{subj.bedrooms}BR 近期合约中位 ${med:,.0f}/mo（n={len(same_type)}，"
                    f"app 全窗带 {band.get('low', '?')}–{band.get('high', '?')}，"
                    f"均值 {band.get('avg', '?')}）→ 对点估（S${est_price:,.0f}）"
                    f"毛收益率 ~{gy:.1f}%。")
            ya = d.get("yield_analysis") or [""]
            d["yield_analysis"] = [line] + [x for x in ya[1:]]
    mort = (est_price * MORTGAGE_LTV) * (MORTGAGE_RATE / 12) / (
        1 - (1 + MORTGAGE_RATE / 12) ** (-12 * MORTGAGE_YEARS))
    d.setdefault("advisory", {})["cost_stack"] = [
        f"BSD（点估 S${est_price:,.0f}）≈ S${bsd(est_price):,.0f}；公民首套 ABSD 0%、二套 20%、PR 首套 5%",
        "SSD（买方新购）：2025-07-04 起 4 年 16/12/8/4%——短炒通道已死",
        f"月供参考：{MORTGAGE_LTV:.0%} LTV @{MORTGAGE_RATE:.1%} 固定 ≈ S${mort:,.0f}/mo（{MORTGAGE_YEARS} 年）",
        "年度房产税按 AV 累进（自住 0-32% 档）——以 IRAS 计算器为准",
    ]
    gaps = list(res["meta"]["data_gaps"]) + window_gaps
    if res["meta"].get("stale_panel_artifacts"):
        gaps.append(f"Tower View 采集中检出 {len(res['meta']['stale_panel_artifacts'])} 组跨座重复"
                    "指纹（切座失败伪影）——已按指纹门去重、座位标记为未知；受影响单元的座位归属"
                    "以下轮重采为准")
    if res["meta"]["beds_warnings"]:
        gaps.append(f"户型未解析行（已排除出调整网格）：{res['meta']['beds_warnings']}")
    hand = [g for g in d.get("data_gaps", []) if not any(
        k in g for k in ("Tower View 只暴露", "View All 尾部", "户型未解析",
                         "窗口下采集", "跨座重复"))]
    d["data_gaps"] = gaps + hand
    d["pipeline"] = {"tool": "researcher.pipelines.condo_valuation", "asof": args.asof,
                     "harvest_slug": args.slug, "trend": trend,
                     "floor_premium": {"rate_per_floor": floor_pp, "method": floor_method},
                     "cross_surface_merges": res["meta"]["cross_surface_merges"]}

    json.dump(d, open(digest_path, "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, indent=2)
    print(f"digest updated -> {digest_path}")
    print(f"  点估 {v.estimate_psf:,.0f} psf → S${est_price:,.0f}   "
          f"区间 {v.low_psf:,.0f}–{v.high_psf:,.0f} psf")
    print(f"  trend {trend['rate_pa'] * 100:+.2f}%/yr via {trend['method']}  "
          f"sens {sens}")
    if triangulation["negotiation_band_psf"]:
        t = triangulation
        print(f"  三角：AVM {t['avm_cohort_median_psf']} · 模型 {t['model_psf']} · "
              f"最新同规格 {t['freshest_same_spec']['psf'] if t['freshest_same_spec'] else '—'}"
              f" → 谈判带 {t['negotiation_band_psf'][0]:,}–{t['negotiation_band_psf'][1]:,} psf")

    # ── 5. gates ─────────────────────────────────────────────────────────────
    results = validate_digest.check(d)
    fails = [r for r in results if not r["ok"]]
    for r in results:
        print(f"  [{'PASS' if r['ok'] else 'FAIL'}] {r['gate']}: {r['detail']}")
    if fails:
        print("\ngates FAILED — fix the digest (narrative TODOs are yours to write; "
              "numeric mismatches mean re-run the pipeline), then re-run")
        return 1

    # ── 6. report ────────────────────────────────────────────────────────────
    if not args.no_report:
        r = subprocess.run([sys.executable,
                            os.path.join(ROOT, "deliverables", "build_condo_report.py"),
                            args.digest_slug],
                           capture_output=True, text=True, encoding="utf-8")
        print(r.stdout.strip() or r.stderr.strip())
        if r.returncode != 0:
            return r.returncode
    print("\nnext: acceptance review — use the property-report-review skill "
          "(hostile analyst, iterate to PASS), then record scores under digest['review']")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slug", help="harvest slug (research/<slug>_*.json)")
    ap.add_argument("--digest-slug", required=True,
                    help="digest slug (researcher/valuation/<digest_slug>_digest.json)")
    ap.add_argument("--asof", required=True, help="YYYY-MM-DD")
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--default-trend", type=float, default=0.018,
                    help="fallback annual trend when too few pairs to fit")
    ap.add_argument("--trend", type=float, default=None,
                    help="explicit trend override (e.g. 0.025) — use only with a written "
                         "rationale, typically out of a review round")
    ap.add_argument("--init", action="store_true", help="write a skeleton digest and stop")
    ap.add_argument("--force", action="store_true", help="allow --init to overwrite")
    ap.add_argument("--no-report", action="store_true")
    return run(ap.parse_args())


if __name__ == "__main__":
    sys.exit(main())
