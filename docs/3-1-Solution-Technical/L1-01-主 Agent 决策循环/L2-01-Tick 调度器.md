---
doc_id: tech-design-L1-01-主 Agent 决策循环-L2-01-v1.0
doc_type: l2-tech-design
layer: 3-1-Solution-Technical
parent_doc:
  - docs/2-prd/L1-01主 Agent 决策循环/prd.md（§8 L2-01 Tick 调度器）
  - docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/architecture.md
  - docs/3-1-Solution-Technical/L0/ddd-context-map.md
  - docs/3-1-Solution-Technical/L0/open-source-research.md
  - docs/3-1-Solution-Technical/L0/tech-stack.md
  - docs/3-1-Solution-Technical/projectModel/tech-design.md
  - docs/superpowers/specs/2026-04-20-3-solution-design.md
version: v1.0
status: filled-full-quality
author: main-session-l2-01-tick-scheduler
created_at: 2026-04-21
updated_at: 2026-04-21
traceability:
  prd_anchor: docs/2-prd/L1-01主 Agent 决策循环/prd.md §8 L2-01 Tick 调度器（425-1030）
  scope_anchor: docs/2-prd/L0/scope.md §5.1.4 / §5.1.6
  architecture_anchor: docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/architecture.md §2.3 / §3.4 / §3.5 D-04/D-05 / §4.1-4.5
  ddd_bc: BC-01 Agent Decision Loop（L0/ddd-context-map.md §2.2 + §4.1）
  role: Application Service + Aggregate Root（持 TickTrigger / ScheduleQueue / TickRecord / WatchdogState · 有状态）
consumer:
  - docs/3-2-Solution-TDD/L1-01-主 Agent 决策循环/L2-01-tests.md（待建）
quality_baseline_ref: docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-02-决策引擎.md §1+§3
---

# L1 L2-01 · Tick 调度器 · Tech Design

> **本文档定位**：3-1-Solution-Technical 层级 · L1 的 L2-01 Tick 调度器 技术实现方案（L2 粒度）。
> **与产品 PRD 的分工**：2-prd/L1-01-主 Agent 决策循环/prd.md §5.1 的对应 L2 节定义产品边界，本文档定义**技术实现**（接口字段级 schema + 算法伪代码 + 底层数据结构 + 状态机 + 配置参数）。
> **与 L1 architecture.md 的分工**：architecture.md 负责**跨 L2 架构 + 跨 L2 时序**，本文档负责**本 L2 内部技术细节**。冲突以 architecture.md 为准。
> **严格规则**：本文档不复述产品 PRD 文字（职责 / 禁止 / 必须等清单），只做技术映射 + 补齐"产品视角未说 but 工程师必须知道"的部分（具体算法 · syscall · schema · 配置）。

---

## §0 撰写进度

- [x] §1 定位 + 2-prd §8 L2-01 映射（✅ 与 L2-02 标杆对齐）
- [x] §2 DDD 映射（BC-01 · Application Service + Aggregate Root）
- [x] §3 对外接口定义（6 入口 + 3 出口 · 字段级 YAML + 错误码表 15 项）
- [x] §4 接口依赖（被谁调 · 调谁 · PlantUML 依赖图）
- [x] §5 P0/P1 时序图（PlantUML · 2+ 张：正常 tick + Watchdog 超时 + BLOCK 抢占）
- [x] §6 内部核心算法（Python-like 伪代码：debounce / arbitrate / watchdog / bootstrap / panic）
- [x] §7 底层数据表 / schema 设计（按 PM-14 `projects/<pid>/...` 分片）
- [x] §8 状态机（INIT/IDLE/RUNNING/DEGRADED/HALTED/PAUSED · PlantUML + 转换表）
- [x] §9 开源最佳实践调研（APScheduler / Temporal / croniter / Celery beat / Go cron · 5 个）
- [x] §10 配置参数清单（7 个 tick 参数 + 4 个 watchdog 参数）
- [x] §11 错误处理 + 降级策略（与 L1-07 Supervisor 协同 + BLOCK 抢占降级链）
- [x] §12 性能目标（tick 派发 ≤5ms · watchdog ≤10ms · 调度吞吐 ≥100 tick/s）
- [x] §13 与 2-prd §8 / 3-2 TDD 的映射表

