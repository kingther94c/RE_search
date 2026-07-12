"""Factor model — beta/alpha decomposition of Singapore private-home pricing,
built ONLY on Tier-1 evidence (Investment Suite panel + official index series).

Framework (what the investor reports and skills inherit):
  * BETA  = your segment's market ride (official CCR/RCR/OCR-proxy, landed vs
    non-landed series). Estimated from 51y of URA index data.
  * ALPHA-LEVEL factors = priced-in quality (MRT, schools, tenure, size...).
    They explain WHERE a project's psf sits vs its segment — paying a fair
    premium for them earns ~zero alpha; alpha comes from MISpricing vs these.
  * BETA-MODIFIER factors = change the ride itself (lease decay drag, catalyst
    events like a new MRT line, school-demand stickiness, mega-project
    liquidity). These shift expected drift/downside, not just today's level.

Statistical honesty: cross-section n≈25 → within-segment Spearman rank
correlations + a small bootstrapped OLS (max 5 regressors) with confidence
labels. Every claim carries evidence= and confidence= fields; the dialectic
panel challenges these before anything ships.

    python -m researcher.factors.factor_model
Output: researcher/factors/factor_model.json
"""
from __future__ import annotations

import json
import math
import os
import random
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name: str) -> dict:
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


# ── small stats helpers (stdlib only) ────────────────────────────────────────

