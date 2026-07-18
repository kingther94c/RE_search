---
name: harvest-scrolling-android-table
description: Use when an Android app shows a table wider or taller than the screen with no API and no per-cell ids, and you need every row as structured records (dump, snap to columns, scroll, dedup, stop).
---

# Harvest a scrolling Android table into structured rows

## When to use this
Use this whenever an Android app shows tabular data that is **wider/taller than the
screen** and you need every row as structured records — but the app exposes no API and
(typically) no per-cell resource-ids. The technique is **app-agnostic**: dump the
accessibility tree, rebuild rows by snapping cells to header columns, scroll the data
region, dedup, and stop when no new rows appear. Reference implementation:
`research/lib/harvest_sale.py` (built on the `research/lib/mbx.py` harness; see
`read-investment-suite` for the harness commands).

## Calibrate for your device
Every coordinate in this skill is **screen-specific**. The CURRENT reference device is
**mb_play: 1080x2400 portrait** (single source of truth: mobile_bridge `AGENTS.md`);
the worked examples below were measured on the RETIRED **2560x1600** tablet profile
(find your resolution with `adb shell wm size`). Before
harvesting on a different device, re-derive the column x-centres and swipe band from a
live header dump's `bounds`/`center` — treat the numbers here as worked examples, not
gospel. Point the harness at your device with `MBX_SERIAL` (your `adb devices` serial),
`MBX_ADB` (your adb path, or rely on PATH), and `MBX_OUT`.

## Why the naive approach fails
- Cells often have **no resource-id**, so you can't address rows/columns by id.
- A row's cells are independent `TextView` nodes — there is no "row" object; you must
  **reconstruct rows from geometry** (shared y, column-snapped x).
- Many tables have a **frozen column** (e.g. a left date column) that does not scroll
  with the data; a centre swipe scrolls nothing useful.
- **Fling momentum** makes scrolling non-deterministic — the same swipe lands on
  different rows each time, so you cannot page deterministically. You must dedup and
  detect a stale steady-state.

## The pipeline
```
dump  ->  parse nodes  ->  snap cells to header columns  ->  build rows
  ^                                                              |
  |                                                              v
stale-stop  <-  dedup into a seen{} map  <-  scroll the DATA region (loop)
```

## Steps
1. **Measure the header columns once.** From a live dump of the header row, record the
   x-centre of each column. Mark which column is **frozen** (won't scroll) vs **data**
   (will scroll). The x-centres below are EXAMPLE values from a 2560x1600 tablet — read
   your own from the header dump:
   ```python
   # EXAMPLE column x-centres (2560x1600) — re-derive per device from header bounds:
   COLUMNS = [("date", 91), ("street", 367), ("level", 609), ("unit", 886),
              ("unit_type", 1201), ("area_sqft", 1462), ("psf", 1737),
              ("price", 2028), ("sale_type", 2311)]
   DATA_COLS = COLUMNS[1:]            # everything except the frozen "date" column
   ```
2. **Pick a row anchor.** Choose one column whose value is unambiguous per row and
   matches a tight regex — it identifies each row's y-band. In the reference it's the
   frozen date: `DATE_RE = re.compile(r"^\d\d \w{3} \d{4}$")`.
3. **Rebuild rows from nodes.** For each anchor node, take its y-centre, collect all
   text nodes within a y-tolerance (`abs(node_y - anchor_y) <= 30`), and snap each to
   the nearest data column by x. Keep the **first** value per column (wrapped cells can
   collide on x). This is `rows_from_nodes()` + `nearest_col()`:
   ```python
   def nearest_col(x): return min(DATA_COLS, key=lambda c: abs(c[1] - x))[0]
   # row = {"date": d.text, ...}; for each cell: row.setdefault(col, cell.text)
   ```
4. **Dedup into a `seen` map** keyed by a stable composite (something that's unique per
   row), so re-reading the same row on the next scroll is a no-op:
   ```python
   key = (r.get("date"), r.get("level"), r.get("unit"), r.get("price"))
   seen[key] = r
   ```
5. **Scroll the data region, gently.** Swipe **only the data columns** (so a frozen
   column doesn't block it) with a **short distance + slow duration** to minimise fling.
   The coordinates are EXAMPLE values for a 2560x1600 tablet — put `x` in the middle of
   YOUR data band and size the span to your screen:
   ```python
   mbx.swipe_region(1300, 1300, 1300, 860, 450)   # x in the data band, ~440px, 450ms
   time.sleep(0.85)                                # let it settle before the next dump
   ```
6. **Stale-stop.** After each scroll, ingest and count newly-added rows. If a scroll
   adds **0 new rows for N consecutive rounds** (`stop_after_stale`, e.g. 6), stop. Cap
   total scrolls (`max_scrolls`, e.g. 40) as a safety bound.
   ```python
   stale = stale + 1 if gained == 0 else 0
   if stale >= stop_after_stale: break
   ```
7. **Seed from existing captures (optional).** If you already snapshotted pages to disk,
   ingest those JSON dumps first so you start with rows already in hand
   (`harvest_sale.harvest()` seeds from prior `08_/09_/10_*.json` captures).
8. **Save deterministically.** Sort rows (e.g. by date desc) and write JSON + CSV with a
   fixed field order so reruns produce identical output.

## Tuning knobs
| Knob | Reference value | Effect |
|---|---|---|
| y-tolerance | `30` px | How tightly cells must share a row's baseline |
| swipe distance | `1300→860` (~440 px, 2560x1600) | Shorter = less overshoot, more scrolls |
| swipe duration | `450` ms | Slower = less fling momentum |
| `time.sleep` | `0.85` s | Let momentum settle before dumping |
| `stop_after_stale` | `6` | Rounds of zero gain before stopping |
| `max_scrolls` | `40` | Hard upper bound |

## Adapting to a new table
1. Dump the header, read off each column's x-centre → fill `COLUMNS`.
2. Identify the frozen column(s); put the rest in `DATA_COLS`.
3. Choose the anchor column + its regex.
4. Choose the dedup key from columns that are unique per row.
5. Set the swipe x to the middle of the **data** band; tune distance/duration to your
   screen size.

## Gotchas / limitations
- **Coordinates are screen-specific.** Column x-centres and swipe points must be
  re-measured per device/resolution (`adb shell wm size` → re-read header bounds).
- **Wrapped or merged cells collide on x.** `setdefault` keeps the first; verify a few
  rows by eye or against a screenshot.
- **Fling can skip rows** if the swipe is too aggressive — prefer many gentle swipes
  over a few hard ones; the dedup+stale loop tolerates re-reads but not skips.
- **Anchor regex must be strict.** A loose pattern will match stray text and fabricate
  rows; a too-strict one will drop rows. Validate the count against the app's own total
  if it shows one.
- **No row object means partial rows are possible** if a cell is mid-scroll. Re-reads
  across scrolls usually fill them in; the last/first visible row is the most at-risk.

## Related files
- `research/lib/harvest_sale.py` — the reference harvester (snap-to-column, dedup, stale-stop)
- `research/lib/mbx.py` — `dump_xml()`, `parse()`, `swipe_region()` used above
