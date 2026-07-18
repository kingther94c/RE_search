---
name: investment-suite-valuation
description: "PropNex Investment Suite app + the Researcher work — now split into its own repo RE_search; mobile_bridge is back to a clean tool"
metadata:
  node_type: memory
  type: project
  originSessionId: 00e62779-5c6e-4a94-8f62-60034e67882f
---

**Two repos now (split 2026-06-30):**
- **`mobile_bridge`** (github.com/kingther94c/mobile_bridge) = the focused Android
  read-bridge TOOL only. Tip after cleanup ~`f2ec908`. Keeps `mobile_bridge/apps/
  investment_suite.py` (the app profile = bridge config).
- **`RE_search`** (github.com/kingther94c/RE_search) = the cross-source **Researcher**
  ("大脑"). Sibling folder `D:\projects\git_projects\RE_search`. Houses the migrated
  `research/` (mbx.py adb harness, harvest_sale.py, captures/), `researcher/legacy/valuation/`
  (comparable-adjustment engine), `deliverables/` (bilingual HTML report), and
  `.claude/skills/` (native Claude Code skills). Run: `python -m researcher.valuation.run`,
  `python deliverables/build_report.py`. mobile_bridge moved here = removed from mobile_bridge.

**Design decision (validated by a judge-panel workflow + the user's key point that
data-gathering is Claude-driven with NO fixed tool):** the Researcher is a *skills-centric*
project; data is fetched by Claude with whatever fits (WebFetch/WebSearch for web,
`research/lib/mbx.py` for Android apps). Dependency arrow one-way `RE_search → mobile_bridge`,
and currently there's NO code dep (mbx shells `adb` directly). Future sources: web, and
小红书/Xiaohongshu. Skills live in `.claude/skills/` (auto-discovered via frontmatter),
de-machine-pinned (no baked-in `emulator-5554`/coords/paths). See `RE_search/ARCHITECTURE.md`.

**App = PropNex Investment Suite** (`com.investmentsuite` / activity
`com.propnex.investmentsuite.MainActivity2`), a Singapore property-data app; user logs in
manually (UI automation only; session persists across emulator reboots — 2026-07-03 run needed
no re-login). Emulator: tablet AVD `mb_play` 2560×1600, launch WINDOWED (see
[[emulator-windowed-visible]]). **Extraction reality (non-obvious):** values are native
`TextView` (readable) but MOST nodes have NO resource-id (Compose classes like `s2.e2`) →
use text/desc selectors + full-screen dumps. Sale "Past Transactions" table has a **frozen
left Contract-Date column**; only swiping the *data* columns scrolls it; fling momentum is
non-deterministic (dedup + stale-stop). **Tower View** = per-unit grid with the app's own
**Est. Val** per unit (benchmark AVM).

