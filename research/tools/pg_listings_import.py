"""PG explorer 运行结果 → researcher/landed/<slug>_listings.json —— screen 的进料口。

用法(先在 mobile_bridge 里跑 explorer,再导入):
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\propertyguru.ps1 `
        --out .\\artifacts_propertyguru\\<run> listings "<area / MRT>" --intent buy `
        --property-type Landed --max-results 30
    python research/tools/pg_listings_import.py <run-dir-or-listings.json> --slug <area_slug>

行为:
  - rent 卡剔除;area 非 (land) 口径的卡不产生 land_psf(进 VERIFY DATA 闸,见 pg_cards.py);
  - 已存在的 <slug>_listings.json 默认 MERGE:市场字段刷新,判断层字段(estate_tier/
    catchment/flood_risk/rebuild_status/notes/…)原样保留 —— 导入永远不清洗人的判断;
  - 本次拉取里消失的旧 id 只报告,不自动标 stale(掉出第一页 ≠ 卖掉,是否 stale 由人定);
  - benchmark_land_psf / benchmark_note 保留现值;新文件则留空并提醒(基准带来自
    landed-area-research,不是导入工具能发明的)。
导入后:python -m researcher.landed.screen <slug>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.lib import pg_cards  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(ROOT, "researcher", "landed")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src", help="explorer 运行目录(含 listings.json)或 listings.json 路径")
    ap.add_argument("--slug", required=True, help="区域 slug → researcher/landed/<slug>_listings.json")
    ap.add_argument("--area-name", help="报告抬头用的区域名(新文件时必填)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = a.src if a.src.endswith(".json") else os.path.join(a.src, "listings.json")
    if not os.path.exists(src):
        print(f"找不到 {src} —— 传 explorer 的运行目录或 listings.json 本身")
        return 2
    cards = json.load(open(src, encoding="utf-8"))

    imported, warns, skipped = [], [], []
    for c in cards:
        lst, w = pg_cards.card_to_listing(c)
        (imported.append(lst) if lst else skipped.extend(w))
        if lst:
            warns.extend(w)

    out_path = os.path.join(OUT_DIR, f"{a.slug}_listings.json")
    if os.path.exists(out_path):
        data = json.load(open(out_path, encoding="utf-8-sig"))
        merged, rep = pg_cards.merge(data.get("listings", []), imported)
        data["listings"] = merged
        data["pulled"] = f"{data.get('pulled', '')} | PG explorer import {date.today()}".strip(" |")
    else:
        if not a.area_name:
            print("新文件需要 --area-name(报告抬头);benchmark_land_psf 请从 "
                  "landed-area-research 的区域基准带填入 —— 导入工具不发明基准。")
            return 2
        rep = {"new": [l["id"] for l in imported], "updated": [], "missing": []}
        data = {"area": a.area_name, "pulled": f"PG explorer import {date.today()}",
                "benchmark_land_psf": {}, "stale_ids": [],
                "listings": imported,
                "benchmark_note": "TODO: 基准带来自 landed-area-research 的区域报告"}

    print(f"导入 {len(imported)} 条(新 {len(rep['new'])} · 刷新 {len(rep['updated'])}"
          f" · 本次未见 {len(rep['missing'])});剔除 {len(skipped)} 条")
    for s in skipped:
        print(f"  - {s}")
    for w in warns:
        print(f"  ! {w}")
    if rep["missing"]:
        print(f"  本次拉取未出现的旧 id(是否 stale 由人判断,未自动标):{rep['missing']}")
    if rep["new"]:
        print("\n新条目需要补判断层字段(screen 的 GO/CHECK 依赖它们):"
              "estate_tier · catchment(OneMap 核) · flood_risk(PUB+区域证据) · "
              "rebuild_status · zoning_risk/hazards · notes(来源与复核日期)")
    if not data.get("benchmark_land_psf"):
        print("  ⚠ benchmark_land_psf 为空 —— value_flag 全部会是 '?';"
              "先跑 landed-area-research 拿区域基准带。")
    if a.dry_run:
        print("\n(dry-run,未写文件)")
        return 0
    json.dump(data, open(out_path, "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, indent=1)
    print(f"\n写入 {os.path.relpath(out_path, ROOT)} —— 下一步:"
          f"python -m researcher.landed.screen {a.slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
