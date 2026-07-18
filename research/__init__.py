"""research/ — the Investment-Suite harvest harness + the program's durable records.

Four zones (2026-07-18 reorg):

- ``lib/``          importable harness: mbx (adb UI core), the six table
                    harvesters, reconstruct_comps. ``from research.lib import mbx``.
- ``tools/``        live CLIs: doctor (readiness gate), the fingerprint-enforced
                    conformal recalibration stampers (analyze_r3 / analyze_landed),
                    audits, build_factor_panel, reconcile_is_ura,
                    calibrate_landed_guidance.
- ``experiments/``  frozen EXP-numbered one-off scripts; verdicts live in
                    registry/experiment_registry.md. Do not import from live code.
- ``data/``         harvested per-property dumps (tracked deliberately — the
                    replayable evidence base). ``is_street/`` = EXP-0018/0019
                    landed-street harvests backing the street-alias evidence rule.

``captures/`` (PNG+XML+JSON audit trail; some files are parser test fixtures)
and ``registry/`` (methodology + experiment log — start at 01_roadmap.md) are
unchanged.
"""
