---
name: read-investment-suite
description: Use when you need to extract property data (development facts, transactions, rents, per-unit AVMs, realised returns) out of the PropNex Investment Suite Android app via UI automation only.
---

# Read PropNex Investment Suite via UI automation

## When to use this
Use this when you need to extract real property data (development facts, transactions,
rents, per-unit AVM estimates, realised returns) out of the **PropNex Investment Suite**
Android app and you only have UI access — no API, no reverse engineering. The app is
data-dense and table-driven; almost every value is a readable native `TextView`, but
**most nodes carry no resource-id**, so you drive it by screen-captures + `uiautomator`
dumps and select by visible **text/desc**, not by id. This is the entry point before
`harvest-scrolling-android-table` and `value-a-property`.

## This skill spans two repos
- **RE_search** (this repo): you read the app with the **`research/lib/mbx.py`** adb harness.
  That is all you need to harvest data.
- **mobile_bridge** (a SEPARATE repo): supplies the RUNNING EMULATOR only — the mb_play
  AVD and `scripts\start_emulator.ps1` live there (device profile truth: its
  `AGENTS.md`). Its old Appium bridge + IS explorer were retired to `legacy/`
  (2026-07-18); Investment Suite harvesting is owned entirely by this repo's
  `research/lib/` harness.

## Calibrate for your device
The values below were measured on one specific tablet. Re-derive them for yours before
you trust any coordinate.

| Placeholder | What it is | How to find yours |
|---|---|---|
| `$SERIAL` | adb device serial (the reference machine used `emulator-5554`) | `adb devices` |
| `$ADB` | path to `adb` (reference: `…\Android\Sdk\platform-tools\adb.exe`) | use it from PATH, or set the full path |
| resolution | **current mb_play: 1080x2400 portrait (Pixel 6, 420dpi)** — single source of truth is mobile_bridge `AGENTS.md`; the old 2560x1600 tablet numbers below are historical examples | `adb shell wm size` |

Point the harness at your device via env vars: `MBX_ADB` (→ `$ADB`),
`MBX_SERIAL` (→ `$SERIAL`), `MBX_OUT` (capture output dir).

## Prerequisites
- Run the emulator **windowed (visible), never headless** — so the user can watch the
  automation live and step in at any moment (sign in, correct navigation, tap). Launch via
  mobile_bridge `scripts\start_emulator.ps1` (windowed by default; for Investment Suite pass
  `-AvdName mb_play`); do **not** use `-NoWindow` / `-no-window` for a research run. Before
  driving, confirm the emulator window is up and, if it may be hidden, ask the user to bring
  it to the foreground.
