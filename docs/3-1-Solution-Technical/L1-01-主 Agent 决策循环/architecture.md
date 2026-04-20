---
doc_id: tech-arch-L1-01-main-agent-loop-v1.0
doc_type: l1-architecture
layer: 3-1-Solution-Technical · L1 顶层
parent_doc:
  - docs/2-prd/L1-01主 Agent 决策循环/prd.md
  - docs/2-prd/L0/scope.md#5.1
  - docs/3-1-Solution-Technical/L0/architecture-overview.md
  - docs/3-1-Solution-Technical/L0/ddd-context-map.md
  - docs/3-1-Solution-Technical/L0/open-source-research.md
  - docs/3-1-Solution-Technical/L0/tech-stack.md
  - docs/3-1-Solution-Technical/L0/sequence-diagrams-index.md
  - docs/3-1-Solution-Technical/projectModel/tech-design.md
  - docs/superpowers/specs/2026-04-20-3-solution-design.md
version: v1.0
status: draft
author: harnessFlow-tech-arch
created_at: 2026-04-20
updated_at: 2026-04-20
traceability:
  prd_anchor: docs/2-prd/L1-01主 Agent 决策循环/prd.md（全部 16 章 · 6 L2 详细）
  scope_anchor: docs/2-prd/L0/scope.md §5.1（L1-01 职责+边界+约束+禁止+义务+IC）
  ddd_bc_anchor: L0/ddd-context-map.md §2.2 BC-01 Agent Decision Loop
  l0_overview_anchor: L0/architecture-overview.md §7（10 L1 component diagram）
  os_anchor: L0/open-source-research.md §2（LangGraph / AutoGen / CrewAI / OpenHands / Devin 5 项）
  project_model: projectModel/tech-design.md（harnessFlowProjectId · 作为本 L1 所有决策/tick/审计的根归属键）
consumer:
  - 3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-01-Tick调度器/tech-design.md（待建）
  - 3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-02-决策引擎/tech-design.md（待建）
  - 3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-03-状态机编排器/tech-design.md（待建）
  - 3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-04-任务链执行器/tech-design.md（待建）
  - 3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-05-决策审计记录器/tech-design.md（待建）
  - 3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-06-Supervisor建议接收器/tech-design.md（待建）
  - 3-2-Solution-TDD/L1-01/（TDD 用例以本 architecture 的时序图与跨 L2 控制流/数据流为骨架）
---

# L1-01 · 主 Agent 决策循环 · 总架构（architecture.md）

> **本文档定位**：本文档是 3-1-Solution-Technical 层级中 **L1-01 主 Agent 决策循环** 的**总架构文档**，也是**这 6 个 L2（Tick 调度器 / 决策引擎 / 状态机编排器 / 任务链执行器 / 决策审计记录器 / Supervisor 建议接收器）的公共骨架**。
>
> **与 2-prd/L1-01 的分工**：2-prd 层的 `prd.md` 回答**产品视角**的"这 6 个 L2 各自职责 / 边界 / 约束 / 禁止 / 义务 / IC 签名字段骨架"；本文档回答**技术视角**的"在 Claude Code Skill + hooks + jsonl + Claude session 这套物理底座上，6 个 L2 怎么串成一个可运行的 Agent loop"——落到 **运行模型**、**控制流 / 数据流**、**时序图**、**对外 IC 承担**、**与各 L2 tech-design 的分工边界** 五件事上。
>
> **与 6 个 L2 tech-design.md 的分工**：本文档是 **L1 粒度的汇总骨架**，给出"6 L2 在同一张图上的位置 + 跨 L2 时序 + 对外 IC 承担"；每 L2 tech-design.md 是**本 L2 的自治实现文档**（具体算法 / 数据结构 / 内部状态机 / 白盒逻辑 / 单元测试骨架），不得与本文档冲突。冲突以本文档为准。
>
> **严格规则**：
> 1. 任何与 2-prd/L1-01 产品 PRD 矛盾的技术细节，以 2-prd 为准；发现 2-prd 有 bug → 必须先反向改 2-prd，再更新本文档。
> 2. 任何 L2 tech-design 与本文档矛盾的"跨 L2 控制流 / 时序 / IC 字段语义"，以本文档为准。
> 3. 任何技术决策必须给出 `Decision → Rationale → Alternatives → Trade-off` 四段式，不允许堆砌选择。
> 4. 本文档不复述 2-prd/prd.md 的产品文字（职责 / 禁止 / 必须清单等），只做技术映射 + 补齐"产品视角未说 but 工程师必须知道"的部分。

