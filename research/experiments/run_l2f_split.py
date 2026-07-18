"""EXP-0019 / L2f — 真实门牌路 vs URA 母路桶,谁该当 comp 池?

EXP-0018 证明 URA 的 landed `street` 是**发展项目登记的街道**,所以 LC2 的「同街网格」
其实是「同母路网格」:URA "LOYANG RISE"(135) = Loyang Rise(104) + Loyang View(31);
ALNWICK ROAD 的 427 笔里混着 Cardiff Grove。**这未必是错的** —— LV1 那 9.05% 就是在这个
池子上测出来的。本实验测两件被报告默认了答案的事(门槛见 EXP-0019 预注册):

  P 点估值:把 comp 限制在标的**真实所在路**,median APE 会更好还是更差?(更纯但更薄)
  D 分布  :子路的**真实成交**落在母路桶 p25/p75 的比例,是否符合报告公布的
            (~73-83% 高于 p25、~32-38% 高于 p75)?这是对「别名街道抑制议价门槛」
            这道闸的正式检验 —— 它目前只靠 19 Cardiff Grove 一个观测支撑。

归属图只来自**已在磁盘上的 IS 采集**(month+price+area 匹配),不新采数据。

    python research/run_l2f_split.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from statistics import median

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

from researcher.backtest.harness import _prev_ym                       # noqa: E402
from researcher.backtest.index import PriceIndex                       # noqa: E402
from researcher.backtest.landed_candidates import lc2_fitted_curve     # noqa: E402
from researcher.engine.landed_engine import shipped_time_ctx         # noqa: E402
from researcher.backtest.market import MarketView                      # noqa: E402
from researcher.backtest.store import (LANDED_PSF_BAND, TransactionStore,  # noqa: E402
                                       month_end)
from researcher.engine.value_landed import _adjusted_comp_psfs, _pctl  # noqa: E402

IS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "is_street")
# IS 采集 slug -> 它在 URA 里被归到哪个母路桶(EXP-0018 已证)
ATTRIBUTION = {
    "loyang_rise": ("LOYANG RISE", "LOYANG RISE"),
    "loyang_view": ("LOYANG RISE", "LOYANG VIEW"),
    "cardiff_grove": ("ALNWICK ROAD", "CARDIFF GROVE"),
}
# 报告公布的标记命中率(EXP-0013/0017 实测),D 门槛拿它做基准
PUBLISHED_P25 = (0.73, 0.83)
PUBLISHED_P75 = (0.32, 0.38)


def _num(s) -> float:
    return float(re.sub(r"[^\d.]", "", str(s or "0")) or 0)


def build_map() -> dict[tuple, str]:
    """(bucket, contract_ym, round(price)) -> 真实路名。面积用于消歧。"""
    out: dict[tuple, str] = {}
    for slug, (bucket, road) in ATTRIBUTION.items():
        p = os.path.join(IS_DIR, f"{slug}_sale.json")
        if not os.path.exists(p):
            print(f"  [skip] 没有 {slug} 的 IS 采集")
            continue
        with open(p, encoding="utf-8") as f:
            rows = json.load(f)["rows"]
        for r in rows:
            dt = datetime.strptime(r["date"], "%d %b %Y")
            out[(bucket, dt.strftime("%Y-%m"), round(_num(r["price"])))] = road
    return out


def real_road(t: dict, amap: dict) -> str | None:
    return amap.get(((t["street"] or "").upper(), t["contract_ym"], round(t["price"])))


def main() -> None:
    store = (TransactionStore.load().is_pure_landed().exclude_bulk()
             .psf_band(*LANDED_PSF_BAND))
    amap = build_map()
    buckets = sorted({b for b, _ in ATTRIBUTION.values()})
    rows = [t for t in store.txs if (t["street"] or "").upper() in buckets]
    attributed = {id(t): real_road(t, amap) for t in rows}
    n_att = sum(1 for v in attributed.values() if v)
    print(f"归属图:{len(amap)} 条 IS 成交;桶内 {len(rows)} 笔 URA 行,"
          f"其中 {n_att} 笔可归属真实路")
    for b in buckets:
        br = [t for t in rows if (t["street"] or "").upper() == b]
        got = sum(1 for t in br if attributed[id(t)])
        print(f"  {b}: {len(br)} 笔,已归属 {got} ({got/len(br):.0%})")

    subjects = [t for t in rows if t["type_of_sale"] == "Resale"
                and t["contract_ym"] >= "2023-01" and attributed[id(t)]]
    print(f"\n可用 subjects(resale, >=2023-01, 已归属):{len(subjects)}")
    by_road = defaultdict(int)
    for t in subjects:
        by_road[attributed[id(t)]] += 1
    print("  " + " · ".join(f"{k} {v}" for k, v in sorted(by_road.items())))

    idx = PriceIndex.load()
    by_month = defaultdict(list)
    for s in subjects:
        by_month[_prev_ym(s["contract_ym"])].append(s)

    res = {"pooled": [], "split": []}
    dist = defaultdict(lambda: {"p25": 0, "p75": 0, "n": 0})
    for asof_ym, group in sorted(by_month.items()):
        t = month_end(asof_ym)
        view = store.as_of(t, 56)
        ctx = {"asof_ym": asof_ym, "asof_date": t, "index": idx,
               "asof_q": idx.as_of_quarter(t), **shipped_time_ctx(view.txs, asof_ym)}
        mkt_pooled = MarketView(view.txs, asof_ym)
        for subj in group:
            road = attributed[id(subj)]
            # SPLIT:同一个 as-of 视图,但只留下真实路相同的行(归属未知的一律排除 ——
            # 未知不能算作「同路」,那会把整个桶偷渡回来)
            same = [x for x in view.txs
                    if (x["street"] or "").upper() != (subj["street"] or "").upper()
                    or real_road(x, amap) == road]
            mkt_split = MarketView(same, asof_ym)
            for tag, mkt in (("pooled", mkt_pooled), ("split", mkt_split)):
                est = lc2_fitted_curve(subj, mkt, ctx)
                res[tag].append({"pred": est["price"] if est else None,
                                 "actual": subj["price"], "road": road,
                                 "ym": subj["contract_ym"],
                                 "n_comps": est["n_comps"] if est else 0})
            # D(修正版):不能只看「落在母路桶分位数之上的比例」—— 那个比例被引擎在这个
            # 上涨屋苑里的整体偏低(medSigned -5.4%)污染了,直连街道 Loyang Rise 上同样偏高。
            # 要隔离「桶混路」这个效应,必须在**同一笔 subject** 上对比:母路桶分位数 vs
            # 真实路分位数,给出的 p25/p75 差多少。若两者几乎一样 → 混路不改变门槛 → 抑制过度;
            # 若母路桶把门槛显著推低/推高 → 混路确实错置 → 抑制 justified。
            area = subj["area_sqft"]
            adj_pool = _adjusted_comp_psfs(subj, mkt_pooled, ctx)
            adj_split = _adjusted_comp_psfs(subj, mkt_split, ctx)
            if len(adj_pool) >= 4 and len(adj_split) >= 4:
                d = dist[road]
                d["n"] += 1
                p25p, p25s = _pctl(adj_pool, 0.25) * area, _pctl(adj_split, 0.25) * area
                p75p, p75s = _pctl(adj_pool, 0.75) * area, _pctl(adj_split, 0.75) * area
                d["p25"] += abs(p25p / p25s - 1)          # 母路桶 p25 相对真实路偏多少
                d["p75"] += abs(p75p / p75s - 1)

    print("\n=== P 点估值:pooled(母路桶,现行)vs split(真实路)===")
    print(f"{'arm':<8}{'scored':>8}{'declined':>10}{'medAPE':>9}{'sign':>8}{'medSigned':>11}"
          f"{'med n_comps':>12}")
    summ = {}
    for tag in ("pooled", "split"):
        sc = [r for r in res[tag] if r["pred"]]
        apes = sorted(abs(r["pred"] - r["actual"]) / r["actual"] for r in sc)
        sg = [(r["pred"] - r["actual"]) / r["actual"] for r in sc]
        summ[tag] = {"n": len(sc), "dec": len(res[tag]) - len(sc),
                     "ape": median(apes) if apes else float("nan"),
                     "sign": (sum(1 for r in sc if r["actual"] > r["pred"]) / len(sc)
                              if sc else float("nan"))}
        print(f"{tag:<8}{len(sc):>8}{len(res[tag])-len(sc):>10}"
              f"{median(apes):>9.4f}{summ[tag]['sign']:>8.3f}"
              f"{median(sg):>+11.4f}{median([r['n_comps'] for r in sc]):>12.0f}")
    d_ape = (summ["split"]["ape"] - summ["pooled"]["ape"]) * 100
    d_dec = (summ["split"]["dec"] - summ["pooled"]["dec"]) / max(len(res["pooled"]), 1) * 100
    print(f"\n  Δ medAPE (split - pooled) = {d_ape:+.2f}pp   额外 decline = {d_dec:+.1f}pp")
    print(f"  预注册:P1 split 胜需 ≤-0.5pp 且额外 decline ≤15pp;P2 pooled 胜需 >+0.5pp;"
          f"P3 |Δ|<0.5pp 或任一臂 <25 笔 → MONITOR")
    verdict = ("P1 SPLIT WINS" if d_ape <= -0.5 and d_dec <= 15 else
               "P2 POOLING WINS" if d_ape > 0.5 else "P3 INCONCLUSIVE (MONITOR)")
    if min(summ["pooled"]["n"], summ["split"]["n"]) < 25:
        verdict = "P3 INCONCLUSIVE (MONITOR) — 样本 <25"
    print(f"  -> {verdict}")

    print("\n=== P 分路 medAPE ===")
    for road in sorted(by_road):
        line = f"  {road:<16}"
        for tag in ("pooled", "split"):
            sc = [r for r in res[tag] if r["pred"] and r["road"] == road]
            line += (f"{tag} n={len(sc):<3} medAPE="
                     f"{median(sorted(abs(r['pred']-r['actual'])/r['actual'] for r in sc)):.4f}  "
                     if sc else f"{tag} n=0  ")
        print(line)

    print("\n=== D 分布:母路桶门槛 vs 真实路门槛,平均相对偏离(隔离引擎偏低这个共因)===")
    print(f"{'真实路':<16}{'n':>5}{'|Δp25|':>9}{'|Δp75|':>9}   >5% = 混路显著改变门槛")
    d_verdict = "D2 抑制 UNJUSTIFIED —— 母路桶门槛与真实路几乎一致,混路不改变分位数"
    worst = 0.0
    for road in sorted(dist):
        d = dist[road]
        if not d["n"]:
            continue
        a, b = d["p25"] / d["n"], d["p75"] / d["n"]
        worst = max(worst, a, b)
        off = a > 0.05 or b > 0.05
        print(f"{road:<16}{d['n']:>5}{a:>9.1%}{b:>9.1%}   {'<-- 显著' if off else ''}")
        if off:
            d_verdict = "D1 抑制 JUSTIFIED —— 母路桶把门槛推离真实路 >5%"
    print(f"  -> {d_verdict}  (最大偏离 {worst:.1%})")
    print("  注:此判据比较的是**同一 subject 上** pooled 与 split 给出的门槛差,"
          "已隔离引擎在上涨屋苑整体偏低的共因(该偏低在直连街道 Loyang Rise 上同样存在)。")


if __name__ == "__main__":
    main()
