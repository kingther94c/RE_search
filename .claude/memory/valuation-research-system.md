---
name: valuation-research-system
description: "The pivot from per-property valuation to a research-to-skill quant program (3 skills: condo-resale/new-launch/landed); URA API is the backtest base, Module 0 harness built 2026-07-15"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4510089b-467e-49e5-b9de-e50ba3717d1c
---

Kelvin reframed the RE_search property work (2026-07-15): no longer "build a valuation
model" but **build a Singapore residential valuation RESEARCH SYSTEM** that graduates
validated methods into **three** user-facing skills — `condo-resale-valuation`,
`new-launch-valuation`, `landed-valuation` — over shared modules (value geography,
market/time adjustment, independent evidence families, ensemble, validation). Geography
is a **shared dependency, NOT a user-facing skill**. Method **graveyard must be kept**.

**Decisions on record (his words):**
- Backtest base = **URA private-residential transaction API** (bulk, official, as-of
  replayable). Establish the baseline there, then **calibrate with Investment Suite** —
  IS has *far more* (granular per-unit/floor/stack/rent) data; the real bottleneck is
  "we have no good skill to guide the search/harvest of IS" → improving IS harvest is its
  own work-line. This nuances [[data-source-trust-hierarchy]] (IS still Tier-1 for live
  single-property; URA is the bulk backtest spine).
- Sequencing: **condo-resale loop first** (most data, most mature engine, cleanest truth),
  then reuse the harness for landed / new-launch.

**My correction he accepted implicitly:** the validation protocol is NOT uniform across
assets. Condo = quant walk-forward; landed = walk-forward + heavy case regression (noisy,
n small); new-launch = **mostly case-based + separation-of-quantities** (developer price ≠
fair value; often no clean OOS fair-value truth).

