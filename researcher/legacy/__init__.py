"""Legacy (superseded) analysis code — kept RUNNABLE as the craft reference.

The June-2026 engine-v1 condo chain: comp-adjustment engine, the Spottiswoode
#18-03 trial scripts, digest quality gates, and the Investment-Suite end-to-end
pipeline. Superseded for NEW valuations by researcher/engine (walk-forward
validated v2 / LV1), but deliberately retained because the value-a-property
skill uses this three-surface IS craft pipeline to corroborate hard cases.

Rules: bug-fix only, no new features; canonical tax math lives in
researcher/tax.py (the ABSD table here in valuation/dataset.py carried a wrong
PR-3rd rate once — see tax.py's correction record).
"""
