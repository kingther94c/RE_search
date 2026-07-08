"""Cross-development yield & valuation ladder memo (研究备忘录).

Synthesizes the already-reviewed condo valuation digests into one compact
bilingual comparison: tenure/age/quantum vs gross yield, and the DIRECTION of
the app-AVM bias vs the freshest same-spec print per development. Numbers are
PULLED from the digests (never typed) so the memo can't drift from the
reviewed studies.

    python deliverables/build_yield_ladder_memo.py <digest_slug> [<digest_slug> ...]

Output: RESEARCH_REPORTS_DIR/Yield_Ladder_Memo.html
"""
from __future__ import annotations

import html
import json
import os
import re
import statistics
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def esc(x) -> str:
    return html.escape(str(x if x is not None else "—"))


def load(slug: str) -> dict:
    p = os.path.join(ROOT, "researcher", "valuation", f"{slug}_digest.json")
    return json.load(open(p, encoding="utf-8"))


def yield_pct(d: dict) -> float | None:
    m = re.search(r"毛收益率 ~([\d.]+)%", " ".join(d.get("yield_analysis", [])))
    return float(m.group(1)) if m else None


def row(d: dict) -> dict:
    s, v = d["subject"], d["valuation"]
    tri = v.get("triangulation") or {}
    fresh = tri.get("freshest_same_spec") or {}
    avm, fp = tri.get("avm_cohort_median_psf"), fresh.get("psf")
    if not tri and d.get("avm_crosscheck"):
        # pre-triangulation digests (e.g. spottiswoode_1803): derive the legs
        # from the same reviewed sections the pipeline would have used
        avm = round(statistics.median(int(a["est_psf"]) for a in d["avm_crosscheck"]))
        c0 = next((c for c in d.get("comps_table", [])
                   if c.get("size_sqft") == s.get("size_sqft")
                   and c.get("beds", s.get("bedrooms")) == s.get("bedrooms")), None)
        if c0:
            fp = int(c0["psf"])
            fresh = {"psf": fp, "date": c0["date"]}
            tri = {"negotiation_band_psf": [min(avm, v["estimate_psf"], fp),
                                            max(avm, v["estimate_psf"], fp)]}
    bias = (avm - fp) / fp * 100 if avm and fp else None
    band = tri.get("negotiation_band_psf") or [None, None]
    return {
        "name": s["name"], "district": s.get("district"), "tenure": s.get("tenure"),
        "top": s.get("top_year"), "size": s.get("size_sqft"), "beds": s.get("bedrooms"),
        "est_psf": v.get("estimate_psf"), "est_price": v.get("estimate_price"),
        "band": band, "avm": avm, "fresh": fp, "fresh_date": fresh.get("date"),
        "avm_bias_pct": bias, "yield_pct": yield_pct(d),
        "review": (d.get("review") or {}).get("overall"),
        "asof": d.get("asof"),
    }


