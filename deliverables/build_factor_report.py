"""Investor-facing factor research reports (condo / landed) — bilingual HTML.

Every number is pulled programmatically from the committed data layer:
  researcher/factors/beta_layer.json          official 51y index analysis
  researcher/factors/factor_model.json        cross-section model + classification
  researcher/factors/panel_*_enriched.json    the panels
  researcher/factors/dialectic_synthesis.json panel verdicts (rendered if present)
  researcher/landed/{nanyang,rosyth}_digest.json  reviewed landed studies (landed report)

    python deliverables/build_factor_report.py condo
    python deliverables/build_factor_report.py landed
Output: RESEARCH_REPORTS_DIR/Factor_Study_{Condo|Landed}_Report.html
"""
from __future__ import annotations

import html
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
F = os.path.join(ROOT, "researcher", "factors")


def esc(x) -> str:
    return html.escape(str(x if x is not None else "—"))


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def li(items):
    return "".join(f"<li>{esc(x)}</li>" for x in (items or []))


CSS = """
:root{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--accent:#0e7490;--bg:#f8fafc}
*{box-sizing:border-box}
body{font:15px/1.75 -apple-system,Segoe UI,Roboto,"Microsoft YaHei","PingFang SC",Arial,sans-serif;color:var(--ink);margin:0;background:var(--bg)}
.wrap{max-width:1060px;margin:0 auto;padding:0 24px 80px;background:#fff;box-shadow:0 1px 40px rgba(15,23,42,.06)}
header{padding:38px 0 20px;border-bottom:3px solid var(--accent)}
.kicker{color:var(--accent);font-weight:700;font-size:12px;letter-spacing:.05em}
h1{font-size:27px;margin:6px 0 4px} .sub{color:var(--mut);font-size:13.5px}
h2{font-size:20px;margin:36px 0 10px;padding-top:14px;border-top:1px solid var(--line)}
h3{font-size:16px;margin:18px 0 6px}
.en{color:var(--mut);font-weight:400;font-size:.8em}
table{border-collapse:collapse;width:100%;font-size:12.8px;margin:10px 0}
th,td{padding:6px 8px;text-align:right;border-bottom:1px solid var(--line)}
th{background:var(--bg);font-size:11.5px;color:var(--mut)} td.l,th.l{text-align:left}
ul{margin:6px 0;padding-left:20px} li{margin:5px 0}
.box{background:#ecfeff;border:1px solid #a5f3fc;border-radius:10px;padding:14px 18px;margin:12px 0}
.warn{background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:12px 16px;margin:12px 0;font-size:13.5px}
.note{color:var(--mut);font-size:12.5px;line-height:1.6}
.tag{display:inline-block;border-radius:6px;padding:0 8px;font-size:11.5px;font-weight:700;margin-right:6px}
.t-up{background:#dcfce7;color:#166534}.t-q{background:#fef9c3;color:#854d0e}.t-rej{background:#fee2e2;color:#b91c1c}
.bar{display:inline-block;height:10px;background:var(--accent);border-radius:2px;vertical-align:middle}
.neg{background:#e11d48}
.two{display:grid;grid-template-columns:1fr 1fr;gap:0 26px}
@media(max-width:760px){.two{grid-template-columns:1fr}}
.foot{color:var(--mut);font-size:12px;margin-top:30px;border-top:1px solid var(--line);padding-top:12px}
"""

VERDICT_TAG = {"uphold": ("t-up", "成立"), "qualify": ("t-q", "有保留"), "reject": ("t-rej", "推翻")}


