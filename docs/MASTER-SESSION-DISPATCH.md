---
doc_id: master-session-dispatch-v1.0
doc_type: master-dispatch-guide
layer: root（top-level dispatch guide）
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md（总执行计划 · 内容源头）
  - docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/（11 份）
  - docs/4-exe-plan/main-4-final-integration-exe-plan.md
  - docs/4-exe-plan/4-3-exe-monitoring&controlling/4-3-monitoring-impl-plan.md
  - docs/5-exe-test-plan/（5 份）
  - docs/6-finalQualityAcceptance/（4 份）
version: v1.0
status: ready
updated_at: 2026-04-22
---

# MASTER-SESSION-DISPATCH · 会话分工总指引

> **本 md 定位**：**用户最终操作指南**。读完本 md 即知：
>
> 1. 一共多少会话（23 slot）
> 2. 每会话读哪份 md（exe-plan 全路径）
> 3. 会话之间的依赖顺序（7 波推进）
> 4. 主会话 vs 分派会话的边界
>
> **使用方式**：
>
> - 按**波 1-7**顺序 · 依次 open 会话
> - 每会话发一句话：`按 <md 路径> 执行`
> - 等会话汇报 DoD 绿后 · 再开下一波

---

## §1 会话总数 · 23 slot

| 组 | 类型 | 数量 | 职责 |
|:---:|:---|:---:|:---|
| **Dev-α ~ Dev-θ** | Dev 独立分派 | **8** | 8 个 L1 BC · 单 L1 深度开发 + TDD |
| **main-1** | 主会话接力 | **1** | L1-04 Quality Loop（最复杂单 L1）|
| **main-2** | 主会话接力 | **1** | L1-01 主决策循环（心脏）|
| **main-3** | 主会话接力 | **1** | 集成层（24 integration + 12 acceptance）|
| **main-4** | 主会话接力 | **1** | 最终集成 + bug fix + release（终末）|
| **QA-1 ~ QA-5** | 测试独立 | **5** | 5 种测试执行 |
| **Sign-1 ~ Sign-4** | 签收独立 | **4** | 4 种签收资产准备 |
| **4-3** | 融合进 Dev-ζ + 主-1 | **0** | 监督规约 · 不独立开会话 |
| **合计** | - | **23** | - |

> **补充**：4-3 监督规约实际融合进 Dev-ζ（L1-07）+ 主-1（L1-04）· 无独立会话 · 但有独立 md 作源导读（`docs/4-exe-plan/4-3-exe-monitoring&controlling/4-3-monitoring-impl-plan.md`）。

---

## §2 23 会话总表 · 读哪份 md

### 2.1 波 1-3 · 底座 + 业务 + 监督（11 Dev · 独立分派）
进行中：
| # | 会话名        | L1 | md 路径 | 估时 | 波 |
|:---:|:-----------|:---:|:---|:---:|:---:|
| 1 | **Dev-α**  | L1-09 韧性+审计 | `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-α-L1-09-resilience-audit.md` | 5-7 天 | 1 |
| 2 | **Dev-β**  | L1-06 3 层 KB | `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-β-L1-06-kb-3-layer.md` | 6.5 天 | 1 |
| 3 | **Dev-γ**  | L1-05 Skill+subagent | `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-γ-L1-05-skill-subagent.md` | 5 天 | 2 |
| 4 | **Dev-δ**  | L1-02 项目生命周期 | `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-δ-L1-02-lifecycle.md` | 7 天 | 2 |
| 5 | **Dev-ε**  | L1-03 WBS+WP | `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-ε-L1-03-wbs-wp.md` | 5.25 天 | 2 |
| 6 | **Dev-ζ**  | L1-07 Harness 监督 | `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-ζ-L1-07-supervisor.md` | 7.5 天 | 3 |
| 7 | **Dev-η**  | L1-08 多模态 | `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-η-L1-08-multimodal.md` | 5.5 天 | 3 |
| 8 | **Dev-θ**  | L1-10 UI | `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-θ-L1-10-ui.md` | 8.5 天 | 3 |




> **4-3 监督规约**：Dev-ζ 和主-1 会话内自行读 `docs/4-exe-plan/4-3-exe-monitoring&controlling/4-3-monitoring-impl-plan.md` · 作源导读 · 不单独开会话。




**波 1-3 并发情况**：同波内的 Dev 组可并行（如 Dev-α + Dev-β 同时开）· 分 2-3 machine slot 共用。

### 2.2 波 4-5 · 核心集成 + 主循环（主会话接力）