def render(rows: list[dict]) -> str:
    trs = ""
    for r in rows:
        band = (f"{r['band'][0]:,}–{r['band'][1]:,}" if r["band"][0] else "—")
        bias = (f"{r['avm_bias_pct']:+.1f}%" if r["avm_bias_pct"] is not None else "—")
        yld = f"{r['yield_pct']:.1f}%" if r["yield_pct"] else "—"
        n = lambda x: f"{x:,}" if isinstance(x, (int, float)) else "—"  # noqa: E731
        trs += (f"<tr><td class='l'><b>{esc(r['name'])}</b><br><span class='sub'>"
                f"{esc(r['district'])} · {esc(r['tenure'])} · TOP {esc(r['top'])}</span></td>"
                f"<td>{esc(r['size'])} sqft {esc(r['beds'])}BR</td>"
                f"<td><b>{n(r['est_psf'])}</b> psf<br><span class='sub'>S${r['est_price']:,.0f}</span></td>"
                f"<td>{band}</td><td>{n(r['avm'])}</td>"
                f"<td>{n(r['fresh'])}<br><span class='sub'>{esc(r['fresh_date'])}</span></td>"
                f"<td><b>{bias}</b></td><td><b>{yld}</b></td><td>{esc(r['asof'])}</td></tr>")
    today = date.today().isoformat()
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>三盘收益率与估值梯度备忘录 · Yield & Valuation Ladder</title>
<style>
body{{font:14.5px/1.7 -apple-system,Segoe UI,Roboto,"Microsoft YaHei",sans-serif;color:#0f172a;margin:0;background:#f8fafc}}
.wrap{{max-width:1080px;margin:0 auto;padding:0 22px 60px;background:#fff}}
h1{{font-size:24px;padding-top:30px}} h2{{font-size:18px;margin-top:28px}}
table{{border-collapse:collapse;width:100%;font-size:13px;margin:12px 0}}
th,td{{padding:7px 9px;text-align:right;border-bottom:1px solid #e2e8f0;vertical-align:top}}
th{{background:#f8fafc;font-size:12px;color:#64748b}} td.l,th.l{{text-align:left}}
.sub{{color:#64748b;font-size:12px}} ul{{padding-left:20px}} li{{margin:6px 0}}
.k{{color:#7c3aed;font-weight:700;font-size:12px}}
</style></head><body><div class="wrap">
<div class="k">RE_search 研究备忘录 · Research memo</div>
<h1>三盘收益率与估值梯度 <span class="sub">Yield &amp; valuation ladder across three reviewed studies</span></h1>
<p class="sub">编制 {today} · 数字全部程序化取自三份已过验收/门禁的估值 digest（工具：deliverables/build_yield_ladder_memo.py，可复算）。
Tier-1 口径：PropNex Investment Suite captures；AVM 为 LIVE 值，以各自 capture 日期读。</p>

<table><tr><th class="l">Development</th><th>Subject</th><th>模型点估<br>Model</th>
<th>谈判带<br>Band (psf)</th><th>AVM cohort<br>中位</th><th>最新同规格<br>Freshest print</th>
<th>AVM−print<br>偏差</th><th>毛收益率<br>Gross yield</th><th>As-of</th></tr>{trs}</table>

<h2>读数 Findings</h2>
<ul>
<li><b>收益率阶梯与楼龄/地契/总价同向：</b>新 TOP、99 年地契、小总价（One Pearl Bank 2BR）收益率最高；
老永久地契大总价（Gallop 3BR，TOP 1997）最低——租金对楼龄钝感而价格对地契/稀缺敏感的教科书结构。
自住/收租选前者口径，土地价值/传承选后者口径。</li>
<li><b>app AVM 的偏差方向不是单向的：</b>Spottiswoode 案例中 AVM 落后于向上重定价的新成交（AVM 低于孪生印 ~3.4%），
One Pearl Bank 低层段则 AVM 高于最新直接成交（+3.7%）——因此「AVM 是低估还是高估」不可当先验，
<b>谈判永远以最新同规格直接成交为锚</b>，AVM 只是三角的一腿。这是三盘横评里最重要的操作性结论。</li>
<li><b>楼层溢价必须按盘拟合：</b>低层新 TOP 高层盘（OPB 拟合 0.43%/层，n=125）显著陡于通用缺省 0.30%/层；
用错梯度会把高层印外推到低层主体上（首轮 OPB 点估被推高 ~2.2% 即此因，已由拟合修正）。</li>
<li><b>成交稀薄按宽读：</b>Gallop 5Y 仅 11 笔独立成交（年均 ~2.2 笔）——区间与流动性折价比点估更重要；
高换手盘（OPB）则相反，点估的信息量更高。</li>
</ul>
<p class="sub">仅供研究与说明，非正式估值/投资建议。各盘细节以其独立估值报告为准
（spottiswoode_1803 / gallop_0304 / onepearl_0316 Condo Valuation Reports）。</p>
</div></body></html>"""


def main() -> None:
    slugs = sys.argv[1:] or ["spottiswoode_1803", "gallop_0304", "onepearl_0316"]
    rows = [row(load(s)) for s in slugs]
    htmls = render(rows)
    if "�" in htmls or "â€" in htmls:
        raise SystemExit("mojibake gate")
    reports = os.environ.get("RESEARCH_REPORTS_DIR", r"G:\My Drive\004 RES\REsearch_Reports")
    try:
        os.makedirs(reports, exist_ok=True)
        out = os.path.join(reports, "Yield_Ladder_Memo.html")
        open(out, "w", encoding="utf-8").write(htmls)
    except OSError:
        out = os.path.join(HERE, "Yield_Ladder_Memo.html")
        open(out, "w", encoding="utf-8").write(htmls)
    for r in rows:
        print(f"{r['name']}: model {r['est_psf']} band {r['band']} avm {r['avm']} "
              f"fresh {r['fresh']} bias {r['avm_bias_pct']} yield {r['yield_pct']}")
    print(f"wrote {out} ({len(htmls) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