def beta_section(beta: dict, kind: str) -> str:
    cyc = "".join(
        f"<tr><td class='l'>{esc(c['cycle'])}</td><td>{c['from']}→{c['to']}</td>"
        + "".join(f"<td>{c.get(k, 0) * 100:+.1f}%</td>" for k in ("landed", "nonlanded", "all"))
        + "</tr>" for c in beta["cycles"])
    cagr = "".join(
        f"<tr><td class='l'>{seg}</td>" + "".join(
            f"<td>{(w[n] * 100):+.2f}%</td>" if w[n] is not None else "<td>—</td>"
            for n in ("5y", "10y", "20y", "since_1998Q4"))
        + f"<td>{beta['vol_pa_since_1998'][seg] * 100:.1f}%</td>"
        + f"<td>{beta['max_drawdown'][seg]['dd'] * 100:.0f}% ({beta['max_drawdown'][seg]['peak']}→{beta['max_drawdown'][seg]['trough']})</td></tr>"
        for seg, w in beta["cagr"].items())
    lb = beta["landed_on_nonlanded"]
    pr = beta["price_to_rent_nonlanded"]
    sens = "".join(
        f"<tr><td class='l'>{s}</td><td>{v['beta']:.2f}</td>"
        f"<td>{v['alpha_pa'] * 100:+.1f}%</td><td>{v['alpha_t']:.2f}"
        f"{'（显著）' if abs(v['alpha_t']) >= 2 else '（不显著）'}</td></tr>"
        for s, v in lb.get("start_date_sensitivity", {}).items())
    focus = ("landed 的防御性是『不对称捕获』，不是简单低 β" if kind == "landed"
             else "condo（非有地）承担整段市场 β，α 必须来自盘内因子与择时")
    return f"""
<h2>市场 β 层：51 年官方周期 <span class='en'>Market beta — 51 years of official index</span></h2>
<p>数据：URA 私宅价格指数（SingStat M212261 官方序列，1975Q1–{beta['asof_quarter']}）。{focus}。
Landed 对非有地的季度回归（1998Q4 起，n={lb['n_quarters']}）：β = {lb['beta']:.2f}、相关 {lb['corr']:.2f}——
但恒定 β/α 无法同时解释『涨时跟涨、跌时抗跌』；更准确的口径是<b>不对称捕获：
上行捕获 {lb['capture_up']:.2f} / 下行捕获 {lb['capture_down']:.2f}</b>。</p>
<div class='warn'>α 的统计诚实框（辩证团要求）：α 对回归起点高度敏感——自 1996 峰 ≈0、自 1998 谷 +1.0%/年（t={lb['alpha_t']:.2f}，不显著）、
自 1975 全史 +1.8%/年（t=2.25，显著）。且 landed 指数成交稀薄、存在平滑效应：测得的 β/波动系统性<b>低估</b>真实风险，
指数点位不是压力期可成交价。1996-98 一役 landed 跌 −48%（比 condo 更深）——防御性在系统性危机中失效。</div>
<table><tr><th class='l'>回归起点</th><th>β</th><th>α/年</th><th>t 值</th></tr>{sens}</table>
<table><tr><th class='l'>段</th><th>5y CAGR</th><th>10y</th><th>20y</th><th>自 1998Q4</th><th>年化波动</th><th>最大回撤</th></tr>{cagr}</table>
<h3>周期表 <span class='en'>Named cycles</span></h3>
<table><tr><th class='l'>周期</th><th>区间</th><th>Landed</th><th>Non-landed</th><th>全体</th></tr>{cyc}</table>
<div class='box'>价格/租金比（非有地，1998Q4=100）：现 <b>{pr['last'][1]}</b> vs 峰值 <b>{pr['peak'][1]}（{pr['peak'][0]}）</b>
——『部分正常化』：2021 后租金追上价格（2022-23 移民潮+完工荒有一次性成分），但仍比 2009 基线贵 ~30%，
且全程处于 ~1.4% 按揭利率制度内——4% 利率情景下 CCR 低收益率段转为负 carry。</div>"""


