# experiments/ — frozen one-off scripts, by experiment id

Moved here from `research/` root in the 2026-07-18 reorg. Each script's verdict
is recorded in [`../registry/experiment_registry.md`](../registry/experiment_registry.md);
the constants they fitted were lifted into `researcher/` (citations in the code).

| Script | Experiment | What it established |
|---|---|---|
| `fit_elasticity.py` | EXP-0007 | condo size elasticity from near-simultaneous same-project pairs |
| `fit_floor_premium.py` | EXP-0008 | per-floor premium from size-matched cross-band pairs |
| `landed_noise_floor.py` | EXP-0010 / L1 | same-plot repeat-pair bundle-noise floor (accuracy lower bound) |
| `fit_land_size_curve.py` | EXP-0011 / L2a | three-estimator landed land-size curve |
| `diagnose_l2b.py` | EXP-0016 | landed hot-regime low bias diagnosis (cap-binding hypothesis REFUTED) |
| `run_l2b_variants.py` | EXP-0017 | L2b candidate runs (V2 lt_tail / V3 lt_full) vs pre-registered gates |
| `validate_l2b_v2.py` | EXP-0017 | V2 lag-stability + full leaderboard + conformal dump |
| `run_l2f_split.py` | EXP-0019 / L2f | true-road vs URA parent-street comp pool test |
| `thomson_reserve.py` | (new-launch study) | Thomson Reserve pre-launch scorecard + pricing run |

The **live** recalibration path is NOT here: `tools/analyze_r3.py` and
`tools/analyze_landed.py` are the fingerprint-enforced conformal stampers, and
`tools/reconcile_is_ura.py` is the street-alias evidence procedure.
