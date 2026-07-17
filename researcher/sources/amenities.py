"""全岛的小学与 MRT 站清单(官方源 + OneMap 坐标),一次构建、落盘缓存。

为什么它必须存在:DD 链原本把 15 所小学、8 个 MRT 站**硬编码**在 `researcher/landed/dd.py`
里 —— 那是它第一次开发时那个片区(Seletar / Serangoon)的清单。换一个地址,它不会报错,
它会**静默地说「2.2km 内无小学」「4km 内无 MRT」**。385 LOYANG RISE 的报告就是这么出来的,
而 Loyang 附近既有小学也有 Pasir Ris MRT。**假阴性比缺失更危险**:缺失看得见,假阴性看不见,
而且学区是 landed 最大的价值驱动之一(因子研究:school > age > MRT ≈ FH)。

源:
  - 小学 = MOE「School Directory and Information」(data.gov.sg,官方,带 postal_code),
    逐个 postal 用 OneMap 地理编码。`mainlevel_code` 取 PRIMARY 与 `MIXED LEVEL (P1-…)` ——
    后者也招 P1,漏掉就等于对那 3 所学校的邻居撒谎。
  - MRT = OneMap 枚举 "MRT STATION"(它直接给 SVY21 X/Y)。LRT 一并收,车站名保留原样。

缓存 `amenities_cache.json` 是**派生产物**,但**入库**:报告因此可以离线复现,不必每次跑
~200 次 OneMap 请求(0.6s/次的礼貌限速 = 每份报告 2 分钟)。学校会开会关、线路会通车,
所以缓存带 `built` 日期,报告应当把它印出来。

    python -m researcher.sources.amenities --rebuild     # 重建缓存(约 2-3 分钟)
    from researcher.sources.amenities import primary_schools, mrt_stations
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date

# 中文进度输出会在 cp1252 控制台上抛 UnicodeEncodeError(和 mbx / report_out 同一个坑)
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "amenities_cache.json")
_UA = "RE_search/0.1"

MOE_RESOURCE = "d_688b934f82c1059ed0a6993d2a829089"   # School Directory and Information
MOE_URL = ("https://data.gov.sg/api/action/datastore_search"
           f"?resource_id={MOE_RESOURCE}&limit=500")
ONEMAP_SEARCH = ("https://www.onemap.gov.sg/api/common/elastic/search"
                 "?searchVal={q}&returnGeom=Y&getAddrDetails=Y&pageNum={p}")
_MRT_RE = re.compile(r"^(?P<name>.+?)\s+(?:MRT|LRT)\s+STATION(?:\s*\(.*\))?$", re.I)

_mem: dict | None = None


def _get(url: str, timeout: int = 40, tries: int = 4) -> dict:
    """带退避重试 —— OneMap 的公开 search 会限流(实测:0.2s/页 在第 13 页就 HTTPError,
    于是 LRT 一站都没收到,清单静默地少了一整类车站)。"""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


# ------------------------------------------------------------------ build
def _build_schools() -> list[dict]:
    from researcher.sources import onemap
    recs = _get(MOE_URL)["result"]["records"]
    want = [r for r in recs
            if (r.get("mainlevel_code") or "").upper() == "PRIMARY"
            or (r.get("mainlevel_code") or "").upper().startswith("MIXED LEVEL (P1")]
    out = []
    for i, r in enumerate(want, 1):
        postal = (r.get("postal_code") or "").strip()
        g = onemap.geocode(postal) if postal else None
        if not g:
            print(f"  [skip] {r['school_name']}: postal {postal!r} 无法地理编码")
            continue
        out.append({"name": r["school_name"].strip(), "postal": postal,
                    "lat": g["lat"], "lon": g["lon"], "x": g.get("x"), "y": g.get("y")})
        if i % 40 == 0:
            print(f"  ...{i}/{len(want)}")
    return out


def _build_mrt() -> list[dict]:
    """OneMap 的车站条目要**分两次查**:LRT 站叫 "XXX LRT STATION",搜 "MRT STATION" 一条
    都不会返回。第一版只查了 MRT、又用「连续 8 页无新站」早停,结果只收到 69 站(全岛约 170)
    —— 测试当场抓到。早停已去掉:页数是有限的(每种查询 ≤80 页),翻完即可。"""
    seen: dict[str, dict] = {}
    for q in ("MRT STATION", "LRT STATION"):
        page, pages = 1, 1
        while page <= pages:
            try:
                d = _get(ONEMAP_SEARCH.format(q=urllib.parse.quote(q), p=page), timeout=20)
            except Exception as e:
                print(f"  [warn] {q} page {page}: {type(e).__name__} — 停止分页,保留已收集的")
                break
            pages = min(int(d.get("totalNumPages") or 1), 80)
            for x in d.get("results") or []:
                val = (x.get("SEARCHVAL") or "").strip()
                m = _MRT_RE.match(val)
                if not m or not x.get("LATITUDE"):
                    continue
                # 同一车站有多个出口/条目 —— 按站名去重(站点级精度对 km 级距离足够)
                seen.setdefault(m.group("name").upper(), {
                    "name": val, "station": m.group("name").title(),
                    "lat": float(x["LATITUDE"]), "lon": float(x["LONGITUDE"]),
                    "x": float(x["X"]) if x.get("X") else None,
                    "y": float(x["Y"]) if x.get("Y") else None})
            if page % 20 == 0:
                print(f"  ...{q} page {page}/{pages}, {len(seen)} 站")
            page += 1
            time.sleep(0.6)                  # 与 onemap.geocode 同一个礼貌限速
    return sorted(seen.values(), key=lambda s: s["station"])


def _save(schools: list[dict], mrt: list[dict]) -> dict:
    data = {"_meta": {"built": date.today().isoformat(),
                      "schools_source": "MOE School Directory and Information (data.gov.sg)",
                      "mrt_source": "OneMap search 'MRT STATION' + 'LRT STATION'",
                      "note": "派生产物,入库以便离线复现。学校/车站会变 —— "
                              "定期 `python -m researcher.sources.amenities --rebuild`"},
            "primary_schools": schools, "mrt": mrt}
    with open(CACHE, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"-> {CACHE}  ({len(schools)} 所小学, {len(mrt)} 站)")
    return data


def rebuild() -> dict:
    """分段保存:学校那 ~2 分钟的地理编码不能因为 MRT 分页超时而白跑一遍。"""
    old = {}
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as f:
            old = json.load(f)
    print("小学(MOE 名录 + OneMap 地理编码)...")
    schools = _build_schools()
    print(f"  -> {len(schools)} 所")
    _save(schools, old.get("mrt") or [])          # 先落盘,再去做会超时的那半边
    print("MRT/LRT(OneMap 枚举)...")
    mrt = _build_mrt()
    print(f"  -> {len(mrt)} 站")
    return _save(schools, mrt)


# ------------------------------------------------------------------ read
def _load() -> dict:
    global _mem
    if _mem is None:
        if not os.path.exists(CACHE):
            raise RuntimeError(
                f"没有 {CACHE}。先构建:python -m researcher.sources.amenities --rebuild")
        with open(CACHE, encoding="utf-8") as f:
            _mem = json.load(f)
    return _mem


def primary_schools() -> list[dict]:
    return _load()["primary_schools"]


def mrt_stations() -> list[dict]:
    return _load()["mrt"]


def built_on() -> str:
    return _load()["_meta"]["built"]


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
    if "--rebuild" in sys.argv:
        rebuild()
    else:
        d = _load()
        print(f"built {d['_meta']['built']}: {len(d['primary_schools'])} 所小学, "
              f"{len(d['mrt'])} 个车站")
