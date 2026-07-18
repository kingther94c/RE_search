"""Conformal-table code fingerprints — ONE definition, used by the stamper AND the test.

A conformal table is calibrated on one specific point-method's residuals. Change that code
without recalibrating and the bands silently skew, so each table carries a sha1 of the code
that produced it and a test turns drift red. Two things this module exists to prevent:

  1. **Drifting file sets.** The stamper (research/analyze_*.py) and the guard test each
     used to hard-code their own tuple of filenames. They can disagree — and did: the
     landed set omitted `landed_benchmarks.py`, a hole exactly where L2b's time adjustment
     lives, so an engine change there hashed as "unchanged" (found 2026-07-17). The sets
     below are the single source of truth for both sides.
  2. **EOL-sensitive hashing.** Hashing raw bytes makes the fingerprint depend on how git
     checked the file out: Windows `core.autocrlf=true` writes CRLF, Linux/CI writes LF, so
     the same commit hashes differently per machine. That is how the two tables ended up
     calibrated against different conventions — condo's stamped from a CRLF checkout,
     landed's from an LF one, each green only where it was stamped and red in a fresh clone
     of the other kind. `code_sha1` normalizes CRLF->LF so the fingerprint tracks the CODE,
     not the checkout. (.gitattributes forces LF too — belt and braces, since an editor or
     a stray tool can still write CRLF locally.)

Regenerate a table (and its fingerprint) with the command in its own analyze script; never
hand-edit a fingerprint to make a test green — that is the exact silent skew the guard exists
to catch. The one legitimate re-stamp is a pure representation change (e.g. the EOL fix
itself), where the code's TEXT is provably identical and the residuals cannot have moved.
"""
from __future__ import annotations

import hashlib
import os

# The fingerprinted point-method sources live in researcher/backtest (the lab);
# this module moved to researcher/engine with the production surface. Hashing is
# content-only, so the move itself did not change any table's fingerprint.
_BACKTEST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "backtest")

#: condo engine v2 point method (C1 grid)
CONDO_CODE_FILES = ("candidates.py",)
#: landed engine LV1 point method — the FULL residual-determining set: the grid, the size
#: curve, the time adjustment (landed_benchmarks._tadj_psf) and L2b's local-trend bridge.
LANDED_CODE_FILES = ("landed_benchmarks.py", "landed_candidates.py",
                     "landed_size_curve.py", "local_trend.py")


def code_sha1(filenames, base: str = _BACKTEST) -> str:
    """sha1 over the named researcher/backtest sources, EOL-normalized (CRLF->LF).

    Order matters and is the tuple's order — keep the constants above as the only callers'
    input so the stamper and the test cannot disagree.
    """
    h = hashlib.sha1()
    for fn in filenames:
        with open(os.path.join(base, fn), "rb") as f:
            h.update(f.read().replace(b"\r\n", b"\n"))
    return h.hexdigest()