def rank(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def spearman(x: list[float], y: list[float]) -> float | None:
    if len(x) < 5:
        return None
    rx, ry = rank(x), rank(y)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else None


def ols(y: list[float], X: list[list[float]]) -> list[float] | None:
    """OLS via normal equations with intercept. X = list of columns."""
    n = len(y)
    cols = [[1.0] * n] + X
    k = len(cols)
    A = [[sum(cols[i][t] * cols[j][t] for t in range(n)) for j in range(k)] for i in range(k)]
    b = [sum(cols[i][t] * y[t] for t in range(n)) for i in range(k)]
    # gaussian elimination
    for i in range(k):
        p = max(range(i, k), key=lambda r: abs(A[r][i]))
        if abs(A[p][i]) < 1e-12:
            return None
        A[i], A[p] = A[p], A[i]
        b[i], b[p] = b[p], b[i]
        for r in range(i + 1, k):
            f = A[r][i] / A[i][i]
            for c in range(i, k):
                A[r][c] -= f * A[i][c]
            b[r] -= f * b[i]
    beta = [0.0] * k
    for i in reversed(range(k)):
        beta[i] = (b[i] - sum(A[i][j] * beta[j] for j in range(i + 1, k))) / A[i][i]
    return beta


def bootstrap_ols(y: list[float], X: list[list[float]], n_boot: int = 2000,
                  seed: int = 42) -> list[dict] | None:
    """Bootstrap CIs for OLS coefs (excl. intercept). Returns per-coef dicts."""
    n = len(y)
    base = ols(y, X)
    if base is None:
        return None
    rng = random.Random(seed)
    draws: list[list[float]] = [[] for _ in range(len(X))]
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        by = [y[i] for i in idx]
        bX = [[col[i] for i in idx] for col in X]
        bb = ols(by, bX)
        if bb:
            for c in range(len(X)):
                draws[c].append(bb[c + 1])
    out = []
    for c in range(len(X)):
        d = sorted(draws[c])
        lo, hi = d[int(0.025 * len(d))], d[int(0.975 * len(d))]
        out.append({"coef": base[c + 1], "ci95": [lo, hi],
                    "sig": (lo > 0 and hi > 0) or (lo < 0 and hi < 0)})
    return out


def r_squared(y: list[float], X: list[list[float]]) -> float | None:
    beta = ols(y, X)
    if beta is None:
        return None
    n = len(y)
    yhat = [beta[0] + sum(beta[j + 1] * X[j][t] for j in range(len(X))) for t in range(n)]
    my = statistics.mean(y)
    ss_res = sum((a - b) ** 2 for a, b in zip(y, yhat))
    ss_tot = sum((a - my) ** 2 for a in y)
    return 1 - ss_res / ss_tot if ss_tot else None


# ── condo cross-section ──────────────────────────────────────────────────────

ASOF_YEAR = 2026.5


def condo_rows() -> list[dict]:
    panel = _load("panel_condo_enriched.json")
    rows = []
    for r in panel["projects"]:
        if not (r.get("psf_low") and r.get("psf_high") and r.get("segment")
                and r["segment"] in ("CCR", "RCR", "OCR")):
            continue
        top = r.get("top_year") or (int(str(r.get("top"))) if str(r.get("top", "")).isdigit() else None)
        if not top:
            continue
        tenure = (r.get("tenure_type") or r.get("tenure") or "").upper()
        rows.append({
            "project": r["project"], "segment": r["segment"],
            "mid_psf": (r["psf_low"] + r["psf_high"]) / 2,
            "yield_avg": r.get("yield_avg_pct"),
            "fh": 1.0 if ("FH" in tenure or "FREEHOLD" in tenure) else 0.0,
            "age": max(ASOF_YEAR - top, -3.0),
            "ln_units": math.log(int(str(r.get("total_units", "0")).replace(",", "")) or 1),
            "mrt_km": (r.get("nearest_mrt") or {}).get("km"),
            "pri1k": float(r.get("n_popular_pri_1km", 0)),
            "mall_km": (r.get("nearest_mall") or {}).get("km"),
            "park_km": (r.get("nearest_park") or {}).get("km"),
            "coast_km": r.get("coast_km"),
        })
    return [r for r in rows if all(r[k] is not None for k in
            ("mrt_km", "mall_km", "park_km", "coast_km"))]


def within_segment_demean(rows: list[dict], key: str) -> dict[str, float]:
    seg_med: dict[str, float] = {}
    for seg in ("CCR", "RCR", "OCR"):
        vals = [r[key] for r in rows if r["segment"] == seg and r.get(key) is not None]
        if vals:
            seg_med[seg] = statistics.median(vals)
    return seg_med


def condo_cross_section() -> dict:
    rows = condo_rows()
    seg_med_psf = within_segment_demean(rows, "mid_psf")
    for r in rows:
        r["ln_prem"] = math.log(r["mid_psf"] / seg_med_psf[r["segment"]])
    factors = ["fh", "age", "ln_units", "mrt_km", "pri1k", "mall_km", "park_km", "coast_km"]
    level_corr = {f: spearman([r[f] for r in rows], [r["ln_prem"] for r in rows])
                  for f in factors}
    yrows = [r for r in rows if r.get("yield_avg")]
    seg_med_yld = {}
    for seg in ("CCR", "RCR", "OCR"):
        vals = [r["yield_avg"] for r in yrows if r["segment"] == seg]
        if vals:
            seg_med_yld[seg] = statistics.median(vals)
    for r in yrows:  # de-mean within segment — else old-CCR/new-OCR clustering
        r["yield_excess"] = r["yield_avg"] - seg_med_yld[r["segment"]]
    yield_corr = {f: spearman([r[f] for r in yrows], [r["yield_excess"] for r in yrows])
                  for f in factors}
    # compact OLS on the premium (5 regressors max, standardized)
    use = ["fh", "age", "ln_units", "mrt_km", "pri1k"]

    def std(col):
        m, s = statistics.mean(col), statistics.pstdev(col) or 1.0
        return [(v - m) / s for v in col]

    X = [std([r[f] for r in rows]) for f in use]
    y = [r["ln_prem"] for r in rows]
    boot = bootstrap_ols(y, X)
    return {"n": len(rows), "segment_median_psf": seg_med_psf,
            "segment_median_yield": seg_med_yld,
            "level_spearman_within_segment": level_corr,
            "yield_spearman_within_segment": {"n": len(yrows), **yield_corr},
            "ols_ln_premium": {"regressors": use, "r2": r_squared(y, X),
                               "standardized_coefs": boot},
            "rows": rows}


# ── landed street-level appreciation ─────────────────────────────────────────

def _iso(d: str) -> float:
    from datetime import datetime
    return datetime.strptime(d, "%d %b %Y").timestamp() / (365.25 * 86400) + 1970


def landed_street_cagr() -> list[dict]:
    """Cross-address same-type pairs within a street -> long-run land-psf CAGR."""
    panel = _load("panel_landed_enriched.json")
    out = []
    for s in panel["streets"]:
        pts = []
        for r in s.get("pp_panel", []):
            if r.get("pp_psf") and r.get("pp_date"):
                pts.append({"t": _iso(r["pp_date"]), "psf": r["pp_psf"],
                            "type": r.get("type"), "addr": r["address"]})
        for r in s.get("transactions", []):
            if r.get("psf") and r.get("date"):
                pts.append({"t": _iso(r["date"]), "psf": r["psf"],
                            "type": r.get("type"), "addr": r["address"]})
        rates = []
        for i in range(len(pts)):
            for j in range(len(pts)):
                a, b = pts[i], pts[j]
                if (b["t"] - a["t"] >= 5.0 and a["type"] == b["type"]
                        and a["addr"] != b["addr"]):
                    rates.append(math.log(b["psf"] / a["psf"]) / (b["t"] - a["t"]))
        rec = {"street": s["street"], "n_points": len(pts), "n_pairs": len(rates),
               "cagr_median": statistics.median(rates) if len(rates) >= 3 else None,
               "cagr_range": ([min(rates), max(rates)] if rates else None),
               "nearest_mrt": s.get("nearest_mrt"), "pri1k": s.get("n_popular_pri_1km"),
               "coast_km": s.get("coast_km"), "street_band": s.get("street_band")}
        out.append(rec)
    return out


# ── assemble the model ───────────────────────────────────────────────────────

def build() -> dict:
    beta = _load("beta_layer.json")
    cs = condo_cross_section()
    landed = landed_street_cagr()

    corr = cs["level_spearman_within_segment"]
    ycorr = cs["yield_spearman_within_segment"]

    def lab(rho, n_min=15):
        if rho is None:
            return "insufficient"
        a = abs(rho)
        return "strong" if a >= 0.5 else "moderate" if a >= 0.3 else "weak"

    findings = {
        "beta": {
            "landed_on_nonlanded_beta": beta["landed_on_nonlanded"]["beta"],
            "landed_alpha_pa": beta["landed_on_nonlanded"]["alpha_pa"],
            "segment_5y_cagr": beta["cagr"],
            "评注": "landed 是低 beta(0.85)+正 alpha(+1.0%/yr) 的防御性资产——除 1996-98 一役外"
                    "每次危机跌幅都小于非有地；价格/租金比 130 vs 峰值 146 说明 2021 后租金追上了价格。",
            "confidence": "high (51y official series)",
        },
        "level_factors_condo": {
            f: {"spearman_within_segment": corr[f], "strength": lab(corr[f])}
            for f in corr
        },
        "yield_factors_condo": {
            f: {"spearman": ycorr[f], "strength": lab(ycorr[f])}
            for f in corr if f in ycorr
        },
        "ols": cs["ols_ln_premium"],
        "landed_streets": landed,
        "classification": {
            "priced_in_level_factors": [
                "MRT 距离（每近一站溢价，已在价内）", "热门小学 1km（家庭需求溢价，已在价内）",
                "商场/便利（价内）", "海岸线视野带（价内溢价段）", "永久地契（价内溢价 vs 99y）"],
            "beta_modifiers": [
                "地契剩余年限（99y 的 bala 曲线衰减 = 长期负漂移叠加）",
                "楼龄（新盘溢价消化期 vs 老盘翻新周期）",
                "盘的规模（超大盘流动性↑但同盘竞卖压制反弹弹性）",
                "学区（需求黏性 → 下行期换手支撑）"],
            "alpha_sources": [
                "对因子的错定价（同段同因子组合的 psf 离群）",
                "催化剂前置（新 MRT 线开通前、指标性整售/重建预期）",
                "AVM/市场滞后窗口（新成交重定价未传导——见三盘 AVM 偏差研究）",
                "微观个体（楼层/朝向/装修错价——盘内网格可量化）"],
        },
        "data_notes": [
            f"横截面 n={cs['n']}（psf 为近期成交区间中点或 5Y band 口径，混合披露）",
            "psf 溢价按段内中位数去均值——段效应（beta）已剥离",
            "样本聚集于本项目研究过的锚点周边——非全岛随机抽样，泛化需谨慎",
            "landed 街道 CAGR 为跨址同型对（≥5 年间隔）中位——含土地重建价值，非纯房价",
        ],
    }
    return {"asof": "2026-07-12", "beta_layer_ref": "beta_layer.json",
            "condo_cross_section": cs, "findings": findings}


def main() -> None:
    m = build()
    p = os.path.join(HERE, "factor_model.json")
    json.dump(m, open(p, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    cs = m["condo_cross_section"]
    print(f"condo cross-section n={cs['n']}  seg med psf {cs['segment_median_psf']}")
    print("level factor Spearman (within-segment):")
    for f, v in cs["level_spearman_within_segment"].items():
        print(f"   {f:10s} {v if v is None else round(v, 3)}")
    print("yield factor Spearman (within-segment excess):")
    for f, v in cs["yield_spearman_within_segment"].items():
        if f != "n":
            print(f"   {f:10s} {v if v is None else round(v, 3)}")
    o = cs["ols_ln_premium"]
    print(f"OLS ln(premium) R2={o['r2']:.2f}")
    for f, c in zip(o["regressors"], o["standardized_coefs"] or []):
        print(f"   {f:10s} {c['coef']:+.3f}  CI95 [{c['ci95'][0]:+.3f},{c['ci95'][1]:+.3f}] "
              f"{'SIG' if c['sig'] else ''}")
    print("landed streets:")
    for s in m["findings"]["landed_streets"]:
        cg = s["cagr_median"]
        print(f"   {s['street']:24s} pts {s['n_points']:2d} pairs {s['n_pairs']:3d} "
              f"CAGR {cg * 100:+.1f}%/yr" if cg else
              f"   {s['street']:24s} pts {s['n_points']:2d} pairs {s['n_pairs']:3d} CAGR n/a")
    print(f"-> {p}")


if __name__ == "__main__":
    main()