---

## 0. 撰写进度

- [x] §1 定位与 2-prd L1-01 映射（哪些产品章节落成本文档的哪些技术章节）
- [x] §2 DDD 映射（BC-01 Agent Decision Loop · 引 L0/ddd-context-map.md）
- [x] §3 L1-01 内部 L2 架构图（Mermaid component · 6 L2 + 对外 IC）
- [x] §4 核心 P0 时序图（Mermaid sequence · tick 端到端 / supervisor BLOCK 消费 / async 回收 / panic / bootstrap）
- [x] §5 主 loop 运行模型（tick = Claude session 内长对话 · 30s 周期 · hooks + 事件触发 · 混合 pacing）
- [x] §6 跨 L2 控制流 / 数据流（IC-L2-01..10 · 事件字段在 L2 间如何流转）
- [x] §7 对外 IC 承担（本 L1 发起 IC-01/04/05/06/07/09/11 · 本 L1 接收 IC-13/14/15/17）
- [x] §8 开源最佳实践调研（LangGraph StateGraph · AutoGen v0.4 topic-based · CrewAI event bus · OpenHands event-stream · Devin planner-executor · 引 L0/open-source-research.md §2）
- [x] §9 与 6 L2 tech-design.md 的分工声明（本 architecture 负责什么 · 每 L2 负责什么）
- [x] §10 性能目标（tick 响应 ≤30s · decision latency / hard_halt 响应 / panic 响应 / 调度吞吐）
- [x] §11 错误处理与降级（halt-on-audit-fail / IC-09 失败 / watchdog 告警 / supervisor silent 监测）
- [x] §12 配置参数清单（从 L2 prd §8.10.7 / §9.10.x / §13.10.5 汇总）
- [x] §13 与现有 harnessFlow.md MVP 蓝图的对比
- [x] 附录 A · 与 L0 系列文档的引用关系
- [x] 附录 B · 术语速查（L1-01 本地）
- [x] 附录 C · 6 L2 tech-design 撰写模板（下游消费）

---

## 1. 定位与 2-prd L1-01 映射

### 1.1 本文档的唯一命题

把 `docs/2-prd/L1-01主 Agent 决策循环/prd.md`（产品级 · v1.0 · 3399 行 · 6 L2 详细 + 对外 IC 映射 + retro 位点）定义的**产品骨架**，一比一翻译成**可执行的技术骨架**——具体交付物是：

1. **1 张 L1-01 component diagram**（6 L2 + 对外 IC · Mermaid · §3）
2. **5 张 P0 核心时序图**（tick 端到端 / BLOCK / async 回收 / panic / bootstrap · Mermaid · §4）
3. **1 套主 loop 运行模型** ——说明 tick 物理上到底是什么（§5）
4. **1 张跨 L2 控制流 / 数据流矩阵**（IC-L2-01 .. 10 · §6）
5. **1 张对外 IC 承担矩阵**（本 L1 发起哪几条 / 接收哪几条 / 承担 L2 是谁 · §7）
6. **1 份开源调研综述**（5 个 > 1k stars 项目 · 本 L1 的借鉴 / 弃用 · §8）
7. **1 份 L2 分工声明**（本 architecture 负责什么 / 每 L2 负责什么 · §9）
8. **1 张性能目标表**（tick 响应 ≤30s 等 · §10）

### 1.2 与 2-prd/L1-01/prd.md 的映射（精确到小节）

