"""Same-plot repeat-sale matcher for pure landed (L0 / EXP-0009).

URA landed caveats carry NO address or lot id, so plots are matched on
(street, EXACT area_sqm, property_type) — land areas are surveyed to 0.1 sqm and
near-unique per lot (68% of keys are singletons on the 2026-07 snapshot). The known
collision source is cookie-cutter developments: a row of new terraces shares one street,
one exact plot size and one type, so exact-area matching alone would chain different
houses into fake "repeats". Rules 2-4 below exist to kill exactly that.

Matching rules (validated on the 2026-07-15 snapshot, EXP-0009 — hand spot-check: 24/25
sampled pairs structurally plausible, the 1 miss being a New->New twin-unit pair that
rule 6 now removes; ~7-8% of pairs are legitimate >|30-60%| annualized movers, the
rebuild signature L2e wants surfaced, NOT filtered):

  1. input slice: pure-landed, bulk-excluded, landed psf band (caller's job — see
     `audit_landed.py` / L1 harness usage);
  2. within a key, collapse same (month, price) copies to one trade — twin-pair sale or
     registry double-entry, either way dt=0 carries no time signal (measured: ~18% of
     landed rows sit in such copies; irreducibly ambiguous from URA alone);
  3. drop keys with more than MAX_TRADES_PER_PLOT distinct trades in the window —
     one house trading 5+ times in ~5 years is a development-collision signature;
  4. drop keys where one month shows two DIFFERENT prices — two identical plots trading
     simultaneously cannot be one plot;
  5. drop keys with two or more New Sale trades — a plot cannot be developer-sold twice;
     that is a row of mirror units trickling out over months (measured: 18 keys / 21
     New->New pairs, 20 of them inside the gap<=18mo noise-floor fuel). Resale->New Sale
     survives deliberately: that is a REAL redevelopment pair (L2e's rebuild signal);
  6. pairs = CONSECUTIVE trades within a surviving key (each pair = one holding period).

Downstream: L1 noise floor (gap <= 18mo pairs -> market-adjusted dispersion bound),
L2b repeat-sales time signal, L2e rebuild detection (long-gap price jumps).
"""
from __future__ import annotations

from collections import defaultdict

from .store import months_between

MAX_TRADES_PER_PLOT = 4


def plot_key(t: dict) -> tuple[str, float, str]:
    return (t["street"], t["area_sqm"], t["property_type"])


def same_plot_groups(txs: list[dict]) -> dict[tuple, list[dict]]:
    """{plot_key: trades sorted by month} after dedup/cap/twin rules. Only keys with
    >= 2 surviving trades are returned."""
    raw: dict[tuple, list[dict]] = defaultdict(list)
    for t in txs:
        raw[plot_key(t)].append(t)

    out: dict[tuple, list[dict]] = {}
    for key, rows in raw.items():
        # rule 2: same (month, price) -> one trade
        seen: set[tuple] = set()
        trades = []
        for r in sorted(rows, key=lambda r: (r["contract_ym"], r["price"])):
            k = (r["contract_ym"], r["price"])
            if k not in seen:
                seen.add(k)
                trades.append(r)
        if len(trades) < 2:
            continue
        # rule 3: too many trades = collision, not a busy house
        if len(trades) > MAX_TRADES_PER_PLOT:
            continue
        # rule 4: two different prices in one month = identical twin plots
        yms = [r["contract_ym"] for r in trades]
        if len(set(yms)) < len(yms):
            continue
        # rule 5: >=2 New Sales = mirror units of one development, not one plot
        if sum(1 for r in trades if r["type_of_sale"] == "New Sale") >= 2:
            continue
        out[key] = trades
    return out


def repeat_pairs(txs: list[dict]) -> list[dict]:
    """Consecutive same-plot trade pairs. Each dict is self-contained for analysis:
    street/type/area, both trades' (ym, price, psf, type_of_sale), gap_months, ratio,
    annualized (None when gap < 3 months — too short to annualize honestly)."""
    pairs: list[dict] = []
    for (street, area_sqm, ptype), trades in same_plot_groups(txs).items():
        for a, b in zip(trades, trades[1:]):
            gap = months_between(a["contract_ym"], b["contract_ym"])
            ratio = b["price"] / a["price"]
            pairs.append({
                "street": street, "area_sqm": area_sqm, "property_type": ptype,
                "market_segment": a["market_segment"], "district": a["district"],
                "tenure_type": a["tenure_type"],
                "a_ym": a["contract_ym"], "a_price": a["price"], "a_psf": a["psf"],
                "a_sale": a["type_of_sale"],
                "b_ym": b["contract_ym"], "b_price": b["price"], "b_psf": b["psf"],
                "b_sale": b["type_of_sale"],
                "gap_months": gap, "ratio": ratio,
                "annualized": (ratio ** (12 / gap) - 1) if gap >= 3 else None,
            })
    pairs.sort(key=lambda p: (p["street"], p["area_sqm"], p["a_ym"]))
    return pairs
