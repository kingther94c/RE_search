# RE_search — 跨源研究 agent / cross-source research agent

积累**可复用的 skills**(知道*怎么找数据*、*怎么比较*、*怎么分析*),在多个数据源上工作。
核心理念:**数据靠 Claude 用现成能力去拿**——网页用 `WebFetch`/`WebSearch`,安卓 App 用
`research/lib/mbx.py`(adb UI 自动化)——**不绑定某个固定 tool**。skills 是核心资产,放在
`.claude/skills/`,Claude 会自动发现并调用(13 个 skill 的索引见
[`.claude/skills/README.md`](.claude/skills/README.md))。

> Accumulate reusable **skills** (how to *find*, *compare*, *analyse* data) across data sources.
> Data is gathered by Claude with whatever is available — `WebFetch`/`WebSearch` for the web, the
> `research/lib/mbx.py` adb harness for Android apps — **no fixed tool required**. Skills are the
> core asset and live in `.claude/skills/` (auto-discovered).

## 现状 / what ships today

两台经 walk-forward 验证的估值引擎(`researcher/engine/`,conformal 区间 + 代码指纹):

- **Condo engine v2** — URA caveat 谱系,~3.7% median APE(skill:`condo-resale-valuation`)
- **Landed engine LV1** — land-psf 口径 + 街道别名证据规则(skill:`landed-valuation`)

加上 landed 区域研究 / DD / 新盘 / 因子框架等共 **13 个 skills**,以及把 PropNex
Investment Suite 当 Tier-1 数据源用的 adb 收获链(`research/lib/`)。研究方法与每个
实验的裁决记录在 `research/registry/`(从 `01_roadmap.md` 进入)。

## 布局 / layout(2026-07-18 重构后)

```
.claude/skills/        ★ 核心资产:13 个原生 skills(.agents/skills 为生成的 Codex 镜像,
                         用 python tools/sync_agents_skills.py 再生,勿手改)
researcher/            分析"大脑"(纯 stdlib Python 包)
  engine/              ★ 生产估值面:engine v2 + LV1 + conformal 表 + 指纹守卫
  backtest/            walk-forward 实验室:harness、benchmarks、as-of URA store
  landed/  newlaunch/  factors/  sources/     领域包与官方数据适配器
  tax.py               全仓库唯一的 BSD/ABSD/SSD 实现(带生效日/来源元数据)
  legacy/              v1 条o链(value-a-property 的手艺参考,只修 bug)
research/              收获 harness + 研究记录
  lib/                 mbx.py(adb 取屏+解析+操作)+ 6 个 harvester + reconstruct_comps
  tools/               doctor、conformal 重校准 stamper(analyze_r3/analyze_landed)、审计
  experiments/         冻结的 EXP-编号一次性脚本(索引见其 README)
  data/                收获数据落盘处;registry/ 方法论与实验登记;captures/ 留痕
deliverables/          报告构建器(全部经 report_out.py 双写 reports/ 与 Drive 库)
tests/                 251 项;含 skills 路径引用守卫与 .agents 镜像一致性守卫
```

## 跑起来 / run

```powershell
pytest                                            # 251 tests,离线可跑(URA snapshot 回退)
# 条o估值(engine v2)
python deliverables/build_condo_valuation_report.py --project "TREASURE AT TAMPINES" --area 936 --floor 12
# landed 估值(LV1;完整报告默认入口)
python deliverables/build_landed_full_report.py --address "19 Cardiff Grove"
# 读安卓 App(需先登录、adb 可连):见 .claude/skills/read-investment-suite
python research/lib/mbx.py cap my_screen
```

报告默认**双写**:repo 根下 gitignored 的 `reports/` + `G:\My Drive\004 RES\REsearch_Reports`。

## 与 mobile_bridge 的关系 / relationship to mobile_bridge

[`mobile_bridge`](https://github.com/kingther94c/mobile_bridge) 是**模拟器宿主 + PropertyGuru
探索器**:mb_play AVD、`scripts\start_emulator.ps1` 和设备参数真相(其 `AGENTS.md`,现为
Pixel 6 竖屏 1080x2400)在那边;Investment Suite 的收获完全在**本仓库**(`research/lib/`)。
两边**互无代码依赖**——`research/tools/doctor.py` 只是 shell 调它的启动脚本(可用
`MBX_EMULATOR_CMD` 覆盖)。其旧 Appium 桥与 IS explorer 已退役进它的 `legacy/`。
详见 [`ARCHITECTURE.md`](ARCHITECTURE.md)。
