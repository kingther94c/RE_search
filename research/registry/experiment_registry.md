# Experiment registry

Newest first. One row per experiment; link to code/commit. Verdict vocabulary in
[`README.md`](README.md).

---

## EXP-0019 — L2f VERDICT: splitting is NOT a general engine win (P3 MONITOR); the alias suppression is JUSTIFIED but is really a MINORITY-SHARE test (2026-07-17)
- **Status: DONE. P = P3 (MONITOR, keep the pooled engine). D = D1 (suppression justified),
  but the corrected criterion reframes WHY — it is a minority-share effect, not a generic
  "mixed bucket" one. `research/run_l2f_split.py`.**
- **Universe (as pre-registered, scoped):** LOYANG RISE bucket fully decomposed (135/135 via
  EXP-0018) + Cardiff Grove inside ALNWICK (16/427 attributed — the emulator's adbd is wedged,
  so an Alnwick-Road IS harvest to lift that 4% is deferred). 91 walk-forward subjects
  (Cardiff 13 / Loyang Rise 59 / Loyang View 19).
- **P (point) → P3 INCONCLUSIVE.** Split vs pooled median APE **+0.39pp** (worse, inside the
  ±0.5pp band), 0 extra declines. **But per-road it splits by minority share, and that is the
  real finding:** Cardiff Grove, 4% of the ALNWICK bucket, **improves 14.1%→11.3% (−2.8pp)**
  when restricted to its own road — it was being diluted by 96% Alnwick-proper comps; Loyang
  Rise, which IS 77% of its bucket, gets **worse** (6.3%→7.0%) — splitting just starves it of
  sample. So "split the pool" is not a universal upgrade; **"a road that is a small minority of
  its parent bucket is mispriced by the pool" is.** The shipped pooled engine stays (P2's bar
  to replace it was not met).
- **D (distribution) → D1 JUSTIFIED, after a criterion I had to FIX mid-run.** My first D
  metric ("share of a road's sales above the bucket p25") fired on ALL three roads (85/95/100%
  vs the published 73-83%) and I nearly reported "the bucket mis-places every road". **That was
  wrong — it measured the engine's known LOW bias in a rising estate, not bucket mixing:** the
  same 85-100% shows up on Loyang RISE, a DIRECT street with no alias and no mixing, and Loyang
  Rise vs Loyang View 2025+ psf are 1,479 vs 1,437 (same sub-market — pooling them cannot
  misplace them). The corrected criterion compares, **on the same subject**, the pooled
  threshold vs the true-road threshold (differencing out the common engine bias): **Cardiff
  Grove 15.8%, Loyang View 3.8%, Loyang Rise 0.7%.** So the alias-street guidance suppression
  is JUSTIFIED **for a minority-share road (Cardiff)** and near-harmless for same-sized-share
  roads — which matches the shipped behaviour (report suppresses on `alias` basis; Cardiff is
  alias-minority, Loyang View is alias but same sub-market).
- **What ships (report change):** the suppression is kept, but its *reason string* is upgraded
  from "the bucket mixes roads" to the measured driver — a road that is a **small minority of
  its parent bucket** is the one whose thresholds the pool distorts (Cardiff 4% of ALNWICK →
  15.8% off). No engine change; `value_landed` untouched.
- **Lesson (the third time this exact shape has cost me):** a rate-above-a-quantile metric
  cannot tell "the pool is wrong" from "the engine is low" — they both push sales above p25.
  Only a WITHIN-SUBJECT pooled-vs-split difference isolates the pool effect. Caught because the
  signal fired on a control road (direct-street Loyang Rise) it had no business firing on.

