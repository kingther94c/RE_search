"""Hedonic AVM anchor (A1) — an independent valuation opinion that needs NO same-project
comp. Stdlib OLS (no numpy), fit strictly on as-of data, once per valuation month.

This is the anchor that must rescue the cases where same-project methods have nothing to
say (thin/boutique/new projects) — the production population the backtest under-weights.
It is the mandate's transparent hedonic: log(psf) ~ log(area) + floor + time + segment +
tenure + lease-age + district. Every feature is a property attribute known at valuation OR
the as-of time coordinate — never anything dated after t.

Leakage discipline:
  - fit on `market.condo()` which is already as-of filtered by the harness;
  - the subject is NOT in that set (it transacts in month M; the view is as-of end of M-1);
  - the subject is evaluated at the AS-OF time coordinate, not its own (future) month.
"""
from __future__ import annotations

import math
import random

from .store import months_between

_T0 = "2021-07"           # time origin for the linear trend term
_RIDGE = 1e-6             # tiny L2 to keep X'X invertible with sparse district dummies
_TRAIN_CAP = 8000        # subsample per-month training for a tractable pure-python fit


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Solve a x = b (a symmetric, ridge-regularised) by Gaussian elimination w/ pivoting."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-12:
            continue
        m[col], m[piv] = m[piv], m[col]
        inv = 1.0 / m[col][col]
        for j in range(col, n + 1):
            m[col][j] *= inv
        for r in range(n):
            if r != col and m[r][col]:
                f = m[r][col]
                for j in range(col, n + 1):
                    m[r][j] -= f * m[col][j]
    return [m[i][n] for i in range(n)]


class HedonicAVM:
    def __init__(self, beta, districts, t_asof, resid_std, fallback_psf):
        self.beta = beta
        self.districts = districts          # ordered list -> dummy columns
        self.t_asof = t_asof
        self.resid_std = resid_std          # sd of log residuals (for later conformal use)
        self.fallback_psf = fallback_psf

    # feature vector: keep in sync with fit()
    def _row(self, tx, t_months):
        d = {dd: 0.0 for dd in self.districts}
        if tx["district"] in d:
            d[tx["district"]] = 1.0
        lease_age = 0.0
        if tx["tenure_type"] == "leasehold" and tx["lease_start"]:
            lease_age = max(0.0, int(tx["contract_ym"][:4]) - tx["lease_start"])
        fl = tx.get("floor_lo")
        floor_mid = ((fl + tx["floor_hi"]) / 2) if fl is not None else 8.0
        return [1.0, math.log(tx["area_sqft"]), floor_mid / 10.0, t_months / 12.0,
                1.0 if tx["market_segment"] == "CCR" else 0.0,
                1.0 if tx["market_segment"] == "RCR" else 0.0,
                1.0 if tx["tenure_type"] == "leasehold" else 0.0,
                1.0 if tx["tenure_type"] == "freehold_equiv" else 0.0,
                lease_age / 10.0] + [d[dd] for dd in self.districts]

    @classmethod
    def fit(cls, train: list[dict], asof_ym: str) -> "HedonicAVM | None":
        if len(train) < 200:
            return None
        if len(train) > _TRAIN_CAP:
            train = random.Random(42).sample(train, _TRAIN_CAP)
        districts = sorted({t["district"] for t in train if t["district"]})[:-1]  # drop 1 baseline
        t_asof = months_between(_T0, asof_ym)
        self = cls([], districts, t_asof, 0.0, 0.0)
        rows = [self._row(t, months_between(_T0, t["contract_ym"])) for t in train]
        ys = [math.log(t["psf"]) for t in train]
        k = len(rows[0])
        xtx = [[0.0] * k for _ in range(k)]
        xty = [0.0] * k
        for r, y in zip(rows, ys):
            for i in range(k):
                ri = r[i]
                if ri:
                    xty[i] += ri * y
                    row_i = xtx[i]
                    for j in range(i, k):
                        row_i[j] += ri * r[j]
        for i in range(k):
            for j in range(i):
                xtx[i][j] = xtx[j][i]
            xtx[i][i] += _RIDGE * len(rows)
        beta = _solve(xtx, xty)
        self.beta = beta
        resid = [y - sum(b * v for b, v in zip(beta, r)) for r, y in zip(rows, ys)]
        mean = sum(resid) / len(resid)
        self.resid_std = (sum((e - mean) ** 2 for e in resid) / len(resid)) ** 0.5
        self.fallback_psf = math.exp(sum(ys) / len(ys))
        return self

    def predict_psf(self, subject) -> float:
        row = self._row(subject, self.t_asof)     # subject at the AS-OF time coordinate
        logpsf = sum(b * v for b, v in zip(self.beta, row))
        return math.exp(logpsf)


def _fitted(market):
    if "hedonic" not in market.cache:
        market.cache["hedonic"] = HedonicAVM.fit(market.condo(), market.asof_ym)
    return market.cache["hedonic"]


def avm_hedonic(subject, market, ctx):
    """A1: independent hedonic AVM. Fits once per month on the as-of condo set."""
    model = _fitted(market)
    if model is None:
        return None
    psf = model.predict_psf(subject)
    if not (300 <= psf <= 7000):
        return None
    area = subject["area_sqft"]
    # a rough +/- band from the fit's log-residual sd (properly calibrated in R3 conformal)
    lo = round(math.exp(math.log(psf) - model.resid_std) * area, 0)
    hi = round(math.exp(math.log(psf) + model.resid_std) * area, 0)
    return {"method": "A1_avm_hedonic", "psf": round(psf, 1), "price": round(psf * area, 0),
            "low": lo, "high": hi, "n_comps": 0, "note": "hedonic AVM (as-of fit)"}


ANCHORS = {"A1_avm_hedonic": avm_hedonic}