**Module 0 built & tested (98/98):** `researcher/sources/ura.py` (client + offline
`normalize`; needs `URA_ACCESS_KEY` — user must register, I can't), `researcher/backtest/`
(`store` as-of firewall = month-end+56d caveat-lag; `index` time-adj w/ pub lag; `metrics`;
`benchmarks` B1–B5; `harness` walk-forward valuing each subject as of end of month M-1;
`run` CLI). Research台账 in `research/registry/` (master methodology, experiment registry,
method graveyard, feature evidence, geography registry, changelog).

**Known URA limits shaping everything:** contractDate is MONTH-only, ~5y rolling, floor is
a BAND not exact, no unit/stack id → exact-floor/stack premium needs IS, not URA. Enriched
`factors/` panels are full-history → **leakage-prone inside a backtest**, need as-of rebuild
before use. Builds on [[condo-valuation-pipeline]], [[investment-suite-valuation]],
[[factor-study-capability]]. Repo default: push to main ([[git-default-main]]).

**Key & smoke done (2026-07-15):** URA key verified live (batch 1 = 20,548 caveats /
292 projects, 2021-07..2026-07); smoke caught real-data fixes (landed spelling
`Semi-detached` + strata variants → substring match; EC excluded from condo universe).
Key stored in gitignored `research/.secrets/ura_access_key` (env `URA_ACCESS_KEY` also
works) — never in git.

**Roadmap v1 (Fable-planned, in repo):** `research/registry/01_roadmap.md` — phases
R0–R8 with gates: R0 full pull + audit → R1 condo baseline leaderboard (sets THE BAR)
→ R2 error-driven bake-offs (only slices >1.5× bar open) → R3 multi-anchor + conformal
uncertainty (engine v2) → R4 IS calibration bridge + read-investment-suite v2 rewrite
(parallel) → R5 condo skill ship (G5 bar: beat benchmarks on ≥70% slices, regression
suite, hostile PASS) → R6 landed → R7 new-launch (premium persistence IS backtestable
via new-sale→resale caveats — upgraded position) → R8 monthly refresh ops. Est 12–18
sessions. Start every session from the roadmap's current phase.

**Progress R0-R3 (2026-07-15, on opus-4-8):**
- **R0 DONE (G0 PASS):** full pull = 136,436 caveats / 3,880 projects / 61 months; 61,097
  resale-condo subjects; 2,285 condo projects. `research/audit_ura.py` + EXP-0002.
  Exclusions: bulk(>1 unit), psf∉[500,6500], EC out of condo universe. Frozen 3.5MB gz
  snapshot committed (`researcher/sources/snapshots/`), store.load() falls back to it.
  Real-data fixes: cp1252 decode, landed spellings, EC.
- **R1 DONE (bar set):** harness perf refactor (`market.py` MarketView per-month indexes;
  dropped per-subject O(n) copy). **THE BAR = 4.1% median APE** (C1 grid ≈ B3; same-project
  dominates). Segment-avg (17.8%,+20% bias) → GY-0001; nearest-project (13.9%) → GY-0002.
  Medians flat across slices; real defects = TAIL (pct>10%=15%, worse >4M) + interval
  coverage 44%. EXP-0003. Lag-stable 42/56/70d.
- **R3 ENGINE v2 — G3 MET (EXP-0004/0005):** A1 hedonic AVM (`avm.py`); team fan-out
  (Workflow wf_234bc499-6eb, 4 worktree agents) built A2 pooled-shrinkage (`avm_pooled.py`,
  5.46% — best independent anchor), A3 kNN (`avm_knn.py`, 7.2%), E1 learned-weights
  (`ensemble_learned.py`). **Engine v2 = E2_ensemble_pooled (C1⊕A2): median 4.16% / 100%
  cover / interval 87%** — ties the C1 bar (4.08%) while fixing calibration 43%→87% + always
  answers. E0 superseded. **Workflow died at session boundary before verify/synthesis tail;
  I re-verified from journal + main-repo reproduction + code leakage-read (all clean)** —
  lesson: orchestrator must re-verify from journal, not trust the run to finish.
- **R3-finish DONE (EXP-0006), G3 MET cleanly.** **Engine v2 = `engine_v2.py` (V2): C1
  point wherever it answers, else anchor fallback (A2→A3→A1), + split-conformal band per
  (liquidity×segment) cell (`conformal_table.json`, 85% nominal).** Backtest: **median 4.09%
  / 100% coverage / interval 82.7%.** **Reversal lesson:** blending anchors into C1 HURTS the
  point everywhere same-project data exists — even at 1-2 comps (C1 4.84% vs blends 5.1-5.8%);
  anchors buy COVERAGE (~0.6% no-comp fallback) + INTERVALS, not point accuracy. So the
  simpler "best-method + fallback + calibrated band" beat the team's E0-E3 blends (all
  superseded). Conformal (held-out 82%/0.197 width) ~30-57% sharper than union bands.
  `research/analyze_r3.py` = thin-comp matrix + conformal calibrate/validate; run.py --dump.
- **7 commits pushed to main (62da2ce latest). 109 tests pass. R0-R3 COMPLETE.**

**R5 SHIPPED (2026-07-16), G3+G5 MET.** `condo-resale-valuation` skill accepted — hostile
review PASS **8.7/10** (4 rounds: 6.6→7.6→7.6→8.7; reviewer reproduced everything). Engine
v2.1 = C1 same-project grid (segment elasticity re-fit EXP-0007, size-gating, time-cap) +
lease-aware anchor fallback + split-conformal band. `value_unit.py` = production entry
(infer→value→confidence→guidance); hard-case honesty (freshest same-size ref, directional
"stale-comp" flag, point blended toward it, band widened, conf smooth, IS-corroboration
mandated). `build_condo_v2_report.py` bilingual HTML; `tests/test_value_unit.py` regression
suite; value-a-property SUPERSEDED. Numbers: median 3.71% / 100% cover / ~82% held-out
interval (85% nominal). Review lesson: the hostile round CAUGHT a real guardrail-#5
violation (ported −0.08 elasticity) and fixing it IMPROVED the population 4.1%→3.7%.

**Fable review round (EXP-0008, 2026-07-16):** applied safe fixes — **live-vs-reconstruction
as-of** (live = lag 0, the old blanket 56d lag was discarding the freshest ~2 months on live
valuations — real production bug), day-granular reconstruction, **fallback band widened to
anchor's own band** (C1-calibrated conformal under-covers on fallback), conformal↔code sha1
fingerprint + red-test guard, smooth confidence curve. **Deferred (fitted, recorded):**
FLOOR_PP 0.004 + CCR elasticity −0.016 — need a recalibration run to apply.

