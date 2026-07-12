"""Market beta layer — everything the factor study needs from the OFFICIAL
price/rental index series (researcher/marketdata/*.json, SingStat-republished
URA data).

Computes, per segment (All / Landed / Non-Landed):
  * CAGR over standard windows (5y/10y/15y/20y, since 1998Q4, since 2009Q1)
  * annualized volatility of quarterly log returns, max drawdown (dated)
  * landed-vs-non-landed: OLS beta & correlation of quarterly returns,
    cumulative relative strength, named cycle table with per-cycle returns
  * price-to-rent ratio drift (valuation stretch) where rental series overlap

    python -m researcher.factors.beta_layer      # compute + persist + print
Output: researcher/factors/beta_layer.json

Pure stdlib; all functions offline-testable against the committed JSONs.
"""
from __future__ import annotations

import json
import math
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
MARKET = os.path.join(os.path.dirname(HERE), "marketdata")

# URA-history cycle boundaries (quarter of index peak/trough, well documented)
CYCLES = [
    ("1996 顶 → 1998 亚洲金融危机底", "1996Q2", "1998Q4"),
    ("1998 底 → 2000 反弹顶", "1998Q4", "2000Q2"),
    ("2000 顶 → 2004 SARS 底", "2000Q2", "2004Q1"),
    ("2004 底 → 2008 全球金融危机前顶", "2004Q1", "2008Q2"),
    ("2008 顶 → 2009 GFC 底", "2008Q2", "2009Q2"),
    ("2009 底 → 2013 降温措施顶", "2009Q2", "2013Q3"),
    ("2013 顶 → 2017 TDSR 冷却底", "2013Q3", "2017Q2"),
    ("2017 底 → 2019 顶", "2017Q2", "2019Q3"),
    ("2019 顶 → 2020 COVID 底", "2019Q3", "2020Q1"),
    ("2020 底 → 2026 现水平", "2020Q1", "2026Q1"),
]


def _load(name: str) -> dict:
    with open(os.path.join(MARKET, f"{name}.json"), encoding="utf-8") as f:
        return json.load(f)


def _qnum(q: str) -> float:
    return int(q[:4]) + (int(q[5]) - 1) / 4.0


def series_map(tbl: dict, name: str) -> dict[str, float]:
    return {q: v for q, v in tbl["series"][name]}


def window_cagr(s: dict[str, float], start: str, end: str) -> float | None:
    if start not in s or end not in s:
        return None
    yrs = _qnum(end) - _qnum(start)
    return (s[end] / s[start]) ** (1 / yrs) - 1 if yrs > 0 else None


def quarterly_log_returns(s: dict[str, float]) -> list[tuple[str, float]]:
    qs = sorted(s, key=_qnum)
    return [(b, math.log(s[b] / s[a])) for a, b in zip(qs, qs[1:])]


def ann_vol(s: dict[str, float], since: str | None = None) -> float:
    rets = [r for q, r in quarterly_log_returns(s) if since is None or _qnum(q) >= _qnum(since)]
    return statistics.stdev(rets) * 2 if len(rets) > 3 else float("nan")  # *sqrt(4)


def max_drawdown(s: dict[str, float]) -> dict:
    qs = sorted(s, key=_qnum)
    peak, peak_q, worst = -1.0, "", {"dd": 0.0}
    for q in qs:
        if s[q] > peak:
            peak, peak_q = s[q], q
        dd = s[q] / peak - 1
        if dd < worst["dd"]:
            worst = {"dd": dd, "peak": peak_q, "trough": q}
    return worst


def beta_corr(dep: dict[str, float], indep: dict[str, float],
              since: str = "1998Q4") -> dict:
    """OLS beta + correlation of quarterly log returns, dep on indep."""
    d = dict(quarterly_log_returns(dep))
    i = dict(quarterly_log_returns(indep))
    qs = [q for q in d if q in i and _qnum(q) >= _qnum(since)]
    x = [i[q] for q in qs]
    y = [d[q] for q in qs]
    n = len(qs)
    mx, my = sum(x) / n, sum(y) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y)) / (n - 1)
    vx = sum((a - mx) ** 2 for a in x) / (n - 1)
    vy = sum((b - my) ** 2 for b in y) / (n - 1)
    return {"beta": cov / vx, "corr": cov / math.sqrt(vx * vy),
            "alpha_pa": (my - (cov / vx) * mx) * 4, "n_quarters": n, "since": since}