| # | 会话名 | L1 | md 路径 | 估时 | 波 |
|:---:|:---|:---:|:---|:---:|:---:|
| 9 | **main-1** | L1-04 Quality Loop | `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/main-1-L1-04-quality-loop.md` | 10-14 天 | 4 |
| 10 | **main-2** | L1-01 主决策循环 | `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/main-2-L1-01-main-decision-loop.md` | 7-10 天 | 5 |

> main-1 / main-2 都是**主会话 resume**（不 subagent 分派 · 因跨 IC 数过多需主会话仲裁）。

### 2.3 波 6 · 集成 + QA（1 主会话 + 5 QA 独立）

| # | 会话名 | 类型 | md 路径 | 估时 | 波 |
|:---:|:---|:---:|:---|:---:|:---:|
| 11 | **main-3** | 主会话集成 | `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/main-3-integration-and-acceptance.md` | 7-10 天 | 6 |
| 12 | **QA-1** | 独立 | `docs/5-exe-test-plan/5-1-integration-test-run.md` | 3-5 天 | 6 |
| 13 | **QA-2** | 独立 | `docs/5-exe-test-plan/5-2-acceptance-test-run.md` | 3-4 天 | 6 |
| 14 | **QA-3** | 独立 | `docs/5-exe-test-plan/5-3-performance-test-run.md` | 2-3 天 | 6 |
| 15 | **QA-4** | 独立 | `docs/5-exe-test-plan/5-4-failure-injection.md` | 2-3 天 | 6 |
| 16 | **QA-5** | 独立 | `docs/5-exe-test-plan/5-5-regression-test.md` | 1-2 天 × N 轮 | 6-7 |

> QA-1 ~ QA-4 可**4 并发**（等 main-3 完 + 对应前置 ready）· QA-5 在 main-4 fix 后跑。

### 2.4 波 7 · 最终集成 + 签收 + release（1 主 + 4 Sign 独立）

| # | 会话名 | 类型 | md 路径 | 估时 | 波 |
|:---:|:---|:---:|:---|:---:|:---:|
| 17 | **main-4** | 主会话最终 | `docs/4-exe-plan/main-4-final-integration-exe-plan.md` | 12-17 天 | 7 |
| 18 | **Sign-1** | 独立 | `docs/6-finalQualityAcceptance/6-1-delivery-checklist.md` | 1 天 | 7 |
| 19 | **Sign-2** | 独立 | `docs/6-finalQualityAcceptance/6-2-release-process.md` | 0.5-1 天 | 7 |
| 20 | **Sign-3** | 独立 | `docs/6-finalQualityAcceptance/6-3-signoff-templates.md` | 0.5 天 | 7 |
| 21 | **Sign-4** | 独立 | `docs/6-finalQualityAcceptance/6-4-release-notes-and-docs.md` | 1-2 天 | 7 |

> Sign-1/2/3/4 **4 并发**（独立准备 release 资产 · main-4 WP07-08 消费）。

### 2.5 归纳 · 波 × 并发 × 会话 slot

```
波 1（底座）：Dev-α + Dev-β 并行 → 2 slot
波 2（业务）：Dev-γ + Dev-δ + Dev-ε 并行 → 3 slot（可复用波 1 slot）
波 3（监督+扩展）：Dev-ζ + Dev-η + Dev-θ 并行 → 3 slot
波 4（Quality Loop）：main-1 独占 → 1 slot（主会话）
波 5（主循环）：main-2 独占 → 1 slot（主会话）
波 6（集成+QA）：main-3 + QA-1/2/3/4 并行 → 5 slot
波 6-7（回归）：QA-5 × N 轮 → 1 slot（可迭代）
波 7（最终+签收）：main-4 + Sign-1/2/3/4 并行 → 5 slot
```

**峰值并发**：5 slot（波 6 或 波 7）· 建议**最少配 5 slot**。

---

## §3 会话依赖图（简版）

```
波 1 Dev-α(L1-09) ─┐
波 1 Dev-β(L1-06) ─┼─┐
                    ↓ ↓
波 2 Dev-γ(L1-05) ──┤
波 2 Dev-δ(L1-02) ──┤
波 2 Dev-ε(L1-03) ──┤
                    ↓
波 3 Dev-ζ(L1-07) ──┤
波 3 Dev-η(L1-08) ──┤
波 3 Dev-θ(L1-10) ──┤
                    ↓
波 4 main-1(L1-04) ─┤（所有 Dev ready 前置）
                    ↓
波 5 main-2(L1-01) ─┤（main-1 ready 前置）
                    ↓
波 6 main-3(集成测试 + acceptance)
                    ↓
波 6 QA-1/2/3/4 (4 并发 · 等 main-3 测试代码 ready)
                    ↓
波 6-7 QA-5 regression × N
                    ↓
波 7 main-4(最终集成 + bug fix + release)
                    ↓
波 7 Sign-1/2/3/4 (4 并发 · main-4 消费)
                    ↓
                🎉 release v1.0.0
```

