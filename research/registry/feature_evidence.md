# Feature evidence registry

Per valuation feature: economic mechanism · evidence · estimated scope · functional form ·
confidence · known interactions. **No fabricated adjustment factors** — a feature with no
calibrated estimate stays "unresolved" (the skill then requests info / widens uncertainty),
it does not get a made-up number.

Format:

> ### <feature>
> - **Mechanism:** why it should move price.
> - **Evidence:** experiment id + finding (or "professional convention, untested").
> - **Functional form:** linear / log / spline / discontinuity / partial-pooled effect.
> - **Estimate & scope:** value + the slice it applies to (or "unresolved").
> - **Confidence:** high / medium / low.
> - **Interactions:** features it depends on.

---

### time (market movement)
- **Mechanism:** market level drifts between a comp's date and the valuation date.
- **Evidence:** _EXP-0001 pending._ Prior craft value (`value-a-property`) uses a fitted
  trend ladder clamped [0%,5%]; URA PPI available for index-based adjustment.
- **Functional form:** index ratio (benchmark) vs fitted local trend (to be compared).
- **Estimate & scope:** unresolved at the panel level; segment-specific (3BR ≠ 1-2BR in the
  #18-03 study — never pool segments).
- **Confidence:** medium (direction), low (magnitude by micro-market).

### floor
- **Mechanism:** higher floor → view/light premium.
- **Evidence:** `value-a-property` fits per-development floor premium from same-spec ±90d
  cross-floor pairs (One Pearl Bank 0.43%/floor vs 0.30% default). **URA gives only a floor
  BAND**, so URA-only backtests can't isolate exact-floor premium — this needs Investment Suite.
- **Functional form:** ~linear %/floor, clamped [0%,2%]; test spline/discontinuity later.
- **Estimate & scope:** 0.30% default, fitted when ≥8 same-spec pairs; high-rise new-TOP steeper.
- **Confidence:** medium on liquid towers, low elsewhere.

### size (quantum / psf elasticity)
- **Mechanism:** smaller units carry higher psf.
- **Evidence:** engine uses elasticity −0.08 + a compact-3BR (≤800sf) 3% bump. Untested OOS.
- **Functional form:** psf ∝ area^elasticity; nonlinearity to be checked.
- **Estimate & scope:** −0.08 provisional; **unresolved** across segments.
- **Confidence:** low.

### tenure / remaining lease
- **Mechanism:** leasehold decay vs freehold.
- **Evidence:** URA `tenure` parsed to freehold / freehold_equiv / leasehold + lease start.
  Effect **unresolved** — to be estimated from matched pairs, not assumed at 15%.
- **Confidence:** low.