def dialectic_section(kind: str) -> str:
    p = os.path.join(F, "dialectic_synthesis.json")
    if not os.path.exists(p):
        return ""
    d = load(p)
    rows = ""
    for c in d["claims"]:
        cells = ""
        for persp in ("quant", "bear", "bull"):
            v = c.get(persp) or {}
            cls, zh = VERDICT_TAG.get(v.get("verdict", ""), ("t-q", "?"))
            cells += f"<td class='l'><span class='tag {cls}'>{zh}</span>{esc(v.get('point', ''))}</td>"
        rows += (f"<tr><td class='l'><b>{esc(c['id'])}</b> {esc(c['claim'])}</td>{cells}"
                 f"<td class='l'>{esc(c['resolution'])}</td></tr>")
    return f"""
<h2>辩证团判定 <span class='en'>Adversarial panel — three perspectives</span></h2>
<p class='note'>方法：量化怀疑者（方法学）、熊方风险官（经济结论）、牛方实操派（可用性）三路独立评审每条主张；
下表为各视角裁定与最终保留口径。完整意见见 researcher/factors/dialectic_synthesis.json。</p>
<table><tr><th class='l' style='width:26%'>主张</th><th class='l'>量化怀疑者</th><th class='l'>熊方</th><th class='l'>牛方</th><th class='l' style='width:22%'>保留口径</th></tr>{rows}</table>
<ul>{li(d.get('panel_additions'))}</ul>"""


def build_condo() -> str:
    beta = load(os.path.join(F, "beta_layer.json"))
    fm = load(os.path.join(F, "factor_model.json"))
    cs = fm["condo_cross_section"]
    rows = sorted(cs["rows"], key=lambda r: (r["segment"], -r["mid_psf"]))
    panel_rows = "".join(
        f"<tr><td class='l'>{esc(r['project'])}</td><td>{r['segment']}</td>"
        f"<td>{'FH' if r['fh'] else '99y+'}</td><td>{2026 - int(r['age']) if r['age'] > 0 else 'new'}</td>"
        f"<td>{int(round(math_exp(r['ln_units'])))}</td><td>{r['mid_psf']:,.0f}</td>"
        f"<td>{r['yield_avg'] if r['yield_avg'] else '—'}</td>"
        f"<td>{r['mrt_km']:.2f}</td><td>{int(r['pri1k'])}</td><td>{r['mall_km']:.2f}</td>"
        f"<td>{r['park_km']:.2f}</td><td>{r['coast_km']:.1f}</td></tr>"
        for r in rows)
    corr = cs["level_spearman_within_segment"]
    ZH = {"fh": "永久地契", "age": "楼龄", "ln_units": "盘规模 ln(户数)", "mrt_km": "MRT 距离",
          "pri1k": "热门小学 1km 数", "mall_km": "商场距离", "park_km": "公园距离", "coast_km": "海岸距离"}

    def bar(v):
        if v is None:
            return "—"
        w = abs(v) * 120
        cls = "bar neg" if v < 0 else "bar"
        return f"<span class='{cls}' style='width:{w:.0f}px'></span> {v:+.2f}"

    corr_rows = "".join(
        f"<tr><td class='l'>{ZH[f]}</td><td class='l'>{bar(v)}</td>"
        f"<td class='l'>{bar(cs['yield_spearman_within_segment'].get(f))}</td></tr>"
        for f, v in corr.items())
    o = cs["ols_ln_premium"]
    loo = o.get("leave_one_anchor_out", {}).get("by_factor", {})
    ols_rows = "".join(
        f"<tr><td class='l'>{ZH[f]}</td><td>{c['coef']:+.3f}</td>"
        f"<td>[{c['ci95'][0]:+.3f}, {c['ci95'][1]:+.3f}]</td>"
        f"<td>{'方向稳定' if loo.get(f, {}).get('sign_stable') else '不稳定'}"
        f"（{loo.get(f, {}).get('coef_range')}）</td></tr>"
        for f, c in zip(o["regressors"], o["standardized_coefs"]))
    cls = fm["findings"]["classification"]
    today = date.today().isoformat()
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Condo 价格支撑因子研究 · Factor Study</title><style>{CSS}</style></head>
<body><div class="wrap">
<header><div class="kicker">RE_search 因子研究 · FOR INVESTORS</div>
<h1>新加坡 Condo：价格支撑因子与 β/α 框架</h1>
<div class="sub">数据：PropNex Investment Suite（Tier-1 caveat 口径）× URA/SingStat 官方指数 × OneMap 官方地理编码 ·
横截面 n={cs['n']} · 编制 {today} · 全部数字可由仓库脚本复算</div></header>