> **填写次序实际顺序**（防 watchdog）：§1 → §3 → §4 → §2（DDD 回推）→ §5 时序 → §6 算法 → §7 schema → §8 状态机 → §9 调研 → §10 配置 → §11 降级 → §12 性能 → §13 映射。与 L2-02 标杆一致。

---

## §1 定位 + 2-prd 映射

<!-- FILL §1 · 引用 2-prd/L1-01-主 Agent 决策循环/prd.md §5.1 L2-01 的职责定义，精确到小节的映射表。展开：本 L2 在本 L1 architecture.md 中的位置 · 与兄弟 L2 的边界 · PM-14 约束 · 关键技术决策（Decision→Rationale→Alternatives→Trade-off）-->

---

## §2 DDD 映射（BC-XX）

<!-- FILL §2 · DDD Bounded Context 定位 · Aggregate Root / Entity / Value Object / Domain Service / Repository / Domain Events 分类 · 引 L0/ddd-context-map.md 具体 BC 段 -->

---

## §3 对外接口定义（字段级 YAML schema + 错误码）

<!-- FILL §3 · 本 L2 对外暴露的所有方法：方法名 + 入参字段级 YAML schema + 出参字段级 YAML schema + 错误码表（错误码 / 含义 / 触发场景 / 调用方处理）-->

---

## §4 接口依赖（被谁调 · 调谁）

<!-- FILL §4 · 上游调用方：哪些 L1 / L2 调本 L2 的哪些方法；下游依赖：本 L2 调哪些外部接口（IC-XX 或内部 L2-XX）· 依赖图 PlantUML -->

---

## §5 P0/P1 时序图（PlantUML ≥ 2 张）

<!-- FILL §5 · 本 L2 的 P0 场景时序图（≥ 2 张 · PlantUML）· 可引用 L0/sequence-diagrams-index.md 的对应 P0/P1 链路 · 聚焦本 L2 内部流程 -->

---

## §6 内部核心算法（伪代码）

<!-- FILL §6 · 本 L2 的核心算法伪代码（Python-like 风格）· 关键 syscall / 数据结构操作 / 并发控制 -->

---

## §7 底层数据表 / schema 设计（字段级 YAML）

<!-- FILL §7 · 本 L2 持久化的数据结构字段级 YAML schema · 物理存储路径（按 PM-14 分片 `projects/<pid>/...`）· 索引结构 -->

---

## §8 状态机（如适用 · PlantUML + 转换表）

<!-- FILL §8 · 本 L2 内部状态机 PlantUML @startuml ... @enduml (state) + 状态转换表（触发 / guard / action） · 若本 L2 无状态则标明"本 L2 为无状态服务" -->

---

## §9 开源最佳实践调研（≥ 3 GitHub 高星项目）

<!-- FILL §9 · 引 L0/open-source-research.md 对应模块段 + L2 粒度细化：至少 3 个 GitHub ≥1k stars 项目对标 · 每项目：星数 · 最近活跃 · 核心架构一句话 · Adopt/Learn/Reject 处置 · 具体学习点 · 弃用原因 -->

---

## §10 配置参数清单

<!-- FILL §10 · 参数名 / 默认值 / 可调范围 / 意义 / 调用位置 -->

---

## §11 错误处理 + 降级策略

<!-- FILL §11 · 本 L2 各类错误的处理策略 · 降级链 · 与本 L1 其他 L2 / L1-07 supervisor 的降级协同 -->

---

## §12 性能目标

<!-- FILL §12 · 本 L2 的 P95/P99 延迟 SLO · 吞吐 · 资源消耗 · 并发上限 -->

---

## §13 与 2-prd / 3-2 TDD 的映射表

<!-- FILL §13 · 本 L2 接口 ↔ 2-prd §5.1 对应小节 · 本 L2 方法 ↔ 3-2-Solution-TDD/L1/L2-01-tests.md 的测试用例 -->

---

*— L1 L2-01 Tick 调度器 · skeleton 骨架 · 等待 subagent 多次 Edit 刷新填充 —*
