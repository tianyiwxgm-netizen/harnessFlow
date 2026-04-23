---
doc_id: exe-plan-main-3-integration-v1.0
doc_type: development-execution-plan
layer: 4-exe-plan / 4-1-exe-DevelopmentExecutionPlan
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/3-1-Solution-Technical/L1集成/architecture.md（集成层顶层）
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
  - docs/3-1-Solution-Technical/integration/p0-seq.md（12 条 P0）
  - docs/3-1-Solution-Technical/integration/p1-seq.md（11 条 P1）
  - docs/3-2-Solution-TDD/integration/（24 份 · 未建 · M3 写）
  - docs/3-2-Solution-TDD/acceptance/（12 份 · 未建 · M3 写）
  - docs/2-prd/L1集成/prd.md（12 场景 · 10×10 矩阵 · 失败传播 · 性能）
version: v1.0
status: draft
assignee: **主会话（不分派）**
wave: 6（集成 + QA 前期）
priority: P0（e2e 跨 L1 · 无法分派）
estimated_loc: ~15000 行（集成测试代码 + acceptance e2e + bff 小量集成代码）
estimated_duration: 7-10 天
---

# main-3 · 集成层（integration + acceptance）· Execution Plan

> **定位**：**主会话必做** · 跨 L1 e2e · 无法分派（Q-04 硬约束）。
>
> **范围**：
> 1. 落地 3-2 integration/ 24 份集成测试（20 IC × 5 TC + 4 专项 matrix/PM14/failure/perf）
> 2. 落地 3-2 acceptance/ 12 场景 e2e
> 3. 少量集成胶水代码（如跨 L1 mock 基础设施 · 测试 harness）
>
> **前置**：所有 Dev + main-1 + main-2 全 ready · 波 5 后启动。

---

## §0-§10

---

## §1 范围

### 两块

**Block A · integration 集成测试**（3-2 M5 产物 · 24 份）：
- 20 IC 契约集成（每 IC ≥ 5 用例 · 测生产方 ↔ 消费方真实协作）
- 4 专项：
  - matrix-10x10-tests（45 对 × 4 用例）
  - pm14-violation-tests（跨 20 IC 的 PM-14 违规专项）
  - failure-propagation-tests（10 L1 失败 + PM-14 隔离）
  - performance-integration-tests（7 SLO）

**Block B · acceptance 端到端验收**（12 场景）：
- scenario-01 ~ 12 · 对应 PRD §5 / L1集成 arch §6
- 每场景 500-1500 行 pytest code · 含 GWT + 完整链路断言

**代码目录**：

```
tests/integration/
├── ic_01/ ~ ic_20/        # 每 IC 一个包
├── matrix/
├── pm14/
├── failure/
└── perf/

tests/acceptance/
├── scenario_01_wp_quality_loop/
├── scenario_02_s1_to_s7_full/
├── scenario_03_s2_gate_rework/
├── scenario_04_change_request/
├── scenario_05_hard_red_line/
├── scenario_06_panic_resume/
├── scenario_07_verifier_fail_rollback/
├── scenario_08_cross_session_recovery/
├── scenario_09_loop_escalation/
├── scenario_10_kb_promotion/
├── scenario_11_multi_project_v2/   # V2+ 骨架（本版本不跑）
└── scenario_12_large_codebase_onboarding/

tests/shared/                  # 共享 fixture / mock
├── conftest.py
├── project_factory.py
├── ic_assertions.py
└── e2e_harness.py
```

---

## §2 源导读

| 优先级 | 文档 |
|:---:|:---|
| P0 | `3-1/L1集成/architecture.md` §4-§11（全章节） |
| P0 | `ic-contracts.md §3.1~3.20` 每 IC 详规 |
| P0 | `integration/p0-seq.md` 12 条 P0 |
| P0 | `integration/p1-seq.md` 11 条 P1 |
| P0 | `2-prd/L1集成/prd.md §3-§11` |
| P0 | 10 L1 的 L2 tech-design（消费方视角）|
| P0 | 已完成的 57 L2 tests（单元 TDD · 作 integration 前提）|

---

## §3 WP 拆解（10 WP · 10 天）