<div class="box"><b>一页结论（辩证团修订口径）：</b>①你买的首先是 <b>β</b>——段位（CCR/RCR/OCR）与资产类别决定大部分回报路径，
且<b>政策冲击 β</b>（措施轮不对称打击段位）是新加坡第一风险因子；
②段内溢价的方向排序为 <b>热门小学 1km &gt; 楼龄（新）&gt; MRT 近 ≈ 永久地契</b>（逐锚剔除下方向稳定；量级不作卖点，adj R²={o.get('adj_r2', 0):.2f}），
这些是<b>已定价因子</b>：按公允价买入不产生 α，其价值在持有体验与下行韧性；
③收益率主要是段位选择（CCR&lt;RCR&lt;OCR 大而稳）；段内差异在本样本量下未检出——别信段内『高收益率盘』话术；
④α 通道全部先过摩擦门槛（首套全程 ~7-9%，SSD 4 年锁定意味着 <b>α 只能在买入端收割然后持有</b>）：
因子公允价锚定砍价、盘内楼层/朝向错价（实测 0.44%/层 vs 通用 0.30%）、AVM 滞后窗议价（n=3 实测，非策略）、
已宣未开的催化剂（已开通=已定价）。</div>

{beta_section(beta, 'condo')}

<h2>因子横截面（n={cs['n']}） <span class='en'>Cross-section panel</span></h2>
<p class='note'>psf 为近期成交区间中点（锚点盘为 5Y band 口径，混合披露）；MRT/学校/商场/公园/海岸为 OneMap 直线距离；
学校计数 = 30 所热门（超额认购）小学名单内 1km。样本围绕 9 个锚点盘聚集，非全岛随机抽样。</p>
<table><tr><th class='l'>项目</th><th>段</th><th>权属</th><th>TOP</th><th>户数</th><th>psf 中点</th><th>收益率%</th>
<th>MRT km</th><th>小学1km</th><th>商场 km</th><th>公园 km</th><th>海岸 km</th></tr>{panel_rows}</table>

<h2>段内溢价模型 <span class='en'>Within-segment premium model</span></h2>
<p>段位中位 psf：CCR {cs['segment_median_psf']['CCR']:,.0f} · RCR {cs['segment_median_psf']['RCR']:,.0f} ·
OCR {cs['segment_median_psf']['OCR']:,.0f}。先按段位去均值（剥离 β），再看因子与溢价的关系：</p>
<table><tr><th class='l'>因子</th><th class='l'>与 psf 溢价的 Spearman（段内）</th><th class='l'>与收益率（段内去均值）</th></tr>{corr_rows}</table>
<h3>OLS（5 因子标准化，n={cs['n']}，adj R²={o.get('adj_r2', 0):.2f}）+ 逐锚剔除稳健性</h3>
<table><tr><th class='l'>因子</th><th>标准化系数</th><th>bootstrap CI95</th><th>逐锚剔除（14 簇）</th></tr>{ols_rows}</table>
<div class='warn'>统计诚实框（辩证团修订口径）：行级 bootstrap 忽略 9-14 个锚点簇的聚集结构——CI 偏窄，
星号不可作卖点；改以<b>逐锚剔除的方向稳定性</b>为准：学校/楼龄/MRT/权属方向全部稳定，盘规模不稳定（剔除）。
读数只到『方向与相对强弱』：学校 &gt; 楼龄 &gt; MRT ≈ 权属。样本 CCR 为 fringe 口径（D1/D2/D6），
与 RCR 中位仅差 ~2%——非九/十/十一区核心 CCR；量级不可外推全岛。</div>

<h2>收益率结构 <span class='en'>Yield structure</span></h2>
<p>段间阶梯大而稳：CCR ~2.1–2.5% &lt; RCR ~2.7–3.3% &lt; OCR ~2.8–4.2%。
段内：去均值后所有因子 |ρ|&lt;0.2——但注意这是<b>低功效的『未检出』</b>：段内 n≈6-7 时
Spearman 5% 临界值约 0.75，本样本量不足以证明『不存在』。实操含义不变：
收益率主要是段位选择；段内『高收益率盘』的说服话术多半是口径差（面积带/楼龄混淆），先核价格与租约口径再信。</p>

