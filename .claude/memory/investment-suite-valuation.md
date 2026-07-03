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
  `research/` (mbx.py adb harness, harvest_sale.py, captures/), `researcher/valuation/`
  (comparable-adjustment engine), `deliverables/` (bilingual HTML report), and
  `.claude/skills/` (native Claude Code skills). Run: `python -m researcher.valuation.run`,
  `python deliverables/build_report.py`. mobile_bridge moved here = removed from mobile_bridge.

**Design decision (validated by a judge-panel workflow + the user's key point that
data-gathering is Claude-driven with NO fixed tool):** the Researcher is a *skills-centric*
project; data is fetched by Claude with whatever fits (WebFetch/WebSearch for web,
`research/mbx.py` for Android apps). Dependency arrow one-way `RE_search → mobile_bridge`,
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