**#18-03 re-valuation (2026-07-03, analyst PASS 8.8/10, 4 rounds):** point S$1,716,000
(2,309 psf), negotiation band $1.67–1.73m — twin #18-02 (same floor/743sf/type) printed
$1,730,900 ($2,330) on 2026-06-23 = the ceiling anchor; app AVM $2,250 = floor (it LAGS the
twin print ~3.6% — the app itself marks that buyer −$59,900). Old 2,269-psf report underpriced
by treating the 2021 covid-dip own-purchase ($2,020) as neutral (stack's 2013 prints $2,107-2,258).
**Three-surface 5Y comp reconstruction is now the method**: Sale table (lazy-loads AND skips
mid-window rows) ∪ Profitability sell-legs ∪ Tower View PP fields, fuzzy-dedup cross-surface
(same unit+price within 30 days = one caveat, date fields differ ~4 days between surfaces).
Band-head figures (e.g. 5Y low $1,968) are the app's own opaque aggregates — never
force-reconcile per-print. NEW tool `research/lib/harvest_towerview.py` (block-verified, dual-axis,
offline-testable parser). CCL6 Cantonment opens 2026-07-12 (LTA) — re-check prints in August.

**2026-07-08 harvest lessons (One Pearl Bank run + hostile review findings):**
- **Stale-panel artifact is the #1 multi-block trap:** naive block-tab taps silently no-op,
  so the SAME Tower View grid gets captured under several block names → identical
  (unit,sqft,pp_date,pp_price) fingerprints across blocks → one real sale enters the comp
  set N times (Gallop: 1 print counted 7×, +$62k on the estimate — caught by review).
  `reconstruct_comps.strip_stale_panel_artifacts` gates it; only trust `twr_`-era captures.
- **Rent tab is TWO lists:** Past Rentals (Tier-1 contracts: area BANDS + month-year dates)
  then a live/agency list (EXACT sqft + full dates + "live data" badges + "Unit Mix
  Rentals" footer) — Tier-2, never mix. Contract rows can have type '-' and psf without
  cents ('$6'). Rows have no unit identity → identical contracts collapse on dedup; on
  high-volume devs read volume from the app band + advertised totals, not row counts.
- Profitability: break-even rows print unsigned "$0"; a "View All (N)" footer belongs to
  the section of the rows ABOVE it (scrolled headers lie).
- Big Tower View grids (OPB 774 units) need the SERPENTINE scan + cross-run seed
  accumulation — a single vertical+horizontal pass covered only 34%.
- Floor premium must be FITTED per development (OPB 0.44%/层 vs 0.30% default) — the
  default overprices low floors from high-floor comps.
- **Wide-grid cross-cell misalignment:** during horizontal panning, a Tower View cell's
  sqft can pair with a NEIGHBOUR column's PP/Est strings (OPB: 62/450 units; 41 impossible
  rows reached a comp set). Defense: price/psf implies sqft — >2% off the cell's sqft →
  quarantine those fields (parser) + per-row price=psf×sqft gates in reconstruct AND
  validate_digest. Zero false positives on clean data (Spottiswoode 0/161).
- **Profitability section labels come from the PROFIT SIGN, never screen position** — the
  section header scrolls off and mid-list rows inherit the wrong section (OPB mislabelled
  14/5 vs the true 10/1/8; the fixed counts reconciled exactly with the app's View All (9)
  for losses+breakeven). Break-even rows print unsigned "$0".
  See [[condo-valuation-pipeline]].

**2026-07-03 harvest lessons (cost real debugging):**
- Search: tap bar at (1280,200), `mbx.py clear` (MOVE_END + batched DEL — adb can't select-all)
  before `mbx.py type` or queries CONCATENATE; landed addresses need precise street names
  ("Kingsmead Road" works, "Kings Road" doesn't fuzzy-match the Landed section).
- **Landed coverage is rich**: per-address pages (type/tenure/land size/subtown/history since
  1998) + Sale tab with **Nearby / District / Street** scopes + a separate "Realtime Agency
  Data" panel (NOT caveats — tag rows by panel). Street files are the Tier-1 anchor for
  landed price bands.
- Tower View block tabs (y≈371): verify the grid actually changed after each tap (first-unit
  sqft signature) — naive tab taps silently no-op.
- `swipe down 0.9` from mid-screen pulls the **Android notification shade**; scroll only
  inside the content region (e.g. region 1280,1250→1280,700).
- Scrolling harvest can pair one transaction with 2-3 neighbouring frozen-column dates
  (phantom duplicate rows) — `harvest_sale._collapse_scroll_artifacts` collapses them; verify
  the true date on a static re-read of the table top.

**Trial result — #18-03 Spottiswoode Suites** (16 Spottiswoode Park Rd, D02, freehold,
743 sqft compact 3BR): model fair value **S$1.686M ($2,269 psf)**, +1.5% vs app AVM
(S$1.661M); gross yield ~3.2%. "18 Spottiswoode Park Road" is a *different* development
(Spottiswoode 18); subject is at **16**, "#18-03" = floor 18 / stack 03.
See [[android-read-bridge]], [[kelvin-user]].