def compute() -> dict:
    px = _load("price_index")
    rent = _load("rental_index")
    segs = {"all": series_map(px, "Residential Properties"),
            "landed": series_map(px, "Landed"),
            "nonlanded": series_map(px, "Non-Landed")}
    latest = max(segs["all"], key=_qnum)

    def windows(s):
        y = int(latest[:4])
        qq = latest[4:]
        return {f"{n}y": window_cagr(s, f"{y - n}{qq}", latest) for n in (5, 10, 15, 20)} | {
            "since_1998Q4": window_cagr(s, "1998Q4", latest),
            "since_2009Q1": window_cagr(s, "2009Q1", latest)}

    out = {"asof_quarter": latest,
           "source": px.get("source"),
           "levels_2009q1_100": {k: segs[k][latest] for k in segs},
           "cagr": {k: windows(segs[k]) for k in segs},
           "vol_pa_since_1998": {k: ann_vol(segs[k], "1998Q4") for k in segs},
           "max_drawdown": {k: max_drawdown(segs[k]) for k in segs},
           "landed_on_nonlanded": beta_corr(segs["landed"], segs["nonlanded"]),
           "nonlanded_on_all": beta_corr(segs["nonlanded"], segs["all"]),
           "landed_on_all": beta_corr(segs["landed"], segs["all"]),
           "cycles": []}
    for label, a, b in CYCLES:
        row = {"cycle": label, "from": a, "to": b}
        for k in segs:
            if a in segs[k] and b in segs[k]:
                row[k] = round(segs[k][b] / segs[k][a] - 1, 4)
        out["cycles"].append(row)
    # price-to-rent drift: rebase both to 2009Q1=100 already; ratio>100 = pricier vs rent
    ratio = {}
    rent_nl = series_map(rent, "Non-Landed")
    for q, v in segs["nonlanded"].items():
        if q in rent_nl:
            ratio[q] = round(v / rent_nl[q] * 100, 1)
    qs = sorted(ratio, key=_qnum)
    out["price_to_rent_nonlanded"] = {
        "first": [qs[0], ratio[qs[0]]], "last": [qs[-1], ratio[qs[-1]]],
        "peak": max(((q, r) for q, r in ratio.items()), key=lambda t: t[1]),
        "series_tail": [[q, ratio[q]] for q in qs[-12:]]}
    return out


def main() -> None:
    out = compute()
    p = os.path.join(HERE, "beta_layer.json")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"asof {out['asof_quarter']}  levels(2009Q1=100): " +
          ", ".join(f"{k}={v:.1f}" for k, v in out["levels_2009q1_100"].items()))
    for k, w in out["cagr"].items():
        print(f"  {k:10s} " + "  ".join(
            f"{n}:{(v * 100):+.2f}%" if v is not None else f"{n}:n/a" for n, v in w.items()))
    lb = out["landed_on_nonlanded"]
    print(f"  landed vs nonlanded: beta {lb['beta']:.2f} corr {lb['corr']:.2f} "
          f"alpha {lb['alpha_pa'] * 100:+.2f}%/yr (since {lb['since']}, n={lb['n_quarters']})")
    for c in out["cycles"]:
        print(f"  {c['cycle']:32s} landed {c.get('landed', float('nan')) * 100:+7.1f}%  "
              f"nonlanded {c.get('nonlanded', float('nan')) * 100:+7.1f}%")
    pr = out["price_to_rent_nonlanded"]
    print(f"  price/rent nonlanded: {pr['first']} -> {pr['last']} (peak {pr['peak']})")
    print(f"-> {p}")


if __name__ == "__main__":
    main()
