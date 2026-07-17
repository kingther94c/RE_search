"""Address road -> the URA street its caveats are actually filed under.

WHY THIS EXISTS. URA's landed `street` is **the DEVELOPMENT's registered street, not the
house's road**. Landed project names are anonymised to "LANDED HOUSING DEVELOPMENT", and the
street is what survives — so every road of a multi-road estate can land in ONE bucket. Two
consequences, both measured in EXP-0018:

  - a road can have NO URA caveats under its own name while its houses trade every year:
    **CARDIFF GROVE -> ALNWICK ROAD** (16 of 17 in-window sales matched on month+price+area;
    the #19 craft study's own subject, 19 Cardiff Grove @ 1,839.57 sqft sold 2023-03 for
    $4.15M, is in URA as an ALNWICK ROAD Terrace, 1,840 sqft, 2023-03, $4,150,000);
  - a URA street set can contain roads you did not ask for:
    **URA "LOYANG RISE" (135) = Loyang Rise (104) + Loyang View (31)**, exactly.

WHY THERE IS NO CLEVER RESOLVER. The obvious one — nearest URA street centroid, since URA
carries an SVY21 point per street and OneMap geocodes the address — is REJECTED (GY-0006):
it is right by luck and wrong in silence. 43 Loyang View -> LOYANG RISE at 189m (right), but
19 Cardiff Grove -> CHUAN DRIVE at 158m (wrong; the proven parent ALNWICK ROAD ranks #17 at
710m, behind 16 nearer streets in other estates). Proximity does not imply the same bucket:
the estate is filed under one road that may be 650m away. So an alias is only ever entered
here with TRANSACTION EVIDENCE, and an unknown road REFUSES rather than guesses — a wrong
parent prices a house off another estate at full confidence, which is worse than no answer.

HOW TO ADD ONE (the only accepted method):
  1. harvest the road from Investment Suite — it is the only source that knows addresses:
       python research/harvest_street_sale.py "SOME ROAD" --window 5Y
  2. match those transactions against URA buckets on month+price+area:
       python research/reconcile_is_ura.py "SOME ROAD"
  3. if a bucket carries them, add the entry below WITH its evidence string.
"""
from __future__ import annotations

# road (as OneMap spells it) -> (URA street bucket, evidence)
ALIASES: dict[str, tuple[str, str]] = {
    "CARDIFF GROVE": (
        "ALNWICK ROAD",
        "EXP-0018: 16 of 17 in-window Investment Suite transactions on Cardiff Grove match an "
        "ALNWICK ROAD caveat on month+price+area (incl. 19 Cardiff Grove 1,839.57sf, 2023-03, "
        "$4,150,000 — the #19 study's subject). Serangoon Garden Estate, 999yr from 1956.",
    ),
    "LOYANG VIEW": (
        "LOYANG RISE",
        "EXP-0018: all 31 Investment Suite Loyang View transactions are in URA's LOYANG RISE "
        "bucket (135 = Loyang Rise 104 + Loyang View 31, 0 unexplained).",
    ),
}


def resolve(road: str, has_caveats) -> dict:
    """Which URA street should this road's comps come from?

    `has_caveats(street) -> bool` is injected so this module never imports the store (and so
    the caller decides what "has caveats" means — pure-landed only, a psf band, etc.).

    Returns {"ura_street", "basis", "evidence"}; `ura_street` is None when the road is
    unknown — a REFUSAL, deliberately, per GY-0006.
    """
    r = (road or "").strip().upper()
    if r and has_caveats(r):
        return {"ura_street": r, "basis": "direct",
                "evidence": "URA files caveats under this road's own name."}
    if r in ALIASES:
        street, why = ALIASES[r]
        if has_caveats(street):
            return {"ura_street": street, "basis": "alias", "evidence": why}
        return {"ura_street": None, "basis": "alias_empty",
                "evidence": f"{r} maps to {street} ({why}) but that bucket has no caveats "
                            f"in the current pull — refresh the URA data."}
    return {
        "ura_street": None, "basis": "unresolved",
        "evidence": (
            f"URA has no landed caveats filed under {r!r}, and no evidence-backed parent is "
            f"registered for it. This does NOT mean the road has no sales — URA files landed "
            f"caveats under the DEVELOPMENT's street, which can be a different road 650m away "
            f"(EXP-0018). Guessing the parent geographically is rejected (GY-0006: it picked a "
            f"different estate for Cardiff Grove). Resolve it with evidence: "
            f"`python research/harvest_street_sale.py \"{r}\" --window 5Y` then "
            f"`python research/reconcile_is_ura.py \"{r}\"`, and add the alias."
        ),
    }
