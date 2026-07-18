---
name: data-source-trust-hierarchy
description: "For SG property research, Investment Suite + SG-official data are ground truth; property research/agent reports are low-trust (conflicted). Anchor every load-bearing number to Tier 1."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 05a8a0f6-1bf9-4533-9ace-a43bc7336084
---

For any Singapore property research, rank sources by trust — and never launder a low-trust
number as fact:

**Tier 1 — ground truth (anchor every load-bearing number here):**
- **PropNex Investment Suite** (the Android app) — URA-caveat transactions, per-unit **Est. Val**
  (AVM benchmark), **realised returns** (buy/sell pairs), rental contracts. Read via the
  `read-investment-suite` skill / `research/mbx.py`. See [[investment-suite-valuation]].
  **MEASURED against the URA API (EXP-0018, 2026-07-17) — three corrections:**
  (1) on caveats IS and the URA API are the **SAME data at the SAME lag** — IS is NOT fresher
  (0 of 104 rows newer) and NOT "far more data" per road (a strict subset: 104 vs URA's 135,
  because **URA's `street` is a coarse PARENT label merging adjacent roads**);
  (2) IS's genuine, unique edge is **address↔caveat mapping** (URA carries no address at all),
  **history depth** (10Y street window; per-address back to ~1996), per-unit floor/stack,
  rents, Est.Val — use it for THOSE, not for freshness;
  (3) **inside the app, one panel is NOT Tier 1**: *Realtime Agency Data* (sits directly under
  the caveat table, tenure renders as `-`) is agency/asking data — it carries newer dates than
  the caveats and mixing it in silently turns asks into "transactions". Caveats only.
- **Singapore official / primary sources**: URA (SPACE Master Plan, price index, REALIS), OneMap
  (school 1km query, geocoding — use `researcher/sources/onemap.py`), PUB (flood-prone list), SLA
  (INLIS title, LDAU foreign-ownership), MOE (P1 balloting / school data), IRAS (BSD/ABSD/SSD,
  property tax), MAS (SSD rules, SORA), LTA (rail), data.gov.sg.

**Tier 2 — usable but verify against Tier 1:** EdgeProp / SRX / PropertyGuru / 99.co transaction
data (ultimately re-presented URA caveats, but re-keyed and sometimes stale/wrong).

**Tier 3 — low trust, treat as CLAIMS not facts:** property research reports, brokerage/agent
editorial and marketing sites (Stacked Homes, agent lead-gen "collection" sites, darrenong,
newlaunchesreview, etc.). **Why:** Kelvin's directive (2026-07-03) — 研报都有目的性和利益相关
(they have an agenda and a conflict of interest; they're selling). Do NOT trust them blindly.

**How to apply:**
- Every psf / price / date / policy rate / balloting figure / distance must trace to Tier 1
  before it drives a conclusion. Use Investment Suite for transactions/AVM/rents/realised returns;
  SG-official for policy, planning, geography, flood, title.
- When only a Tier-3 source is available, mark the number "unverified — agent/report source" and
  flag it for Tier-1 confirmation; never present it as confirmed.
- This is exactly what the hostile-analyst critique loop kept catching ("not cross-checked vs URA
  REALIS"). Bake the verification in **upfront**, not after. Concrete gap to close: the 2026-07-03
  study suite ran on Tier-2/3 web data and never invoked Investment Suite — redo the transaction/
  valuation layer through Tier 1 when it matters. See [[landed-research-capability]], [[kelvin-user]].