### EXP-0019 — the original PRE-REGISTRATION (committed at `47b27f7` before the run)
- **Status: PRE-REGISTERED (committed BEFORE the run — the EXP-0017 review's MINOR-8).**
- **The question.** EXP-0018 proved URA's landed `street` is the DEVELOPMENT's registered
  street, so LC2's "same-street grid" is really a same-PARENT-street grid: `URA "LOYANG RISE"
  (135) = Loyang Rise (104) + Loyang View (31)`, and ALNWICK ROAD's 427 include Cardiff Grove.
  **This is not automatically wrong** — adjacent roads of one estate may be the right pool, and
  LV1's shipped 9.05% was measured WITH that pooling. Two separate things must be tested, and
  the report currently assumes an answer to the second one:
  - **(P) the POINT**: does restricting LC2's comps to the subject's TRUE road improve median
    APE? Purer but thinner (Loyang View subjects drop from 135 to 31 candidate rows).
  - **(D) the DISTRIBUTION**: the full report SUPPRESSES buyer/seller thresholds on
    alias-resolved streets because the bucket's p25/p75 mix roads. That suppression is
    currently justified by ONE observation (19 Cardiff Grove: bucket p25 S$3.87M vs the road's
    own original stock at S$3.25-3.58M). D tests it properly: **do a sub-road's actual sales
    land inside the BUCKET's p25/p75 at the rate the report claims (~73-83% above p25,
    ~32-38% above p75), or does the bucket systematically mis-place them?**
- **Universe (fixed here).** Only rows whose TRUE road is known from an IS harvest
  (EXP-0018 attribution on month+price+area): the **LOYANG RISE bucket, fully decomposed**
  (135/135 attributed → the clean case), plus **Cardiff Grove subjects inside ALNWICK ROAD**
  (17 in-window attributed → the case that motivated the module). This is ONE fully-decomposed
  estate + one partial: **any verdict is scoped to that, and says so.** Extending to ALNWICK
  needs an IS harvest of Alnwick Road itself (blocked today: the emulator's adbd is wedged —
  `adb get-state` says device but every `shell` call times out).
- **PRE-REGISTERED criteria:**
  - **P1 — SPLIT WINS (ship it)** iff split median APE ≤ pooled − 0.5pp AND the extra decline
    rate ≤ 15pp AND no regime half-year that was unbiased under pooling (sign ∈[45,55]) leaves
    [42,58] under split (the GY-0003/GY-0005 failure mode).
  - **P2 — POOLING WINS (keep the shipped engine)** iff split median APE > pooled + 0.5pp.
    Then the parent-street pool is doing real work and the roadmap's L2f(a) is answered NO.
  - **P3 — INCONCLUSIVE (MONITOR)** iff |Δ| < 0.5pp, or either arm scores < 25 subjects.
    A tie on this sample is not evidence of equivalence — say so, do not ship on it.
  - **D1 — the report's suppression is JUSTIFIED** iff, for at least one sub-road, the share of
    its actual sales above the bucket's p25 (or p75) deviates from the published band
    (73-83% / 32-38%) by **>10pp** — i.e. the bucket genuinely mis-places that road.
  - **D2 — the suppression is UNJUSTIFIED and must be relaxed** iff every sub-road's rates sit
    inside the published bands. Then the alias guard is over-cautious and costs real guidance.
- **Guardrails.** Walk-forward + as-of firewall (the harness, unchanged); the attribution map
  is built ONLY from IS harvests already on disk; a split arm that declines is counted as
  declined, never back-filled from the pooled arm (that would launder the coverage cost).
- **Deliverable:** `research/run_l2f_split.py` + this entry's verdict + whatever the verdict
  forces to change (engine, report guard, or the graveyard).

## EXP-0018 — R4a VERDICT: F1 REFUTED (our own claim struck); the real finding is that URA's "street" is a PARENT LABEL (2026-07-17)
- **Status: DONE. The pre-registered claim FAILED and is being struck from three documents.
  The finding that replaced it is bigger than the one we went looking for.**
- **F1 (freshness) — REFUTED. Our own sentence is struck.** L2b closed by asserting, in the
  roadmap, `00_master_methodology` and the SKILL, that *"the residual bias is the caveat-
  visibility lag itself → only fresher observations (R4 IS live pulls) can shrink it"*.
  Measured: **IS is not fresher.** LOYANG RISE newest caveat — IS `19 Jun 2026`, URA
  `2026-06`; the same transaction. IS has **zero** rows URA lacks (0/104). Per the
  pre-registration, F2 fires: **the sentence is struck** and the landed residual is declared
  **not shrinkable by any live-data source we have**.
  - **The trap that would have inverted this:** the Sale screen stacks *Street Transactions*
    (caveats) above *Realtime Agency Data* (Tier-2 agency rows, tenure renders as `-`). The
    agency panel DID carry newer dates (Loyang Rise: `30 Jun 2026`, `10 Jun 2026` — absent
    from caveats). Reading "the newest date on the Sale screen" scores IS as FRESHER **on
    asking data**. `harvest_street_sale.assert_caveat_table` refuses to harvest that panel;
    it fired for real during this run when a `View All` tap landed on it.
- **A1 (agreement) — CONFIRMED, 100%.** All 104 matched LOYANG RISE rows agree on price
  exactly and on area to the rounding (IS renders `1,615`, URA carries `1,614.6`). *Our
  first pass reported 98.1% — that was OUR bug*: the matcher popped an arbitrary member of a
  (month, price) group and crossed two same-price sales, then reported the crossing as a data
  disagreement. Pair-by-nearest-area → **1.0**. Nearly published as "the two Tier-1 sources
  disagree on area".
- **D1 (depth) — CONFIRMED.** IS's 10Y window reaches `02 Sep 2016`; the per-ADDRESS *Unit
  Transaction History* on the Property Info tab reaches **1996** (385 Loyang Rise: 1996 New
  Sale $1,136,116 → 2003 $760k → 2006 $680k — the post-1997 crash, correctly rendered).
  URA's API is a rolling ~5y window. IS adds ~25 years of history URA cannot serve.
- **C1 (completeness) — THE QUESTION WAS MIS-POSED, and the answer is the discovery.**
  URA's LOYANG RISE bucket holds 135 rows; IS's Loyang Rise holds 104; the 31-row gap looked
  like "IS is missing 23% of caveats". It is not. **URA's `street` field is a coarse PARENT /
  locality label that merges adjacent roads; IS resolves the TRUE address street.** Proven
  in both directions, exactly:
  - `IS Loyang Rise (104) + IS Loyang View (31) = 135 = URA "LOYANG RISE"` — all 31 orphans
    are Loyang View transactions (same month+price+area), **0 unexplained**;
  - **CARDIFF GROVE**, which the engine REFUSES as `street_not_found`, is carried by URA under
    **`ALNWICK ROAD`**: 16 of its 17 in-window IS transactions match an ALNWICK ROAD caveat on
    month+price+area (incl. `26 Jun 2026, 17 Cardiff Grove, 2,640sf, $4,698,000`). Tenure
    corroborates: IS says Cardiff Grove is `999 yrs from 01/01/1956`; the engine infers
    ALNWICK ROAD as `freehold_equiv, lease_start 1955`. Same estate.
- **Harvest completeness — proven independently of the harvester.** The 104 harvested rows
  reproduce the app's OWN 5Y header to the dollar: LOWEST `$1,500,000` ✓, **AVERAGE
  `$2,183,582` ✓ (exact)**, HIGHEST `$2,780,000` ✓. One missing or extra row moves that mean.
  And URA holds two ALNWICK-bucket sales ABOVE the app's stated maximum (`2024-07 $2,940,000`,
  `2026-03 $2,800,000`) — the app's own aggregate proves the app's own scope, not a harvest gap.
- **What this means for the programme (the real R4 dividend):**
  1. **`street_not_found` is a NAMING failure, not a data gap** — the Cardiff class is
     valuable *today* via the parent street. The SKILL's "escalate to IS because URA has
     nothing" is FALSE and is corrected.
  2. **LC2's "same-street grid" is a same-PARENT-STREET grid** — it already pools adjacent
     roads (ALNWICK ROAD's 201 comps include Cardiff Grove). Whether splitting to the true
     address street helps or hurts is now a measurable open module (**L2f**), not an assumption.
  3. **IS's unique asset is the ADDRESS↔caveat mapping**, not freshness and not volume: it is
     the only source that says WHICH road (and which house) a caveat belongs to. That also
     makes an exact per-address same-plot matcher possible (today's matcher keys on
     `(street, area, type)` — EXP-0009).
  4. `data-source-trust-hierarchy` needs amending: on caveats the two sources are the SAME
     data at the SAME lag; IS is not "far more data" for bulk street work (it is a strict
     subset per road). Its edge is per-address detail, history depth, rents, Est.Val.
- **Deliverables:** `research/harvest_street_sale.py` (landed street harvester + the caveat/
  agency guard + a format-based, coordinate-free parser), `research/reconcile_is_ura.py`,
  `tests/test_harvest_street.py` (9 offline parser tests), harvested sets for LOYANG RISE /
  LOYANG VIEW / CARDIFF GROVE.
- **Method note — three self-inflicted bugs caught before publication**, each of which would
  have produced a confident wrong finding: (a) hardcoded column x-centres shifted 28/125 rows
  and swallowed the price → replaced with format-based classification (the header is NOT
  sticky and the h-swipe offset varies, so no coordinate map can work); (b) the greedy matcher
  → fake area disagreement; (c) a `View All` tap that silently opened the agency panel.

### EXP-0018 — the original PRE-REGISTRATION (2026-07-17, committed at `1f43c90` before the first harvest)
- **The claim under test is OUR OWN.** The L2b verdict (EXP-0017) closed with a sentence now
  sitting in the roadmap, the master methodology and the SKILL: *"the residual bias is the
  caveat-visibility lag itself → only fresher observations (R4 IS live pulls) can shrink it,
  not more model."* **That is an untested assertion about a data source we have never
  measured against the spine.** L2b's own lesson (the cap hypothesis: arithmetic right,
  exposure ~zero) is that a mechanism must be measured before it is believed. If IS turns
  out to carry the SAME caveats at the SAME lag, that sentence is false and must be struck
  from all three documents — a REFUTATION is a legitimate and publishable outcome here.
- **Why it is not obvious either way:** both sources ultimately draw on URA caveat data, so
  IS may be a re-skin (no freshness gain); but the URA *public API* pull of 2026-07-15
  already contained 2026-07 caveats, so the API's real-world lag is far shorter than the
  backtest's conservative `month_end + 56d` firewall — meaning the LIVE freshness gap IS may
  close could be small or nil. Separately, IS demonstrably has *something* URA lacks: CARDIFF
  GROVE carries a PASS-8.5 craft valuation off app street history while the URA 5y window has
  **zero** caveats there (EXP-0015).
- **Sample (fixed here, before looking):** landed streets LOYANG RISE · BOWMONT GARDENS ·
  ALNWICK ROAD · AROOZOO AVENUE · EMERALD HILL ROAD · CARDIFF GROVE (the known URA-gap case),
  plus 2 condo projects. Per street/project: harvest the IS Sale table at its widest time
  window; compare against the URA store slice for the same street/project; match rows on
  (contract month, land/strata area, price) with a tolerance; classify every row.
- **PRE-REGISTERED criteria (each is a claim that either survives or is struck):**
  - **F1 — the freshness lever EXISTS** iff IS's newest caveat is newer than URA's newest on
    **≥50% of sampled streets** AND the median date advantage is **≥30 days**. Only then does
    "fresher observations shrink the landed residual bias" survive as a hypothesis, and only
    then does an IS-fed trend bridge get built (it would then need its own regime-panel
    validation — no shipping on a freshness claim alone).
  - **F2 — the lever is REFUTED** iff IS's newest ≤ URA's newest on ≥50% of streets. Then the
    sentence above is **struck from the roadmap, 00_master_methodology and the SKILL**, the
    landed residual is declared structurally irreducible on available data, and R4 re-scopes
    to depth + per-unit detail only.
  - **D1 — depth** iff IS's oldest < the URA window start on ≥50% of streets → the CARDIFF
    class (`street_not_found`) is systematically addressable, and the refusal gets a
    documented IS route rather than a dead end.
  - **A1 — agreement** iff, on matched rows, price AND area agree exactly on **≥95%**. Below
    95%, the disagreement is itself the finding: two "Tier-1" sources that contradict each
    other means the URA spine's trust — and every number built on it — needs a verdict, and
    `data-source-trust-hierarchy` must be rewritten to say which wins and why.
  - **C1 — completeness** iff URA-only rows inside IS's own window are **<10%**. At ≥10% IS
    is provably missing caveats → it may supplement the spine, never replace it.
- **Guardrails.** UI only, no auth bypass, no web fallback (Tier-1 rule); every harvested row
  carries provenance (screen, window, harvest timestamp) so the comparison is auditable; the
  IS reads are the DEPENDENT variable — the URA store is frozen and untouched by this work.
- **Deliverable:** `research/reconcile_is_ura.py` (offline-testable matcher + report) +
  this entry's verdict + whatever documents the verdict forces to change.

## EXP-0017 — L2b VERDICT: the observed local-trend bridge ships (engine upgrade); the "fixed" bar is NOT met; two variants graveyarded (2026-07-17)
- **Status: DONE. Verdict: ACCEPT-WITH-SCOPE for V2 "lt_tail" as an ENGINE change — LV1
  9.34% → 9.05% median APE, hot-regime bias reduced ~5pp with zero stable-regime damage.
  The pre-registered A1 ("bias fixed": every regime sign ∈[42,58]) FAILED — hot regimes
  measure 59.6-62.1 — so the regime-bias DISCLOSURE STAYS, with updated numbers. V1 (cap
  widening) → GY-0004; V3 (lt_full replacement) → GY-0005.**
- **What V2 is:** `local_trend.py` — a month-granular ln-level curve fitted AS-OF each
  valuation month from visible caveats only (two-way FE: ln psf ~ (street,type) + month;
  alternating demeaning; 3-mo median smoothing; clamps at the fitted range — never
  extrapolates). `_tadj_psf` bridges each comp from **max(comp month, published quarter's
  midpoint)** to the newest fitted month, multiplying the capped PPI leg. One constructor
  (`landed_engine.shipped_time_ctx`) feeds production, the harness default AND the tests —
  the EXP-0015 "shipped ≠ backtested" class is now structurally impossible at this seam.
- **Gates (pre-registered in EXP-0016 BEFORE any V-run):** A1 **FAIL** (2025H1 60.8, 2025H2
  62.1, 2026H1 59.6 — target ≤58; so NO "fixed" claim anywhere). A2 PASS (stable four:
  53.0/47.1/53.0/51.4, all inside [44,56]). A3 PASS (9.05 ≤ 9.49; actually beats the
  shipped 9.34 by 0.29pp). A4 PASS (P90 0.288). A5 PASS (recalibrated conformal, held-out
  **78.88%** through the PRODUCTION band code incl. big-plot widening). A6 PASS (lag 42/56
  identical; 70d +0.05pp). Leaderboard same-adjustment: LV1 9.05% vs LC1 bar 10.45%.
  **Design had ZERO tuning iterations against the test panel** — the bridge construction,
  smoothing window and fit window were fixed a priori; the temptation to nudge smoothing
  until 60.8→58 was explicitly refused (that would be selection on the validation set).
- **A real defect caught by a FIELD case, not the backtest:** the first bridge implementation
  anchored EVERY comp at the published quarter's midpoint — double-bridging comps newer than
  it (the freshest, highest-weight prints; a subject's own same-month print came out +4%
  above itself — BOWMONT GARDENS' 2026-07 S$14.00M caveat). The walk-forward had IMPROVED
  anyway (the over-adjustment mimicked the missing hot-regime signal — a right-direction
  wrong-mechanism artifact). Fixed to the per-comp anchor; hot-regime gains held (60.3/61.6
  flawed → 60.8/62.1 corrected) and pooled medAPE improved further (9.09 → 9.05).
  Regression-locked: `test_tadj_lt_tail_fresh_comp_is_not_double_bridged`.
- **Field re-renders (live, corrected engine):** LOYANG RISE 1,635sf → **S$2.45M — exactly
  on its 2026-05 size-twin print** (pre-L2b: S$2.38M). BOWMONT GARDENS 9,225sf → S$14.77M
  vs its own 2026-07 print S$14.00M (+5.5%, inside the 8.2% detached noise floor; conf 45
  case-tier; the flawed bridge had said 14.98). ALNWICK 2,800sf → S$5.22M, and it STOPPED
  being a hard case (the bridge freshened the anchors; spread now <18%) — the suppression
  test archetype moved to EMERALD HILL ROAD (conservation street, spread 33%, hard by
  nature). AROOZOO 4,518sf → S$6.22M. CARDIFF GROVE still refuses (street_not_found → IS).
- **Marker rates re-measured under the shipped adjustment** (`python
  research/calibrate_landed_guidance.py`, sample default now 800 → 547 scored): ~73-83% of
  sales land above p25, ~32-38% above p75; the regime drift REMAINS (p50 hit 53.1%
  pre-2025H2 vs 67.2% after) — markers stay labelled as evidence, not probabilities.
  T3 same-plot repeat signal MEASURED (not just the ~6.5/mo prior): median **24 pairs/mo**
  — still under the ~30 an index needs; verdict "cross-check only" stands on the number.
- **Residual bias, understood and disclosed:** the un-bridgeable tail is the caveat
  visibility lag itself (~2-3 months in reconstruction; less live). 2026H1 illustrates why
  no in-window trick closes it: the fitted curve's visible months were flat/falling while
  the market re-accelerated intra-half — only fresher OBSERVATIONS (IS live pulls) can
  shrink it further, not more model.
- **Files:** `local_trend.py` (+`shipped_time_ctx`), `_tadj_psf` modes, harness
  `extra_ctx`/`ctx_hook`, `run_landed --no-ltrend` ablation, conformal fingerprint extended
  to the FULL residual-determining set (benchmarks+candidates+size_curve+local_trend — the
  old 2-file set had a hole exactly where L2b operates), `analyze_landed` A5 now scored
  through production `_band`. Scripts: `diagnose_l2b.py`, `run_l2b_variants.py`,
  `validate_l2b_v2.py`, re-run `calibrate_landed_guidance.py`. Tests: 159 (8 new).
- **HOSTILE REVIEW: PASS 8.4/10 (fresh reviewer, one round).** Every load-bearing number
  reproduced exactly (baseline panel regenerated by a full independent V0 run; conformal
  table regenerated BYTE-IDENTICAL from the dump; dump row-identical on 3 re-run months;
  leakage + bridge + regime-cancellation attacks all failed; "A1 declared FAILED" called
  the strongest honesty signal). Findings, all fixed in the acceptance commit: MAJOR-1 the
  tree mutated mid-review (my docstring edit during the review — the reviewed object must
  be frozen; fixed by committing, and next cycle the EXP gates get committed BEFORE the
  first candidate run, which also answers MINOR-8 "pre-registration is asserted, not
  provable"); MAJOR-2 the shipped marker rates needed an undocumented `800` arg (the
  documented default gave p75 29.2%, OUTSIDE the quoted range — sample-size artifact;
  default now 800 so the documented command reproduces the documented number); MINOR-3
  p50 pre-2025H2 is 53.1 not 52.8; MINOR-4 T3 measured 24 pairs/mo (the ~6.5 prior was 4×
  off; verdict unchanged); MINOR-5 sweep-coverage is 78.2% (a 78.4% typo lived only in the
  review handoff) + 2024H2's 8.5% cap exposure now stated (strengthens GY-0004); MINOR-6
  the observed bridge no longer silently drops when no quarter is published (latent);
  MINOR-7 a live partial terminal month under 5 prints is dropped from the fit (the
  backtest only ever validated complete months; min complete-month n=90); MINOR-9 the
  2026H2 thin slice (n=28) is footnoted in the SKILL table instead of silently omitted.

## EXP-0016 — L2b diagnosis: cap hypothesis REFUTED; the mechanism is staleness × market pace (2026-07-17)
- **Status: DONE (diagnosis).** Hypothesis tested: the regime bias (sign 47.6-51.6% in
  2023-24 → 66.3-66.5% in 2025) is **TIME_ADJ_CAP (0.80, 1.25) swallowing PUBLISHED index
  growth** (the landed PPI moved ×1.335 2021Q3→2025Q4 — above the cap inside LC2's 60mo
  window). The arithmetic was right and the hypothesis is still **REFUTED — this is why we
  measure**: the 18mo recency half-life leaves almost no WEIGHT on comps old enough to bind.
- **P1 (cap-bound weight inside LC2's own comp universe):** 2025H1 **0.0%**, 2025H2 3.1%,
  2026H1 7.3% — and the HIGHEST exposure of all, **8.5%, sits in 2024H2, an UNBIASED
  regime** (sign 50.1), which strengthens the refutation; mean capped-away effect ≤0.32% —
  two orders of magnitude below the −4~5% medSigned bias. **P3 (counterfactual, full walk-forward):** cap 1.25→2.50 moves 2025H2
  sign 66.5→66.1, medSigned −5.18→−5.11, everything else ~unchanged. **V1 (cap widening)
  is DEAD as a fix** (kept only as an experiment knob).
- **P2 — the real mechanism (measured):** the last PUBLISHED PPI quarter's midpoint is
  **~4.5 months stale at EVERY valuation date** (uniform 4.4-4.6 across regimes). Staleness
  is invisible when the market is flat (2024: +0.9%/yr → ~0.3%) and is exactly the observed
  bias when it runs (2025: +7.6%/yr × ~4.5-5.5mo ≈ **3.2-3.5%**, vs measured medSigned
  −4.2~−5.2%). This also explains GY-0003 cleanly: a TRAILING-4Q extrapolation is late at
  every turn — it pushed 2022's rise into flat 2023-24 (breaking them) and 2025's rise into
  falling 2026Q1 (overshooting). Staleness must be closed with an **OBSERVATION** — visible
  caveats reach ~asof−2mo (56d-lag reconstruction) and ~asof (live) — not a forecast.
- **Baseline regime panel (full n=7,027 run, for EXP-0017 comparison):** sign 51.6 / 47.6 /
  49.6 / 50.1 / 66.3 / 66.5 / 60.4 (2026H1, n=1,162) / 60.7 (2026H2, n=28); pooled 9.34%
  median APE, P90 0.287.
- **PRE-REGISTERED acceptance criteria for ANY L2b fix (fixed BEFORE reading P3/EXP-0017
  results; validated on the walk-forward regime panel, never APE alone):**
  - **A1** every half-year regime sign test ∈ [42, 58] (baseline worst: 66.5);
  - **A2** no regime that sat in [47, 53] at baseline leaves [44, 56] (the GY-0003 failure
    mode — breaking already-unbiased regimes — is an automatic REJECT);
  - **A3** pooled median APE ≤ 9.49% (no worse than +0.15pp vs the shipped 9.34%);
  - **A4** pooled P90 APE ≤ baseline + 0.02;
  - **A5** conformal recalibrated (fingerprint) with held-out coverage ∈ [75, 85]%;
  - **A6** lag-stability: median APE at lag 42/70 within ±0.3pp of lag 56.
  - **Selection rule:** the SIMPLEST variant passing A1-A6 ships (guardrail 4); ties break
    on max|sign−50| across 2025H1/2025H2/2026H1. If nothing passes → graveyard the variants,
    keep the disclosure (EXP-0014's stance stands).
- **Candidate ladder (EXP-0017, simplest first):** V1 = cap treatment only (published factor
  is an OBSERVATION; keep only a wide data-error guard). V2 = V1 + fitted local trend as an
  OBSERVATION-ONLY bridge from the published quarter's midpoint to the newest VISIBLE caveat
  month (`local_trend.py`: two-way FE ln(psf) ~ (street,type) + month, alternating demeaning,
  3-mo median smoothing, clamps — never extrapolates). V3 = fitted local trend as the whole
  adjustment (PPI unused; sanity clamp only). T3 (same-plot repeat signal as an index) is
  measured for feasibility only (expected too thin: ~6.5 pairs/mo).

## EXP-0015 — L4 ACCEPTED: hostile review PASS 8.05, GL4 MET (2026-07-17)
- **Status: DONE. `landed-valuation` SHIPPED. GL4 PASS.** Six hostile rounds, fresh reviewer
  each: **6.9 → 7.05 → 7.8 → 7.55 → 6.65 → 8.05 PASS** (zero blockers, every dimension ≥7.0).
- **The question the loop existed to answer** — is DISCLOSING the regime bias adequate, or
  does a ~15pp directional bias make the point unusable? The reviewer measured the **money**,
  not the sign test: hot-regime median signed error is **−3.9%** — **smaller than the 6.0-8.2%
  per-print bundle noise floor we measured**. Verdict: *"A 4% shift is not reliably correctable
  under 6-8% irreducible per-print noise; they tried (GY-0003), it broke four unbiased
  regimes, and they reverted it and published the table instead. Disclosure is the
  methodologically correct answer here, not an excuse."* The revert (EXP-0014) is vindicated.
- **Independently verified:** all 8 trials reproduce byte-identically; the full regime table
  and its APEs; the noise floor; condition-blindness (every numeric field identical across
  condition inputs); the conformal fingerprint passes against shipped code. **The engine
  UNDERSTATES itself** — claimed 78.9% held-out band coverage, the shipped band delivers
  **79.62%**.
- **Two P1s found and fixed in this round (both self-indicting by our own standard):**
  1. **The shipped point was NOT the backtested point.** A `directional AND hard` blend lived
     only in `value_landed` (the harness scores `landed_engine`). Measured on 2,600 firewalled
     resales: it fires on 3.9%, where the RAW point was **already unbiased** (sign 48.5%,
     median signed +0.83%) and the blend made them **worse** (sign 64.4%, median signed
     −5.98%, +0.85pp APE) — **injecting the very bias the engine discloses as its weakness.
     That is exactly why GY-0003 was buried** ("broke the regimes that were already
     unbiased"), left running in production. **DELETED**; the validated LC2/LV1 point stands,
     locked by `test_shipped_point_is_the_backtested_point`.
  2. **The directional flag was one-sided** — fired 17/17 when the point sat ABOVE the freshest
     print (the side the engine is NOT biased on) and 0/58 BELOW, where the gap genuinely
     predicts error (point <−20% below fresh → median signed −7.6%, 70% of sales above).
     Worse, `_banner` rendered the fresh reference ONLY when the flag fired, so low-side
     reports computed the evidence and dropped it — the "computed it then discarded it"
     pattern for the third time. Now **SYMMETRIC** (annotates both directions, never moves the
     point) and the reference **always renders**. Live proof: AROOZOO (a 4,517.6sf size-twin
     printed 14% above our point four months earlier) now raises a BELOW flag; it was silent.
- **Open, disclosed, non-blocking:** L2b (fitted local trend) is the proper fix for the regime
  bias and is the highest-value open landed module; the guidance pool has no time window while
  LC2 uses 60mo (two comp counts in one report); the conformal sweep doesn't call
  `landed_engine._band` (conservative today: 78.91% published vs 79.62% actual).

## EXP-0014 — L4 review round 5: the drift fix REVERTED; the bias is regime-dependent (2026-07-17)
- **Status: DONE. Verdict: GY-0003 (drift) REJECTED and reverted; the residual bias is
  DISCLOSED; the lease guard's second half closed.**
- **The finding (hostile round 5, REVISE 6.65, 2 blockers).** Both real, both ours.
- **BLOCKER 1 — the lease guard was half-closed.** EXP-0012 fixed "DECLARED leasehold with no
  lease_start → REFUSE" but left "tenure NOT declared → infer the street MODE". On a mixed
  street the mode silently upgrades a real leasehold plot to freehold and prices it off
  freehold comps — the 232% class, at high confidence with live guidance. Measured on JALAN
  RINDU (14 FH / 11 LH): omitting the *optional* tenure input yields **+69.8%** (S$5.34M vs
  S$3.14M declared-leasehold), conf 70, live ask. Worse, the engine COMPUTED the evidence
  (LC2 builds an "N lease-mismatched dropped" note) and `landed_engine` then discarded it.
  **Fix:** `tenure_required` refusal when tenure is inferred AND the street is MATERIALLY
  mixed. Material, not binary — measured: ALNWICK 1.5% minority (3 stray LH in 205) is a
  data quirk where the mode is safe; JALAN RINDU 44% is a coin flip. Threshold 10% + n≥4 →
  **26 of 781 street×type groups (3.3%) refuse without a tenure input.**
- **BLOCKER 2 — "sign test 51.7% = unbiased" was REGIME CANCELLATION.** The reviewer sliced
  the sign test BY REGIME — the slice we still had not computed. Drift OFF → ON:
  | regime | 2023H1 | 2023H2 | 2024H1 | 2024H2 | 2025H1 | 2025H2 |
  |---|---|---|---|---|---|---|
  | OFF | 51.6 | 47.6 | 49.6 | 50.1 | 66.3 | 66.5 |
  | ON  | **41.6** | **37.6** | **43.9** | **44.7** | 63.4 | **67.1** |
  **The fix BROKE the four regimes that were already unbiased and made the one it targeted
  worse**, while costing median APE (9.34→9.49%). The pooled 51.7% was a HIGH bias cancelling
  a LOW one; **no regime measured 50%**. It also projected momentum against the latest
  observation (2026Q1 landed PPI FELL 0.40% while drift applied +3.31%). **REVERTED → GY-0003.**
  The round-4 diagnosis it rested on (~1.2pp = publication lag) was itself WRONG: the 2025
  bias survives the fix, so it is not staleness — it is a comp-based estimate structurally
  lagging an ACCELERATING market.
- **What ships instead — disclosure, not correction.** LV1 back to **9.34% median / 78.9%
  held-out band / 100% coverage**, with the regime table published in the SKILL and in EVERY
  report's limitations: *unbiased in stable markets (sign 47.6-51.6% across 2023-24), ~15pp
  low when the market accelerates (66% in 2025) — in a hot market read the point as a FLOOR.*
- **The institutional lesson, now twice over: a metric not computed is a bias not seen.**
  L1 closed module L2b because "regime slices are flat" — they were flat on **APE** (8.4-10.0%
  across every half-year) while the **sign test** swung 47.6%→66.5% in those same slices.
  Flat APE is not flat bias. **The sign test + median_signed now ship in EVERY slice of the
  landed leaderboard, and the regime slice is by HALF-YEAR** (an annual bucket averages away
  the 2025H1-vs-H2 signal). **L2b (a fitted LOCAL trend) is re-opened in the backlog as the
  proper fix** — it was closed on the wrong metric.

## EXP-0013 — L4 review round 4: the systematic LOW bias, and why the metric set hid it (2026-07-17)
- **Status: DONE. Verdict: bias FIXED (sign test 63%→51.7%); guidance markers RE-LABELLED
  after a calibration attempt honestly FAILED out-of-sample.**
- **The finding (hostile round 4, REVISE 7.55, 1 blocker).** LV1's point was systematically
  ~3.5% LOW: on 400 as-of-firewalled production valuations the **actual sale exceeded the
  point 63.2% of the time** (unbiased = 50%), and the guidance inherited it — real sales
  printed above the p75 "ask" **44.8%** of the time against a label promising 25%.
- **Why we could not see it — the institutional root cause.** The landed leaderboard reported
  `signed_bias` as a **MEAN** (−0.96%, looks negligible). The error distribution is skewed, so
  a few large over-predictions dragged the mean to ~0 while the typical case ran low. **The
  SIGN TEST and the MEDIAN were the metrics that expose it, and neither was in the metric
  set.** Added `median_signed` + `pct_actual_above` to `metrics.summarise` and the leaderboard
  — a mean-only bias column cannot see a one-directional error.
- **Diagnosis (the reviewer falsified their own first hypothesis, which is why this is
  trustworthy):** NOT staleness (24/60mo windows and an 18mo half-life all leave it at
  ~39-43% >p75) and NOT the caveat lag (lag 0 reproduces +3.6%). **~1.2pp is the INDEX
  PUBLICATION LAG:** comps were adjusted only to the last *published* quarter (35d lag), so at
  as-of 2026-07 the newest level available is 2026Q1 — in a market running ~7.6%/yr the point
  is structurally 1-2 quarters stale.
- **Fix:** `PriceIndex.drift_factor` projects the published→as-of gap at the recent PUBLISHED
  trend (leakage-safe: no unpublished data; capped ±6% because an extrapolation is a forecast).
  Routed every landed adjustment (point, guidance pool, street ref, comps exhibit) through the
  ONE corrected `_tadj_psf`. **Result: pct_actual_above 63.2% → 51.7%, median_signed +3.5% →
  −0.46%**, for +0.15pp median APE (9.34→9.49%) — the right trade: an unbiased estimator with
  a hair more variance beats a biased one.
- **The calibration that FAILED (and ships as a finding, not a fix).** `research/
  calibrate_landed_guidance.py` walks real resales through the production path and measures
  where the actual sale falls vs the guidance markers. Post-fix, **p25 is well calibrated
  (73.8% above vs a 75% target)** but **p75 delivers 35.1%, not 25%** — the adjusted-comp
  distribution is NARROWER than the outcome distribution (adjustment shrinks spread; the
  subject carries condition/idiosyncratic variance the comps do not). We tried to re-cut the
  upper marker on a TIME SPLIT: p0.80 chosen on <2025-07 (26.2% above) delivered **34.3%**
  held-out. **It did not transfer** — the residual is REGIME-dependent (p50 → 50.8% on
  2024-2025H1 vs 62.6% on 2025H2+; the trailing-trend drift lags an accelerating market).
  **Verdict: REJECT the fixed-quantile calibration** (would be false precision) and ship the
  natural p25/p75 markers with their MEASURED rates + the regime caveat, killing the
  "cheap/dear quartile" label that asserted a property that does not hold stably.
- **Lesson:** a metric you don't compute is a bias you can't see — and the condo leaderboard
  had already carried the column the landed one dropped.

## EXP-0012 — L3/L4: landed engine LV1 + conformal + the `landed-valuation` skill (2026-07-16)
- **Status: DONE. GL2 PASS · GL3 PASS · GL4 REVISE→fixed (hostile round 1: 6.9, 3 blockers).**
- **LV1** (`landed_engine.py`) = LC2 street point where the street answers, else LA1 pooled
  fallback (coverage only, NEVER blended — L1 showed even 1-2 street comps beat every pool),
  + split-conformal band per (street-liquidity × type), + a ×1.6 widening and confidence cap
  ≥8k sqft. Same architecture the condo line validated ("best method where it applies +
  fallback + calibrated band", not an ensemble blend).
- **Result (7,027 walk-forward landed resales, ≥2023-01, lag 56d):**
  **LV1 median APE 0.0949 / P90 0.290 / coverage 100% / held-out band coverage 77.5%
  / sign test 51.7% (median_signed −0.46%)** — post-EXP-0013 bias fix; the pre-fix figures
  were 0.0934 / 78.9% but carried a systematic ~3.5% LOW skew (actual exceeded the point
  63.2% of the time). vs the L1 bar LC1 0.1037/87.3%: **−0.9pp median, −5.3pp P90, +12.7pp
  coverage, interval 39.0%→77.5%.**
  - **GL3 PASS:** beats the bar; band inside 80%±5pp; respects the ~6% bundle noise floor
    (9.5% is ~3pp above it — the rest is unobservable, not slack).
  - LA1 alone 0.0976 (coverage 99.97%) — pooled anchors buy COVERAGE, not points (the condo
    reversal, transposed, confirmed again).
  - Conformal table fingerprinted (sha1 of landed_candidates.py + landed_size_curve.py);
    `test_conformal_table_matches_landed_code` turns drift RED.
- **L4 skill** (`landed-valuation`): `value_landed.py` + bilingual report + `tests/test_landed.py`
  (22). Field trials (asof 2026-07-01 = reconstruction, so the checks below were INVISIBLE
  to the engine): Loyang Rise 1,635sf 99yr → 1,507 land-psf vs an unseen 2026-05 print at
  ~1,514 psf (**−0.5%**, post-bias-fix; it was −3.6% pre-fix — a clean draw of the
  systematic skew EXP-0013 removed); Bowmont Gardens 9,225sf detached → S$14.88M vs an
  unseen 2026-07 print at S$14.00M (+6.3%; was +2.9% pre-fix — individual cases move
  both ways when a systematic bias is removed; the aggregate sign test is the evidence) — in the regime the engine honestly calls its weakest; Cardiff Grove →
  DECLINES (no URA caveat in the 5y window despite a PASS-8.5 craft valuation) and routes to
  Investment Suite. **Finding: the IS app carries deeper street history than the URA API
  window** — the escalation path is real, not a cop-out.
- **Hostile review round 1 (REVISE 6.9)** — quant core reproduced EXACTLY (leaderboard
  bit-for-bit, all trial arithmetic, conformal multipliers); **all 3 blockers were in the
  CLIENT-FACING layer and are fixed:**
  1. `condition` was a DEAD INPUT while the report claimed "band widened, NOT guessed"
     (identical output for None/original/rebuilt). Fixed by telling the truth: the engine is
     condition-blind, the band already embeds AVERAGE condition ignorance (calibrated on
     condition-blind residuals), and condition now yields a DIRECTIONAL note (floor/ceiling)
     with magnitude explicitly NOT quantified → L2e.
  2. The comps exhibit filtered on type only while captioned "lease-matched" — it displayed
     FH prints against leasehold subjects, the very pairing the 232% guard forbids (32 mixed
     street groups). `_comps` is now lease-matched.
  3. **Guidance converted ignorance into aggression:** ask = band top → "ask S$21.8M" on a
     plot that printed S$14.0M, implied psf above every comp shown. The conformal band is the
     ENGINE'S predictive error, not achievable dispersion. Guidance is now SUPPRESSED with a
     reason when big-plot / fallback / band >±22.5%.
  - Also fixed: **latent `999`-in-`1999` tenure-parser collision** (substring scan turned a
    99yr-from-1999 lease into quasi-freehold → would silently re-arm the 232% failure on a
    data refresh; inert today only because landed lease_start jumps 1997→2000) — anchored
    regex + a regression test; report money → 3 sig figs (was 8 sig figs on a ±44% band).
- **Hostile review round 2 (REVISE 7.05)** — quant core again reproduced BYTE-IDENTICALLY
  (all four trial dicts, band multipliers to 6dp incl. the non-obvious `_type|Detached`
  fallback, size-curve integration to 0.1 psf). Two blockers, both real, both fixed:
  1. **The lease guard disabled itself for the SUBJECT.** `remaining_lease` returns quasi-FH
     when `lease_start` is unknown — correct for a COMP (dropped, conservative), catastrophic
     for the SUBJECT: it upgraded a real leasehold to quasi-freehold and priced it off
     freehold comps, silently. Reviewer's probe: FABER AVENUE Semi-D leasehold → 2,080
     land-psf off all-FH comps; supply `lease_start=1995` → 1,196 psf (**−42% on an input the
     SKILL called "optional"**). Now **REFUSES** (`lease_start_required`) rather than guessing,
     and the CLI gained `--tenure` / `--lease-start` so the documented run honours SKILL's Inputs.
  2. **The guidance gate was blind to hard cases.** It keyed on `band_rel`, which comes from a
     conformal table keyed on (liquidity × type) — a per-CELL CONSTANT that can never respond
     to a subject. 26/120 sampled subjects were hard_case and still emitted an ask; trial 1
     (ALNWICK, hard_case, 18% spread) asked 2,185 land-psf — above EVERY comp on its own page
     (the round-1 blocker, still live for the general class because I had gated only the
     big-plot branch). Now gated on **hard_case + confidence<55** as well.
  - **P1 fixed: LIVE mode did not honour its own claim.** `as_of(lag_days=0)` still applied the
    month-END convention, hiding the current partial month (0 of 30 July-2026 landed caveats
    visible) — **the exact EXP-0008 defect, fixed for condo and reintroduced here**, and
    untested because every test used a past asof. Month-gate branch ported from `value_unit`
    + a live-path test. Report now renders the buyer/seller notes in the LIVE branch too
    (the "NOT a negotiation target" caveat was being dropped exactly where unhedged numbers
    were shown).
- **Verdict:** LV1 ACCEPT. Skill ships scope-limited (see GL4 line in the roadmap).
- **Lesson (recorded):** both rounds passed the MODEL and failed the CLIENT-FACING LAYER —
  dead inputs, exhibits contradicting their captions, and uncertainty mechanically converted
  into negotiation aggression. The quant work was the easy half.

## EXP-0011 — L2a: the landed land-size curve, re-fitted (2026-07-16)
- **Status: DONE. Verdict: ACCEPT (<8k sqft) / ACCEPT-WITH-SCOPE-LIMIT (≥8k).**
- **Trigger:** L1/EXP-0010's error map — LC1 median APE climbs monotonically with plot size
  (1.5-3k 8.8% → 3-5k 12.2% → 5-8k 14.5% → 8-15k **24.0%** → 15k+ **41.2%**) — and LC1's
  size prior was `CRAFT_SIZE_ELASTICITY = -0.877`, ported from ONE street's two cross-size
  legs in the Cardiff craft study (guardrail-#5: unvalidated globally).
- **Method** (`research/fit_land_size_curve.py`), three estimators so the answer doesn't rest
  on one design: (A) **within-street FIXED EFFECTS** slope of ln(psf) on ln(area) — demean
  inside each (street,type) group so street prestige/location cannot contaminate the size
  read; n=10,399 rows in 1,027 groups. (B) near-simultaneous (≤6mo) same-street cross-size
  **pairs**, no index at all. (C) FE **by size bucket** = the functional-form test.
- **Findings.** Global elasticity **−0.500** (FE) / **−0.575** (pairs) — **the ported −0.877
  over-corrects ~1.7×**. A single log-log constant is **inadequate**: the slope collapses with
  size — <3k −0.53 | 3-5k −0.60 | 5-8k −0.59 | **8-15k −0.01** | **15k+ +0.05**. Economically:
  small terraces trade on QUANTUM (extra land ≈ free); big plots trade on LAND (each sqft
  carries ~full marginal value). **TYPE is not an independent axis** — within the 3-5k band
  Detached is as steep as Terrace (Terr −0.73 / Semi −0.56 / Deta −0.63), so the global
  "Detached −0.24" was a size-composition artifact. (Honest caveat: at 5-8k the bands diverge,
  Semi −0.16 (n=106) vs Deta −0.69 (n=433) — the no-type claim is firm at 3-5k, not everywhere.)
- **Leakage:** pre-2023 vs full-history agree where identified (global −0.482/−0.500; <3k
  −0.509/−0.526; 5-8k −0.547/−0.585) ⇒ the curve is **structural, not a price signal**.
  Shipped: <3k −0.51 (pre-2023 value); 3-5k −0.64 and 5-8k −0.56 are **pre/full midpoints**
  (documented deviation from a pure pre-2023 rule; effect ~0.8% psf on a 20% size move).
- **SCOPE LIMIT ≥8k:** the two periods DISAGREE (8-15k pre −0.349 vs full −0.006) on n=14-51
  street groups. **The regime with the largest error is the one URA identifies worst.** Ship a
  conservative flat −0.20 there and force wide band + case-tier in the engine — never a point.
- **Shipped** as `landed_size_curve.py`: a piecewise elasticity **integrated in ln(area)**, so
  the price surface is continuous across the 3k/5k/8k breaks (tested).
- **Impact (L2c lease matching applied in the same candidate, LC2):** bar 10.51% → **9.12%**,
  P90 0.341 → 0.283, and **the size explosion is gone: 8-15k 24.0%→11.4%, 15k+ 41.2%→17.5%,
  GCB-flag 30.0%→18.9%.** (Those are LC2's, which declines ~29% of 15k+ subjects; the SHIPPED
  LV1 answers 100% and measures 11%/20% there — quote LV1 to clients.)
- **L2c (same commit):** lease matching — quasi-FH (FH/999yr) may NEVER price a real
  leasehold; leaseholds must be within ±25y of remaining lease. This is the fix for L1's
  decisive failure (spatial kNN priced ~20-yr-left 99yr terraces off freehold neighbours:
  median APE **232%** on sub-2M subjects). Applied even to same-street grids — streets mix tenures.
- **L2b/L2d/L2e:** L2d delivered as LA1 (coverage anchor, EXP-0012). **L2b time adjustment and
  L2e improvement bounds NOT opened** — L1's regime slices are flat (10.1-10.8% across 2023-26)
  and the noise floor already bounds L2e's answer; both stay MONITOR in the backlog rather than
  spending a module on unjustified error mass.

## EXP-0010 — L1 landed baseline: the honest leaderboard + noise floor, GL1 (2026-07-16)
- **Status: DONE (7,027 resale pure-landed subjects ≥2023-01, walk-forward, lag 56d).
  GL1: PASS** — leaderboard lag-stable, bar/tail/coverage/noise floor recorded, L2
  selection justified by error mass (memo below).
- **Leaderboard (median APE / P90 / coverage / pct>10% / interval-cover):**
  - **LC1_craft_landed 0.1051 / 0.341 / 87.3% / 0.514 / 0.397 ← THE LANDED BAR**
    (Cardiff craft skeleton: street same-spec grid, recency HL 18mo, ported size prior)
  - LB4_spatial_knn **0.1114 / 0.310** / 79.1% — best TAIL; geography earns keep via retrieval
  - LB1_same_street 0.1297 / 0.382 / 79.4% — street median alone
  - LB2_street→district 0.1423 / 0.383 / **99.8%** — pooling buys coverage, costs 4pp median
  - LB5_district_price 0.1494 / 0.418 / 99.8% · LB3_type×tenure×seg 0.1512 / 0.381 / 100%
  - Lag-stability: 42d ≡ 56d EXACTLY (month-end arithmetic: any lag in (31,58] lands in
    the same visibility bucket for 30/31-day months); 70d moves the bar +0.03pp. Stable.
  - Interval baseline: comp-IQR bands cover 38-50% (target 80) — broken as expected
    (condo's were 43%); the calibrated fix is L3 conformal, not a benchmark's job.
- **Noise floor (`research/landed_noise_floor.py`, 395 same-plot pairs gap≤18mo,
  landed-index adjusted): per-print floor ~5.3-6.2%** (trimmed of 39 |ann|>60% rebuild
  suspects vs all-pairs; pair medians 7.6%/8.8% ÷ √2). By type: Terrace ~6.0%, Semi-D
  ~7.8%, Detached ~8.2%. Gap gradient sane (7.2% @1-6mo → 12.1% @13-18mo). **Reading:
  bar 10.5% vs floor ~5.5-6% → only ~4-5pp of the bar is closable error; landed honest
  accuracy will sit HIGH-SINGLE-DIGIT at best — the skill must publish this.**
- **Error-mass map (LC1, the bar):** size is the dominant axis — **1.5-3k sqft 8.8% →
  3-5k 12.2% → 5-8k 14.5% → 8-15k 24.0% → 15k+ 41.2%** (monotone). Detached 17.2% (p90
  0.53) vs Terrace 9.5%. GCB-flag (crude) 30.0% (n=29). Quantum >8M 16.4%. Street depth
  helps monotonically (1-2 comps 13.5% → 16+ 8.8%) — even 1-2 street comps beat every
  cross-street pool (the condo thin-comp reversal, transposed). Regime flat (10.1-10.8%
  across 2023-26). Leasehold is LC1's BEST slice (6.7%) — same-street comps inherit the
  street's lease profile.
- **The decisive cross-street failure:** LB4 on sub-2M subjects = **median APE 232%**
  (n=36, 33 leasehold): spatial kNN prices ~20-years-left 99yr terraces (Jalan Bangket,
  99yr from 1947) off freehold neighbours at **6-10× actual**. LC1 same subjects: 21%.
  **Remaining-lease control is MANDATORY for any cross-street landed method.**
- **L2 decision memo (what the error mass opens):**
  - **L2a land-size curve — OPEN, mandatory confirmed** (the monotone size explosion;
    the ported −0.877 prior already buys LC1 ~2.5pp over size-blind LB1, so a properly
    fitted type×tenure×segment curve is the highest-leverage module).
  - **L2c retrieval/pooling — OPEN, with tenure/remaining-lease matching REQUIRED**
    (the 232% lesson) and spatial-kNN retrieval as the tail-control candidate.
  - **L2d pooled/hedonic anchors — OPEN as pre-scoped** (coverage + hard-case detection,
    NOT points: LB2/LB3 cost 4-5pp median vs the bar but answer ~100%; L3 needs them
    for the 12.7% of subjects where LC1 declines).
  - **L2b time adjustment — OPEN, cheap** (850 repeat pairs now exist to test island vs
    segment index vs repeat-sales drift; regime slices are flat so expectation modest).
  - **L2e improvement bounds — OPEN** (inputs ready: noise floor + 7.7% wild-mover
    rebuild signals from EXP-0009's matcher).
  - **Detached ≥8k sqft / GCB — case-tier + wide-band scope** from day one (41%/30%
    median APE is not engine territory on URA data alone).
- **Files:** `landed_benchmarks.py` (LB1-LB5+LC1, leakage notes inline) ·
  `run_landed.py` (leaderboard/slices/dump; GCB flag) · `landed_noise_floor.py` ·
  tests (125 total, +2 behaviour suites). Artifacts regenerable; dumps gitignored.
- **Leakage sign-off:** comps via MarketView (as-of'd by the harness); landed-PPI
  adjustment to the last PUBLISHED quarter (35d pub lag), capped ±20/25%; subject's own
  month excluded by valuing at end of M-1 (`test_as_of_excludes_future`); noise-floor
  study uses full index history DELIBERATELY (offline data property, documented in the
  script header — not a walk-forward number).

## EXP-0009 — L0 landed data foundation: hygiene, land-psf band, same-plot matcher (2026-07-16)
- **Status: DONE. GL0 GATE: PASS** (`research/audit_landed.py` — re-runnable, `--json`
  machine-readable, `--pairs` prints the spot-check artifact).
- **Slice (2026-07-15 snapshot):** landed universe 12,990 = **pure-landed 11,344**
  (post-hygiene: Terrace 6,033 / Semi-D 3,693 / Detached 1,585; OCR 7,584 / RCR 2,303 /
  CCR 1,424; FH 7,961 / 999yr 1,723 / LH 1,627) + **strata-landed 1,629 ROUTED OUT**
  (orphaned sub-market — neither engine values it; condo backlog #4) + **17 stray
  Apartment+Land rows EXCLUDED** (walk-up / whole-building deals under placeholder
  projects like 'RESIDENTIAL APARTMENTS'; 15 after bulk — the roadmap's "15 stray rows"
  reconciled). **Rule R1: pure-landed requires BOTH type_of_area='Land' AND exact type in
  {Terrace, Semi-detached, Detached}.**
- **Land-psf band (R3):** `LANDED_PSF_BAND = [100, 6500]`, cuts **0 rows** — deliberate:
  BOTH extremes verified REAL (p0 = 107 psf = 70-yr-lease-from-1964 terrace with ~8 years
  left, Jalan Chempaka Kuning; p100 = 5,756 psf = Emerald Hill conservation terrace), and
  psf<700 is 81% leasehold — a genuine decaying-lease sub-market the band must NOT trim.
  The band wraps the verified range as a future-junk guard (percentile method, condo
  analogue [500, 6500] which does cut errors).
- **Exact-copy finding (OPEN, measured not resolved):** 21.4% of pure-landed rows sit in
  same-(street, exact-area, month, price) copies; 95% Resale; **zero normalized-id
  collisions → NOT pull/batch overlap — URA itself lists them as separate entries.**
  Twin-pair sales vs registry double-entry is unresolvable from URA alone. Decision:
  keep in store (condo cross-check: its 4.4% same-key rate is launch-batch pricing =
  real units, so global dedup is wrong), collapse inside the matcher (dt=0 carries no
  signal either way), and carry the documented ≤~21% overstatement bound on
  street-liquidity counts into L1.
- **Same-plot matcher** (`researcher/backtest/landed_pairs.py`): key = (street, exact
  area_sqm, property_type) + 5 rules — dedup dt=0 copies; >4 trades/key = development
  collision; same-month different-price = twin plots; **≥2 New Sales = mirror units (18
  keys / 21 New→New pairs killed — 20 of them would have contaminated the ≤18mo
  noise-floor fuel)**; Resale→New Sale KEPT deliberately (real redevelopment pairs, n=5,
  the L2e signal). Consecutive-trade pairs only (one holding period each).
- **Result:** **685 plots → 850 pairs; 395 with gap ≤18mo** (L1 noise-floor fuel);
  annualized p50 **+7.6%** (plausible for the 2021-26 landed run); wild movers (>|30/60%|
  ann.) 7.8% = rebuild signatures, surfaced not filtered.
- **Spot-check (by hand, seed 7, 25 pairs):** **24/25 structurally plausible** (gate bar
  ≥80%); the 1 miss — JALAN GRISEK New→New mirror pair — motivated rule 5, which removes
  its whole class. 3 pairs carry clear rebuild signatures (Alnwick 350sqm ×1.93/27mo,
  Jalan Chegar ×2.08/16mo, Joo Chiat ×1.82/21mo): same-plot-plausible AND exactly what
  L2e wants to detect.
- **Infra landed (all tested):** `store.is_pure_landed()/is_strata_landed()` +
  `PURE_LANDED_TYPES`/`LANDED_PSF_BAND`; `subjects(kind='pure-landed')` with LAND-area
  defaults 400..150,000 sqft (measured p0.1=883 / p99.9=27,909 — guards, not filters);
  `MarketView.landed()/landed_on_street()/landed_near()` (street index newest-first +
  own spatial grid); harness rows keep street/type_of_area for L1 slicing. 123 tests (+4).
- **GL0:** subjects 10,789 ≥10k ✓ | months 61 ≥48 ✓ | band set from data ✓ | pairs 850
  ≥500 ✓ | noise-floor fuel 395 ≥300 ✓ | rules documented (R1–R5) ✓ → **PASS. L1 (honest
  leaderboard + noise floor) unblocked.**

## EXP-0008 — Fable review round: production-semantics fixes + deferred re-fits (2026-07-16)
- **ADDENDUM (review round 2, 2026-07-16):** the applied fix #1 was itself incomplete —
  "live = lag 0" still ran `as_of`'s month-END visibility convention, so a LIVE valuation
  hid the current partial month's prints (measured: 205 July-2026 caveats in the 07-15
  snapshot invisible on 07-16; TREASURE had 2). Fixed: LIVE mode now gates at month
  granularity only (`contract_ym <= asof month` — drops future-dated data errors, keeps
  the partial month); reconstruction unchanged. Verified: TREASURE live n_comps 140→141
  (the 1,033 sqft July print enters; the 592 sqft one is correctly size-gated out).
  +2 regression tests (live sees current month; reconstruction still excludes). 119 tests.
- **Trigger:** post-ship Fable review of R0–R5. Found 2 real defects beyond the 4 hostile
  rounds, plus closed 3 recurring reviewer P2/P3s. **Mid-round the user pivoted priority to
  LANDED** — so fixes that change C1's residual distribution were fitted, recorded, and
  **deferred** (they require a recalibration run; condo is frozen).
- **APPLIED (safe — do not touch C1 residuals; 117 tests green):**
  1. **Live-vs-reconstruction as-of semantics** (`value_unit.value`): a LIVE valuation (no
     asof) now uses lag_days=0 — the freshly pulled store IS the information set; the old
     blanket 56d lag silently discarded the freshest ~2 months of prints (the most valuable
     evidence). An explicit past asof = reconstruction mode (56d, now DAY-granular, closing
     the month-end coarsening P3). Verified: Treasure live n=140 vs 7/1-reconstruction n=133.
  2. **Fallback band under-coverage fix** (`engine_v2`): the conformal table is calibrated on
     C1 residuals (~3.7% median) but was wrapped around fallback-anchor points (5.5–10%
     error) — and the "0|seg" cell doesn't even exist (C1 rows always have n>=1). Fallback now
     uses the WIDEST of the anchor's own coverage-swept band and the conformal cell.
  3. **Conformal↔code fingerprint**: `analyze_r3.py` stamps sha1(candidates.py) into the
     table; `test_conformal_table_matches_current_c1` turns silent drift into a red test.
  4. **Smooth confidence depth curve** (90 − 45·e^(−n/6)) — no more 7-vs-8-comp 9-point jump.
- **FITTED BUT DEFERRED (condo backlog — apply when condo resumes):**
  - **FLOOR_PP 0.003 → 0.004** (`research/fit_floor_premium.py`: 4,415 same-project
    near-simultaneous size-similar cross-band pairs; global +0.40%/floor, CCR +0.41 /
    RCR +0.37 / OCR +0.46). The last ported constant, now measured.
  - **CCR elasticity −0.02 → −0.016** (align to the EXP-0007 fit).
  - Apply = edit candidates.py, then `run --sample 8000 --dump` → `analyze_r3.py` (recalibrate
    + re-fingerprint) → verify leaderboard didn't regress → update SKILL numbers.
- **Also verified in review:** `_infer` uses the full store deliberately (static attrs only,
  never price — no leakage); `_wquantile`/comp-ranking correct; report renderer consistent.

## EXP-0007 — R5 hostile-review revision: size/time fixes → engine v2.1 (2026-07-16)
- **Trigger:** the R5 acceptance reviewer (REVISE 6.6) blocked on a real defect — the ported
  `SIZE_ELASTICITY=-0.08` was never re-fit on URA, and a 505sf shoebox was setting an 1100sf
  unit's value (The Foliage: point 1716 vs freshest same-size print 1488). Guardrail-#5
  violation (unvalidated constant). Fixed properly, not patched.
- **Elasticity re-fit** (`research/fit_elasticity.py`, 12,638 same-project near-simultaneous
  pairs): global median **−0.068** (≈ the old −0.08 — the reviewer over-generalized from one
  project), but **segment-varying: CCR −0.02, RCR −0.08, OCR −0.09**. Now segment-specific.
- **C1 fixes (all re-backtested):** (a) size-gating — prefer same-project comps within ±35%
  size, so a shoebox can't set a large unit's median; (b) heavier size penalty (×5); (c)
  stronger recency (dmonths/15) + a time-adjustment-QUALITY penalty (a stale comp needing a
  big index adjustment is down-weighted); (d) time-adjustment cap [0.80, 1.25].
- **Result: the fixes IMPROVED the whole population, not just the edge case** —
  **C1 median 4.10% → 3.68%**, V2 3.71% / 100% cover / conformal recalibrated to ~82-85%
  held-out (85% nominal) / width 0.185. Every segment/tenure/regime slice improved.
  pct>10% 15.4%→12.8%. (Headline the conservative ~82% from EXP-0006 held-out.)
- **Hard-case honesty (value_unit):** surface the freshest same-size print as
  `recent_same_size_reference`; a **directional flag** when the point sits >5% above it
  ("possibly optimistic on stale comps — corroborate"); widen the band down to that reference
  on hard cases; hard-case confidence cap 62→55; lease-aware fallback order (A1 first for
  leasehold); SKILL.md IS-corroboration downgraded from "automated" to a manual to-do.
- **The Foliage after fixes:** point 1710 (defensible from the comps), but now conf 55,
  band widened to 1680 (= the fresh reference), directional flag "12% above the 1527 fresh
  print", verify-before-offer says pull IS comps. Honest, not misleading.
- **Round-2 fresh review: REVISE 7.6, ZERO blocking issues** (up from 6.6 + 2 blockers —
  prior blockers confirmed closed). Two P1s fixed to cross the 8.0 PASS bar: (P1a) on a
  directional hard case the POINT is now pulled toward the fresh same-size print
  (median blend) + band rescaled — The Foliage 1710→1619 (was +12% over the 1528 fresh ref,
  now +6%); (P1b) SKILL.md/docstring numbers reconciled to v2.1 (3.7% / ~82% held-out, 85%
  nominal / segment elasticity); (P3) the recent-ref is now size-adjusted so the directional check is
  apples-to-apples (Stirling correctly 4.2% < trigger).
- **Known refinements (backlog, non-blocking — R5-follow / R8):** re-fit FLOOR_PP=0.003
  (still a ported constant, guardrail-#5); within-project lease-decay term for short-lease
  projects; conformal table point-method fingerprint + a 3rd split for nominal selection.
- **Verdict:** engine v2.1 ACCEPT. **R5 SHIPPED — hostile acceptance review PASS 8.7/10**
  (round 4; every dimension ≥8.0, zero blockers). Rounds: 6.6 (2 blockers: unvalidated
  elasticity) → 7.6 (0 blockers, point-vs-fresh-print) → 7.6 (doc coverage inconsistency) →
  **8.7 PASS**. Reviewer independently reproduced all field trials byte-for-byte, the
  elasticity fit, ~84% held-out conformal, and the leakage firewall. G5 MET. Remaining P2/P3
  are polish (FLOOR_PP re-fit, base-tier smoothing, as-of day granularity) — backlog. 116 tests.

## EXP-0006 — R3-finish: thin-comp reversal, 3-anchor blend, conformal → engine v2 (2026-07-16)
- **Status:** DONE. **G3 MET, cleanly.** Engine v2 = `engine_v2.py` (V2).
- **① Thin-comp reversal (the important finding).** Sliced every method by same-project comp
  count. Even at **1-2 comps**, plain **C1 is BEST (4.84%)**; blending in an anchor makes it
  WORSE (E2 5.08%, E3 5.57%, E1 5.81%). The anchors (5-15% APE cross-project) never beat even
  a 1-2-comp same-project read. **This REVERSES the R3-kickoff hypothesis** that anchors help
  thin-comp point estimates: they help COVERAGE (the ~0.6% no-same-project cases) and
  INTERVALS, not the point. Blending down-weights C1 exactly where it shouldn't.
- **② 3-anchor blend E3** (C1 ⊕ median(A1,A2,A3)): median 4.16%, tail marginally best of the
  blends, but union band over-covers (94%). Same lesson — no point-accuracy gain over C1.
- **③ Conformal intervals** (`research/analyze_r3.py`, split by time: cal<2025-01,
  test>=2025-01, per liquidity×segment cell, 85% nominal chosen by sweep): **coverage 82.0%,
  width 0.197 held-out** vs C1's own IQR band (43%, far too narrow) and the E-series union
  band (86-94%, too wide). ~30-57% sharper than union at target coverage.
- **Engine v2 = V2** (`engine_v2.py`): **C1 point wherever it answers, else anchor fallback
  (A2→A3→A1), + conformal band.** Backtest: **median 4.09% / coverage 100% / interval 82.7%
  / P90 12.6% / pct>10% 16.0%.** Ties C1 on median (no anchor drag), beats every blend
  (E2/E3 4.16%), fixes C1's coverage (99.3→100%) and calibration (43→83%).
- **Verdict:** V2 ACCEPT (engine v2). **E0/E1/E2/E3 SUPERSEDED** — necessary experiments that
  proved the blend doesn't help the point; kept as code + registry record, not shipped. A1/A2/A3
  retained as fallback + (future) interval inputs. Conformal table `conformal_table.json` shipped.
- **Simplicity win (mandate):** the evidence killed the more complex ensembles in favour of
  "best method where it applies + fallback + calibrated band." Complexity was not free — it hurt.
- **Leakage sign-off:** conformal calibration STRICTLY precedes its evaluation slice (time
  split); table is a fixed lookup at inference; V2 reads only as-of C1/anchors. Clean.

## EXP-0005 — R3 team fan-out: alt anchors + learned ensemble (2026-07-15/16)
- **Status:** DONE for 3 of 4 threads; **independently re-verified in the main repo** (numbers
  reproduce exactly; I read every method for leakage — all clean). Conformal thread did not
  finish (workflow died at the session boundary) — carried to R3-finish.
- **Method:** background Workflow (wf_234bc499-6eb) — 4 worktree-isolated agents each built +
  backtested a method; adversarial verify stage started but did not complete, so I did the
  verification myself (code read + full-backtest reproduction at n=4000/5000).
- **Results (verified, sorted best-first):**
  - **E2_ensemble_pooled (C1+A2)**: median **4.16%** / P90 12.7% / cover 100% / **interval 87%** / pct>10% 16.0%
  - **E1_ensemble_learned (C1+A1)**: median **4.18%** / P90 12.7% / cover 100% / **interval 81%** / pct>10% 16.3%
  - E0_ensemble (hand-set): 4.42% / interval 81%  (SUPERSEDED by E1/E2)
  - **A2_avm_pooled** (empirical-Bayes shrinkage, project→segment→broad): median **5.46%** / cover 100% — best independent anchor
  - **A3_avm_knn** (feature-space kNN, k=40): median **7.2%** / cover 100%
  - A1_avm_hedonic: 10.3% (weakest anchor)
- **Findings.** (1) A learned/tuned ensemble recovers the median to ~C1 (4.08%) while keeping
  100% coverage and fixing interval calibration to the 80% target — **E1/E2 meet G3** on the
  "tie within noise + materially better calibration (43%→81-87%)" branch. (2) The pooled
  anchor A2 (5.46%) >> hedonic A1 (10.3%): shrinking same-project psf toward a market prior
  beats regressing on hedonic attributes for this data. (3) Swapping A2 for A1 in the ensemble
  (E2) marginally wins in-sample (4.16 vs 4.18, better tail + calibration).
- **Honest nuance (the synthesis judgement).** E1 vs E2 are within noise. E2 is marginally
  better *in-sample* but A2 is same-project-CORRELATED (it uses same-project comps), so E2 is
  less genuine anchor-diversity and more "C1 + graceful fallback + honest band". E1 pairs C1
  with A1 which is attribute-based and genuinely independent — likely more robust on the
  thin/no-same-project production cases the backtest under-weights. **Recommendation: E2 as the
  default point estimate; keep A1/A2/A3 as validated components; R3-finish = (a) proper
  per-cell conformal to tighten intervals to exactly 80%, (b) test a 3-anchor blend, (c)
  re-check E1 vs E2 on a thin-comp-enriched slice before locking the skill.**
- **Team process lesson.** Worktree agents produced integrable, tested, leakage-clean code
  (verified). But the verify+synthesis tail was lost when the session ended — record: for
  long fan-outs, the orchestrator must re-verify from the journal, not trust the run to finish.

## EXP-0004 — R3 kickoff: independent hedonic AVM anchor + evidence-state ensemble (2026-07-15)
- **Status:** IN PROGRESS (5,000-subject walk-forward). Anchor + naive ensemble built &
  integrated; refinement (learned weights, alt anchors, conformal) handed to the team.
- **A1 hedonic AVM** (`researcher/backtest/avm.py`): stdlib OLS, log(psf) ~ log(area) +
  floor + time + segment + tenure + lease-age + district, fit once/month on the as-of condo
  set, subject evaluated at the as-of time coordinate (leakage-safe; unit test recovers
  synthetic coefficients within 3%). **Result: median APE 10.4% / P90 32% / coverage 100%
  / interval-cover 70%.** Far worse than same-project (4%) BUT never declines and beats the
  proxies (B4 14%, B5 18%) — a viable anchor for the thin/no-same-project cases.
- **E0 evidence-state ensemble** (`ensemble.py`): blend C1⊕A1 by same-project comp count.
  **Result: median 4.42% / P90 13.9% / coverage 100% / interval-cover 81%.**
- **Finding.** The ensemble **fixes the headline defect: interval coverage 44%→81% (hits the
  80% target) + full coverage**, at a small median cost (4.08→4.42%) caused by over-weighting
  the AVM on liquid cases (w_c1 only reaches 1.0 at n>=10). The point-accuracy trade is a
  weighting-tuning issue; the interval + coverage win is real and is what production needs.
- **Verdict:** A1 ACCEPT (as a thin-comp anchor, scope-limited). E0 MONITOR — beat it with
  learned weights before shipping. Next: team fan-out (below).
- **Leakage sign-off:** AVM fits on market.condo() (as-of only); subject evaluated at as-of
  time, never its own month; no full-history artifact. Unit-tested coefficient recovery.

## EXP-0003 — Condo-resale baseline leaderboard + G1 (2026-07-15)
- **Status:** DONE (8,000-subject sample, subjects >= 2023-01; lag-stable at 42/56/70d).
- **Result (median APE / P90 / cover / pct>10% / bias):**
  - C1_grid_adapted **0.041** / 0.122 / 0.994 / 0.154 / +0.007  ← THE BAR
  - B3_same_project_filtered 0.041 / 0.110 / 0.905 / 0.126 / -0.013
  - B2_median_last3 0.048 / 0.148 / 0.994 / 0.211
  - B1_latest 0.049 / 0.161 / 0.994 / 0.228
  - B4_nearest_project **0.139** / 0.376 / 0.997 / 0.626
  - B5_segment_avg **0.178** / 0.561 / 1.000 / 0.687 / **+0.204**
- **Findings.** (1) Same-project methods dominate (~4-5%); geographic/segment proxies are
  2.7-4.3x worse. (2) **C1 (the value-a-property grid) only ties B3 and beats the naive
  same-project median B2 by ~0.7pp median** — but with better tails (P90 0.122 vs 0.148,
  pct>10% 0.154 vs 0.211) at full coverage. The grid's time/floor/size adjustments earn a
  MARGINAL keep; the same-project signal itself carries the result. (3) Slices are flat on
  MEDIAN (segment 0.040-0.045, tenure 0.040-0.043, regime 0.040-0.045, all <6.0% = 1.5x
  bar) — leasehold is NOT worse (tenure is controlled within a project). (4) The real
  failures are in the TAIL: >4M quantum pct>10%=0.28 / P90=0.197; thin liquidity (1-2
  comps) pct>10%=0.236. (5) Interval coverage 0.44 vs 0.80 target — bands far too narrow.
- **G1 VERDICT — nuanced.** The strict "median >1.5x bar" rule opens NOTHING (max slice
  median 0.050 < 0.060). But that rule mis-measures here: the median is solved by
  same-project comps; the unacceptable defects are **(a) tail risk, (b) broken interval
  calibration, (c) same-project dependency** — and the backtest population (established
  resale) UNDER-represents production's thin/no-same-project cases, where our only fallback
  (B4/B5) is 14-18% APE. **Decision: skip the R2a/R2b/R2c median-driven bake-offs; pull R2d
  (independent AVM anchor) forward INTO R3, and make R3 = {AVM anchor that needs no
  same-project comp} + {conformal intervals} + {evidence-state ensemble}.** Re-open R2b/R2c
  only if R3 leaves a slice/tail gap. Recorded rationale, not a silent override.
- **Leakage sign-off:** as_of firewall (test_as_of_excludes_future); lag-stable 42/56/70;
  4% median is plausible for liquid same-project resale (not a leak signature); no
  full-history artifact used. contractDate month-granularity and index pub-lag respected.

## EXP-0002 — URA store audit / G0 (2026-07-15)
- **Status:** DONE. `research/audit_ura.py` (re-runnable).
- **Data:** full 4-batch pull — **136,436 caveats, 3,880 projects, 2021-07..2026-07 (61
  months)**. Segment CCR 20,582 / RCR 39,122 / OCR 76,732. Sale: Resale 83,461 / New
  47,910 / Sub 5,065. Tenure: leasehold 95,678 / freehold 36,066 / freehold_equiv 4,692.
- **Condo universe (Apt+Condo, EC excl):** 106,549. Landed 12,990. EC excluded 16,897.
  **Resale-condo subjects: 61,097.** Distinct condo projects 2,285 (liquid >=8: 1,431).
- **Exclusion rules (applied as subject AND comp):** no_of_units>1 (60 bulk/en-bloc);
  psf outside [500, 6500] (107 low + 2 high — data errors); EC excluded from condo
  universe (distinct sub-market); Land-type rows bucketed to landed.
- **G0 GATE: PASS** (>=48 months ✓ 61; >=20k subjects ✓ 61k; >=800 projects ✓ 2,285).
- **Real-data bugs caught (verify-before-trust paying off):** URA emits stray cp1252 bytes
  mid-batch (robust decode added); landed spelling `Semi-detached` + `Strata *` variants
  (substring match); EC contamination (excluded).

## EXP-0001 — Walk-forward harness + simple-benchmark baseline (condo resale)
- **Status:** infrastructure built; **awaiting the first real URA pull** to produce numbers.
- **Hypothesis:** a leakage-safe walk-forward backtest over URA caveats can rank valuation
  methods, and the mandate's 5 simple benchmarks form the bar every complex method must clear.
- **Data:** URA `PMI_Resi_Transaction` (rolling ~5y, month-granular caveats), normalized by
  `researcher/sources/ura.py`. As-of firewall = month-end + 56d caveat-lag buffer
  (`researcher/backtest/store.py`). Subject valued as of end of month M-1.
- **Methods under test (benchmarks):** B1 latest same-project · B2 median last-3 same-project ·
  B3 same-project ±30% size / 12mo · B4 nearest other project (1km, 12mo) · B5 segment
  (CCR/RCR/OCR) median psf, index-time-adjusted.
- **Benchmark:** these ARE the benchmarks — they set the bar for later hedonic/ML/graph methods.
- **Metrics:** MAE, mean/median/P75/P90 APE, %>10%, signed bias, interval coverage/width
  (`researcher/backtest/metrics.py`).
- **Result:** _pending real data._ Run: `python -m researcher.backtest.run`.
- **Failure analysis / slices to check first:** thin-volume projects (B1/B2 decline rate),
  CCR vs OCR, large/penthouse units, leasehold with short remaining lease, new-vs-resale mix.
- **Verdict:** _pending._

### Open leakage risks to audit before trusting any number
1. **contractDate is month-only** → same-month look-ahead is structurally avoided by valuing
   as of M-1, but verify no method reaches into month M.
2. **Caveat lag** is modelled as a flat 56d buffer — a guess. Sensitivity-test 42/56/70d.
3. **Index publication lag** (`index.as_of_quarter`, 35d) — a backtest at t must target the
   last *published* quarter, never a later one.
4. **Enriched panels** (`factors/panel_condo_enriched`, `dialectic_synthesis`, OneMap
   enrichment) are learned on FULL history → must NOT be fed into a pre-t valuation as-is.
   Any use inside the harness needs an as-of rebuild. **Not yet done — do not use them here.**