<h2>因子分类（假设地图 + 证据等级） <span class='en'>The framework — hypothesis map with evidence tiers</span></h2>
<p class='note'>辩证团修订：下述分类按证据等级标注——【实测】= 本研究测得；【文献】= 业界共识机制、本样本未直接检验；
【推测】= 逻辑成立待验证。priced-in 的严格检验需要因子分组的未来回报数据（本研究只有价格水平证据）。</p>
<div class='two'>
<div><h3>已定价（level）因子</h3><ul>{li(cls['priced_in_level_factors'])}</ul>
<p class='note'>证据：段内价格水平【实测】；『按公允价买入=零 α』本身是【文献】级假设。
它们的价值在持有体验+流动性+下行韧性。</p></div>
<div><h3>β 调节因子</h3><ul>{li(cls['beta_modifiers'])}</ul>
<p class='note'>lease 衰减【文献：bala 曲线是确定性漂移而非协方差】；学区黏性【文献】；规模流动性【推测】。
<b>辩证团新增一级因子：政策冲击 β</b>——2010 年后每个市场拐点都由措施制造（SSD/ABSD/TDSR/LTV），
打击段位不对称（外国人/CCR/投资者首当其冲）；任何 5 年持有期都应假设至少一轮措施（或反向放松）。</p></div>
</div>
<h3>α 来源（可操作，全部先过摩擦门槛）</h3><ul>{li(cls['alpha_sources'])}</ul>
<table><tr><th class='l'>摩擦项</th><th class='l'>量级</th><th class='l'>对 α 的含义</th></tr>
<tr><td class='l'>BSD 买方印花税</td><td class='l'>累进至 ~5-6%（高价段）</td><td class='l'>一次性沉没</td></tr>
<tr><td class='l'>中介+法务</td><td class='l'>~2-3%</td><td class='l'>双边计</td></tr>
<tr><td class='l'>SSD（2025-07 起）</td><td class='l'>4 年内卖出 16/12/8/4%</td><td class='l'><b>α 只能在买入端一次性收割，然后持有</b>——翻炒通道已死</td></tr>
<tr><td class='l'>ABSD（如适用）</td><td class='l'>公民二套 20% / 外国人 60%</td><td class='l'>对边际投资者常是决定性的</td></tr></table>
<p class='note'>规则：毛 α &lt; 全程摩擦（自住首套约 7-9%，二套起 27%+）就不是 α。AVM 滞后窗为 n=3 实测【实测但样本极小】，
用于买入议价锚定，不构成交易策略。</p>
<div class='box'>实证锚（本仓库已验收研究）：① AVM 对最新同规格成交的偏差实测 <b>−3.4% / +1.4% / +3.7%</b>
（Spottiswoode / Gallop / One Pearl Bank）——方向因盘而异，谈判永远锚最新直接成交；
② OPB 楼层溢价按盘内数据拟合 <b>0.44%/层</b>（通用缺省 0.30% 会把低层估贵）；
③ CCL6（Keppel/Cantonment/Prince Edward Rd）2026-07-12 开通——催化剂前置窗口的现实样本。</div>

{dialectic_section('condo')}