**详细依赖**：见 `docs/4-exe-plan/4-0-master-execution-plan.md §4` PlantUML 图。

---

## §4 主会话 vs 分派会话边界

### 4.1 主会话做（不可 delegate）

- main-1 / main-2 / main-3 / main-4 全 main 组
- 4-0 master-execution-plan 维护
- 跨组仲裁（§6 自修正情形 C/D/E）
- 源文档修改（2-prd / 3-1 / 3-2 / 3-3）
- 会话汇总（每波 DoD 检查）

### 4.2 分派会话做（独立）

- 8 Dev 组（α-θ）
- 5 QA 组
- 4 Sign 组
- 合计 17 独立会话

**判据**：单 L1 深度开发 + TDD · L2 ≤ 7 个 · 跨 IC ≤ 6 个 · 无跨 L1 e2e 需求 → 可独立。

---

## §5 推进节奏（用户视角）

### 5.1 用户实际开会话顺序

**Day 0**：读本 md + 4-0 master + 确认 scope

**Day 1**：开波 1 · Dev-α + Dev-β 两会话

**Day 7**：波 1 预计完 · 开波 2 · Dev-γ/δ/ε 三会话

**Day 14**：波 2 完 · 开波 3 · Dev-ζ/η/θ 三会话

**Day 23**：波 3 完 · 主会话接力 · 波 4 main-1（L1-04）

**Day 35**：波 4 完 · 主会话 · 波 5 main-2（L1-01）

**Day 45**：波 5 完 · 开波 6 · main-3 + QA-1/2/3/4 五会话

**Day 54**：波 6 部分完（main-3 + QA-1/2/3/4）· QA-5 回归开始

**Day 55**：开波 7 · main-4 + Sign-1/2/3/4 · 主会话主推 main-4 · Sign 4 并发

**Day 70**：main-4 bug fix 完 · QA-5 R{final} 释 release gate · 打包 · release **v1.0.0** 🎉

**合计 50-70 天墙钟**（取决于并发 slot + bug fix 周期）。

### 5.2 分 slot 建议

- 最少 **3 slot**（Dev 期并发 2 + 主会话 1）· 延期 +20%
- 推荐 **5 slot**（并发峰值）· 上文节奏表
- 最大 **7 slot**（加买 Claude seat）· 进一步加速 Dev 期

---

## §5.5 代码所有权矩阵（防冲突必读）

**所有 Dev 会话启动前必读**：`docs/CODE-OWNERSHIP-MATRIX.md`

**核心 3 条铁律**：
1. 各 Dev **只写 `app/l1_XX/**` + `tests/l1_XX/**`**（自己 L1 目录）
2. 共享文件（`pyproject.toml` / `tests/conftest.py` / `scripts/` / `docs/`）**冻结 · 找主会话合并**
3. 跨 L1 消费 **只通过 IC 接口**（mock / stub）· 不读不改对方源码

**推荐分支策略**：各 Dev 开独立分支 `dev-<你的名>-l1-<数字>` · 主会话定期 merge 到 main。

---

## §6 会话启动模板（用户用）

### 6.1 启动必须用 superpowers 全链路执行（强制）

**所有 Dev / main / QA / Sign 会话统一用 `superpowers` 插件驱动**（已安装 · 见 `.claude/plugins/`）：

| 阶段 | superpowers skill | 作用 |
|:---:|:---|:---|
| 接到任务 | `superpowers:using-superpowers` | 启动技能调度 · 扫 md 定 skill |
| 规划 | `superpowers:writing-plans` | 把 md 的 §3 WP 细化为 step-by-step plan · 落到 `docs/superpowers/plans/` |
| 执行（推荐）| `superpowers:subagent-driven-development` | 每 WP 一个 subagent · 两阶段 review(spec + code quality) |
| 执行（替代）| `superpowers:executing-plans` | 同会话内逐 task 跑 · 断点 checkpoint |
| TDD（必用）| `superpowers:test-driven-development` | red-green-refactor 铁律(Q-04) |
| 完成前 | `superpowers:verification-before-completion` | 确认真完成(能跑 + test 绿 + DoD 勾齐) |
| Review | `superpowers:requesting-code-review` | 分派 code-reviewer subagent 审 |
| 收尾 | `superpowers:finishing-a-development-branch` | commit + push + PR |
| 跨会话隔离 | `superpowers:using-git-worktrees` | 推荐用 worktree 隔离(波 1-3 并发期防冲突) |