**LANDED SHIPPED (2026-07-17). `landed-valuation` skill ACCEPTED — hostile review PASS 8.05
after SIX rounds (6.9→7.05→7.8→7.55→6.65→8.05).** Engine LV1 = LC2 lease-matched street grid
+ fitted size curve → LA1 pooled fallback → conformal band; time adjustment = published PPI
+ **observed local-trend bridge (L2b, EXP-0017)**. **9.05% median APE / 100% coverage /
78.9% held-out band** (L1 bar 10.45 same-adjustment). Files: `value_landed.py`,
`landed_engine.py` (+`shipped_time_ctx` — ONE ctx constructor for production+harness+tests),
`landed_candidates.py`, `landed_size_curve.py`, `landed_benchmarks.py`, `local_trend.py`,
`build_landed_v2_report.py`, `tests/test_landed.py`+`test_local_trend.py`. EXP-0009..0017;
GY-0003/0004/0005.

**The landed findings that matter (all measured):**
- **Noise floor ~6.0/7.8/8.2%/print by type** (395 same-plot repeats) — URA prices a
  LAND+BUILDING BUNDLE it cannot decompose. Landed CANNOT reach condo-grade accuracy; 9.3% is
  ~3pp above the floor. Publish this, never promise better.
- **Size elasticity re-fit (EXP-0011, within-street FE, n=10,399):** the ported Cardiff −0.877
  was ~1.7× too steep. A single log-log constant is INADEQUATE — it collapses with size
  (<3k −0.51 … 8k+ ~−0.2): small terraces trade on QUANTUM, big plots on LAND. Fixed the size
  explosion (8-15k 24%→11%, 15k+ 41%→17%). TYPE is not an axis (Detached −0.24 was a size
  artifact). ≥8k is worst-identified where error is largest → case-tier, conf ≤45, band ×1.6.
- **Lease matching is mandatory** (LB4 priced ~20yr-left 99yr terraces off FH neighbours:
  **232% APE**). Quasi-FH never prices a leasehold; ±25y. Guards: leasehold w/o lease_start
  REFUSES; MIXED-tenure street (≥10% minority) REFUSES when tenure inferred (JALAN RINDU
  swings **+69.8%** on that "optional" input). Anchored regex (999-vs-1999).
- **REGIME BIAS — L2b DONE (2026-07-17, EXP-0016/0017), partially closed, still disclosed:**
  diagnosis first REFUTED my cap hypothesis by measurement (arithmetic right — PPI ×1.335 >
  the ×1.25 cap — but the 18mo half-life leaves ~0 WEIGHT on comps old enough to bind;
  GY-0004). Real mechanism: published-quarter staleness ~4.5mo × market pace. Fix that
  survived: **observed local-trend bridge** (as-of two-way FE monthly curve; per-comp anchor
  max(comp month, quarter mid) → newest VISIBLE month; never extrapolates). Hot regimes
  66.3/66.5→60.8/62.1, stable unharmed, medAPE 9.34→9.05. Pre-registered "fixed" bar (all
  regimes ∈[42,58]) NOT met → disclosure stays. Full-PPI-replacement REJECTED (GY-0005,
  broke 2023H1). Residual = caveat-visibility lag itself → only fresher observations (R4 IS
  live pulls) can shrink it; in-window modelling is exhausted.
  **Two lessons that cost/paid:** (1) diagnose-before-fit — measure the EXPOSURE, not just
  the arithmetic, before believing a mechanism; (2) **right-direction-wrong-mechanism** —
  the first bridge double-counted fresh comps (+4% on a subject's own same-month print) yet
  IMPROVED the backtest; a live field case (BOWMONT) caught what the panel could not.

**THE recurring lesson (cost 6 rounds): the quant core passed every time; the CLIENT-FACING
layer failed every time** — dead inputs (condition), exhibits contradicting captions
(non-lease-matched comps under a "lease-matched" header), guidance derived from the engine's
own error bar (72% of asks above every comp on their page), a production-only blend that was
never backtested, one-sided flags. **And: a metric you don't compute is a bias you can't see**
— mean signed_bias hid it; the SIGN TEST + median_signed (now in every slice, regime by
HALF-YEAR) exposed it.

**Emulator (verified 2026-07-17):** adb + AVD moved to **D:\Android\Sdk**; `mb_play` AVD in
mobile_bridge `.local/android/avd`; boot windowed via `scripts\start_emulator.ps1 -AvdName
mb_play`; `com.investmentsuite` already logged in. `research/doctor.py` first, every session.

**R4a MEASURED IS vs URA (EXP-0018, 2026-07-17) — it refuted two of my own beliefs:**
- **"IS is fresher" — FALSE.** Same caveats, same lag (0 of 104 LOYANG RISE rows newer;
  both newest 2026-06). The L2b sentence "only fresher observations (R4 IS) can shrink the
  landed residual bias" is **STRUCK** from roadmap/methodology/SKILL — the residual is
  permanent. IS's newer-LOOKING rows are the Tier-2 **Realtime Agency Data** panel (agency
  asks, tenure shows `-`), which sits right under the caveat table — reading "newest date on
  the Sale screen" scores IS as fresher on ASKING data. Guard: `assert_caveat_table`.