| 2-prd/L1-01/prd.md 章节 | 本文档对应章节 | 翻译方式 |
|---|---|---|
| §1 L1-01 范围锚定（引 scope §5.1） | §1（本章）+ §7 对外 IC 承担 | 引用锚定，不复述；§7 表格映射产品 IC ↔ 技术 L2 |
| §2 L2 清单（6 个） | §3 L1-01 内部 L2 架构图 + §9 L2 分工 | 落成 component diagram + 分工表 |
| §3 L2 整体架构图 A（主干控制流 ASCII）| §3 Mermaid component diagram | ASCII → Mermaid；加"对外 IC 进出口" |
| §4 L2 整体架构图 B（横切响应面 ASCII）| §4 核心时序图 5 张 | 4 个响应面 → 5 张时序图 |
| §5 9 条 L2 间业务流程（流 A-I） | §4 时序图 + §6 控制流矩阵 | 9 流里 P0 的 5 条画时序图；剩余 4 条归入 §6 表格 |
| §6 10 条 IC-L2 契约骨架 | §6 跨 L2 控制流 / 数据流 | 10 IC 分类：控制（路由）/ 数据（审计打包）/ 响应（中断）|
| §7 L2 定义模板（9 小节） | §9 L2 分工声明 + 附录 C 下游模板 | 给 L2 tech-design 的撰写模板 |
| §8-§13 L2-01 .. L2-06 详细（9 小节每 L2） | 不在本文档展开 | 落到各 L2 tech-design.md（本文档只画入口 + 出口） |
| §14 对外 IC 映射（被调 4 / 发起 7 / 矩阵图）| §7 对外 IC 承担（本文档镜像重绘） | 原矩阵图扩为"IC × L2 × 发起/接收/路由"三维 |
| §15 retro 位点（11 项） | 本文档不涉 | 归产品 PRD 自身；本文档只做技术实现 |
| §16 L3 合并到各 L2 §X.10 | §9 L2 分工声明 + 附录 C | 落到各 L2 tech-design 内的 §6 内部核心算法 |

### 1.3 与 scope.md §5.1 的映射

| scope §5.1 锚点 | 本文档落实位置 |
|---|---|
| §5.1.1 职责（持续 tick → 决策 → 执行 → 留痕 · HarnessFlow 控制流唯一源） | §5 主 loop 运行模型 + §3 component diagram 的"单一决策源 / 单一审计源"注 |
| §5.1.2 输入/输出（5 类事件 / 输出决策+执行+事件）| §6 跨 L2 控制流 / 数据流 + §7 对外 IC 承担 |
| §5.1.3 边界（只做决策调度 / 6 条 OoS）| §9 L2 分工 + §3 component diagram 边界 |
| §5.1.4 约束（PM-02/10/11 + 4 条硬约束）| §5 运行模型 + §10 性能目标 + §11 错误处理 |
| §5.1.5 🚫 禁止行为（6 条）| §11 错误处理对应拦截点 |
| §5.1.6 ✅ 必须义务（6 条：tick ≤30s / 响应 BLOCK 等）| §10 性能目标 + §11 错误处理 |
| §5.1.7 与其他 L1 交互（9 行）| §7 对外 IC 承担 |
| §8.2 对外 IC 契约（IC-01/04/05/06/07/09/11/13/14/15/17 · 与本 L1 相关的 11 条）| §7 对外 IC 承担矩阵（全量 11 条） |

### 1.4 与 projectModel/tech-design.md 的关系（PM-14 硬约束）

`docs/2-prd/L1-01主 Agent 决策循环/prd.md` 开篇的 **PM-14 项目上下文声明**（第 28 行）硬性要求：**每个 tick / 决策 / state 转换 / 审计事件必须携带 `harnessFlowProjectId`**，由 L1-02 在 S1 启动时创建，本 L1 **只消费不创建**。

本文档的落实点：

| PM-14 要求 | 本 L1 落实 L2 | 本文档章节 |
|---|---|---|
| L2-01 Tick 调度器在每次 tick 入队时强制验证 project_id 非空 | L2-01 | §6 TickTrigger schema · project_id 必填字段 |
| L2-02 决策引擎把 project_id 作为决策上下文根字段 | L2-02 | §6 ContextSnapshot schema · project_id 必填根字段 |
| L2-05 决策审计记录器把 project_id 作为 audit_entry 必填字段 | L2-05 | §6 AuditEntry schema · project_id 必填字段 + §11 未带 project_id 硬拦截 |

**本 L1 不持有 `ProjectAggregate`**（那是 L1-02 / BC-02 的事）；本 L1 只**引用 `harnessFlowProjectId`（值对象）**作为所有内部数据结构的根归属键（Shared Kernel 关系，见 §2.2）。

