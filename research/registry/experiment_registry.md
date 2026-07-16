# Experiment registry

Newest first. One row per experiment; link to code/commit. Verdict vocabulary in
[`README.md`](README.md).

---

## EXP-0012 — L3/L4: landed engine LV1 + conformal + the `landed-valuation` skill (2026-07-16)
- **Status: DONE. GL2 PASS · GL3 PASS · GL4 REVISE→fixed (hostile round 1: 6.9, 3 blockers).**
- **LV1** (`landed_engine.py`) = LC2 street point where the street answers, else LA1 pooled
  fallback (coverage only, NEVER blended — L1 showed even 1-2 street comps beat every pool),
  + split-conformal band per (street-liquidity × type), + a ×1.6 widening and confidence cap
  ≥8k sqft. Same architecture the condo line validated ("best method where it applies +
  fallback + calibrated band", not an ensemble blend).
- **Result (7,027 walk-forward landed resales, ≥2023-01, lag 56d):**
  **LV1 median APE 0.0934 / P90 0.287 / coverage 100% / held-out band coverage 78.9%**
  (`research/analyze_landed.py`, calibrate <2025-01 → validate ≥2025-01, nominal 80%,
  width 0.399). vs the L1 bar LC1 0.1051/87.3%: **−1.2pp median, −5.4pp P90, +12.7pp
  coverage, interval 39.7%→78.9%.**
  - **GL3 PASS:** beats the bar; band inside 80%±5pp; respects the ~6% bundle noise floor
    (9.3% is ~3pp above it — the rest is unobservable, not slack).
  - LA1 alone 0.0976 (coverage 99.97%) — pooled anchors buy COVERAGE, not points (the condo
    reversal, transposed, confirmed again).
  - Conformal table fingerprinted (sha1 of landed_candidates.py + landed_size_curve.py);
    `test_conformal_table_matches_landed_code` turns drift RED.
- **L4 skill** (`landed-valuation`): `value_landed.py` + bilingual report + `tests/test_landed.py`
  (15). Field trials (asof 2026-07-01 = reconstruction, so the checks below were INVISIBLE
  to the engine): Loyang Rise 1,635sf 99yr → 1,459 land-psf vs an unseen 2026-05 print at
  ~1,514 psf (−3.6%); Bowmont Gardens 9,225sf detached → S$14.41M vs an unseen 2026-07 print
  at S$14.00M (+2.9%) — in the regime the engine honestly calls its weakest; Cardiff Grove →
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
- **Verdict:** LV1 ACCEPT. Skill ships scope-limited (see GL4 line in the roadmap).

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