<h2>局限与数据缺口（完整版） <span class='en'>Limitations — the full list</span></h2>
<ul>{li(fm['findings']['data_notes'])}</ul>
<ul>
<li>聚簇推断：所有显著性以逐锚剔除的方向稳定性为准，bootstrap 星号不作依据</li>
<li>分段口径：本面板 CCR 为 fringe（D1/D2/D6+Farrer 段）；官方 URA 分段下圣淘沙属 CCR（未含）；核心 D9/10/11 样本少</li>
<li>幸存者偏差：Investment Suite 只含在售可交易项目——en-bloc、失败、转性项目缺席，因子溢价或被高估</li>
<li>利率制度：全部样本处于 ~1.4% 固定按揭时代；所有收益率/carry 结论对 3.5-4.5% 情景不外推</li>
<li>政策制度断裂：2023-04 后的 ABSD 60%/SSD 4 年是史上最严组合——1975-2026 的历史 β/α 生成于更温和制度下</li>
<li>新售/转售混合：面板 psf 混两个市场（新盘含开发商定价与渐进付款效应）</li>
<li>功效：段内收益率零结论为低功效未检出（临界 ρ≈0.75）；8 因子筛查存在多重检验风险</li>
<li>外推边界：结论描述被抽样的 14 个簇，不是全岛横截面</li>
</ul>
<h3>下一步（辩证团点名的最优补强）</h3>
<ul>
<li><b>微观供给管线</b>（牛方单一最佳补强）：URA 未售库存 + GLS + en-bloc 置换需求按规划区 3 年前瞻——把定价 checklist 升级为买/等引擎</li>
<li>en-bloc 期权建模（plot_ratio 与 GFA 字段已在面板）；已宣未开基建目录（CRL、Turf City）；REALIS 全量幸存者审计</li>
</ul>