---

## 2. DDD 映射（BC-01 Agent Decision Loop）

### 2.1 Bounded Context 定位

本 L1 对应的 Bounded Context 在 `L0/ddd-context-map.md §2.2 BC-01 Agent Decision Loop`（位于 ddd-context-map.md 第 128-167 行），已明确：

**BC 名**：`BC-01 · Agent Decision Loop`
**一句话定位**：整个 HarnessFlow 的"**心脏**"与"**大脑**"——持续 tick、做决策、派活给别的 BC、所有动作留痕。
**BC 角色**：**唯一控制源**（All other BCs are consumers or observers of BC-01's commands/events）。

**与其他 BC 的关系**（引自 L0/ddd-context-map.md §2.2 "跨 BC 关系"一节）：

| 对方 BC | 关系模式 | 本 L1 视角 |
|---|---|---|
| BC-09（Resilience & Audit · L1-09） | **Partnership** | 任何决策必经 IC-09 append_event，强耦合同步演进；L2-05 决策审计记录器是 Partnership 的接口实现 |
| BC-02/03/04/05/06/08（L1-02/03/04/05/06/08） | **Customer**（BC-01 是客户，消费它们的能力）| L2-02 发起 IC-01/02/03/04/05/06/11 去调用这些 BC |
| BC-07（Supervision · L1-07） | **反向 Customer**（BC-07 推建议/硬红线/回退路由给 BC-01）| L2-06 是反向 Customer 的接收接口（接 IC-13/14/15） |
| BC-10（UI · L1-10） | **Customer-Supplier** | L2-01 接收 IC-17 user_intervene（panic / resume / authorize）|
| 所有 BC（Shared Kernel） | **Shared Kernel** | 共享 `harnessFlowProjectId` 值对象（PM-14） |

### 2.2 本 L1 内部的聚合根（Aggregate Roots）

引自 `L0/ddd-context-map.md §2.2` BC-01 的主要聚合根表（第 149-155 行），落到 6 L2 的映射：

| 聚合根 | 内部 entity + VO | 一致性边界 | 所在 L2 |
|---|---|---|---|
| **TickContext** | project_id(VO) / trigger(VO) / context_snapshot(entity) / kb_injection(entity) / five_discipline_results(entity[]) | 单 tick 内强一致；tick 结束即持久化为 AuditEntry | **L2-02 决策引擎**（构造者） |
| **DecisionRecord** | decision_id(VO) / tick_id(VO) / rationale(VO) / chosen_action(VO) / alternatives(VO[]) / evidence_links(VO[]) | 一旦生成即不可变（immutable event） | **L2-02 决策引擎**（生产者）+ **L2-05 审计记录器**（持久化者） |
| **AdviceQueue** | advice_id(VO)[] / level(VO) / dimension(VO) / counter(entity) | 单 project 级单例；4 级计数独立 | **L2-06 Supervisor 建议接收器** |
| **TickTrigger + ScheduleQueue + TickRecord** | trigger(VO) / priority(VO) / debounce_bucket(entity) / tick_record(entity) | 单 session 级单例；入队即不可变 | **L2-01 Tick 调度器** |
| **StateTransitionRequest + StateMachineSnapshot** | from_state(VO) / to_state(VO) / allowed_next(table) | 本 session state 单例 | **L2-03 状态机编排器** |
| **TaskChain + MiniStateMachine** | chain_id(VO) / step_list(entity[]) / outcome(VO) | 单 chain 内强一致 | **L2-04 任务链执行器** |
| **AuditEntry + ReverseIndex** | audit_id(VO) / source_ic / hash_chain(entity) | audit 一旦落盘不可变 | **L2-05 决策审计记录器** |

**关键不变量**（Invariants · 引自 BC-01 §2.2）：

1. **I-01 TickContext 不跨 project**：每 TickContext 的 `project_id` 字段不可变；跨 project 的 tick 必须是两个独立 TickContext 实例。
2. **I-02 DecisionRecord immutability**：decision_id 一经生成不可修改（append-only）。
3. **I-03 AdviceQueue 单 project 单例**：同一 `harnessFlowProjectId` 下只有一个 AdviceQueue 实例，4 级计数不跨 project。
4. **I-04 Audit 顺序与决策顺序一致**：`AuditEntry.ts` 单调递增（FIFO），hash_chain 逐条校验。