**铁律**：
- 不准跳过 `writing-plans`（即使 md 已有 §3 WP · 仍要落到 `superpowers/plans/` 便于追踪）
- 不准跳过 `verification-before-completion`（DoD 自检入口）
- `test-driven-development` 每 WP 必用（Q-04 硬约束）

### 6.2 会话启动模板（复制发送）

每开一个会话 · 复制下面模板发第一条消息：

```
按 harnessFlow 会话分工执行任务 · 启动 superpowers 全链路：

目标 exe-plan md：<md 全路径>
  例如：/Users/zhongtianyi/work/code/harnessFlow/docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-α-L1-09-resilience-audit.md

执行流程（必须按此顺序启动 skill · 不得跳步）：

1. 调 Skill(`superpowers:using-superpowers`) · 扫本次任务可用 skill
2. 读 <md 全路径> 完整 §1-§10
3. 读 md 中声明的 parent_doc（2-prd + 3-1 + 3-2 + 3-3 相关部分 + ic-contracts.md）
4. 调 Skill(`superpowers:writing-plans`) · 把 md 的 §3 WP 落成 `docs/superpowers/plans/<会话名>-impl.md`
5. 调 Skill(`superpowers:using-git-worktrees`) · 创建隔离 worktree（波 1-3 并发期强烈推荐）
6. 调 Skill(`superpowers:subagent-driven-development`) · 逐 WP 推进（或 `superpowers:executing-plans` 同会话执行）
7. 每 WP 内：调 Skill(`superpowers:test-driven-development`) · red → green → refactor → commit
8. 全部 WP 完 · 调 Skill(`superpowers:verification-before-completion`) · 自检 DoD
9. 调 Skill(`superpowers:requesting-code-review`) · 分派 code-reviewer 审
10. 调 Skill(`superpowers:finishing-a-development-branch`) · commit + push + PR

约束（来自 4-0-master-execution-plan.md Q-01~Q-04 + PM-08/PM-14）：
- Code + TDD test **必须在同一会话内**完成（Q-04 铁律）
- PM-14：所有写操作必含 root pid
- PM-08：仅 L1-09 events.jsonl 为事实源（其他 L1 读不写）
- 100ms 硬约束（panic/halt/tick-drift）· 任一破 → P0
- 源文档不一致 → 冻结 · 走 md §6 自修正（不硬改代码）
- 跨 L1 / 跨 IC 问题 → 向用户汇报 · 主会话仲裁
- 不得修改本会话 L1 以外的代码（越界走 §6 情形 D）

每日 standup：提交到 `docs/4-exe-plan/standup-logs/<会话名>-<date>.md`

开干。
```

### 6.3 主会话专用模板补充（main-1 / main-2 / main-3 / main-4）

主会话接力 · 在上面模板基础上额外加：

```
主会话铁律附加：
- 本会话负责跨 L1 仲裁（情形 C/D/E）· 有权改源文档（2-prd / 3-1 / 3-2 / 3-3 / ic-contracts.md）
- 任何源文档修改必记录到 `projects/_correction_log.jsonl`
- main-4 追加调 Skill(`superpowers:finishing-a-development-branch`) 做 release tag + GitHub release
```

---

## §7 进度追踪（用户手动或 automated）

### 7.1 进度看板模板

建 `docs/4-exe-plan/PROGRESS.md`：

```markdown
# harnessFlow v1.0 开发进度

## 波 1（底座）
- [ ] Dev-α L1-09 韧性+审计 · assigned 2026-04-25 · ETA 2026-05-02
- [ ] Dev-β L1-06 3 层 KB · assigned 2026-04-25 · ETA 2026-05-02

## 波 2（业务）
- [ ] Dev-γ L1-05 · pending 波 1
- [ ] Dev-δ L1-02 · pending 波 1
- [ ] Dev-ε L1-03 · pending 波 1

（...）

## Milestone
- [ ] M0 所有源文档 ready（已完成 2026-04-21）
- [ ] M1 10 L1 代码 ready（波 3 完 · 预计 2026-05-15）
- [ ] M2 主会话集成层 ready（波 5 完 · 预计 2026-06-05）
- [ ] M3 QA 全完 · release gate PASSED（波 6-7 · 预计 2026-06-25）
- [ ] M4 release v1.0.0 ✅（波 7 · 预计 2026-06-30）
```

