---
name: value-a-property
description: Use when you need a defensible market value (psf and price, with a range) for a specific condo unit from recent comparable transactions, via an auditable sales-comparison adjustment grid.
---

# Value a property by comparable adjustment

## When to use this
Use this to put a defensible market value on a specific condo unit ("the subject") from
a set of recent transactions in the same (or nearby) development — the standard
sales-comparison appraisal method, codified. It produces a point **psf** + **price** and
a low/high range, with a transparent adjustment grid you can audit. The engine is pure
stdlib and generalises to any unit. Backing code: `researcher/valuation/engine.py`; a
worked run is `researcher/valuation/run.py` → results JSON. Get the inputs from
`read-investment-suite` + `harvest-scrolling-android-table`.

## Inputs needed
- **Subject**: size (sqft), floor, bedrooms, tenure (freehold/leasehold).
- **Comparables**: for each — date, floor, bedrooms, size (sqft), transacted **psf**
  (price optional). Pull from the Sale-tab transaction harvest.
- **Same-line anchor** (optional but strong): the subject's **own last sale**,
  time-adjusted — the single most like-for-like data point.
- **Params**: as-of date and the four adjustment rates (defaults below; calibrate per
  development/segment).

## The four adjustments
Each comparable's raw psf is multiplied by four factors to bring it onto the subject:

| Adjustment | What it corrects | Mechanism (default) |
|---|---|---|
| **Time** | Market moved between comp date and as-of | `(1 + time_trend_pa) ** years` — `time_trend_pa=0.018` (1.8%/yr) |
| **Floor** | Subject is on a higher/lower floor | `(1 + floor_premium_pp) ** (subj_floor − comp_floor)` — `+0.3%/floor` |
| **Size / quantum** | Smaller units carry higher psf | `(subj_sqft / comp_sqft) ** size_elasticity` — `size_elasticity=-0.08` |
| **Unit-type** | Compact-3BR layout discount vs efficient small units | apply/remove a `compact3br_discount=0.03` so comp matches subject; "compact 3BR" = `beds>=3 and sqft<=800` |

`adj_psf = raw_psf × time × floor × size × type`.

## Similarity weighting
Closer comps dominate. Each comp's weight is `1 / (1 + penalties)`:
- size penalty: `|ln(subj_sqft/comp_sqft)| × 3.0`
- floor penalty: `|Δfloor| / 25`
- time penalty: `|years| / 2`
- bedroom penalty: `0` if same bedroom count else `0.6`

The estimate is the **weighted mean** of adjusted psf. The **same-line anchor**, if
supplied, is adjusted like any comp but given an extra `anchor_weight` (default `2.0`)
so the most like-for-like point pulls hardest.

## How to run for ANY unit
```python
from engine import Subject, Comp, Params, value, format_grid   # from researcher/valuation/

subject = Subject(name="#18-03 Spottiswoode Suites", size_sqft=743, floor=18, bedrooms=3)

comps = [
    # Comp(label, date, floor, bedrooms, size_sqft, psf, price=None)
    Comp("2026-02-03 L28 #04 1BR 441sf", "2026-02-03", 28, 1, 441, 2352, 1_038_000),
    Comp("2025-03-25 L10 #01 2BR 581sf", "2025-03-25", 10, 2, 581, 2581, 1_500_000),
    # ... feed the whole harvested transaction table
]

# the subject's own last sale, time-adjusted = strongest single anchor
anchor = Comp("#18-03 own sale 2021", "2021-05-07", 18, 3, 743, 2020, 1_500_000)

p = Params(asof="2026-06-30", time_trend_pa=0.018, floor_premium_pp=0.003,
           size_elasticity=-0.08, compact3br_discount=0.03)

val = value(subject, comps, p, same_line_anchor=anchor, anchor_weight=2.0)
print(format_grid(val))
print(f"{val.estimate_psf:,.0f} psf -> S${val.estimate_price:,.0f} "
      f"(range {val.low_psf:,.0f}-{val.high_psf:,.0f} psf)")
```
Or just run the worked example end-to-end: `python researcher/valuation/run.py` (reads
`researcher/valuation/dataset.py`, writes a results JSON). To value a different unit,
swap the `Subject`, the comp list, and the anchor; keep or recalibrate `Params`.

## How to read the output
- **`estimate_psf` / `estimate_price`** — the weighted point value;
  `estimate_price_rounded` rounds price to the nearest S$1,000.
- **`low_psf` / `high_psf`** — a defensible band from the spread of adjusted comps
  (≈ inter-quartile), widened to keep the point estimate inside it.
- **`grid`** (via `format_grid`) — per-comp `raw / ×time / ×flr / ×size / ×type / adj psf / wt`.
  Read this to see *which* comps drive the number and sanity-check each adjustment.
- **`anchor_psf`** — the time-adjusted same-line anchor; compare it to the estimate.

**Worked result (subject #18-03, 743 sqft 3BR, L18):** model ≈ **2,269 psf → S$1.686M**,
range 2,152–2,417 psf; anchor (2021 sale fwd) 2,214 psf; vs the app's own Est. Val of
2,236 psf / S$1.661M that is **+1.5%** — a healthy cross-check against the app's AVM.
A 1BR validation run (452 sqft, L20) lands ~2,425 psf, inside the recent 1BR resale
cluster — evidence the grid generalises across unit types.

## Limitations
- **Thin volume.** A handful of comps per quarter means the estimate is sensitive to one
  or two outliers; lean on the same-line anchor and weighting, and report the range.
- **Calibration is segment-specific.** `time_trend_pa`, `floor_premium_pp`,
  `size_elasticity`, and `compact3br_discount` are defaults — recalibrate per development
  (e.g. against the URA index, the development's own price band, and the app's per-unit
  Est. Val) before trusting tight numbers.
- **Cross-bedroom comps are weak.** Adjusting 1BR/2BR comps onto a 3BR subject carries
  more model risk; the bedroom penalty down-weights them but cannot fully correct layout.
- **No condition/view/reno adjustment.** The grid covers time/floor/size/type only;
  unit-specific factors (renovation, view, facing, stack premium) are not modelled — note
  them qualitatively.
- **AVM cross-check, not ground truth.** The app's Est. Val is a useful benchmark, not a
  transacted price; agreement increases confidence but isn't proof.

## Related files
- `researcher/valuation/engine.py` — `Subject` / `Comp` / `Params`, `adjust()`, `value()`, `format_grid()`
- `researcher/valuation/dataset.py` — single source of truth for a development's extracted data
- `researcher/valuation/run.py` — applies the engine to #18-03 and writes results
