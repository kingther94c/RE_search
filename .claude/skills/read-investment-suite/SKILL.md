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
- **RE_search** (this repo): you read the app with the **`research/mbx.py`** adb harness.
  That is all you need to harvest data.
- **mobile_bridge** (a SEPARATE repo): the Investment Suite **bridge profile** —
  selectors, ready/detail-ready checks for an Appium-style driver — lives at
  `mobile_bridge/apps/investment_suite.py`. It is **optional** and only relevant if you
  drive the app through that bridge instead of the plain `mbx` harness. In RE_search you
  do not need it; reach into the mobile_bridge repo only if you want that profile.

## Calibrate for your device
The values below were measured on one specific tablet. Re-derive them for yours before
you trust any coordinate.

| Placeholder | What it is | How to find yours |
|---|---|---|
| `$SERIAL` | adb device serial (the reference machine used `emulator-5554`) | `adb devices` |
| `$ADB` | path to `adb` (reference: `…\Android\Sdk\platform-tools\adb.exe`) | use it from PATH, or set the full path |
| resolution | reference device was **2560x1600** | `adb shell wm size` |

Point the harness at your device via env vars: `MBX_ADB` (→ `$ADB`),
`MBX_SERIAL` (→ `$SERIAL`), `MBX_OUT` (capture output dir).

## Prerequisites
- An Android emulator/device with the app **already logged in** (sign-in is the
  operator's job — UI only, no auth bypass).
- `adb` available (see `$ADB` above).
- The `mbx` harness at `research/mbx.py`. Override defaults via env vars if needed:
  `MBX_ADB`, `MBX_SERIAL`, `MBX_OUT`.
- App package `com.investmentsuite`, launch activity `com.propnex.investmentsuite.MainActivity2`.

## Open-failure protocol — pause, report, wait (do NOT fall back to web data)

Investment Suite is **Tier-1 ground truth** for property research; every other skill in this repo
is told to source its load-bearing numbers here first. So if the app cannot be reached, the
correct move is to **stop and hand back to the user — never silently substitute web-aggregator or
research-report data** (those are Tier-2/3 and are exactly what this skill exists to replace).

Check readiness before harvesting, and on ANY of these failure modes pause immediately:

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
   `researcher/valuation/dataset.py` for the shape) — one source of truth per development.

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
For the full table harvest, drive `research/harvest_sale.py` (it imports `mbx`).

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

## Related files
- `research/mbx.py` — the harness (this repo, RE_search)
- `research/harvest_sale.py` — the table harvester (this repo)
- `mobile_bridge/apps/investment_suite.py` — the bridge profile, in the SEPARATE
  mobile_bridge repo (optional; selectors, ready/detail-ready)
- `researcher/valuation/dataset.py` — example of a persisted, single-source-of-truth dataset
