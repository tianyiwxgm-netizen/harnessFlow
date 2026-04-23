---
doc_id: exe-test-plan-5-1-integration-v1.0
doc_type: test-execution-plan
layer: 5-exe-test-plan
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/main-3-integration-and-acceptance.md（integration 集成测试代码由 main-3 落地）
  - docs/3-2-Solution-TDD/integration/（24 份 · main-3 产出）
version: v1.0
status: draft
assignee: **QA-1 · 独立会话**
wave: 6（与 main-3 部分并行 · main-3 代码 ready 后）
priority: P0（集成测试运行 · 出 bug report）
estimated_duration: 3-5 天
---

# QA-1 · 集成测试 Test Run Execution Plan

> **本 md 定位**：**独立会话** · 读本 md 即知如何执行 integration 测试 + 产出 bug report。
>
> **本组做什么**：
> 1. 运行 main-3 落地的 24 份 integration test（20 IC × 5 TC + 4 专项）
> 2. 分析失败 · 产 bug report（P0/P1/P2 分级）
> 3. 交主会话（main-4 WP06 消费）

> **本组不做**：
> - ❌ 不写新 integration 代码（main-3 已落地）
> - ❌ 不独立 fix bug（由 main-4 主会话 fix）
> - ❌ 不独立仲裁（若发现真契约矛盾 · 走 4-0 §6 主会话仲裁）

---

## §0-§10

## §1 范围

### 执行 4 块测试套件

**Block A · 20 IC 契约测试**（20 IC · 每 IC ≥ 15 TC · ~300 TC）：
- IC-01 state_transition
- IC-02 get_next_wp
- IC-03 assign_wp
- IC-04 invoke_skill
- IC-05 delegate_subagent
- IC-06 kb_read
- IC-07 kb_write_session
- IC-08 kb_promote
- IC-09 events_append + PM-08 唯一事实源
- IC-10 events_read
- IC-11 process_content
- IC-12 delegate_codebase_onboarding
- IC-13 push_suggestion
- IC-14 push_rollback_route
- IC-15 request_hard_halt（100ms 硬约束 · 必测 benchmark）
- IC-16 push_gate_card_to_ui
- IC-17 push_panic_event（100ms 硬约束）
- IC-18 audit_query
- IC-19 wbs_decomposition
- IC-20 invoke_verifier

**Block B · 10×10 矩阵**（45 对 L1 × 4 TC = 180 TC）：
- 25 必测对 × 4 TC = 100 TC
- 20 弱依赖 × 1 smoke = 20 TC
- 覆盖率目标：必测 100% · 弱 100% smoke

**Block C · PM-14 违规专项**（跨 20 IC 专项 · ~40 TC）：
- 每 IC 缺 pid 专项
- 每 IC 跨 pid 专项（rootfield 错误）

**Block D · 失败传播专项**（~60 TC）：
- 10 L1 各自失败的 PM-14 隔离
- 系统级 halt（仅 L1-09 可触发）
- 每对 L1 的级联失败路径

**Block E · 性能集成**（7 SLO × 采样 · ~40 TC）：
- PRD §7.1 时延 × 11 条
- PRD §7.2 吞吐 × 5
- PRD §7.3 资源 × 2

**合计 ~620 TC · 3-5 天运行**

---

## §2 源导读

