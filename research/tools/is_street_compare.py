"""IS 街道收获 → 真实路名分布 → (可选) 与引擎 LV1 并排 —— alias/hard-case 佐证的最后一公里。

这是报告里两句话的可执行版:
  - 「议价门槛被抑制 —— 用 Investment Suite 拉本路自己的分布」(alias 桶:URA 把多条真实
    路合在一个母路标签下,桶分位数被多数派主导;IS 行带真实门牌路,能切出本路);
  - 「hard case —— 出价前先用 Investment Suite 佐证」(方法分歧≥抑制线 / AI 盲写臂点估
    差>5% 时的规定动作)。

先收获,后比较:
    python research/lib/harvest_street_sale.py "LOYANG RISE"     # 设备上跑,见 read-investment-suite
    python research/tools/is_street_compare.py loyang_rise --road "LOYANG VIEW" --area 1650 \
        --engine-street "LOYANG RISE" --type Terrace

口径警告(工具自己也会打印):IS 的 psf/price 是 RAW 捆绑价(地+房),未按时间/尺寸调整;
引擎的点估值与 p25/p75 活在调整后的口径上。两边只能做「方向与量级」的互证,不能逐数字画等号。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.lib import is_rows  # noqa: E402


def _fmt(x, money=False) -> str:
    if x is None:
        return "—"
    return f"S${x/1e6:.2f}M" if money and x >= 1e6 else f"${x:,.0f}"


def _print_dist(label: str, dist: dict | None) -> None:
    if not dist:
        print(f"  {label}: 无可用行")
        return
    p = (f"p25 {_fmt(dist['psf_p25'])} · " if dist["psf_p25"] else "")
    print(f"  {label}: n={dist['n']} ({dist['first_ym']}..{dist['last_ym']}) · "
          f"{p}中位 {_fmt(dist['psf_med'])} · "
          + (f"p75 {_fmt(dist['psf_p75'])} · " if dist["psf_p75"] else "")
          + f"价格中位 {_fmt(dist['price_med'], money=True)}")
    cl = "、".join(f"{ym} {_fmt(psf)}" for ym, psf in dist["cluster"])
    print(f"    近12月 n={dist['n12']} 中位 {_fmt(dist['med12_psf'])} · 最近3笔:{cl}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("slug", help="is_street 收获 slug(如 cardiff_grove)或 JSON 路径")
    ap.add_argument("--road", help="只看这条真实路(IS 地址里的路名);缺省 = 全部并分路列出")
    ap.add_argument("--area", type=float, help="标的地块 sqft —— 给了就切 ±tol 队列")
    ap.add_argument("--tol", type=float, default=0.06)
    ap.add_argument("--type", default="Terrace",
                    choices=["Terrace", "Semi-detached", "Detached"])
    ap.add_argument("--engine-street", help="URA 街道(母路)—— 给了就跑引擎 LV1 并排")
    ap.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    a = ap.parse_args()

    try:
        d = is_rows.load_harvest(a.slug)
    except FileNotFoundError:
        print(f"没有收获文件:research/data/is_street/{a.slug}_sale.json —— "
              f"先在设备上跑 research/lib/harvest_street_sale.py(见 read-investment-suite skill)")
        return 2

    meta = d.get("meta", {})
    rows = [r for r in d["rows"] if r["_ptype"] and r["_ptype"] != "Strata cluster"]
    strata_n = sum(1 for r in d["rows"] if r["_ptype"] == "Strata cluster")
    out: dict = {"meta": meta, "roads": {}, "strata_excluded": strata_n}

    if not a.json:
        print(f"IS 收获:{meta.get('street')} · {meta.get('n_rows')} 行 · "
              f"{meta.get('harvested_at', '')[:10]} · {meta.get('device')}")
        print("口径:RAW 捆绑 psf(地+房,未调整)· 日粒度 · 仅 caveat 面板"
              + (f" · 剔除 strata-cluster {strata_n} 行" if strata_n else ""))
        print("\n按真实路(IS 地址)分布:")
    for road, rs in sorted(is_rows.by_road(rows).items()):
        dist = is_rows.distribution(rs)
        out["roads"][road] = dist
        if not a.json:
            _print_dist(road, dist)

    sel = rows
    sel_label = "全部路"
    if a.road:
        want = a.road.strip().upper()
        sel = [r for r in rows if r["_road"] == want]
        sel_label = want
        if not sel:
            print(f"\n收获里没有路「{want}」—— 上面列出的是实际存在的路名")
            return 1
    sel = [r for r in sel if r["_ptype"] == a.type] or sel
    if a.area:
        sel = is_rows.cohort(sel, a.area, a.tol)
        sel_label += f" · {a.type} · 队列 ±{a.tol:.0%} @ {a.area:,.0f} sqft"
    sel_dist = is_rows.distribution(sel)
    out["selection"] = {"label": sel_label, "dist": sel_dist}
    if not a.json:
        print(f"\n选定切片({sel_label}):")
        _print_dist("切片", sel_dist)

    if a.engine_street and a.area:
        from researcher.engine.value_landed import LandedSpec, value_landed  # noqa: E402
        v = value_landed(LandedSpec(street=a.engine_street.strip().upper(),
                                    land_area_sqft=a.area, property_type=a.type))
        if v.get("error"):
            out["engine"] = {"error": v["error"]}
            if not a.json:
                print(f"\n引擎:{v['error']} — {v.get('message', '')[:120]}")
        else:
            fv, bg = v["fair_value"], v["buyer_guidance"]
            out["engine"] = {"psf": fv["land_psf"], "price": fv["price"],
                             "low": fv["low"], "high": fv["high"],
                             "confidence": fv["confidence"],
                             "p25": bg.get("attractive_below"), "p75": bg.get("walk_away_above")}
            if not a.json and sel_dist:
                gap = sel_dist["med12_psf"] and fv["land_psf"] and \
                    sel_dist["med12_psf"] / fv["land_psf"] - 1
                print(f"\n引擎 LV1({a.engine_street.upper()} · 调整后口径):"
                      f"点 {_fmt(fv['land_psf'])} psf({_fmt(fv['price'], money=True)})· "
                      f"区间 {_fmt(fv['low'], money=True)}–{_fmt(fv['high'], money=True)} · "
                      f"置信 {fv['confidence']}/100")
                if gap is not None:
                    print(f"互证读法:IS 本路近12月 RAW 中位与引擎点差 {gap*100:+.0f}% —— "
                          f"口径不同(RAW vs 调整后),|差|≤10% 读作互证;更大就先查:面积口径、"
                          f"condition 结构差、或母路桶被多数派带偏(EXP-0019)。")
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
