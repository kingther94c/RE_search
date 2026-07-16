# Method graveyard

**Read this before proposing a method.** Rejected approaches live here with the evidence
that killed them, so we don't rediscover them. A method lands here only after a REJECT
verdict in the [experiment registry](experiment_registry.md) — nothing is buried on
intuition alone.

Format per entry:

> ### GY-NNNN — <method name> (asset, date)
> - **Claim it made:** …
> - **How tested:** experiment id, data, benchmark it lost to.
> - **Why rejected:** the specific out-of-sample failure (numbers).
> - **Scope of the rejection:** where it fails (may survive on a narrow slice — say so).
> - **Do not resurrect unless:** the condition that would change the verdict.

---

### GY-0001 — Segment (CCR/RCR/OCR) average PSF as a standalone valuation (condo, 2026-07-15)
- **Claim it made:** a market-segment median psf, time-adjusted, approximates a unit's value.
- **How tested:** EXP-0003, benchmark B5, 8,000-subject walk-forward.
- **Why rejected:** median APE **17.8%** vs 4.1% for same-project (4.3x worse), P90 56%,
  pct>10% 69%, and **systematically biased +20.4%** — it over-values because the segment
  pool skews to pricier/newer stock than the median resale subject.
- **Scope of the rejection:** as a *standalone valuation*. It is RETAINED as benchmark B5
  (the bar a real method must clear) and may survive as a coarse prior when NO local comp
  exists — but never as the estimate when same-project or substitute comps are available.
- **Do not resurrect unless:** mix-controlled (hedonic) — at which point it is no longer a
  "segment average" but the R2d/R3 AVM, tested separately.

### GY-0002 — Nearest-project PSF as a substitute (condo, 2026-07-15)
- **Claim it made:** the geographically nearest OTHER project is a good value proxy.
- **How tested:** EXP-0003, benchmark B4.
- **Why rejected:** median APE **13.9%**, P90 38%, pct>10% 63% — geographic proximity alone
  is a weak substitutability signal (adjacent projects differ by age/tenure/positioning).
- **Scope:** rejects "nearest = comparable". Motivates R2b: substitutability distance, not
  raw distance. A *learned/multi-factor* substitute model is a different method, still open.
- **Do not resurrect unless:** distance is combined with tenure/age/quantum/positioning
  similarity (that is the R2b hypothesis, not this one).

### GY-0003 — Index momentum extrapolation ("drift_factor") for the landed time adjustment (2026-07-17)
- **Claim it made:** comps are adjusted only to the last PUBLISHED index quarter (35d pub lag),
  leaving the point structurally 1-2 quarters stale in a rising market; projecting that gap
  forward at the trailing-4Q published trend should remove the resulting low bias.
- **How tested:** EXP-0013 → EXP-0014. Built it (leakage-safe: reads no unpublished quarter,
  capped ±6%), shipped it, then a hostile reviewer sliced the sign test **BY REGIME** — the
  slice we had never computed.
- **Why rejected:** the pooled "51.7% ≈ unbiased" was **regime CANCELLATION, not a fix**.
  Drift OFF → ON, sign test by half-year:
  2023H1 **51.6→41.6** · 2023H2 **47.6→37.6** · 2024H1 **49.6→43.9** · 2024H2 **50.1→44.7**
  (all four were ALREADY unbiased and were BROKEN), while the regime it targeted barely moved
  and got worse: 2025H1 66.3→63.4, **2025H2 66.5→67.1**. Median APE degraded 9.34%→9.49%.
  No regime measured 50%. It also projected momentum against the latest observation — the
  newest published landed quarter FELL (2026Q1, −0.40%) while drift applied +3.31%.
- **Scope of the rejection:** the whole idea of closing publication staleness with an index
  momentum term. The DIAGNOSIS it rested on (~1.2pp from the pub lag) was itself wrong: the
  2025 bias survives the fix, so it is not publication staleness — it is a comp-based estimate
  structurally lagging an ACCELERATING market.
- **Do not resurrect unless:** you have a fitted LOCAL trend (L2b) validated by the regime
  sign test, not an index-momentum hack. The residual is now DISCLOSED instead (unbiased in
  stable regimes; ~15pp low when the market accelerates).
- **Lesson:** this is the second miss from the same cause — **a metric not computed**. L1
  closed L2b because "regime slices are flat" (they were flat on **APE**: 8.4-10.0% across
  every half-year) while the **sign test** swung 47.6%→66.5% in the same slices. Flat APE is
  not flat bias. The sign test now ships in every slice of the landed leaderboard.

**Watch-list (tested, retained as benchmarks, not yet buried):** none outstanding — the two
proxy methods the user flagged are now measured and filed above.