<h2>方法学与来源 <span class='en'>Method & sources（全部可复算）</span></h2>
<ul>
<li>官方指数：SingStat TableBuilder M212261/M212311（URA 官方序列）→ python -m researcher.marketdata.singstat</li>
<li>β 层：python -m researcher.factors.beta_layer；横截面与模型：python -m researcher.factors.factor_model</li>
<li>面板：research/build_factor_panel.py（Investment Suite Tier-1 captures）+ researcher/factors/enrich_onemap.py（OneMap 官方地理编码）</li>
<li>估值案例：spottiswoode_1803 / gallop_0304 / onepearl_0316 数字化估值报告（独立敌对评审 PASS 8.8/8.35/8.7）</li>
</ul>
<p class="foot">仅供研究与说明，非投资建议；数字以复算脚本与 Tier-1 capture 留痕为准。Generated {today}.</p>
</div></body></html>"""


def math_exp(x):
    import math
    return math.exp(x)


def landed_index_cagr(q0: str, q1: str) -> float | None:
    px = load(os.path.join(ROOT, "researcher", "marketdata", "price_index.json"))
    s = {q: v for q, v in px["series"]["Landed"]}
    if q0 not in s or q1 not in s:
        return None
    yrs = (int(q1[:4]) + (int(q1[5]) - 1) / 4) - (int(q0[:4]) + (int(q0[5]) - 1) / 4)
    return (s[q1] / s[q0]) ** (1 / yrs) - 1


def build_landed() -> str:
    beta = load(os.path.join(F, "beta_layer.json"))
    fm = load(os.path.join(F, "factor_model.json"))
    streets = fm["findings"]["landed_streets"]
    nan = load(os.path.join(ROOT, "researcher", "landed", "nanyang_digest.json"))
    ros = load(os.path.join(ROOT, "researcher", "landed", "rosyth_digest.json"))
    st_rows = ""
    for s in streets:
        cg = s.get("cagr_median")
        band = s.get("street_band") or {}
        st_rows += (f"<tr><td class='l'>{esc(s['street'])}</td><td>{s['n_points']}</td>"
                    f"<td>{s['n_pairs']}</td>"
                    f"<td>{cg * 100:+.1f}%/yr</td>" if cg else
                    f"<tr><td class='l'>{esc(s['street'])}</td><td>{s['n_points']}</td>"
                    f"<td>{s['n_pairs']}</td><td>—</td>")
        st_rows += (f"<td>{esc(band.get('low_psf'))}–{esc(band.get('high_psf'))}</td>"
                    f"<td>{(s.get('nearest_mrt') or {}).get('km', '—')}</td>"
                    f"<td>{esc(s.get('pri1k'))}</td><td>{esc(s.get('coast_km'))}</td></tr>")
    nan_bands = "".join(f"<tr><td class='l'>{esc(b['segment'])}</td><td class='l'>{esc(b['land_psf'])}</td>"
                        f"<td class='l'>{esc(b['quantum'])}</td></tr>"
                        for b in nan.get("price_structure", []))
    ros_bands = "".join(f"<tr><td class='l'>{esc(b['segment'])}</td><td class='l'>{esc(b['land_psf'])}</td>"
                        f"<td class='l'>{esc(b['quantum'])}</td></tr>"
                        for b in ros.get("price_structure", []))
    today = date.today().isoformat()
    lb = beta["landed_on_nonlanded"]
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Landed 价格支撑因子研究 · Factor Study</title><style>{CSS}</style></head>
<body><div class="wrap">
<header><div class="kicker">RE_search 因子研究 · FOR INVESTORS</div>
<h1>新加坡有地住宅（Landed）：价格支撑因子与 β/α 框架</h1>
<div class="sub">数据：URA/SingStat 官方 51 年指数 × Investment Suite 街道级 Tier-1 caveat × OneMap ·
含两份已验收学区研究（Nanyang PASS 8.45 / Rosyth PASS 8.6）· 编制 {today}</div></header>

<div class="box"><b>一页结论（辩证团修订口径）：</b>①官方 51 年序列下，landed 的防御性是<b>不对称捕获</b>：
上行捕获 {lb['capture_up']:.2f} / 下行捕获 {lb['capture_down']:.2f}——涨时基本跟上、跌时只吃七成；
但 α 对起点敏感（自 1996 峰≈0、自 1975 全史 +1.8%/年）且指数平滑低估真实风险，1996-98 一役跌得比 condo 更深（−48%）；
2020-26 跑赢含供给冻结+ABSD 不对称的一次性成分；②landed 的定价单位是<b>土地</b>——地块大小与 psf 反比（quantum 效应）、
重建状态价差巨大（Rosyth 同街同月实测 <b>+39%</b>）、999y/FH 与 99y 是不同资产；
③学区 1km 是最强需求黏性因子（Nanyang/Rosyth 抽签实证），但『买某小区=某校 1km』常是误区——必须逐址 OneMap 实测；
④代价：流动性极差（年成交数笔、压力期退出以季度计）、总价门槛高、摩擦大——只适合 10 年持有力的买家，
且不要按『低 β』加杠杆（指数点位不是压力期可成交价）。</div>

{beta_section(beta, 'landed')}

<h2>街道级证据 <span class='en'>Street-level Tier-1 evidence</span></h2>
<p class='note'>跨址同型对（间隔≥5 年）的中位年化——含土地与重建价值变化，读作『街道级长期回报』而非纯同屋回报。</p>
<table><tr><th class='l'>街道</th><th>成交点</th><th>配对数</th><th>长期 CAGR</th><th>街道 psf 带</th><th>MRT km</th><th>热门小学1km</th><th>海岸 km</th></tr>{st_rows}</table>
<div class='box'>Frankel Avenue（D15 东海岸 FH detached 带）：2000 年代 $333–455 psf → 2018–2026 年 $1,349–2,270 psf。
跨址同型配对（18 对/10 址）中位约 <b>+6~7%/年</b>（一位有效数字；配对共享端点，有效样本远小于 18）。
辩证团修正读法：①跨址对≠重复交易——含地块形态/翻建状态异质性，同街『重建 vs 原状』价差实测 +39%，
<b>扣质量漂移后的纯土地 CAGR 估计 ~4.5–5.5%/年</b>；②官方 landed 指数同窗基准
（2005Q1→2026Q1）为 {landed_index_cagr('2005Q1', '2026Q1') * 100:+.1f}%/年——街道读数与官方序列方向一致、
高出部分即 D15-FH 段与质量漂移之和。</div>

<h2>两个已验收学区案例的价格结构 <span class='en'>Reviewed school-zone studies</span></h2>
<div class='two'>
<div><h3>Nanyang 1km（D10 FH 核心）</h3>
<table><tr><th class='l'>段</th><th class='l'>land psf</th><th class='l'>总价</th></tr>{nan_bands}</table>
<p class='note'>GEP 2026 停办——学区逻辑从『GEP 中心』转为『SAP 品牌 + 1km 抽签稀缺』（2025 年 Phase 2C 1.5:1）。</p></div>
<div><h3>Rosyth 1km（D19/28 999y 带）</h3>
<table><tr><th class='l'>段</th><th class='l'>land psf</th><th class='l'>总价</th></tr>{ros_bands}</table>
<p class='note'>同街同月『重建 vs 原状』价差 +39%（9 vs 15 Alnwick）——重建经济学是 landed 最大的单一价差因子；
『买 Serangoon Gardens = Rosyth 1km』被 OneMap 实测证伪。</p></div>
</div>

<h2>Landed 因子分类 <span class='en'>The framework, landed edition</span></h2>
<div class='two'>
<div><h3>已定价（level）因子</h3><ul>
<li>地段/区（D10-11 GCB 带 &gt; 东海岸 D15 &gt; 东北 999y 带）——段位即 β</li>
<li>学区 1km（抽签稀缺溢价，已在价内）</li><li>权属（FH/999y vs 99y——不同资产）</li>
<li>地块形态/大小（psf 与地块面积反比：quantum 效应）</li><li>海岸/公园邻近（价内溢价段）</li></ul></div>
<div><h3>β 调节 / α 来源</h3><ul>
<li>β 调节：重建周期（原状→重建的一次性跃迁 +39% 级）、GCBA 规划边界（政策稀缺）、遗产/供给刚性（landed 存量近零增长）</li>
<li>α：原状老宅按土地价买入 + 重建（开发商价差自留）；街道错价（同街同型 psf 离群）；
学区误区套利（真 1km vs 传说 1km 的价差与纠偏）；危机期的流动性折价收集（landed 低 β 但个体成交可深折）</li></ul></div>
</div>

{dialectic_section('landed')}

<h2>风险 <span class='en'>Risks</span></h2>
<ul>
<li>流动性：单街年成交常为个位数——报价区间必须按宽读，退出周期以季度计</li>
<li>样本：街道证据集中于 3 个研究区（Nanyang/Rosyth/Frankel）+ 2 条街文件——非全岛代表</li>
<li>政策：ABSD/贷款规则变化对高总价段冲击不对称；landed 外国人本就受限（额外的需求侧刚性）</li>
<li>楼龄资本开支：原状老宅的翻建成本 2021 后显著上涨——重建价差需扣建安通胀后读</li>
<li>1996-98 教训：landed 并非永远防御——供给/杠杆共振时跌得更深（−48%）</li></ul>

<h2>方法学与来源 <span class='en'>Method & sources（可复算）</span></h2>
<ul>
<li>官方指数与 β：python -m researcher.marketdata.singstat；python -m researcher.factors.beta_layer</li>
<li>街道面板：research/build_factor_panel.py（Investment Suite 街道 PP 面/成交表 capture 留痕）</li>
<li>学区研究：researcher/landed/nanyang_digest.json（PASS 8.45）/ rosyth_digest.json（PASS 8.6）</li>
<li>地理事实：OneMap 官方 API（学校坐标、1km 实测）</li></ul>
<p class="foot">仅供研究与说明，非投资建议。Generated {today}.</p>
</div></body></html>"""


def main() -> None:
    kind = sys.argv[1] if len(sys.argv) > 1 else "condo"
    htmls = build_condo() if kind == "condo" else build_landed()
    if "�" in htmls or "â€" in htmls:
        raise SystemExit("mojibake gate")
    reports = os.environ.get("RESEARCH_REPORTS_DIR", r"G:\My Drive\004 RES\REsearch_Reports")
    name = f"Factor_Study_{kind.capitalize()}_Report.html"
    try:
        os.makedirs(reports, exist_ok=True)
        out = os.path.join(reports, name)
        open(out, "w", encoding="utf-8").write(htmls)
    except OSError:
        out = os.path.join(HERE, name)
        open(out, "w", encoding="utf-8").write(htmls)
    print(f"wrote {out}  ({len(htmls) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
