---
doc_id: exe-plan-main-2-L1-01-v1.0
doc_type: development-execution-plan
layer: 4-exe-plan / 4-1-exe-DevelopmentExecutionPlan
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/2-prd/L1-01主 Agent 决策循环/prd.md
  - docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/architecture.md
  - docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-01~L2-06.md（13161 行）
  - docs/3-2-Solution-TDD/L1-01-主 Agent 决策循环/L2-01~L2-06-tests.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md（IC-01/02/03/04/05/06/13/15/17 全部经本组）
version: v1.0
status: draft
assignee: **主会话（不分派）**
wave: 5（主循环 · 所有 Dev 组 + 主-1 ready 后）
priority: P0（心脏 · 全系统调度源）
estimated_loc: ~23700 行
estimated_duration: 7-10 天
---

# main-2 · L1-01 主决策循环 · Execution Plan

> **定位**：**主会话必做** · 6 L2 · **整个 harnessFlow 的心脏** · L1-01 是唯一控制源 · tick 驱动全系统。
>
> **前置**：所有 Dev 组（α-θ）+ main-1（L1-04）全 ready · 因为 L1-01 是调度器 · 需调真实的 L1-02~L1-10。
>
> **6 L2**：L2-01 Tick 调度 · L2-02 决策引擎 · L2-03 状态机编排 · L2-04 任务链执行 · L2-05 审计记录 · L2-06 Supervisor 接收。

---

## §0-§10

---

## §1 范围

### 6 L2 · 代码量

| L2 | 职责 | 3-1 行 | 估代码 | 估时 |
|:---:|:---|---:|---:|:---:|
| L2-01 Tick 调度器 | 主循环 · 100ms tick · 全 L1 调度入口 | 2200 | ~4000 | 1.5 天 |
| L2-02 决策引擎 | AST 决策 · mock + history + KB 输入 · 注入候选 | 2100 | ~3800 | 1 天 |
| L2-03 状态机编排器 | 全 project state machine（S1→S7）· 转换发起 | 2000 | ~3600 | 1 天 |
| L2-04 任务链执行器 | tick 调度 → 调 L1-02/03/04 · 发 IC-01/02/03 | 2400 | ~4300 | 1.5 天 |
| L2-05 决策审计记录器 | 每决策发 IC-09 · 可追溯 100% 硬约束 | 2000 | ~3600 | 1 天 |
| L2-06 Supervisor 建议接收器 | 消费 IC-13/14/15 · 主循环降级 mode | 2461 | ~4400 | 1 天 |
| 合计 | 6 | 13161 | ~23700 | 7 天 + 2 天集成 = **9 天** |

### 代码目录

```
app/l1_01/
├── tick_scheduler/        # L2-01
├── decision_engine/       # L2-02
├── state_machine/         # L2-03
├── task_chain_executor/   # L2-04
├── decision_audit/        # L2-05
└── supervisor_receiver/   # L2-06
```

---

## §2 源导读

| 优先级 | 文档 |
|:---:|:---|
| P0 | `2-prd/L1-01主 Agent 决策循环/prd.md` 主循环定义 |
| P0 | `3-1/L1-01/architecture.md` §11 L2 分工 · §5 tick 时序 |
| P0 | `3-1/L1-01/L2-01~06.md` 每份 §3 · §11 |
| P0 | `3-2/L1-01/*.md` G 首批 881 TC |
| P0 | `ic-contracts.md` 全 20 IC（L1-01 经手 10+ IC）|

---

## §3 WP 拆解（7 WP · 9 天）

| WP | L2 | 主题 | 前置 | 估时 | TC |
|:---:|:---:|:---|:---|:---:|:---:|
| M2-WP01 | L2-05 | 决策审计记录器（最先 · 所有决策必审计）| α 真实 | 1 天 | ~52 |
| M2-WP02 | L2-03 | 状态机编排（S1-S7）| δ 真实 IC-01 | 1 天 | ~49 |
| M2-WP03 | L2-02 | 决策引擎（AST + mock + history + KB）| β 真实 IC-06 + WP01 | 1 天 | ~68 |
| M2-WP04 | L2-01 | Tick 调度器（主循环 · 100ms）| WP02 + WP03 | 1.5 天 | ~67 |
| M2-WP05 | L2-04 | 任务链执行器（发 IC-01/02/03/04）| 全 Dev + 主-1 真实 | 1.5 天 | ~71 |
| M2-WP06 | L2-06 | Supervisor 接收器（IC-13/14/15）| ζ 真实 | 1 天 | ~57 |
| M2-WP07 | - | 集成 · tick → 调度 → 决策 → 执行 全链 | WP01-06 | 2 天 | ≥ 15 |