- **"Cardiff Grove has ZERO URA caveats" — FALSE.** **URA's `street` is a coarse PARENT
  label that merges adjacent roads.** Cardiff Grove is in URA under **ALNWICK ROAD** (16/17
  on month+price+area); `URA "LOYANG RISE" = IS Loyang Rise 104 + IS Loyang View 31 = 135`
  exactly. So `street_not_found` = a NAMING failure, fixable by resolving the parent street.
  Consequence: LC2's "same-street grid" is really same-PARENT-street (ALNWICK's 201 comps
  include Cardiff Grove) → **L2f opened**.
- **IS's real edge:** ADDRESS↔caveat mapping (URA has no address at all), history DEPTH
  (10Y street window / per-address back to ~1996), per-unit detail, rents, Est.Val —
  **not** freshness and **not** volume per road (it is a strict subset).
- Agreement on shared rows: **100%** on price and area. (A first pass said 98.1% — that was
  my greedy matcher crossing two same-price sales, not a data disagreement.)

**LANDED 全面报告 SHIPPED (2026-07-17):** `deliverables/build_landed_full_report.py "19 CARDIFF
GROVE" --type Terrace --area 1839.57 --condition original --profile PR --count 2` → 一个地址进,
中文为主、详略分层(结论→关键数据→证据→局限,`<details>` 折叠)的 HTML 出。四层内容:
**估值**(引擎 LV1)+ **DD**(OneMap/MP2025/PUB:地块、分区、学校、水浸、邻地剖面)+
**成本栈**(`researcher/landed/costs.py`:BSD/ABSD/SSD 时钟/盈亏平衡)+ **深度尽调 DD-3**
(由事实自动推导;`--digest` 挂载判断层,不给就明说不给 go/no-go)。范围声明:租金收益、
重建经济、持有成本、判断 —— 四项明确未覆盖。
- **`street_alias.py`**:地址路名→URA街道,**只认证据**(EXP-0018 交易匹配),未知即拒答。
  解锁了 Cardiff Grove 类拒答(→ ALNWICK ROAD,n=201)。
- **别名街道一律抑制议价门槛与方向性提示**(点估值保留):实测桶内 p25 给「买入 < S$3.87M」,
  而本路原装房成交 S$3.25-3.58M —— 照它买会买贵。这道闸只能在报告层(引擎不知道街道是别名来的)。
- **三个只有跑成品才会暴露的错**,都在发出去之前抓到:(1) `dd.py` 硬编码 15 所小学/8 个 MRT
  = **那个片区**的清单 → 385 Loyang Rise 报告说「2.2km 内无小学」,实际 640m 就有一所(在 1km
  学区圈内!)→ 换成全岛官方源 `researcher/sources/amenities.py`(182 校 / 200 站,落盘缓存);
  (2) 我把「SSD 比买入成本还大」**写死成断言**,它只在公民首套成立 → 改为由数字生成;
  (3) **PR 第三套 ABSD 仓库写 30%,正确 35%**(IRAS/MAS 三次交叉核对)—— 错值在两处,
  **两个内部来源一致不等于对:它们同源**。
