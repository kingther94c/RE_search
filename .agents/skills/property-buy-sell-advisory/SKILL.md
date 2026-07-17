---
name: property-buy-sell-advisory
description: Use when you have a unit's value and need a buy/hold/sell call for a Singapore condo — layering rental yield, realised returns, the BSD/ABSD/SSD cost stack, financing, and catalysts.
---

# Property buy / hold / sell advisory (Singapore condo)

## When to use this
Use this once you have a value for a unit (see `value-a-property`) and need to turn it
into an actionable **buy / hold / sell** recommendation. It layers the income picture
(rental yield), realised-return history, the Singapore transaction **cost stack**
(BSD / ABSD / SSD), financing context, and catalyst/timing into a clear decision rule.
The framework is generic — apply it to any unit; the worked figures are from #18-03
Spottiswoode Suites. Inputs come from the app's Rent, Profitability, and Nearby tabs
(see `read-investment-suite`).

## Data source — Investment Suite first (MANDATORY)

Rental yield, realised-return history and the transaction comps behind the value **must come from
Tier-1 ground truth: PropNex Investment Suite** (via `read-investment-suite` / `research/mbx.py`)
— Rent, Profitability and Nearby tabs — plus **SG-official** sources (URA / URA REALIS, IRAS for
the BSD/ABSD/SSD stack, MAS for SORA, LTA for catalysts). EdgeProp / PropertyGuru / 99.co / SRX are
**Tier-2** (usable, but reconcile against Tier-1); property research reports and agent/marketing
sites are **Tier-3** — conflicted, treat as claims, never as facts.

**If Investment Suite won't open, STOP — do not silently fall back to web data.** Emulator not
running, `adb devices` shows no device, app logged out, or session expired → pause immediately,
report the exact error, and wait for the user to start the emulator / sign in. Resume only once
Tier-1 access is restored, or the user explicitly says to proceed on lower-tier data.

## 1. Rental yield (income)
- **Gross yield** = annual rent ÷ price. Use rent comps that match the subject's
  bedrooms + size band (e.g. 743 sqft 3BR → the 700–800 sqft 3BR contracts).
- **Net yield** ≈ gross − ~1.1pp for property tax, maintenance/MCST, vacancy, agent fees
  (calibrate to the actual development).
- Benchmark against the **development's average yield** (Nearby Properties tab) and
  nearby projects.

> Worked: 743 sqft 3BR ≈ S$4,525/mo → **gross 3.2%**, **net ~2.1%**, vs development avg
> ~2.9%. Modest income; this is a capital-appreciation hold, not a yield play.

## 2. Realised holding-period returns (Profitability tab)
Read matched **buy→sell** pairs the app has already paired up: realised profit, holding
period, and **annualised** return. These are the cleanest read on what holders of this
line/stack have actually banked.

> Worked: #17-01 (581 sqft) bought ~2021-04 @ S$1.238M, sold 2024-10 @ S$1.50M →
> +S$262k over 3y5m, **~5.7%/yr**. Development realised-profit band ran roughly
> S$1k–S$346k. The subject's own unrealised gain since 2021: ~S$186k (+12.4%, CAGR ~2.3%/yr).

## 3. The SG transaction cost stack
The largest swing factor in any SG decision — compute it on the **transacting price**.

### Buyer's Stamp Duty (BSD) — progressive, everyone
| Band of price | Rate |
|---|---|
| First S$180,000 | 1% |
| Next S$180,000 | 2% |
| Next S$640,000 | 3% |
| Next S$500,000 | 4% |
| Next S$1,500,000 | 5% |
| Remainder | 6% |

> Worked: BSD on S$1.686M ≈ **S$53,900**.

### Additional Buyer's Stamp Duty (ABSD) — by buyer profile & count
| Buyer | 1st property | 2nd | 3rd+ |
|---|---|---|---|
| Singapore Citizen | 0% | 20% | 30% |
| Permanent Resident | 5% | 30% | **35%** |
| Foreigner | 60% | 60% | 60% |
| Entity / Trustee | 65% | 65% | 65% |

