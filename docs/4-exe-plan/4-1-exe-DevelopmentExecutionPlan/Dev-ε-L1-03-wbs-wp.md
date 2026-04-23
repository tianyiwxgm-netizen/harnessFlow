---
doc_id: exe-plan-dev-epsilon-L1-03-v1.0
doc_type: development-execution-plan
layer: 4-exe-plan / 4-1-exe-DevelopmentExecutionPlan
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/4-exe-plan/4-1-.../Dev-α-L1-09-resilience-audit.md（标杆）
  - docs/2-prd/L1-03 WBS+WP 拓扑调度/prd.md
  - docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度/architecture.md
  - docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度/L2-01~L2-05.md（6584 行）
  - docs/3-2-Solution-TDD/L1-03-WBS+WP 拓扑调度/L2-01~L2-05-tests.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md §3.2 IC-02 · §3.19 IC-19 消费方
version: v1.0
status: draft
author: main-session
assignee: Dev-ε
wave: 2
priority: P0（L1-01 主循环调 IC-02）
estimated_loc: ~11850 行
estimated_duration: 4-6 天
---

# Dev-ε · L1-03 WBS+WP 拓扑调度 · Execution Plan

> **组一句话**：5 L2 · WBS 拆解（从 4 件套 Plan 派生）+ 拓扑 DAG 管理（环检测）+ WP 调度（并发 2）+ 完成度追踪 + 失败回退。**IC-02 入口** 被 L1-01 每 tick 调用 · IC-19 接收方（L2-01 Gate 触发 WBS 拆解）。

---

## §0 撰写进度

- [x] §1 范围 + 5 L2
- [x] §2 源文档
- [x] §3 WP 拆解（6 WP · 5 天）
- [x] §4 依赖图
- [x] §5 standup
- [x] §6 自修正
- [x] §7 对外契约（IC-02 · IC-19 消费）
- [x] §8 DoD（拓扑 · 并发约束）
- [x] §9 风险
- [x] §10 交付

---

## §1 范围

### 5 L2

| L2 | 职责 | 估时 | 3-1 行 | 估代码 |
|:---:|:---|:---:|---:|---:|
| L2-02 拓扑图管理器 | DAG · 环检测 · 状态机（READY/RUNNING/DONE/FAILED/BLOCKED/STUCK）· 6 态 | 1 天 | 1097 | ~2000 |
| L2-01 WBS 拆解器 | 从 4 件套 Plan → WP 层级树 · 差量合并 | 1 天 | 1041 | ~1900 |
| L2-03 WP 调度器 | IC-02 入口 · 拓扑序派发 · 并发 ≤ 2 · backpressure | 1 天 | 999 | ~1800 |
| L2-04 WP 完成度追踪器 | 订阅 IC-09 事件 · 聚合进度 · Burndown | 0.75 天 | 898 | ~1600 |
| L2-05 失败回退协调器 | retry / skip / rollback / escalate · 连续 ≥ 3 升级 | 1 天 | 1091 | ~1950 |
| 合计 5 | — | 4.75 天 + 0.5 集成 = **5.25 天** | 6584 | ~11850 |

### Out-of-scope

- ❌ 跨 project WP 共享（V2+ · 本版本单 project）
- ❌ 动态 priority 调度（V2+）

### 代码目录

```
app/l1_03/
├── wbs_decomposer/      # L2-01
├── topology/            # L2-02（6 态机 + 环检测）
├── scheduler/           # L2-03（IC-02）
├── progress/            # L2-04
└── rollback/            # L2-05
```

---

## §2 源文档导读

| 优先级 | 文档 |
|:---:|:---|
| P0 | `2-prd/L1-03 .../prd.md` 5 L2 产品边界 |
| P0 | `3-1/L1-03/architecture.md` §11 L2 分工 · §5 状态机 |
| P0 | `3-1/L1-03/L2-02.md` §3 7 方法 · §6 DAG 算法 · §11 14 错误码 |
| P0 | `3-1/L1-03/L2-01.md` §3 decompose_wbs + diff_merge |
| P0 | `3-1/L1-03/L2-03.md` §3 IC-02 schema |
| P0 | `3-1/L1-03/L2-04.md` §3 订阅 + Burndown |
| P0 | `3-1/L1-03/L2-05.md` §3 on_wp_failed · FailureCounter |
| P0 | `3-2/L1-03/*.md` (~1080 行 · ~192 TC) |
| P0 | `ic-contracts.md §3.2 IC-02 · §3.19 IC-19` |