### 主要 WP 细节

**M2-WP01 L2-05 决策审计记录器**（最先 · PM-08 单一事实源）：
- 每决策必发 IC-09（decision_made / action_chosen / ic_dispatched · 含 reason + evidence）
- 可追溯率 100% 硬约束（Goal §4.1）· 任何未审计的决策 raise

**M2-WP02 L2-03 状态机编排器**：
- 全 project state machine：INITIALIZED → PLANNING → TDD_PLANNING → EXECUTING → CLOSING → CLOSED（7 态 · 12 合法转换）
- 发 IC-01 给 L1-02 Stage Gate 控制器
- 幂等（同 transition_id）

**M2-WP03 L2-02 决策引擎**：
- AST 决策（白名单）· input: mock 候选 + history + KB · output: chosen action
- 注入 KB boost（调 IC-06）· 降级无 KB 模式

**M2-WP04 L2-01 Tick 调度器**（心脏）：
- asyncio loop · 100ms tick（默认 · config）
- 每 tick：读当前 project state → 调 decision engine → dispatch action
- tick budget（Deadline 传递）· 每层限时
- panic 硬约束：IC-17 panic → state=PAUSED ≤ 100ms（阻塞式）
- halt 协议：IC-09 halt 后 · tick 拒绝所有 action

**M2-WP05 L2-04 任务链执行器**：
- 接受 decision → 路由到 L1-02/03/04/05 · 发对应 IC
- asyncio.Task 管理（per-project · per-wp）
- 异常捕获（下游 L1 失败 · 走 BF-E-*）

**M2-WP06 L2-06 Supervisor 建议接收器**：
- 消费 IC-13 push_suggestion · 软决策（注入 decision 候选）
- 消费 IC-14 push_rollback_route · 触发主-1 L1-04
- 消费 IC-15 request_hard_halt · **Sync ≤ 100ms 硬约束 · 立即 state=HALTED**

**M2-WP07 集成**：
- tick → decision → state transition → dispatch → audit 全链
- panic 100ms e2e + halt 100ms e2e
- 多 project 并发 tick（V1 仅 1 · V2+ ≥ 10）

---

## §4 依赖图

```
M2-WP01 审计（地基）
  ↓
M2-WP02 状态机 ──┐
M2-WP03 决策引擎 ─┤
                 ├─► M2-WP04 Tick 调度（心脏）
                 ├─► M2-WP05 任务链执行
                 └─► M2-WP06 Supervisor 接收
                               ↓
                          M2-WP07 集成
```

### 跨组依赖

全 Dev 组 + main-1 全 ready（L1-01 是调度全系统的心脏）。

---

## §5-§10（简版 · 复用标杆）

- §5 standup · prefix `M2-WPNN`
- §6 自修正：情形 D 高发（L1-01 跨越 10+ IC 契约）· 主会话主动仲裁
- §7 对外契约：几乎所有 IC 都经 L1-01 · 消费 IC-13/14/15/17 · 发起 IC-01/02/03/04/05/06/09 · P95 全依赖各 L1
- §8 DoD：
  - **可追溯率 100%**（Goal §4.1 硬约束）· 无未审计决策
  - tick 稳定（100ms 无 drift）
  - panic / halt 各 ≤ 100ms 硬约束
  - 881 TC 全绿 · coverage ≥ 85%
- §9 风险：
  - R-M2-01 tick drift · 性能瓶颈 · 优化热路径
  - R-M2-02 多 IC 契约矛盾 · §6 情形 D 高发
- §10 交付：6 L2 · 23700 行 · 15-18 commits

---

*— main-2 · L1-01 主循环 · Execution Plan · v1.0 —*