- **教训:假阴性比缺失危险** —— 缺失看得见,假阴性看不见。以及**凡是能被同一份报告里的
  数字证伪的句子,都必须由那些数字生成**。
- **Fable 复审一轮(2026-07-17,PASS w/ revisions ~7.8 → F1-F6 全修,248 tests)。**
  三个 MAJOR 全是「证据在报告里、读者看不见」:authored dd3_alerts 被静默丢弃(含 archetype
  指名的 turnkey 缺陷风险)→ 与自动清单合并+来源打标+过时项标「已取代」;ask 4.83M 与
  「孪生房上月成交 5.22M」隔两屏 → 内联提示 + **近 12 个月窗 p25/p75**(additive 引擎输出
  `guidance_recent_12mo`;Seletar 实测近窗 4.70/4.97 vs 主窗 4.55/4.83,证实热街主门槛偏保守);
  方法分歧 17%(离抑制线 1pp)藏在折叠层 → 明面中文。verdict 提升到 L0;主体中文定稿
  (highlights 实为作者双语 `<span class='zh'>`,复审自己误判过)。**报告=渲染不是翻译:
  中文一律由结构化字段生成,引擎英文原文折叠备查。**

**L2f DONE (EXP-0019, 2026-07-17):** 真实门牌路 vs URA 母路桶做 comp 池,谁更好?walk-forward
91 subjects(Loyang 桶全分解 + Cardiff-in-Alnwick)。**P(点):+0.39pp → P3 MONITOR,保留 pooled
引擎;但分路按份额裂开** —— Cardiff(占 ALNWICK 桶 4%)拆分后 14.1→11.3%(被稀释),Loyang
Rise(占桶 77%)拆分反而更差(丢样本)。所以「拆池」不是普适升级,「少数份额的路被池错置」才是。
**D(分布):D1 抑制 JUSTIFIED,但判据我中途改错又改对** —— 第一版「子路成交高于桶 p25 的比例」
在三条路全触发(85/95/100%),我差点报「桶错置每条路」;**那量的是引擎在上涨屋苑的整体偏低,
不是混路**(直连街 Loyang Rise 同样偏高;Loyang Rise vs View 2025+ psf 1,479 vs 1,437 同子市场)。
改成**同一 subject 上 pooled vs split 门槛差**(差掉引擎共因):Cardiff 15.8% / Loyang View 3.8% /
Loyang Rise 0.7%。报告抑制理由从「混路」升级为实测驱动「少数份额」。**教训(第三次同款):
「高于某分位数的比例」分不清「池错了」和「引擎低了」,只有 within-subject 的 pooled−split 差能
隔离池效应 —— 靠它在一条本不该触发的对照街(直连 Loyang Rise)上触发才抓到。**
**R4b DONE:** landed 街道 IS 采集(导航契约、caveat/agency 双面板陷阱、冻结列+按格式判列、
app 表头完备性校验、归属流)从 harvest_street_sale.py 注释提升进 read-investment-suite SKILL,
冷启动 agent 无需读源码即可采集 landed 街道。`.agents` 已镜像。

**用户裁定(2026-07-18,报告设计,适用于今后所有报告):SSD 逐年时钟表 = 税务算术当占位,
删。** landed 按自住/数十年持有读,「4 年内哪年卖」这个决策不存在 —— 枚举 16/12/8/4% 对任何
真实决策都没有输入。**Why:** 量级大 ≠ 决策相关 —— 没有活的决策,量级只是 trivia。
**How to apply:** 成本栈只保留有决策含量的两句 —— 「4 年 = 硬性最短持有期」+「窗口后退出的
盈亏平衡涨幅」;任何「按年份/档位枚举税额」的表都先问:读者存在对应的活决策吗?

**Next:** ops runbook (both skills — refresh → audit-lite → re-validate → conformal recal)
· R4 IS bridge (now doubly motivated: condo hard-cases AND the landed residual bias, which
only fresher live data can shrink) · new-launch (R7). Condo frozen (backlog: FLOOR_PP
0.004, CCR elasticity −0.016 — fitted, need recalibration).
Roadmap `research/registry/01_roadmap.md`; 158 tests; ~20+ commits on main.