| 优先级 | 文档 |
|:---:|:---|
| P0 | main-3 exe-plan（知道测什么）|
| P0 | 3-2 integration/* 24 份（测试用例规格）|
| P0 | tests/integration/* 实际代码（main-3 产出）|
| P0 | ic-contracts.md §3.1-§3.20（契约断言）|
| P0 | p0-seq.md（12 条 P0 时序 · 必测）|
| P0 | p1-seq.md（11 条 P1 时序）|
| P1 | PRD §7 性能 SLO |

---

## §3 WP 拆解（8 WP · 4 天 · 可并发）

| WP | 主题 | 前置 | 估时 |
|:---:|:---|:---|:---:|
| QA1-WP01 | 环境准备（跑 main-3 测试基础设施 · tmp dir · 清 fixture）| main-3 全绿 | 0.5 天 |
| QA1-WP02 | Block A 20 IC 契约 × 1/2（IC-01~IC-10 · 50%）| WP01 | 1 天 |
| QA1-WP03 | Block A 20 IC 契约 × 2/2（IC-11~IC-20 · 50%）| WP01 · 可与 WP02 并行 | 1 天 |
| QA1-WP04 | Block B 10×10 矩阵 | WP02-03 | 1 天 |
| QA1-WP05 | Block C PM-14 违规专项 | WP02-03 | 0.5 天 |
| QA1-WP06 | Block D 失败传播 | WP02-03 | 0.5 天 |
| QA1-WP07 | Block E 性能集成 | WP02-03 | 0.5 天 |
| QA1-WP08 | bug report 汇总（P0/P1/P2 分级）| 全 WP | 0.5 天 |

### 关键 WP 细节

**QA1-WP01 环境准备**：
- 拉 main-3 最新 HEAD · 本地 `pytest --collect-only tests/integration/` · 确认 620 TC 全列
- `pytest tests/integration/ -x --tb=short` · 先跑一遍热身
- 装 pytest-xdist · 支持并行执行

**QA1-WP02/03 IC 契约（并行）**：
- 逐 IC 跑：`pytest tests/integration/ic_XX/ -v --junitxml=reports/ic_XX.xml`
- 对每失败 TC · 3 次重试（区分 flaky vs 真 bug）
- 产物：每 IC 一份 `reports/ic_XX.md`（PASS/FAIL + 失败明细）

**QA1-WP04 矩阵**：
- `pytest tests/integration/matrix/`
- 失败对 · 追查是生产方还是消费方问题

**QA1-WP05 PM-14**：
- 重点：pid 缺失 raise / 跨 pid raise / 同 pid 幂等
- 任一 TC 失败 · **标 HRL-01 违规** · P0 级

**QA1-WP06 失败传播**：
- 10 L1 各 kill -9 · 看级联是否按 arch §9 预期
- PM-14 隔离：故意 foo 失败 · 看 bar 是否受影响

**QA1-WP07 性能**：
- 跑 benchmark · 对比 PRD §7 SLO
- 不达标项 · 标 P1（main-4 WP05 调优）
- 特别关注：IC-15 halt ≤ 100ms · IC-17 panic ≤ 100ms · tick drift ≤ 100ms

**QA1-WP08 bug report**：
- 按模板：
  ```yaml
  bug_id: QA1-001
  severity: P0/P1/P2
  block: A/B/C/D/E
  ic_or_matrix: IC-09
  failing_tc: test_ic09_audit_chain_break
  expected: audit chain intact after fsync
  actual: chain broke at event #4523
  root_cause_hint: possibly L1-09 L2-02 hash verify bug
  repro_steps: "pytest tests/integration/ic_09/test_chain.py::test_ic09_audit_chain_break -v"
  assigned_to: main-4 主会话
  ```
- 存档 `reports/QA1-final-bug-report.yaml`

---

## §4 依赖图

```
main-3 全绿
  ↓
QA1-WP01 env
  ↓
QA1-WP02 ┬─ QA1-WP03（并行 · 2 slot）
  ↓
QA1-WP04/05/06/07（并行 · 4 slot）
  ↓
QA1-WP08 bug report → main-4 WP06 消费
```

---

## §5 standup + §6 自修正 + §7-§10 简版

- §5 每天 standup · prefix `QA1-WPNN`
- §6 自修正：若测试用例本身有 bug（非被测对象）· 走 4-0 §6 情形 C（3-2 TDD 偏差）· 回锤 main-3 修
- §7 无对外契约（本组是测试消费方）
- §8 DoD：
  - 620 TC 全跑（0 skip · 除 V2+ 标记）
  - 0 flaky（3 次重试稳定）
  - bug report 全分级
- §9 风险：
  - R-QA1-01 大量 P0 bug · 延期（预期 · 属正常）
  - R-QA1-02 IC-15/17 100ms 硬约束不达 · 性能 benchmark 放宽 vs main-4 调优（跨组协调）
- §10 交付：`reports/QA1-final-bug-report.yaml` + 各 IC 子报告

---

*— QA-1 · 集成测试 Test Run · Execution Plan · v1.0 —*