### 2.3 Domain Service / Application Service

引自 L0/ddd-context-map.md §2.2 BC-01 的 service 表：

| Service 名 | 类型 | 职责 | 所在 L2 |
|---|---|---|---|
| `TickScheduler` | **Application Service** | 编排 4 触发源接入 + 去抖 + 优先级仲裁 + watchdog | L2-01 |
| `DecisionEngine` | **Domain Service**（核心）| 5 纪律拷问 + 决策树分派（无状态；输入 TickContext → 输出 DecisionRecord）| L2-02 |
| `ContextAssembler` | **Domain Service** | 组装 TickContext（6 要素）| L2-02 内部组件 |
| `FiveDisciplineInterrogator` | **Domain Service** | 5 纪律拷问（规划 / 质量 / 拆解 / 检验 / 交付）| L2-02 内部组件 |
| `StateMachineOrchestrator` | **Application Service** | allowed_next 查询 + 转换执行 + entry/exit hook | L2-03 |
| `TaskChainExecutor` | **Application Service** | chain mini state machine + 步调度 + 超时 + 回滚 | L2-04 |
| `DecisionAuditor` | **Application Service** | audit_entry 打包 + hash 计算 + IC-09 原子落盘 + 反查索引 | L2-05 |
| `SupervisorAdviceRouter` | **Application Service** | 4 级路由分派（INFO/SUGG/WARN/BLOCK）| L2-06 |

### 2.4 Repository Interface

本 L1 作为**控制源**，**不直接持有任何持久化聚合**（不 own 任何 Repository）；所有持久化必经 `L1-09 Resilience & Audit BC` 的 IC-09 append_event 接口（由 L2-05 承担）。

**唯一例外**：L2-06 的 `AdviceQueue` 有独立持久化需求（跨 session 恢复时建议队列不可丢），但其物理落盘仍走 L1-09（不自建 Repository）。具体 schema 见 §6 表 6.3。

### 2.5 Domain Events（本 BC 对外发布）

引自 L0/ddd-context-map.md §2.2 BC-01 对外发布表：

| 事件名 | 触发时机 | 订阅方 | Payload |
|---|---|---|---|
| `L1-01:tick_started` | L2-01 派发新 tick 到 L2-02 | L1-07 supervisor / L1-10 UI | `{tick_id, trigger_source, priority, ts, project_id}` |
| `L1-01:decision_made` | L2-02 产出 decision_record | L1-07 / L1-10 / L1-02 / L1-03 / L1-04（按决策类型）| `{decision_id, tick_id, decision_type, reason, evidence, project_id}` |
| `L1-01:tick_completed` | L2-01 tick 闭环 | L1-07 / L1-10 | `{tick_id, duration_ms, result, project_id}` |
| `L1-01:tick_timeout` | L2-01 watchdog 超时 | L1-07 / L1-10 | `{tick_id, duration_ms, project_id}` |
| `L1-01:state_transition` | L2-03 转换成功 | L1-02 / L1-10 | `{from_state, to_state, reason, project_id}` |
| `L1-01:chain_step` | L2-04 步完成 | L1-07 / L1-10 | `{chain_id, step_id, outcome, project_id}` |
| `L1-01:hard_halt` | L2-06 接收 BLOCK → L2-01 暂停 | L1-07 / L1-10 | `{red_line_id, halted_at_tick, project_id}` |
| `L1-01:panic` | L2-01 panic 拦截 | L1-07 / L1-10 | `{panic_at_tick, project_id}` |
| `L1-01:idle_spin` | L2-01 watchdog 连续 N 次 no_op | L1-07 | `{spin_count, project_id}` |
| `L1-01:warn_response` | L2-02 回应 supervisor WARN | L1-07 | `{warn_id, response: accept/reject, reason, project_id}` |
| `L1-01:supervisor_info` | L2-06 接收 INFO → L2-05 审计 | L1-07 | `{message, dimension, project_id}` |

**全部事件共享字段**：`project_id`（PM-14 硬约束）+ `hash`（sha256 链式，防篡改）。

---
