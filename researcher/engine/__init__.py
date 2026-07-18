"""Production valuation surface — what the skills actually run.

Split out of ``researcher/backtest`` (2026-07-18) so shipping code no longer
lives inside the lab package. Contents:

- ``value_unit``   / ``engine_v2``      — condo: value ONE unit (engine v2 + conformal bands)
- ``value_landed`` / ``landed_engine``  — landed: value ONE house (LV1 + conformal bands)
- ``conformal_table.json`` / ``landed_conformal_table.json`` — calibrated band tables
- ``fingerprint``  — sha1 guard tying each table to the point-method code that produced it

The residual-determining point methods (candidates.py, landed_benchmarks.py,
landed_candidates.py, landed_size_curve.py, local_trend.py) stay in
``researcher/backtest`` — the walk-forward lab that validates them — and are
hashed there by ``fingerprint``. Recalibrate via research/tools/analyze_r3.py
(condo) and research/tools/analyze_landed.py (landed); never hand-edit a table.
"""
