"""L2b fitted local trend — unit tests.

The estimator's one job: recover the MARKET's month curve from caveats while group
(street,type) mix is absorbed by fixed effects — and never, ever extrapolate beyond
an observed month (GY-0003 is the tombstone for forecasts in the time adjustment).
"""
from __future__ import annotations

import math
import random

from researcher.backtest.landed_benchmarks import _tadj_psf
from researcher.backtest.local_trend import LocalTrend, fit_landed_trend


def _mk(street, ptype, ym, psf):
    return {"street": street, "property_type": ptype, "contract_ym": ym, "psf": psf}


def _months(n, start_y=2023, start_m=1):
    out = []
    y, m = start_y, start_m
    for _ in range(n):
        out.append(f"{y}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def test_recovers_known_trend_through_group_mix():
    """Two streets at very different price levels, trading in DIFFERENT proportions over
    time (cheap street dominates late months). A raw monthly median would read the mix
    shift as a price FALL; the FE fit must recover the true +1%/mo drift instead."""
    rng = random.Random(7)
    months = _months(24)
    txs = []
    for i, ym in enumerate(months):
        level = 0.01 * i                       # true ln-trend: +1%/mo
        n_dear = max(1, 6 - i // 4)            # dear street fades out
        n_cheap = 2 + i // 4                   # cheap street ramps up
        for _ in range(n_dear):
            txs.append(_mk("DEAR ST", "Terrace",
                           ym, math.exp(math.log(2000) + level + rng.gauss(0, 0.03))))
        for _ in range(n_cheap):
            txs.append(_mk("CHEAP ST", "Terrace",
                           ym, math.exp(math.log(1000) + level + rng.gauss(0, 0.03))))
    lt = fit_landed_trend(txs, months[-1])
    got = lt.factor(months[0], months[-1])
    want = math.exp(0.01 * 23)
    assert abs(math.log(got / want)) < 0.05, (got, want)
    # and the raw median WOULD have been fooled (sanity that the test bites):
    from statistics import median
    raw0 = median(t["psf"] for t in txs if t["contract_ym"] == months[0])
    raw1 = median(t["psf"] for t in txs if t["contract_ym"] == months[-1])
    assert raw1 / raw0 < want * 0.9            # mix shift masks the rise in raw medians


def test_never_extrapolates_beyond_last_fitted_month():
    months = _months(12)
    txs = [_mk("A ST", "Terrace", ym, 1000 * math.exp(0.02 * i))
           for i, ym in enumerate(months) for _ in range(5)]
    lt = fit_landed_trend(txs, months[-1])
    # a request 6 months past the data clamps to the last observed level — factor 1.0
    assert lt.factor(months[-1], "2024-06") == 1.0
    assert lt.factor("2020-01", months[0]) == 1.0   # and below the range, symmetric
    assert lt.last_ym == months[-1]


def test_singleton_groups_identify_nothing():
    """A street with ONE print carries no time information — must be dropped, not
    absorbed into the month curve."""
    months = _months(6)
    txs = [_mk("REAL ST", "Terrace", ym, 1000) for ym in months for _ in range(2)]
    txs.append(_mk("LONER ST", "Terrace", months[-1], 5000))   # singleton outlier
    lt = fit_landed_trend(txs, months[-1])
    assert abs(math.log(lt.factor(months[0], months[-1]))) < 1e-6


def test_empty_and_thin_inputs_degrade_to_identity():
    lt = fit_landed_trend([], "2025-01")
    assert lt.factor("2024-01", "2025-01") == 1.0
    assert lt.last_ym is None


def test_thin_live_partial_terminal_month_is_dropped():
    """A live fit can see the CURRENT month mid-flight. The walk-forward only ever
    validated complete months (min n=90), so 2-3 hot prints on the 2nd of a month must
    not steer the bridge: a terminal month under MIN_TERMINAL_N drops out of the fit."""
    months = _months(8)
    txs = [_mk("A ST", "Terrace", ym, 1000) for ym in months[:-1] for _ in range(6)]
    # partial current month: TWO wild prints, 3x the level
    txs += [_mk("A ST", "Terrace", months[-1], 3000) for _ in range(2)]
    lt = fit_landed_trend(txs, months[-1])
    assert lt.last_ym == months[-2]                      # partial month excluded
    assert abs(math.log(lt.factor(months[0], months[-1]))) < 1e-6   # clamps, no jump
    # at MIN_TERMINAL_N prints the month is kept (informative, smoothing damps it)
    txs2 = [_mk("A ST", "Terrace", ym, 1000) for ym in months[:-1] for _ in range(6)]
    txs2 += [_mk("A ST", "Terrace", months[-1], 1100) for _ in range(5)]
    lt2 = fit_landed_trend(txs2, months[-1])
    assert lt2.last_ym == months[-1]


def test_tadj_lt_tail_bridges_from_published_quarter_midmonth():
    """lt_tail multiplies the capped PPI leg by the OBSERVED bridge quarter-mid ->
    newest fitted month; with a flat PPI stub the whole adjustment IS the bridge."""
    class _FlatIdx:
        def factor(self, a, b, kind):
            return 1.0
    lt = LocalTrend({"2025-02": 0.00, "2025-03": 0.01, "2025-04": 0.02}, {})
    ctx = {"index": _FlatIdx(), "asof_q": "2025Q1", "asof_ym": "2025-06",
           "ltrend": lt, "tadj_mode": "lt_tail"}
    c = {"psf": 1000.0, "contract_ym": "2024-12"}
    # bridge: Q1 mid month (2025-02, level 0.00) -> newest fitted (2025-04, 0.02)
    assert abs(_tadj_psf(c, ctx) - 1000.0 * math.exp(0.02)) < 1e-6
    # mode off -> shipped behaviour (flat index -> unchanged)
    ctx2 = {"index": _FlatIdx(), "asof_q": "2025Q1", "asof_ym": "2025-06"}
    assert _tadj_psf(c, ctx2) == 1000.0


def test_tadj_lt_tail_fresh_comp_is_not_double_bridged():
    """A comp NEWER than the published quarter's midpoint bridges from ITS OWN month —
    blanket-bridging from the quarter mid double-counted the recent move on the freshest
    (highest-weight) comps: a subject's own same-month print came out +4% above itself."""
    class _FlatIdx:
        def factor(self, a, b, kind):
            return 1.0
    lt = LocalTrend({"2025-02": 0.00, "2025-03": 0.01, "2025-04": 0.02,
                     "2025-05": 0.03, "2025-06": 0.04}, {})
    ctx = {"index": _FlatIdx(), "asof_q": "2025Q1", "asof_ym": "2025-06",
           "ltrend": lt, "tadj_mode": "lt_tail"}
    # same-month comp: NO bridge at all
    same = {"psf": 1000.0, "contract_ym": "2025-06"}
    assert abs(_tadj_psf(same, ctx) - 1000.0) < 1e-9
    # a May comp bridges only May->Jun (+1%), not Feb->Jun (+4%)
    may = {"psf": 1000.0, "contract_ym": "2025-05"}
    assert abs(_tadj_psf(may, ctx) - 1000.0 * math.exp(0.01)) < 1e-6


def test_tadj_lt_full_replaces_ppi_with_sanity_clamp():
    lt = LocalTrend({"2024-01": 0.0, "2025-01": 5.0}, {})    # absurd fitted jump
    ctx = {"index": None, "asof_q": None, "asof_ym": "2025-01",
           "ltrend": lt, "tadj_mode": "lt_full"}
    c = {"psf": 1000.0, "contract_ym": "2024-01"}
    assert _tadj_psf(c, ctx) == 2000.0                       # clamped at x2.0 guard
