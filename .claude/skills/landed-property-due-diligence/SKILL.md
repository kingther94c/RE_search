---
name: landed-property-due-diligence
description: Use when evaluating a SPECIFIC Singapore landed house (terrace/semi-D/detached/GCB) before offering — land, structure, title, rebuild economics, hazards, negotiation — producing a screening score + go/no-go.
---

# Due-diligence a specific Singapore landed house

Run AFTER `landed-area-research` has shortlisted the area. Produces a **screening verdict**
(score + flags + go/no-go) for one address. The land matters more than the house — score it
that way. Quantify with `researcher/landed/scorecard.py`.

## A. The land (more important than the house)

| Check | Prefer / flag |
|---|---|
| **Shape** | rectangular ✔ · triangular / fan / irregular ✘ (hard to design/rebuild) |
| **Length:width** | ~2:1 comfortable · too long = poor light · too narrow = hard layout |
| **Frontage** | wider is better-utilised (e.g. ~10m > 6m) |
| **Topography** | slightly ABOVE road ✔ · clearly below road ✘ (drainage / damp / ponding) |
| **Corner** | corner terrace = more light/air/parking, but pricier + more sun/upkeep |
| **Water** | near canal/drain/river → confirm it doesn't pond |
| **Orientation** | N–S generally preferred; avoid heavy west sun — but judge with actual shading |

## B. The house

- **Last major reconstruction/A&A date** matters more than TOP. "1985, rebuilt 2018" ≠
  "1985, never touched" — completely different value. Check URA Development Applications.
- Condition: cracks, leaks, termites, mould, water seepage, roof.
- **Sewer pipe**: ideally not running under the living room / future build footprint.
- **Manhole position**: a manhole where you'd want a pool / living room / extension is a real problem.
- Ceiling height (esp. old houses); ease of reconfiguration (load-bearing walls, stair, courtyard).

## C. Title & legal (once seriously considering — SLA INLIS)

Pull the title via SLA INLIS and confirm:
- **Easement** (right-of-way over the land), **Restrictive Covenant**, **road reserve / drainage reserve**.
- Caveats, mortgages, and that the **Land Area matches** the listing.
- (This is RES-exam-level competence — do it before offering.)

## D. Rebuild economics (price the land + rebuild, not the asking price)

- SG landed reconstruction cost (2025–2026): ~**S$450–600/psf GFA** normal quality;
  **S$700+/psf** high-end custom. Add demolition, professional fees, time (~18–24 months).
- For an old house: value = land value + (rebuild cost) − teardown/holding, vs a comparable
  already-rebuilt house. Don't pay rebuilt-price for original-condition.
- GFA potential = land area × allowable plot ratio / storeys (respect GCBA 2-storey, attic/basement rules).

## E. Hazards & environment (street-level)

- Flood: PUB flood-prone + low-lying; ask neighbours about ponding after heavy rain.
- Expressway / major road / canal / temple / school / industrial behind or beside.
- **Protected / mature trees** on or near the plot — can constrain rebuild and add cost.
- Noise: visit at different times (weekday, weekend, night, rush hour). Kerb parking saturation.

## F. Tenure & buyer pool

- **Tenure**: freehold vs 999 vs 99 — remaining years affect financing and resale.
- **Foreign-ownership**: landed is *restricted* under the Residential Property Act (LDAU approval
  needed; Sentosa Cove the main exception). A restricted house has a smaller future-buyer pool —
  factor into resale.

## G. Transaction & negotiation

- **Valuation first**: get a banker/valuer indication BEFORE offering.
- Read transaction history: not just price — how OFTEN it sells (frequent flips can signal a problem).
- **Seller motivation** (upgrade / divorce / estate / migration / financial) shapes negotiation.
- Ignore agent pressure ("many offers", "closes tonight") — hold your budget and your CMA.
- **CMA**: build your own — same street, similar land size / age / plot — and adjust per §A.

## Output — run the scorecard

```powershell
python researcher/landed/scorecard.py   # see the module for the input dict / API
```
It scores the property 0–100 against weighted criteria (land shape/frontage/topography/corner,
zoning risk, flood, rebuild status, tenure, foreign-buyer resale, …) and lists red/amber flags,
mirroring the value ordering Location → Street → Land → Zoning → Neighbours → Future → House.

## Gotchas
- "TOP year" is a trap — ask when it was last *rebuilt*.
- Manholes, sewer lines and protected trees are the cheap-to-miss, expensive-to-fix items.
- A restricted (foreign-ineligible) title narrows resale demand even if it's fine for you now.