---

## §3 WP 拆解（6 WP · 5.25 天）

| WP | L2 | 主题 | 前置 | 估时 | TC |
|:---:|:---:|:---|:---|:---:|:---:|
| ε-WP01 | L2-02 | DAG + 6 状态机 + 环检测 | α mock | 1 天 | ~39 |
| ε-WP02 | L2-01 | WBS 拆解 + 差量合并 | WP01 | 1 天 | ~37 |
| ε-WP03 | L2-03 | IC-02 WP 调度 + 并发 | WP01+02 | 1 天 | ~39 |
| ε-WP04 | L2-04 | 完成度追踪 + Burndown | WP01 + α IC-09 | 0.75 天 | ~36 |
| ε-WP05 | L2-05 | 失败回退 + 连续升级 | WP04 | 1 天 | ~38 |
| ε-WP06 | 集成 | 组内联调 + WBS 全链 | WP01-05 | 0.5 天 | ≥ 10 |

### 3.1 WP-ε-01 · L2-02 拓扑图管理器（地基 · 最先）

**L3**：
- `WBSTopology` Aggregate · 持有 DAG（节点 WP · 边依赖）
- 6 状态机：`READY / RUNNING / DONE / FAILED / BLOCKED / STUCK`
- 12 条合法 `LEGAL_TRANSITIONS`（单点定义 · 供 L2-03/04/05 reference）
- `load_topology(wbs_draft)`（IC-L2-01 · L2-01 调 · 装 DAG + 环检测 + 关键路径）
- `transition_state(wp_id, from, to, reason)` · 硬断言合法
- `read_snapshot(wp_ids)` · 只读视图
- `mark_stuck(wp_id)` · L2-05 调
- `export_readonly_view` · UI / 监督观测

**L4**：
```
app/l1_03/topology/manager.py           ~250 行（主类）
app/l1_03/topology/dag.py               ~200 行（DAG + 环检测 DFS）
app/l1_03/topology/state_machine.py     ~150 行（6 态 + 12 转换）
app/l1_03/topology/snapshot.py          ~100 行
app/l1_03/topology/schemas.py           ~150 行
```

**DoD**：
- [ ] ~39 TC 全绿
- [ ] 环检测正确（构造环 · 返 CYCLE_DETECTED）
- [ ] 12 条转换严格（非法转换 raise）
- [ ] coverage ≥ 80%
- [ ] commit `feat(harnessFlow-code): ε-WP01 L2-02 拓扑图 + 状态机`

### 3.2 WP-ε-02 · L2-01 WBS 拆解器

**L3**：
- `decompose_wbs(four_set_plan, architecture_output) -> WBSDraft`（IC-19 入口）
  - 从 Plan + TOGAF Phase D 派生 WP 层级
  - 每 WP 含 4 要素：`wp_id · description · deps[] · effort_estimate`
  - WP 粒度硬限：≤ 5 天（超则拒绝 · 反馈 Plan 要拆细）
- `diff_merge(old_topology, new_wbs)` · change_request 时差量合并
  - 保留已 RUNNING/DONE 的 WP
  - 新增/删除 WP · 更新 DAG
- 调 L1-05 skill（`wbs-decomposer` · IC-04）做实际 LLM 拆解 · 本 L2 是编排器

**L4**：
```
app/l1_03/wbs_decomposer/factory.py        ~220 行
app/l1_03/wbs_decomposer/diff_merge.py     ~180 行
app/l1_03/wbs_decomposer/skill_invoker.py  ~100 行（调 L1-05）
app/l1_03/wbs_decomposer/schemas.py        ~150 行
```