*(PR 3rd+ was stated here as 30% until 2026-07-17 — wrong. Verified against IRAS and the
MAS/MOF/MND release of 27 Apr 2023. The arithmetic + the sourced table now live in
`researcher/landed/costs.py`; rates change, so print the effective date and send the reader
to IRAS rather than trusting a table in a repo.)*

> Worked on S$1.686M: SC 2nd-property ABSD ≈ **S$337k**; foreigner ABSD ≈ **S$1.01M**.
> ABSD is the dominant gate for additional/foreign buyers.

### Seller's Stamp Duty (SSD) — units **bought on/after 4 Jul 2025**
Holding period from purchase, on the sale price:
| Held | SSD |
|---|---|
| ≤ 1 year | 16% |
| 1–2 years | 12% |
| 2–3 years | 8% |
| 3–4 years | 4% |
| > 4 years | 0% |

> Worked: a hypothetical 1-year flip of the subject would cost ~16% ≈ **S$270k**. The
> actual owner (bought 2021, held >4y) faces **0% SSD** — free to sell.

## 4. Financing context
- **TDSR**: total debt servicing ratio capped at **55%** of gross monthly income.
- **LTV**: up to **75%** on a first private housing loan (lower for 2nd+ loans / longer
  tenures / older borrowers).
- **Rates**: SORA ~**1.0%** (Feb 2026); fixed packages from ~**1.4% p.a.** Low rates lift
  affordability and support prices, but stress-test at a higher floor rate.

## 5. Catalyst / timing
Note dated, location-specific catalysts that can re-rate the segment:
> **Cantonment MRT (Circle Line 6) opens 12 Jul 2026** — adds a ~4th line within walking
> distance of Spottiswoode. A pre-opening window often sees anticipatory demand.

Also weigh the macro tape: URA index roughly flat-to-slightly-up (RCR non-landed
+0.9% q-o-q Q1 2026) but **sale volume down ~40% q-o-q** — a thin, sticky-price market
(slow to transact, prices holding).

## 6. Decision rule
Synthesise the above into one call. Rules of thumb:

**BUY when** — model value ≥ asking (you're not overpaying vs the adjustment grid AND vs
the app's Est. Val); net yield is acceptable for the buyer's profile **after** ABSD;
a dated catalyst is still ahead; financing clears TDSR comfortably at a stressed rate.
*Foreigners / 2nd-property buyers: only if the thesis survives the ABSD haircut.*

**HOLD when** — yield covers carrying costs, SSD is still biting (recent purchase), the
catalyst hasn't played out, and there's no better use of the capital. Default for an
owner sitting on an unrealised gain with 0% SSD and a catalyst ahead — let it run.

**SELL when** — price is at/above the model's high end and the app's AVM; SSD is 0%
(>4y held); yield is weak vs alternatives; or you need to recycle capital ahead of a
soft tape. Time the listing into catalyst-driven demand if one is imminent.

> Worked verdict for #18-03: model ~S$1.686M is **+1.5% over the app AVM** and the owner
> is past SSD with the MRT catalyst weeks away → a **HOLD-to-SELL-into-strength** unit;
> for a new buyer it's fair-to-slightly-full on price with thin yield, so only a
> conviction buy (e.g. owner-occupier or catalyst believer), and a hard pass for a
> foreigner once 60% ABSD is stacked on.

## Limitations
- Schedules change. **BSD/ABSD/SSD/TDSR/LTV/SORA are as of mid-2026** — re-verify against
  IRAS/MAS before advising; ABSD remission and exemptions are case-specific.
- Yields and realised returns are **development-specific and thin** — treat as indicative.
- This is decision support, **not financial or legal advice**; the user must confirm
  their own buyer profile, count, and tax position.

## Related files
- `researcher/valuation/dataset.py` — rents, profitability pairs, nearby yields, macro/regulatory facts
- `researcher/valuation/run.py` — computes BSD/ABSD/SSD and the advisory metrics
- `deliverables/build_report.py` — turns the valuation + advisory into a report