- An Android emulator/device with the app **already logged in** (sign-in is the
  operator's job — UI only, no auth bypass).
- `adb` available (see `$ADB` above).
- The `mbx` harness at `research/lib/mbx.py`. Override defaults via env vars if needed:
  `MBX_ADB`, `MBX_SERIAL`, `MBX_OUT`.
- App package `com.investmentsuite`, launch activity `com.propnex.investmentsuite.MainActivity2`.

## Open-failure protocol — pause, report, wait (do NOT fall back to web data)

Investment Suite is **Tier-1 ground truth** for property research; every other skill in this repo
is told to source its load-bearing numbers here first. So if the app cannot be reached, the
correct move is to **stop and hand back to the user — never silently substitute web-aggregator or
research-report data** (those are Tier-2/3 and are exactly what this skill exists to replace).

**The protocol is automated: run `python research/tools/doctor.py` FIRST, every session.** It checks
adb → device → app-foreground → UI dump → logged-in, prints PASS/FAIL per step with the exact
remediation (including the emulator start command and the launch intent), and exits 0 only when
READY. On NOT READY do what it prints; if the fix is the user's (start emulator, sign in), stop
and wait for their confirmation, then re-run doctor. The table below is the same logic for
reference:

| Symptom | Likely cause | What to report / ask |
|---|---|---|
| `adb devices` lists no device (or `mbx.dump_xml()` raises "came back empty") | emulator/device not running | "The Android emulator isn't running — please start it, then confirm." |
| adb device present but app not foreground / wrong package | app not open | "Investment Suite isn't open on the device — please launch it." |
| Screen shows a login / sign-in page (no bottom-nav `Market`/`ProTrend`) | logged out or session expired | "The app is on the login screen — please sign in (UI only; I don't handle credentials), then confirm." |
| adb path/serial wrong (`MBX_ADB`/`MBX_SERIAL`) | misconfigured harness | report the resolved path/serial and ask the user to correct it |

When you pause: state the **exact** error (the failing command + its output), say which manual step
is needed, and **wait for the user to confirm they've done it** before retrying. Only proceed on
lower-tier data if the user *explicitly* says to. `mbx.dump_xml()` already raises on an empty dump
(device offline / app not foreground) rather than returning 0 nodes — surface that error, don't
swallow it.

## The mbx harness commands
Run from `research/`. Every `cap` writes a PNG + XML + JSON to `MBX_OUT`
(default `research/captures/`) so the whole run is auditable and replayable.

| Command | What it does |
|---|---|
| `python mbx.py cap <name>` | Screencap + `uiautomator dump`, parse the tree, save PNG/XML/JSON, print ordered visible texts |
| `python mbx.py texts` | Print ordered visible texts (+ id) of the current screen, no save |
| `python mbx.py tap "<text>"` | Tap the node whose text contains/equals `<text>` |
| `python mbx.py xy <x> <y>` | Tap a raw coordinate (use for no-id targets / table columns) |
| `python mbx.py swipe up\|down\|left\|right [frac]` | Centre-anchored swipe (content moves; `up` scrolls down) |
| `python mbx.py region <x1> <y1> <x2> <y2>` | Precise swipe between two points (use to scroll a frozen-column table — see gotchas) |
| `python mbx.py back` | Press the system Back key |

Each parsed node carries: `text`, `desc`, `id` (short), `full_id`, `cls`, `clickable`,
`bounds`, and `center` (the tap point). Selectors should key off `text`/`desc`.

## Steps
1. **Confirm the app is on a development screen.** `python mbx.py texts`. You are
   "ready" when bottom-nav labels appear (`Market`, `Property Analysis`, `ProTrend`,
   `ProMap`, `More`); you are on an analysis screen when the analysis **tabs** appear
   (`Property Info`, `Tower View`, `Profitability`, ...).
2. **Open a development** if needed: tap the search EditText, type the project name,
   pick the result row. (Search-field locators are *provisional* in this build —
   verify with a fresh dump; targeting the first `EditText` works.)
3. **Switch tabs by text**, then capture: `python mbx.py tap "Sale"` then
   `python mbx.py cap 08_sale`. If a tab label is off-screen, swipe the tab strip
   `left`/`right` first, or tap a known `xy`.
4. **Read each tab** (see the tab map below) and harvest scrolling tables with the
   table-harvest technique rather than per-element selectors.
5. **Persist** what you read into a single dataset module (see
   `researcher/legacy/valuation/dataset.py` for the shape) — one source of truth per development.

## Tab / nav map and what each yields
Analysis tabs across the top of a development screen:

| Tab | Yields |
|---|---|
| **Property Info** | Development facts: address, region/district, TOP year, tenure (freehold/leasehold), land size, plot ratio, total units, storeys, developer |
| **Sale** | Past-transactions table (date, level, unit, type, sqft, psf, price, sale type) + a price band header (low/avg/high psf & price). **Scrolling table — harvest it.** |
| **Rent** | Recent rental contracts (bedrooms, size band, psf, monthly rent) + a rent band header |
| **Tower View** | Per-unit grid: each unit shows **last transacted price AND the app's own "Est. Val"** (its AVM). The single most valuable benchmark — capture the stack/line you care about |
| **Maps** | Location / surroundings |
| **Planning Decisions** | URA planning / GLS context |
| **Nearby Properties** | Comparable projects within a radius (tenure, TOP, units, sale psf range, sales volume, rent psf range, avg yield, rental volume) |
| **Profitability** | Matched buy→sell pairs: realised profit, holding period, annualised return — feeds the advisory |

Bottom nav: **Market · Property Analysis · ProTrend · ProMap · More**.

## Concrete command examples
```bash
# from research/
python mbx.py texts                       # see what's on screen now
python mbx.py tap "Property Info"          # switch tab by visible text
python mbx.py cap 07_propertyinfo          # snapshot dev facts
python mbx.py tap "Sale"
python mbx.py cap 08_sale                  # snapshot first page of the txn table
python mbx.py tap "Tower View"
python mbx.py cap 11_towerview             # per-unit last-txn + Est. Val grid

# scroll the FROZEN-column transaction table by swiping only the DATA region.
# NOTE: 1300 1300 1300 860 are EXAMPLE values for a 2560x1600 tablet — re-derive
# the data-band x and swipe span from your own header dump's bounds/center first:
python mbx.py region 1300 1300 1300 860    # then re-cap; repeat until stale

# EXAMPLE coordinate (2560x1600) — tap a no-id cell/control. Re-measure per device:
python mbx.py xy 886 1450
```
For full-table harvests, drive the dedicated harvesters (they import `mbx`), one per tab.
**Before each harvest: put the app on that tab and select the time window** (5Y for valuation
work). The selected window tab renders right after the `...` token in the dump and every
harvester records it in `meta.window` — check the "saved ..." line says the window you meant.

| Tab open on screen | Command | Output |
|---|---|---|
| Sale (Past Transactions) | `python harvest_sale.py <slug>` | `<slug>_transactions.json/csv` |
| Profitability | `python harvest_profitability.py <slug>` | `<slug>_profitability.json` (buy→sell pairs, both sections; auto-expands `View All (N)`) |
| Rent | `python harvest_rent.py <slug>` | `<slug>_rents.json` (recent contracts + the app's band head) |
| Tower View | `python harvest_towerview.py <slug>` | `<slug>_towerview.json` (per-unit PP + Est. Val AVM grid) |

All four are dedup-on-scroll with stale-stop; zero-row runs refuse to overwrite existing files.
Then reconstruct the complete comp set: `python reconstruct_comps.py <slug> --asof YYYY-MM-DD
--subject "#NN-SS"` — or go straight to the condo pipeline (see `value-a-property`).

## LANDED is a DIFFERENT path — address-first, not project-first (R4a/R4b, EXP-0018)

The four harvesters above drive a **condo development** screen. **Landed has no project id** —
the app is address-first — so it has its own harvester (`research/lib/harvest_street_sale.py
"<STREET>"`) and its own screen shape. Use it whenever you need a landed street's caveats
(e.g. to resolve a `street_not_found`, or to attribute a URA parent bucket to real roads).

**The landed chain has a last mile — run it, don't eyeball the JSON:**
```bash
python research/lib/harvest_street_sale.py "LOYANG RISE"          # on-device harvest
python research/tools/is_street_compare.py loyang_rise \
    --road "LOYANG VIEW" --area 1650 --engine-street "LOYANG RISE"   # true-road slice vs LV1
python research/tools/reconcile_is_ura.py "LOYANG RISE"           # EXP-0018 four-gate check
```
`is_street_compare` slices the harvest by **true road** (the IS superpower URA lacks), gives
n / p25 / med / p75 / trailing-12m / last-3-cluster on RAW bundle psf, and — with
`--engine-street --area` — prints the engine's adjusted point beside it. Reading rule printed
by the tool: |IS trailing-12m median vs engine point| ≤10% reads as corroboration (the two
are DIFFERENT bases: raw vs time+size-adjusted); bigger gaps → check area basis, condition
mix, or a majority-dominated parent bucket (EXP-0019). Parsing lives in
`research/lib/is_rows.py` — one normalizer for every consumer; never re-parse the app's
strings ad hoc.

**Why you need IS at all for landed** (measured, EXP-0018): **URA's landed `street` is the
DEVELOPMENT's registered street, not the house's road.** URA anonymises landed projects to
"LANDED HOUSING DEVELOPMENT", so one estate's several roads collapse into ONE street bucket —
`URA "LOYANG RISE" (135) = Loyang Rise (104) + Loyang View (31)`, and Cardiff Grove's houses
sit under `ALNWICK ROAD`. **IS is the only source that maps a caveat to a real address.**

**Navigation contract** (verified 1080×2400 phone; re-derive coords for a tablet):
1. **Property Analysis** → tap the search bar → type the STREET → tap any address result.
   *Verify the field before searching* — a residual char turns "LOYANG RISE" into "ELOYANG
   RISE" and returns nothing, which looks exactly like "no data". The harvester's
   `_set_search` reads the field back and retries.
2. **Sale** tab → pick the window (**5Y** matches the URA API's rolling window; 10Y/custom for
   depth). Re-enter Sale from **Property Info** to reset — Back can land on a "Type Summary"
   view with no scope selector.
3. Scope defaults to **Street**. Scroll DOWN gently (≈500px/650ms — 600px flings past the
   whole section) to the **"View All (N)"** under *Street Transactions* and tap it.

**THE TRAP — two panels, only one is caveats.** The Sale screen stacks *Street Transactions*
(URA caveats, real tenure strings) ABOVE *Realtime Agency Data* (**Tier-2** agency listings,
tenure renders as `-`). The agency panel carries NEWER dates the caveats don't — reading "the
newest date on the Sale screen" scores IS as fresher on **asking data**, not transactions. The
two `View All` footers look identical; which one a blind tap hits depends on scroll offset.
`harvest_street_sale.assert_caveat_table()` refuses anything but the expanded caveat table, and
it has fired for real. **Never mix the agency panel into caveat data.**

**Parsing a table WIDER than the screen** (the tablet fit every column; a phone never does):
- The **"Contract Date"** column is FROZEN — its node y-centres are byte-identical across a
  horizontal swipe, so dump each screen twice (left half: address/type/tenure; right half:
  area/psf/price/sale-type) and JOIN on the frozen date's y-band. Exact, unlike joining on the
  date TEXT (a street prints twice on one day).
- **Classify cells by FORMAT, not x-coordinate.** Three things break coordinate snapping: the
  header is not sticky (scrolls away after screen 1), the h-swipe lands on a different offset
  each time, and column x-centres are device-specific. This table's columns are mutually
  exclusive by shape (`99 yrs from …` = tenure, `$1,301` = psf, `$2,100,000` = price by
  magnitude, `Resale` = sale type), so a cell says what it is. Order matters — test tenure
  before address (a tenure string also matches a loose "number word" address pattern).

**Completeness check that needs no second tool:** the harvested rows must reproduce the app's
own band header to the dollar (Loyang Rise: mean **$2,183,582**, matched exactly at 104 rows).
One missing/extra row moves the mean.

**Attribution (the L2f input):** `research/tools/reconcile_is_ura.py "<STREET>"` matches an IS harvest
against the URA bucket on **month+price+area** and reports which rows are the same estate under
a different name. That map feeds `researcher/landed/street_alias.py` (evidence-only aliases,
never geographic guessing — GY-0006) and `research/experiments/run_l2f_split.py` (EXP-0019).

## Gotchas
- **No resource-ids.** UI is Compose-style (classes like `s2.e2`). Do **not** build
  per-element id selectors; use text/desc selectors and full-screen dumps.
- **Frozen left column.** The transaction table's left **"Contract Date"** column is
  frozen. A normal centre swipe won't scroll the data. You must swipe the **data
  columns** using `region` — e.g. `region 1300 1300 1300 860` (those are EXAMPLE values
  for a 2560x1600 tablet; re-derive the data-band x for your screen).
- **Fling momentum is non-deterministic.** Flings overshoot, so the same swipe lands
  on different rows. Don't assume page N+1 starts where page N ended — dedup rows and
  stop on stale rounds (see `harvest-scrolling-android-table`).
- **Tabs can be off-screen.** Swipe the tab strip horizontally before tapping a label
  that isn't visible, or tap by `xy`.
- **Coordinates are device-specific.** The column x-centres and swipe points above were
  measured on a 2560x1600 tablet. Re-measure from a live header dump
  (`adb shell wm size`, then read the `bounds`/`center` of the header nodes) on a
  different screen size before reusing.
- **Login is manual, and opening failures halt the run.** If you land on a logged-out
  screen — or the emulator/device/app isn't reachable at all — follow the **Open-failure
  protocol** above: stop, report the exact error, wait for the user; never attempt an auth
  bypass and never silently fall back to web data.
- **"Realtime Agency Data" is a separate Tier-2 panel** (agency LISTINGS, asking prices) that
  sits below the Rent/Sale caveat tables. Never mix its rows into caveat data — `harvest_rent`
  cuts the parse at that marker; on other screens tag rows by panel. The `View All (N)`
  footer between the two panels is ambiguous — don't tap it on the Rent tab.
- **Frozen right-hand columns** (Unit Type on Profitability, Contract Date on Rent) arrive as
  a trailing token list pairing with the visible rows in order; the harvesters pair them only
  on an exact count match — a partial screen would misalign every value below it.

## Related files
- `research/lib/mbx.py` — the harness (this repo, RE_search)
- `research/tools/doctor.py` — automated readiness gate (run it first, every session)
- `research/lib/harvest_sale.py`, `harvest_profitability.py`, `harvest_rent.py`,
  `harvest_towerview.py` — one harvester per CONDO tab (all offline-testable parsers)
- `research/lib/harvest_street_sale.py` — the **LANDED street** harvester (address-first path,
  caveat/agency guard, coordinate-free format parser). `--here` skips navigation if you are
  already on the expanded caveat table; `--window 10Y` for depth. Parser tested offline in
  `tests/test_harvest_street.py`.
- `research/lib/is_rows.py` — THE normalizer for landed harvests (money/date/road/ptype +
  distribution stats); every consumer imports it, nobody re-parses app strings
- `research/tools/is_street_compare.py` — true-road distribution + optional engine LV1
  side-by-side (the alias/hard-case corroboration step, runnable offline once harvested)
- `research/tools/reconcile_is_ura.py` — IS↔URA attribution on month+price+area (the L2f input)
- `researcher/landed/street_alias.py` — evidence-only address-road → URA-bucket map
- `research/lib/reconstruct_comps.py` — three-surface comp reconstruction + trend ladder
- mobile_bridge repo — emulator host only (`scripts\start_emulator.ps1`, device profile
  in its `AGENTS.md`; the old bridge profile is frozen at
  `legacy/mobile_bridge/apps/investment_suite.py` there)
- `researcher/legacy/valuation/dataset.py` — example of a persisted, single-source-of-truth dataset