**DoD**：
- [ ] ~37 TC 全绿
- [ ] IC-19 schema 对齐
- [ ] WP 粒度硬限测（> 5 天 WP raise）
- [ ] diff_merge 保留 RUNNING WP 测
- [ ] commit `feat(harnessFlow-code): ε-WP02 L2-01 WBS 拆解`

### 3.3 WP-ε-03 · L2-03 WP 调度器（IC-02 入口）

**L3**：
- `get_next_wp(pid, current_running_count) -> WPDef | null`（IC-02）
  - 返三态：有 WP / 全 done null / 依赖未满足 null
  - 并发守护：`parallelism_limit=2`（scope §8.5 PM-04）· 超不返 WP
  - 拓扑序派发（优先关键路径）
  - 调 L2-02 `read_snapshot` 查 WP 状态 + 依赖 deps_met
- 发 IC-09 `wp_dispatched` 事件
- PM-14：跨 pid 拒绝（A project 不能 get B 的 WP）

**L4**：
```
app/l1_03/scheduler/dispatcher.py       ~250 行
app/l1_03/scheduler/priority_queue.py   ~150 行
app/l1_03/scheduler/concurrency_guard.py ~100 行
app/l1_03/scheduler/schemas.py          ~150 行
```

**DoD**：
- [ ] ~39 TC 全绿
- [ ] IC-02 schema 对齐
- [ ] 三态返回语义测（有/null-done/null-deps）
- [ ] 并发 ≥ 2 硬拒绝
- [ ] PM-14 跨 pid 拒绝
- [ ] commit `feat(harnessFlow-code): ε-WP03 L2-03 WP 调度 IC-02`

### 3.4 WP-ε-04 · L2-04 完成度追踪器

**L3**：
- 订阅 IC-09 事件（`wp_completed` / `wp_failed` via Dev-α register_subscriber）
- `on_wp_done(wp_id, result)` / `on_wp_failed(wp_id, reason)` · 更新 topology state
- `transition_state`（调 L2-02）· RUNNING → DONE/FAILED
- Burndown 计算：`total_effort - done_effort` 每 tick 更新
- 导出 `progress_snapshot` · L1-10 UI 消费（SSE）

**L4**：
```
app/l1_03/progress/tracker.py          ~200 行
app/l1_03/progress/event_subscriber.py ~150 行
app/l1_03/progress/burndown.py         ~120 行
app/l1_03/progress/schemas.py          ~130 行
```

**DoD**：
- [ ] ~36 TC 全绿
- [ ] 事件订阅准确（mock IC-09 · 发 wp_done · tracker 更新）
- [ ] Burndown 正确（Effort-based · 非 WP-count）
- [ ] commit `feat(harnessFlow-code): ε-WP04 L2-04 完成度追踪`

### 3.5 WP-ε-05 · L2-05 失败回退协调器

**L3**：
- `on_wp_failed(wp_id, reason, evidence)` · L2-04 转发
- `FailureCounter` 状态机 5 状态（`NORMAL / RETRY-1 / RETRY-2 / RETRY-3 / ESCALATED`）
- 决策表：
  - 首次 failed · NORMAL → RETRY-1 · 本级 retry
  - 连续 2 次 failed · RETRY-1 → RETRY-2 · 本级 retry
  - 连续 3 次 · RETRY-2 → RETRY-3 · **升级**（发 IC-14 push_rollback_route 到 L1-04 · 或 IC-15 硬红线）
  - `on_wp_done_reset(wp_id)` · 成功后 counter 重置
- `on_deadlock_notified`（L2-03 → 本 L2 · 死锁时立即 IC-15 halt）

**L4**：
```
app/l1_03/rollback/coordinator.py       ~220 行
app/l1_03/rollback/failure_counter.py   ~150 行（5 态机）
app/l1_03/rollback/escalator.py         ~120 行（IC-14/15 出口）
app/l1_03/rollback/schemas.py           ~150 行
```

**DoD**：
- [ ] ~38 TC 全绿
- [ ] 5 态机严格（每条转换有测）
- [ ] on_wp_done_reset 幂等
- [ ] 连续 3 次失败升级测
- [ ] commit `feat(harnessFlow-code): ε-WP05 L2-05 失败回退`

### 3.6 WP-ε-06 · 集成