### 7.2 自检脚本

用户可跑：
```bash
# 检查每组 DoD 是否达
bash scripts/check_progress.sh

# 输出：
# Dev-α: DoD 13/13 ✅
# Dev-β: DoD 10/15 🟡（还差 checkpoint + tier 4）
# ...
```

---

## §8 风险 + 应急

| 风险 | 应急 |
|:---|:---|
| 某 Dev 组大幅 overrun（+50% 时间）| 主会话介入 pair · 或拆 WP 给另一会话 |
| 契约矛盾大量发现 | 主会话连跑 §6 情形 D · 批量修 ic-contracts.md |
| QA-1 发现 bug > 20 P0 | main-4 WP06 增带宽 · QA-5 多轮迭代 |
| 性能 SLO 3 硬约束不达 | main-4 WP05 深度调优 · 最极端走 §6 情形 A 放宽 SLO |
| 跨 session 恢复 Tier 4 行为异常 | Dev-α 回锤修 L1-09 L2-05 crash-safety |
| release 后 24h 内 P0 | Sign-2 rollback SOP · 发 v1.0.1 patch |

---

## §9 核心原则（铁律）

- **PM-14** · 所有写操作必有 root pid · 无例外
- **PM-08** · L1-09 events.jsonl 唯一事实源 · 其他 L1 读
- **Code + TDD 同会话** · 不可拆开（Q-04）
- **源文档为锚** · 代码对不上 · 走 §6 自修正（不硬改代码）
- **100% 审计链** · 任何 hash 断链 → halt
- **100ms 硬约束** · panic / halt / tick drift · 不达 block release

---

## §10 所有 md 总索引

### 4-exe-plan（开发执行计划 · 15 份）

- `docs/4-exe-plan/4-0-master-execution-plan.md` · 总调度
- `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-α-L1-09-resilience-audit.md`
- `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-β-L1-06-kb-3-layer.md`
- `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-γ-L1-05-skill-subagent.md`
- `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-δ-L1-02-lifecycle.md`
- `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-ε-L1-03-wbs-wp.md`
- `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-ζ-L1-07-supervisor.md`
- `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-η-L1-08-multimodal.md`
- `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-θ-L1-10-ui.md`
- `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/main-1-L1-04-quality-loop.md`
- `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/main-2-L1-01-main-decision-loop.md`
- `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/main-3-integration-and-acceptance.md`
- `docs/4-exe-plan/main-4-final-integration-exe-plan.md`
- `docs/4-exe-plan/4-3-exe-monitoring&controlling/4-3-monitoring-impl-plan.md`

### 5-exe-test-plan（测试执行计划 · 5 份）

- `docs/5-exe-test-plan/5-1-integration-test-run.md`
- `docs/5-exe-test-plan/5-2-acceptance-test-run.md`
- `docs/5-exe-test-plan/5-3-performance-test-run.md`
- `docs/5-exe-test-plan/5-4-failure-injection.md`
- `docs/5-exe-test-plan/5-5-regression-test.md`

### 6-finalQualityAcceptance（签收 · 4 份）

- `docs/6-finalQualityAcceptance/6-1-delivery-checklist.md`
- `docs/6-finalQualityAcceptance/6-2-release-process.md`
- `docs/6-finalQualityAcceptance/6-3-signoff-templates.md`
- `docs/6-finalQualityAcceptance/6-4-release-notes-and-docs.md`

### 本 md（总调度）

- `docs/MASTER-SESSION-DISPATCH.md` · 本文件

---

**合计 25 份 md**（1 总调度 + 1 master exe-plan + 11 Dev/main exe-plan + 1 main-4 + 1 monitoring impl + 5 test plan + 4 signoff）。

---

## §11 最终交付

完成 23 会话 + 本 md + 4-0 master 后：

1. 代码：10 L1 + 集成层 + UI · ~195,000 行
2. 测试：~4080 TC 全绿 · 3 硬 SLO 达 · 审计 100%
3. 文档：7 篇用户/开发者文档 · 3-1/3-2/3-3 设计文档
4. 交付包：`releases/harnessflow-v1.0.0.tar.zst` + manifest + sha256
5. release：GitHub v1.0.0 · 公告发送
6. 签收：5 维度全绿 · yaml 存档

🎉 **harnessFlow v1.0 正式交付**。

---

*— MASTER-SESSION-DISPATCH · v1.0 · 用户最终操作指南 —*
