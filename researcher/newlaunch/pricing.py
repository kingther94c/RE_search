"""New-launch entry / breakeven / ROI math.

Turns an indicative launch PSF into the numbers that actually decide a new-launch
investment: all-in entry cost (BSD + ABSD), the **breakeven exit PSF** (and the
appreciation needed just to break even after costs), projected ROI on cash at a
few appreciation scenarios, and gross/net yield. Models BUC **progressive payment**
(no rent + ramped interest during construction). Pure stdlib; illustrative, not advice.

    from researcher.newlaunch.pricing import analyze
    r = analyze({"psf": 2200, "size_sqft": 700, "absd_pct": 0, "rent_psf_month": 5.0})
"""
from __future__ import annotations

from dataclasses import dataclass, field


def bsd(price: float) -> float:
    tiers = [(180_000, .01), (180_000, .02), (640_000, .03), (500_000, .04),
             (1_500_000, .05), (float("inf"), .06)]
    duty, rem = 0.0, price
    for band, rate in tiers:
        take = min(rem, band)
        duty += take * rate
        rem -= take
        if rem <= 0:
            break
    return duty


def ssd_rate(holding_years: float) -> float:
    """Seller's Stamp Duty on exit (residential bought on/after 4 Jul 2025):
    16/12/8/4% within years 1-4, zero after. Holding counts from purchase."""
    if holding_years <= 1:
        return .16
    if holding_years <= 2:
        return .12
    if holding_years <= 3:
        return .08
    if holding_years <= 4:
        return .04
    return 0.0


@dataclass
class Result:
    price: float
    stamp_total: float
    cash_outlay: float
    gross_yield: float
    net_yield: float
    breakeven_exit_psf: float
    breakeven_appreciation_pct: float
    scenarios: list = field(default_factory=list)  # (appr_pa, exit_psf, profit, roi_cash, annualised)


def analyze(p: dict) -> Result:
    psf = p["psf"]
    size = p["size_sqft"]
    price = psf * size
    ltv = p.get("ltv", 0.75)
    rate = p.get("mortgage_rate", 0.03)
    absd_pct = p.get("absd_pct", 0) / 100 if p.get("absd_pct", 0) > 1 else p.get("absd_pct", 0)
    holding = p.get("holding_years", 5)
    constr = p.get("construction_years", 3)      # BUC years: no rent + ramped interest
    rent_psf_m = p.get("rent_psf_month", 0)
    occ = p.get("occupancy", 0.95)
    sell_cost = p.get("sell_cost_pct", 0.02)     # agent + legal on exit

    duty = bsd(price) + price * absd_pct
    downpay = price * (1 - ltv)
    cash_outlay = downpay + duty
    loan = price * ltv

    rented_years = max(0, holding - constr)
    interest = loan * rate * (constr * 0.45 + rented_years)   # ramped during BUC
    annual_rent = rent_psf_m * size * 12
    rent_income = annual_rent * rented_years * occ
    net_carry = interest - rent_income

    gross_yield = (annual_rent / price) if price else 0
    net_yield = gross_yield - 0.011 if annual_rent else 0

    # exit-side frictions: selling cost + SSD if exiting inside the 4-year window
    exit_ssd = ssd_rate(holding)
    # breakeven: exit*(1 - sell - ssd) = price + duty + net_carry
    breakeven_exit_price = (price + duty + net_carry) / (1 - sell_cost - exit_ssd)
    breakeven_exit_psf = breakeven_exit_price / size
    breakeven_appr = breakeven_exit_price / price - 1

    scenarios = []
    for appr in p.get("appreciation_scenarios", [0.0, 0.02, 0.04]):
        exit_price = price * (1 + appr) ** holding
        net_sale = exit_price * (1 - sell_cost - exit_ssd)
        profit = net_sale - price - duty - net_carry
        roi_cash = profit / cash_outlay if cash_outlay else 0
        annualised = (1 + roi_cash) ** (1 / holding) - 1 if roi_cash > -1 else -1
        scenarios.append((appr, exit_price / size, profit, roi_cash, annualised))

    return Result(price, duty, cash_outlay, gross_yield, net_yield,
                  breakeven_exit_psf, breakeven_appr, scenarios)


def money(x):
    return f"S${x:,.0f}"


def fmt(p: dict, r: Result) -> str:
    out = [
        f"New-launch pricing — {p.get('name','?')}",
        f"  entry psf S${p['psf']:,} x {p['size_sqft']:,} sqft = {money(r.price)}",
        f"  stamp duty (BSD+ABSD): {money(r.stamp_total)}   cash outlay (downpay+duty): {money(r.cash_outlay)}",
    ]
    if r.gross_yield:
        out.append(f"  yield: gross {r.gross_yield*100:.2f}%  net ~{r.net_yield*100:.2f}%")
    hold = p.get("holding_years", 5)
    if ssd_rate(hold):
        out.append(f"  NOTE: exit at year {hold} pays {ssd_rate(hold)*100:.0f}% SSD (4yr 16/12/8/4 regime) — included below")
    out.append(f"  BREAKEVEN exit: S${r.breakeven_exit_psf:,.0f} psf  "
               f"(+{r.breakeven_appreciation_pct*100:.1f}% just to break even after costs)")
    out.append(f"  {'appr/yr':>8}{'exit psf':>11}{'profit':>14}{'ROI/cash':>10}{'annualised':>12}")
    for appr, xpsf, profit, roi, ann in r.scenarios:
        out.append(f"  {appr*100:>7.0f}%{xpsf:>11,.0f}{money(profit):>14}"
                   f"{roi*100:>9.1f}%{ann*100:>11.1f}%")
    return "\n".join(out)


if __name__ == "__main__":
    ex = {"name": "example 2BR new launch", "psf": 2200, "size_sqft": 700,
          "absd_pct": 0, "holding_years": 5, "construction_years": 3,
          "rent_psf_month": 5.0, "mortgage_rate": 0.03,
          "appreciation_scenarios": [0.0, 0.02, 0.04]}
    print(fmt(ex, analyze(ex)))