- 组内 5 L2 联调：WBS 拆解 → 拓扑装图 → 调度 → 追踪 → 回退 全链
- IC-02 + IC-19 契约测

**DoD**：≥ 10 集成 TC 绿 · commit `feat(harnessFlow-code): ε-WP06 集成`。

---

## §4 依赖图

```
ε-WP01 L2-02 拓扑（地基）
  ↓
ε-WP02 L2-01 WBS 拆解 ← IC-19 from δ
  ↓
ε-WP03 L2-03 调度（IC-02）
  ↓
ε-WP04 L2-04 追踪 ← IC-09 from α
  ↓
ε-WP05 L2-05 回退（IC-14/15 → ζ/L1-01）
  ↓
ε-WP06 集成
```

### 跨组 mock

| 外部 | mock |
|:---|:---|
| IC-09 (α) | mock append · subscriber mock 触发 |
| IC-04 (γ) wbs-decomposer skill | mock 返 dummy WBS |
| IC-14/15 消费方 (主-1 / L1-01) | mock assert 收到 |
| IC-19 调用方 (δ) | 本组测试中作调用方 |

---

## §5 standup + commit

复用 Dev-α §5 · prefix `ε-WPNN`。

---

## §6 自修正

- **情形 B · 3-1 不可行**：6 状态机的某转换实测不合理 · 改 L2-02 §8
- **情形 D · IC-02 契约**：L1-01 消费方对 `null` 返回三态的理解（null-done vs null-deps）· 仲裁 ic-contracts §3.2

---

## §7 对外契约

| IC | 方法 | 角色 |
|:---|:---|:---|
| IC-02 接收 | `get_next_wp(pid)` | L1-01 → L2-03 · P95 ≤ 200ms |
| IC-19 接收 | `request_wbs_decomposition(pid, plan)` | L1-02 → L2-01 · dispatch ≤ 100ms · result 按规模 |
| IC-14/15 发起 | `push_rollback_route` / `request_hard_halt` | L2-05 → 主-1 L1-04 / L1-01 |

**替换时机**：WP03 完 · L1-01 可切真实 IC-02 · WP06 完 · Dev-δ L2-01 可切真实 IC-19。

---

## §8 DoD（拓扑特化）

- 6 状态机合法性 · 所有转换单点定义 · L2-03/04/05 必 reference 同一 `LEGAL_TRANSITIONS`
- DAG 环检测 < 1ms（V ≤ 10）
- 并发 ≤ 2 硬守
- PM-14 跨 pid 拒绝
- FailureCounter 5 态严格
- coverage ≥ 85%
- 集成 ≥ 10 TC

---

## §9 风险

| 风险 | 降级 |
|:---|:---|
| **R-ε-01** WBS 拆解 LLM 返低质结果 | skill 层降级 · 本 L2 多次 retry |
| **R-ε-02** 并发 2 太低 | config 调 · 默认 2 · 急可升 3（PM-04 scope 原定）|
| **R-ε-03** 死锁误判 | L1-09 L2-02 死锁检测兜底 + 人工 review |

---

## §10 交付清单

### 代码（~11850 行）

```
app/l1_03/
├── wbs_decomposer/   (4 文件 · ~650 行)
├── topology/         (5 文件 · ~850 行)
├── scheduler/        (4 文件 · ~650 行)
├── progress/         (4 文件 · ~600 行)
└── rollback/         (4 文件 · ~640 行)
```

### 测试（~4800 行）

```
tests/l1_03/
├── test_l2_01_wbs.py          (~37)
├── test_l2_02_topology.py     (~39)
├── test_l2_03_scheduler.py    (~39)
├── test_l2_04_progress.py     (~36)
├── test_l2_05_rollback.py     (~38)
├── integration/
│   ├── test_l1_03_e2e.py
│   ├── test_ic_02_19.py
│   └── test_pm14_cross.py
└── perf/
    ├── bench_ic_02.py         (P95 ≤ 200ms)
    └── bench_dag_cycle.py     (< 1ms)
```

### commit 8-10 个

---

*— Dev-ε · L1-03 WBS+WP · Execution Plan · v1.0 · 2026-04-23 —*