| WP | 范围 | 前置 | 估时 | TC |
|:---:|:---|:---|:---:|:---:|
| M3-WP01 | tests/shared/ 共享 harness + project factory + 断言工具 | 全 Dev/main-1/main-2 ready | 1 天 | - |
| M3-WP02 | integration ic-09/ic-04/ic-01（最热 3 IC · 深度）| WP01 | 1 天 | ~30 |
| M3-WP03 | integration ic-02/03/13/15/17（次热 5 IC）| WP01 | 1 天 | ~40 |
| M3-WP04 | integration ic-05/06/07/08/11/12/14/16/18/19/20（其余 11 IC · 每 IC ≥ 5 TC）| WP01 | 1.5 天 | ~60 |
| M3-WP05 | matrix-10x10-tests（45 对）| WP02-04 | 1 天 | ~120 |
| M3-WP06 | pm14-violation-tests + failure-propagation | WP02-04 | 1 天 | ~80 |
| M3-WP07 | performance-integration-tests（7 SLO）| WP02-04 | 0.5 天 | ~40 |
| M3-WP08 | acceptance scenario-05/06（硬红线 + panic · 100ms 硬约束 · 先做）| WP01-04 | 0.75 天 | ~20 |
| M3-WP09 | acceptance scenario-01/03/04/07/09/10/12（7 场景）| WP02-04 | 1.5 天 | ~70 |
| M3-WP10 | acceptance scenario-02/08（S1→S7 全链 + 跨 session 恢复 · 最复杂）| 全 WP | 1.5 天 | ~30 |

### 关键 WP 细节

**M3-WP01 共享 harness**：
- `project_factory(pid=None)` fixture · 构造一个干净 project（含 mock chart · wbs · tdd · quality · kb 等）
- `ic_assertions.py` · 抽出公共断言（如 `assert_ic_09_emitted(event_type=...)` / `assert_state_transition_to(state)`）
- `e2e_harness.py` · 启动真实 tick loop · 支持 step/tick_n 调用 · 隔离环境（tmp dir）

**M3-WP02/03/04 integration · 20 IC**：
- 每 IC：正向 / 负向 / PM-14 / 幂等（若声明）/ SLO / 降级 / e2e mini 跨链 · 合计 ~15 TC/IC
- 特别关注：
  - IC-09：全 L1 生产方各 ≥ 1 测（10 L1 测 IC-09 · 确认每 L1 写事件正确）
  - IC-15：100ms 硬约束 benchmark
  - IC-17 panic：100ms 硬约束 benchmark

**M3-WP05 10×10 矩阵**：
- 45 对 × 4 用例（正向 / 负向 / PM-14 / 降级）= 180 用例
- 必测 25 对各 ≥ 4 TC · 弱依赖 20 对各 1 smoke

**M3-WP06 PM-14 + 失败传播**：
- PM-14：每 IC 跨 pid 专项 · 缺 pid 专项
- 失败传播：10 L1 各自失败 + PM-14 隔离（foo 失败不影响 bar）+ 系统级 halt（L1-09 唯一）

**M3-WP07 性能**：
- PRD §7.1 11 条时延阈值各 ≥ 2 采样
- PRD §7.2 吞吐 5 指标
- PRD §7.3 资源 2 维度

**M3-WP08/09/10 acceptance 12 场景**：
- 每场景 GWT 结构 · 完整 e2e
- 场景 2（S1→S7）最复杂 · 压缩版（mock LLM · 真实流程）
- 场景 8（跨 session 恢复）· 模拟 kill -9 + 重启 · Tier 1-4 全测
- 场景 11（多 project V2+）仅建骨架 · mark `@pytest.mark.v2_plus` skip

---

## §4 依赖图

```
M3-WP01 共享 harness（地基）
  ↓
M3-WP02/03/04 integration 20 IC
  ↓
M3-WP05/06/07 专项（matrix / PM-14 / failure / perf）
  ↓
M3-WP08（panic/红线 100ms） ─┐
M3-WP09（其他场景）          ├─► M3-WP10（S1→S7 + 恢复）
                              ↓
                      QA 接手（5-exe-test-plan）
```

---

## §5-§10 简版

- §5 standup · prefix `M3-WPNN`
- §6 自修正：集成期高发 IC 契约矛盾（情形 D）· 主会话主动仲裁
- §7 对外契约：本组**消费所有 20 IC**（作为 integration 测试方）
- §8 DoD：
  - 24 integration + 12 acceptance 全绿
  - 20 IC 每 IC ≥ 15 TC（含 PM-14 + SLO）
  - 10×10 矩阵覆盖率 100%
  - 7 SLO 100% 达标
  - 12 场景 e2e 全绿（scenario-11 骨架）
- §9 风险：
  - R-M3-01 单 IC 集成发现大量契约模糊 · §6 情形 D 高发 · 扩延期
  - R-M3-02 scenario-02 S1→S7 e2e 运行时间长 · 用 mock LLM 加速
- §10 交付：~15000 行 testing code · 20-25 commits

---

*— main-3 · 集成 + acceptance · Execution Plan · v1.0 —*
