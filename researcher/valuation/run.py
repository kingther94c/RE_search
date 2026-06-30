"""Apply the valuation engine to #18-03 Spottiswoode Suites, build the full
buy/sell advisory, validate the model on a 1BR, and write results to JSON for
the HTML report.  Run:  python -m researcher.valuation.run
"""
from __future__ import annotations

import json
import os

try:  # package import (python -m researcher.valuation.run)
    from researcher.valuation import dataset as D
    from researcher.valuation.engine import Comp, Params, Subject, format_grid, value
except ImportError:  # script: python researcher/valuation/run.py from this dir
    import dataset as D
    from engine import Comp, Params, Subject, format_grid, value

OUT = os.path.dirname(os.path.abspath(__file__))


def comps_from_transactions(exclude_unit_floor: int | None = None) -> list[Comp]:
    out = []
    for dt, lvl, stack, beds, sqft, psf, price in D.TRANSACTIONS:
        out.append(Comp(f"{dt} L{lvl} #{stack} {beds}BR {sqft}sf", dt, lvl, beds, sqft, psf, price))
    return out


def bsd(price: float) -> float:
    tiers = [(180_000, 0.01), (180_000, 0.02), (640_000, 0.03),
             (500_000, 0.04), (1_500_000, 0.05), (float("inf"), 0.06)]
    duty, rem = 0.0, price
    for band, rate in tiers:
        take = min(rem, band)
        duty += take * rate
        rem -= take
        if rem <= 0:
            break
    return duty


def money(x) -> str:
    return f"S${x:,.0f}"


# ── 1. Subject valuation ─────────────────────────────────────────────────────
p = Params(asof="2026-06-30", time_trend_pa=0.018, floor_premium_pp=0.003,
           size_elasticity=-0.08, compact3br_discount=0.03)

subject = Subject(name="#18-03 Spottiswoode Suites", size_sqft=743, floor=18, bedrooms=3)
comps = comps_from_transactions()
anchor = Comp("#18-03 own sale 2021", "2021-05-07", 18, 3, 743, 2020, 1_500_000)

val = value(subject, comps, p, same_line_anchor=anchor, anchor_weight=2.0)

print("=" * 78)
print(f"SUBJECT: {subject.name}  ({subject.size_sqft} sqft, {subject.bedrooms}BR, "
      f"L{subject.floor}, {subject.tenure})")
print("=" * 78)
print(format_grid(val))
print("-" * 78)
print(f"Same-line anchor (2021 sale, time-adjusted): {val.anchor_psf:,.0f} psf")
print(f"\nMODEL ESTIMATE : {val.estimate_psf:,.0f} psf  ->  {money(val.estimate_price)} "
      f"(rounded {money(val.estimate_price_rounded)})")
print(f"RANGE          : {val.low_psf:,.0f}–{val.high_psf:,.0f} psf  "
      f"({money(val.low_price)} – {money(val.high_price)})")
print(f"APP Est. Val   : {D.SUBJECT['app_est_psf']:,} psf  ->  {money(D.SUBJECT['app_est_val'])}")
delta = val.estimate_price - D.SUBJECT["app_est_val"]
print(f"vs APP AVM     : {delta:+,.0f}  ({delta / D.SUBJECT['app_est_val'] * 100:+.1f}%)")

# ── 2. Buy/sell advisory metrics ─────────────────────────────────────────────
est = val.estimate_price_rounded
# rental: subject is 743 sqft 3BR -> use 700-800 3BR comps
rent_comps = [r for r in D.RENTALS if r[0] == 3 and r[1] == "700-800"]
mo_rent = sum(r[3] for r in rent_comps) / len(rent_comps)
annual_rent = mo_rent * 12
gross_yield = annual_rent / est
net_yield = gross_yield - 0.011  # ~1.1pp for tax/maintenance/vacancy/agent

last = D.SUBJECT["last_txn_price"]
cap_gain = est - last
cap_gain_pct = cap_gain / last
yrs_held = 5.14
cagr = (est / last) ** (1 / yrs_held) - 1

advisory = {
    "estimate_price": est,
    "estimate_psf": round(val.estimate_psf),
    "range_price": [round(val.low_price, -3), round(val.high_price, -3)],
    "range_psf": [round(val.low_psf), round(val.high_psf)],
    "app_est_val": D.SUBJECT["app_est_val"],
    "vs_app_pct": round(delta / D.SUBJECT["app_est_val"] * 100, 1),
    "monthly_rent_est": round(mo_rent),
    "annual_rent_est": round(annual_rent),
    "gross_yield_pct": round(gross_yield * 100, 2),
    "net_yield_pct": round(net_yield * 100, 2),
    "dev_avg_yield_pct": D.NEARBY[0]["yield_avg"],
    "owner_cost_2021": last,
    "unrealised_gain": cap_gain,
    "unrealised_gain_pct": round(cap_gain_pct * 100, 1),
    "cagr_since_2021_pct": round(cagr * 100, 1),
    "bsd_on_estimate": round(bsd(est)),
    "absd_sc_2nd": round(est * 0.20),
    "absd_foreigner": round(est * 0.60),
    "ssd_if_flip_1yr": round(est * 0.16),
}

print("\n" + "=" * 78)
print("BUY / SELL ADVISORY")
print("=" * 78)
print(f"Indicative rent (3BR 700-800): {money(mo_rent)}/mo  ->  gross yield "
      f"{gross_yield*100:.2f}%  (net ~{net_yield*100:.2f}%)  vs dev avg 2.91%")
print(f"Owner unrealised gain since 2021: {money(cap_gain)} ({cap_gain_pct*100:+.1f}%, "
      f"CAGR {cagr*100:.1f}%/yr); SSD now 0% (held >4y)")
print(f"Buyer entry costs: BSD {money(bsd(est))}; ABSD 2nd-prop SC {money(est*0.20)}; "
      f"foreigner {money(est*0.60)}")

# ── 3. Model validation on a 1BR (should land near recent 1BR transactions) ──
v1 = value(Subject("validate 1BR 452sf L20", 452, 20, 1), comps, p)
print("\n" + "=" * 78)
print("VALIDATION — 1BR 452 sqft L20 (recent 1BR comps cluster ~2,150–2,430 psf)")
print("=" * 78)
print(f"Model: {v1.estimate_psf:,.0f} psf -> {money(v1.estimate_price)} "
      f"(recent 1BR resales: {money(970_000)}–{money(1_085_000)})")

# ── 4. Save results for the report ───────────────────────────────────────────
results = {
    "subject": D.SUBJECT,
    "valuation": {
        "estimate_psf": round(val.estimate_psf),
        "estimate_price": est,
        "low_psf": round(val.low_psf), "high_psf": round(val.high_psf),
        "low_price": round(val.low_price, -3), "high_price": round(val.high_price, -3),
        "anchor_psf": round(val.anchor_psf),
        "grid": [
            {"label": r.label, "raw_psf": round(r.raw_psf),
             "time": round(r.time_adj, 3), "floor": round(r.floor_adj, 3),
             "size": round(r.size_adj, 3), "type": round(r.type_adj, 3),
             "adj_psf": round(r.adj_psf), "weight": round(r.weight, 2)}
            for r in val.grid
        ],
        "params": vars(p),
    },
    "advisory": advisory,
    "validation_1br": {"estimate_psf": round(v1.estimate_psf),
                       "estimate_price": round(v1.estimate_price, -3)},
}
with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\nsaved -> {os.path.join(OUT, 'results.json')}")
