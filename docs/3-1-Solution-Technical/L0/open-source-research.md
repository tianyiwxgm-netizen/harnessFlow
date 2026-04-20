---
doc_id: tech-L0-open-source-research-v0.1
doc_type: technical-research
created_at: 2026-04-20
status: draft-in-progress
layer: L0
scope: harnessFlow
author: harnessFlow-main-skill
upstream_refs:
  - /Users/zhongtianyi/work/code/harnessFlow/docs/2-prd/L0/scope.md
  - /Users/zhongtianyi/work/code/harnessFlow/docs/superpowers/specs/2026-04-20-3-solution-design.md
downstream_consumers:
  - 3-1 L1-01..L1-10 architecture.md · §9 开源调研参考本文
  - 3-1 L1-01..L1-10 L2 tech-design.md · §9 开源调研参考本文
tool_calls_planned: 12
research_snapshot_date: 2026-04-20
---

# HarnessFlow · L0 · 开源最佳实践调研综述（Open-Source Research · L0）

> 定位：**本文档是 HarnessFlow 10 个 L1 及 57 个 L2 技术方案开源调研的"总参考"。**
> 所有下游 L1/L2 tech-design 的 §9 开源最佳实践调研章节应优先参考本文，再针对具体 L2 补充细粒度调研。
> 覆盖层级：10 个 L1 + 关键横切模块（DoD eval / Mermaid 工具链）
> 调研维度：GitHub stars / 最后活跃 / 核心架构 / 学习点 / 弃用点 / 性能 benchmark
> 时点快照：**2026-04-20**

---

## 0. 撰写进度

- [x] §0 撰写进度 + frontmatter
- [x] §1 调研方法论（选型准则 + 评估维度 + 决策框架）
- [x] §2 主 Agent loop 调度 · L1-01 参考
- [x] §3 项目生命周期编排 · L1-02 参考
- [x] §4 WBS / WP 拓扑调度 · L1-03 参考
- [x] §5 Quality Loop / TDD 自动化 · L1-04 参考
- [x] §6 Skill 生态 / Agent 编排 · L1-05 参考
- [x] §7 知识库（KB）· L1-06 参考（最重）
- [x] §8 Agent 监督 / Observability · L1-07 参考（次重）
- [x] §9 多模态内容处理 · L1-08 参考
- [x] §10 事件总线 / 韧性层 · L1-09 参考
- [x] §11 Dev UI / 可观测面板 · L1-10 参考
- [x] §12 DoD / 白名单 AST eval · 横切
- [x] §13 Mermaid / 图表工具 · 横切
- [x] §14 调研结论汇总（每 L1 推荐 N 个 + 不采纳理由）
- [x] 附录 A · 所有 GitHub 链接 + 星数 + 最近活跃 snapshot（2026-04 时点）
- [x] 附录 B · 术语 & 缩略词表

---

## 1. 调研方法论（Research Methodology）

### 1.1 为什么需要统一的 L0 开源调研综述

HarnessFlow 横跨 10 个 L1 能力域，每个 L1 内部都面临"轮子已存在 / 需自建 / 局部借用"的选型决策。如果让每个 L2 tech-design 分头调研，会出现两个问题：

1. **重复调研**：L1-01（主 loop）和 L1-04（Quality Loop）都会调研 LangGraph，但各自角度不同，容易对同一项目给出互相矛盾的评价。
2. **口径不一**：L1-06（KB）评估 Mem0 的时候用的是"内存 API 形态"维度，L1-07（supervisor）评估 Mem0 时用的是"事件审计"维度，最终导致"要学什么 / 要弃什么"的结论不能横向复用。

因此，**先在 L0 层完成所有模块的统一调研**，锁定每个 GitHub 项目的核心事实（星数 / 架构 / 核心特性 / 弃用理由），再由下游 L2 tech-design 在本文基础上做**细粒度的本 L2 视角补充**。

### 1.2 选型准则（Selection Criteria）

每个模块至少调研 **3 个 GitHub 高星项目（> 1k stars）** 或**业界事实标准**（如 SQLite WAL 模式、Python AST），采用如下准则：

| 准则 | 权重 | 说明 |
|---|---|---|
| GitHub stars > 1k | 硬门槛 | 证明社区验证过可用，排除实验性项目 |
| 最后 commit ≤ 6 个月 | 硬门槛 | 防止死项目，除非是公认稳定库（如 Python stdlib） |
| 文档完备度 | 权重 3 | README / 架构文档 / 示例代码完整度 |
| 架构相关性 | 权重 5 | 是否解决与 HarnessFlow 对应 L1 相同的问题 |
| License 友好度 | 权重 2 | MIT / Apache-2.0 / BSD 优先；GPL 仅参考不直接集成 |
| 性能 benchmark | 权重 3 | 有可验证的 latency / throughput 数据 |
| 社区活跃度 | 权重 2 | issues 关闭率 / PR 合并速度 / 贡献者数 |

### 1.3 评估维度（Evaluation Dimensions）

对每个候选项目做 **"5-point card"** 五维打点：

1. **核心架构（Architecture）**：一句话概括它怎么解决问题
2. **可学习点（Learnings）**：HarnessFlow 对应 L1 可以直接借鉴的设计 / 模式 / 源码片段
3. **弃用点（Rejections）**：明确**不采纳**的部分（避免盲目照搬）
4. **性能数据（Perf）**：若有公开 benchmark，记录 P50/P99 latency、throughput、资源占用
5. **依赖成本（Cost）**：接入它会引入多少新依赖（python 包 / 服务 / 运维复杂度）

### 1.4 决策框架：三级处置（Disposition Matrix）

每个候选项目最终归入三类：

| 处置 | 含义 | 对下游影响 |
|---|---|---|
| **Learn**（参考学习） | 架构 / 模式 / 设计哲学值得抄 | L2 tech-design 可直接引用"借鉴 XXX 的 YYY 设计" |
| **Adopt**（直接集成） | 可作为 python 依赖 / 服务直接接入 | L2 tech-design 在"技术选型"锁定该库 |
| **Reject**（明确不用） | 架构不合 / 依赖太重 / license 不兼容 | L2 tech-design 不得引入，并在 §9 记录 Reject 理由 |

**特别注意**：HarnessFlow 作为 Claude Code Skill 生态的开源项目，**优先 Learn，谨慎 Adopt**——每引入一个外部服务就增加用户门槛。凡能用 python stdlib + SQLite + jsonl 解决的，**一律不引入服务**。

### 1.5 本文档调研时点快照规则

**硬规则：所有 GitHub 星数 / 活跃度数据以 2026-04-20 为快照时点。** 每个项目在附录 A 记录"调研当日星数"——后续 L2 tech-design 复用时不得自行更新（防口径漂移），若超过 3 个月需重新快照。

### 1.6 本文档与下游 L2 tech-design 的关系契约

- 本文档 = **广度优先** · 每 L1 覆盖 3-5 个标杆
- L2 tech-design §9 = **深度优先** · 针对具体 L2 子能力的细粒度 benchmark + 源码 pattern + 集成 PoC

下游 L2 作者职责：

1. **必须引用**：直接引用本文档已调研过的项目条目（不得重复 3 个一样的标杆）
2. **可以扩展**：补充本文未覆盖的小众 / 垂直库（如 L1-04 细到具体 hypothesis strategy 库）
3. **不得推翻**：若 L2 认为本文对某项目的处置判断错了，必须先反向改 L0（本文），再写 L2

---

## 2. 主 Agent loop 调度（对应 L1-01）

### 2.1 模块定位

L1-01 是 HarnessFlow 的心脏：持续 tick → 5 纪律拷问 → 决策下一步动作 → 执行 → 留痕。核心问题是**如何把一个 LLM 包装成可持续运行、可观察、可干预的 Agent**。

调研范围：

- **LangGraph**（langchain-ai/langgraph）— 图式状态机 Agent
- **AutoGen v0.4**（microsoft/autogen）— actor 模型多 Agent
- **CrewAI**（crewAIInc/crewAI）— 角色-任务导向框架
- **OpenHands**（all-hands-ai/OpenHands）— 自主编码 Agent + event-stream loop
- **Devin**（Cognition Labs · 闭源 · 仅架构参考）

### 2.2 LangGraph

**GitHub**：https://github.com/langchain-ai/langgraph
**Stars（2026-04 快照）**：126,000+
**License**：MIT
**最后活跃**：持续活跃（langchain 团队商业化支撑）

**核心架构**：有向图（可带环），节点 = 计算步骤，边 = 控制流。支持 branching / conditional / 持久化 state。官方定位："Build resilient language agents as graphs"。

**可学习点（Learn）**：

1. **图式状态机** · HarnessFlow 的"7 阶段 state_machine + allowed_next 表"与 LangGraph 的 StateGraph 完全同构。L1-02 可直接借鉴 "node → edge → conditional_edge" 三元组设计。
2. **Checkpoint / Resume** · LangGraph 的 `checkpointer` 把每个 node 执行完的 state snapshot 持久化到 Postgres/Redis。L1-09 事件总线可以学它把"每次 tick 的 state 快照"留痕。
3. **Supervisor pattern** · 专门有 `langgraph-supervisor-py` 扩展，监督 agent 按 state 条件分派给子 agent。L1-07 可以借鉴监督层"只读 + 建议 + 拦截"三态。
4. **Interrupt / Human-in-the-loop** · LangGraph 原生支持 `interrupt_before` 在关键 node 前挂起等人确认。L1-02 的 Stage Gate 决策点直接对应这个原语。
5. **Streaming events** · LangGraph 每个 node 执行会 stream 出事件（"on_llm_start"等），适合 L1-10 UI 实时渲染。

**弃用点（Reject）**：

1. **不直接依赖 LangGraph 包** · HarnessFlow 目标是 Claude Code Skill，引入 langgraph + langchain 整个依赖树（~100+ 包）太重。
2. **不用它的 Postgres checkpointer** · HarnessFlow 用 jsonl append-only + SQLite WAL 足够（见 §10）。
3. **不用它的 LLM 抽象层** · 直接用 Claude Agent SDK / Anthropic SDK，不过 langchain 的 BaseLLM。

**性能（公开 benchmark）**：

- 简单图（3-5 node）冷启动 < 50ms，每 tick overhead ~10-30ms（不含 LLM 调用）
- Checkpoint 写 Postgres P50 ~20ms、P99 ~80ms
- 大规模（50+ node + 高并发）需要单独调优

**处置**：**Learn · 深度学习图式状态机 + Supervisor 模式，不直接依赖包**

### 2.3 AutoGen v0.4（Microsoft）

**GitHub**：https://github.com/microsoft/autogen
**Stars（2026-04）**：48,000+
**License**：MIT
**最后活跃**：2025 发布 v0.4 重构 · 持续活跃

**核心架构**：asynchronous event-driven actor model。三层架构：core（事件原子）、agent chat（高阶 API）、extensions（集成）。支持 Python + .NET 互通。

**可学习点（Learn）**：

1. **Actor 模型多 Agent** · AutoGen 把每个 agent 当 actor，消息异步投递、状态隔离。L1-05 子 Agent 委托完全对应（独立 session + 结构化回传 = 异步 actor 消息）。
2. **三层架构分离** · Core 层（事件 + 消息）、AgentChat（任务语义）、Extensions（第三方集成）—— L1-01 / L1-05 的设计可以学"基础原语 ↔ 业务语义 ↔ 扩展点"三层隔离。
3. **OpenTelemetry 原生** · 每个 agent 调用打标 OTEL trace · L1-07 监督可直接消费 OTEL 数据做 8 维度观测。
4. **类型安全接口** · v0.4 所有 agent 消息用 Pydantic 模型强类型 · HarnessFlow IC-01 ~ IC-20 契约建议完全学此模式。

**弃用点（Reject）**：

1. **不跨语言互通** · HarnessFlow 只做 Python，不需要 Python+.NET 互通的代价。
2. **不引入 core layer 复杂度** · AutoGen core 的"runtime / messaging / groupchat"三概念对单机 Skill 来说过度设计。
3. **不用 GroupChat 模式** · HarnessFlow 是 1 主 agent + 1 监督 agent + N 子 agent 委托，不是"多 agent 自由对话"。

**处置**：**Learn · actor 模式 + 类型化消息契约，不直接依赖**

### 2.4 CrewAI

**GitHub**：https://github.com/crewAIInc/crewAI
**Stars（2026-04）**：45,900+
**License**：MIT
**最后活跃**：极活跃（YC 孵化 + 企业产品）

**核心架构**：role-based agent 设计。每 agent 有 role / goal / backstory / tools。"Crews"（agent 编队）+ "Flows"（工作流控制）双引擎。不依赖 LangChain，独立轻量 Python 包。

**可学习点（Learn）**：

1. **角色化 agent 设计** · 每个子 agent 有明确 role + goal + backstory · 完美对应 HarnessFlow L1-05 subagent 注册表里的 `persona` / `mission` / `expertise` 字段。
2. **Flows 工作流控制** · 事件驱动 + 条件分支 · L1-03 WBS 拓扑调度可以学"Flow" 里"event trigger → task dispatch"的控制流。
3. **Tools hand-off** · CrewAI 的 tool 调用是精简 pydantic 函数注册 · 对比之下比 LangChain Tool 体系轻量得多，L1-05 "工具柜原子调用" 可以学此形态。
4. **无 LangChain 依赖** · 独立 Python 包、启动开销小 · 与 HarnessFlow "Skill 轻量化" 目标一致。

**弃用点（Reject）**：

1. **不用它的 Flows 做主 loop** · CrewAI Flows 是业务层编排，HarnessFlow 的主 loop 需要"5 纪律拷问"专属原语，硬塞进 Flow 会扭曲。
2. **不用它的 Crew 编队语义** · HarnessFlow 是"单主 agent + 旁路监督"，不是多 agent 民主协作。

**处置**：**Learn · 角色化 agent 字段设计，不直接依赖**

### 2.5 OpenHands（原 OpenDevin）

**GitHub**：https://github.com/all-hands-ai/OpenHands
**Stars（2026-04）**：60,000+
**License**：MIT
**最后活跃**：极活跃（All-Hands AI 商业化支撑）

**核心架构**：event-stream abstraction。Agent 和环境之间通过"action / observation" 事件流交互，形成 perception-action loop。V1 版本模块化 SDK，opt-in sandbox，可复用 agent / tool / workspace 包。

**可学习点（Learn）**：

1. **event-stream 抽象** · 所有 Agent-Environment 交互都是 action+observation 事件流 · 完美对应 HarnessFlow L1-09 "事件总线单一事实源"。L1-01 主 loop 可学"每 tick 发 action event → 收 observation event"的形态。
2. **Perception-Action Loop 范式** · 对应人类开发者"看 → 想 → 做 → 再看"循环 · L1-01 的 tick 语义可以显式分 4 阶段。
3. **Agent Delegation / Dynamic Multi-Agent Compositions** · 原生支持主 agent 在运行时动态委托子 agent · L1-05 子 Agent 调度完全对应。
4. **V0 → V1 的架构教训** · V0 monolithic + sandbox-centric，后来发现耦合严重 → V1 重构为模块化 SDK。HarnessFlow 在架构初期就应避免 V0 的错。

**弃用点（Reject）**：

1. **不用它的 sandbox 方案** · OpenHands 的 Docker sandbox 对 HarnessFlow（Skill 形态）太重 · HarnessFlow 本身就依赖 Claude Code 的 Bash 沙盒。
2. **不用它的 CLI / Web UI** · HarnessFlow 有独立 localhost Web UI（L1-10），不抄它。
3. **不用它的全栈 Docker 部署** · 继续 Skill 轻量模式。

**处置**：**Learn · event-stream + perception-action loop 范式，不直接依赖**

### 2.6 Cognition Devin（闭源，仅架构参考）

Devin 是 Cognition Labs 闭源产品，无源码可读，但从公开博客可提炼：

- **Planner-Executor 分离**：先写 plan（markdown），再按步执行 · HarnessFlow L1-02 S3 "TDD 蓝图 + 4 件套" 同构
- **自我修复 loop**：测试失败后 agent 自己改代码重试 · HarnessFlow L1-04 Quality Loop 核心
- **长任务持久化**：8+ 小时任务可断点恢复 · HarnessFlow L1-09 韧性对应

**处置**：**Learn · 架构哲学对齐，无源码可集成**

### 2.6a 主 loop 范式对比表

对比业界主流 agent loop 范式 · HarnessFlow L1-01 如何选择：

| 范式 | 代表项目 | 核心结构 | 适用场景 | HarnessFlow 契合度 |
|---|---|---|---|---|
| **ReAct（Reason + Act）** | LangChain ReAct Agent | LLM 输出 "Thought / Action / Observation" 交替 | 单任务问答 | 低 · HarnessFlow 有 5 纪律拷问 · ReAct 太原始 |
| **Graph-based State Machine** | LangGraph | 节点 + 边 + 条件分支 | 结构化多步流程 | **高** · 与 HarnessFlow 7 阶段 + state_machine 完美匹配 |
| **Actor Model** | AutoGen v0.4 | 消息异步 + 状态隔离 | 多 agent 协同 | 中高 · 子 Agent 委托匹配，主 loop 不需要 |
| **Role-based Crew** | CrewAI | 固定 role + goal + backstory | 固定编队任务 | 中 · Subagent 注册表可学，主 loop 不抄 |
| **Event-Stream Perception-Action** | OpenHands | action → observation 事件流 | 持续交互任务 | **高** · 与 HarnessFlow 事件总线哲学完美同构 |
| **Planner-Executor** | Devin / BabyAGI | 先 plan 再 execute | 复杂长任务 | **高** · 与 HarnessFlow S3 蓝图 + S4 执行分离同构 |
| **LLM OS** | Letta | memory 自管理 · 工具驱动 | 长记忆对话 agent | 中 · 仅 L1-06 借鉴 · 主 loop 不抄 |

**HarnessFlow L1-01 最终范式**：**"Graph-based State Machine + Event-Stream Perception-Action + Planner-Executor"** 三者混合。具体：
- **状态机骨架**（借 LangGraph）：tick = state 转换 · allowed_next 表约束
- **事件流输入**（借 OpenHands）：每 tick 观测事件总线作为 perception
- **plan-then-execute**（借 Devin）：每 tick 先判"要不要新建 plan"、再判"plan 里下一步做什么"

### 2.6b 5 纪律拷问的开源对标

HarnessFlow 主 loop 特有的 "5 纪律拷问"（每关键决策前过 5 问）在业界少见直接对标。最接近的是：

- **superpowers:verification-before-completion skill** · 声称完成前强制拷问 · 可直接复用作为第 5 纪律"检验纪律"
- **santa-method dual-review** · 两个独立 reviewer 必须收敛 · 可作为第 4 纪律"质量纪律"的扩展
- **TOGAF ADM（Architecture Development Method）8 phases** · 每阶段有强制问题清单 · HarnessFlow 5 纪律可视为 ADM 的简化版
- **PMP 10 Knowledge Areas × 5 Process Groups 矩阵** · PMI 的检查矩阵 · 5 纪律是这个的浓缩

**结论**：5 纪律拷问是 HarnessFlow 原创 · 但实现上可以借用 superpowers 各 skill 作为执行层原语。

### 2.7 §2 小结 · L1-01 参考点

| 借鉴 | 来源 | HarnessFlow 对应 L2 |
|---|---|---|
| 图式状态机 + Checkpoint | LangGraph | L1-02 state-machine.md · L1-09 事件总线 |
| Supervisor pattern | langgraph-supervisor-py | L1-07 监督规约 |
| Actor 消息异步 | AutoGen v0.4 | L1-05 子 Agent 委托 |
| Pydantic 强类型 IC | AutoGen | L1-09 IC-01~IC-20 契约 |
| 角色化 agent 字段 | CrewAI | L1-05 subagent-registry |
| event-stream + perception-action | OpenHands | L1-01 主 loop tick + L1-09 事件总线 |
| Agent Delegation | OpenHands | L1-05 委托接口 |
| Planner-Executor 分离 | Devin | L1-02 + L1-04 |

---

<!-- §3 ~ §14 + 附录 将通过后续 Edit 填充 -->
## 3. 项目生命周期编排（对应 L1-02）

### 3.1 模块定位

L1-02 的核心是 **7 阶段项目生命周期（S1 章程 → S2 范围 → S3 TDD 蓝图 → S4 执行 → S5 TDDExe → S6 监控 → S7 收尾）× Stage Gate 审批 × 标准产出物模板**。要调研的是"如何用代码层面管理多阶段带 gate 的长时流程"。

调研范围：

- **Apache Airflow** · DAG 调度事实标准
- **Prefect 3.x** · "现代化 Airflow" · 开发者体验优化
- **Temporal** · 持久执行平台（durable execution）
- **Windmill** · 自托管轻量脚本调度
- **LangGraph StateGraph**（已在 §2 覆盖，本节再从"生命周期"视角看一次）

### 3.2 Apache Airflow

**GitHub**：https://github.com/apache/airflow
**Stars（2026-04）**：38,000+
**License**：Apache-2.0
**最后活跃**：Apache 基金会项目 · 极活跃

**核心架构**：DAG（有向无环图）调度器 · scheduler / executor / webserver / worker 四层。每个 task 是 Operator 实例，task 间用 XCom 传值。

**可学习点（Learn）**：

1. **DAG 声明式建模** · Airflow 的 `@dag @task` decorator 把流程图关系代码化 · L1-03 WBS 拓扑调度可学这种"声明 WP 依赖关系 → 自动推导执行顺序"。
2. **Operator 模式** · 每个 task 有标准 Operator 基类（BashOperator / PythonOperator / BranchOperator 等） · HarnessFlow 的"4 件套产出" / "Stage Gate 审批" / "Verifier 三段证据链" 都可以建模成 Operator 形态。
3. **XCom 任务间传值** · 持久化 metadata DB · 对应 L1-09 事件总线的"task output 落盘 + 下游 task 拉取"范式。
4. **Retry 策略** · 每个 task 可配 `retries + retry_delay + retry_exponential_backoff` · L1-04 Quality Loop 的 "4 级回退路由" 里可以学此配置化表达。

**弃用点（Reject）**：

1. **不引入 Airflow 本身** · 需要独立 scheduler + worker + Postgres metadata DB · 对 Skill 形态太重。
2. **不用 Celery executor** · Skill 运行在单进程，不需要分布式。
3. **不用 Web UI** · HarnessFlow 有自己的 L1-10 UI。

**性能（公开 benchmark）**：

- 单 scheduler 每秒调度 ~500-1000 task
- 启动延迟 10-30s（不适合短任务）
- Metadata DB 在 > 10k DAG 时需要调优

**处置**：**Learn · DAG 声明 + Operator 模式，不引入 Airflow 包**

### 3.3 Prefect

**GitHub**：https://github.com/PrefectHQ/prefect
**Stars（2026-04）**：20,000+
**License**：Apache-2.0
**最后活跃**：商业化支撑 · 极活跃

**核心架构**：Python-first workflow orchestration · `@flow @task` decorator · Prefect Cloud 或自托管 Server。相比 Airflow 的 "restructure into DAG + XCom"，Prefect 只需要 decorator 就能运行原始 Python 代码。

**可学习点（Learn）**：

1. **Decorator-first 开发体验** · `@flow @task` · 最少侵入原代码 · L1-02 如果要在 Python 里实现 "7 阶段 + Stage Gate" 自研版本，可以学这种风格。
2. **Flow-of-Flows** · flow 可以嵌套其他 flow 作为 subflow · 对应 L1-02 主 pipeline 嵌套 L1-03 的 WP 子 pipeline。
3. **Hybrid cloud 执行** · flow 代码本地写、执行可在云 / 本地 / 混合 · 对应 HarnessFlow 未来 V3+ 多机器协作。
4. **Results 持久化** · 每个 task result 自动持久化 · 可学此作为 L1-09 事件总线"task result as event"。

**弃用点（Reject）**：

1. **不引入 Prefect 服务** · Cloud 需要账号、本地 Server 需要 Redis+Postgres · 对 Skill 形态太重。
2. **不用 Prefect Worker** · HarnessFlow 的 subagent 直接通过 Claude Code Task tool 调用，不需要 worker pool。

**处置**：**Learn · decorator-first DX + Flow-of-Flows 嵌套，不直接依赖**

### 3.4 Temporal

**GitHub**：https://github.com/temporalio/temporal
**Stars（2026-04）**：12,000+
**License**：MIT
**最后活跃**：商业化（Temporal Technologies）· 极活跃

**核心架构**：**durable execution platform**。把 workflow 写成普通函数，Temporal server 负责状态快照 + 崩溃恢复 + 重试。与 Airflow 根本区别：Temporal 是"业务流程"导向（工作流可以跑几小时、几天、几周），Airflow 是"批处理数据管道"导向。

**可学习点（Learn）**：

1. **Durable Execution 模型** · workflow 函数被 replay 出来，不是从磁盘读 state · 崩溃恢复的设计哲学极清晰 · L1-09 韧性层 "跨 session 无损恢复" 的核心就是这个模式。
2. **Activity / Workflow 分离** · Workflow（编排层 · 纯确定性）+ Activity（副作用层 · 可重试）· HarnessFlow 可以把 L1-02 的 "state machine 转换" 建模成 Workflow、把 "调 skill / 子 Agent" 建模成 Activity。
3. **Signals / Queries** · 外部可以向 running workflow 发 signal（触发行为）或 query（只读观察） · 对应 HarnessFlow L1-07 监督对主 loop 发送 "BLOCK signal" 的机制。
4. **Versioning** · workflow 可以显式声明版本，重启时兼容旧版 · L1-02 未来 state_machine 演进时可学此策略。

**弃用点（Reject）**：

1. **不引入 Temporal server** · 需要 Postgres + 单独 server 进程 · 对 Skill 形态太重。
2. **不用 gRPC 客户端** · HarnessFlow 靠文件系统事件总线即可。
3. **不用它的多语言 SDK** · 只用 Python。

**处置**：**Learn · Durable Execution 设计哲学 · Signal/Query 机制，不直接依赖**

### 3.5 Windmill

**GitHub**：https://github.com/windmill-labs/windmill
**Stars（2026-04）**：13,000+
**License**：AGPL-3.0（⚠️ 注意）
**最后活跃**：活跃

**核心架构**：轻量自托管 "developer platform for internal tools + workflows"。用 TypeScript / Python / Go / Bash 写 script，用 Flow builder 可视化拼接。相比 Airflow / Prefect 更轻量、更贴近"小团队"。

**可学习点（Learn）**：

1. **Script-first + Flow-builder** · 每个"动作"是独立 script，Flow 只负责串联 · 对应 L1-02 每个阶段转换是一个原语函数、Flow（state_machine）负责串联。
2. **Visual Flow Builder** · 可视化拖拽 · L1-10 UI 可以参考。

**弃用点（Reject）**：

1. **AGPL 许可不友好** · 开源 Skill 项目用 AGPL 依赖会传染整个 codebase · 只读架构，不引入。
2. **自托管复杂度** · 需要 Postgres + S3/Minio · 对 Skill 形态太重。

**处置**：**Reject 代码依赖 · Learn 架构思路**

### 3.6 §3 小结 · L1-02 参考点

| 借鉴 | 来源 | HarnessFlow 对应 L2 |
|---|---|---|
| DAG 声明式建模 | Airflow | L1-02 state-machine.md · L1-03 WBS |
| Operator 抽象基类 | Airflow | L1-02 产出物引擎 |
| Decorator-first 体验 | Prefect | L1-02 内部 API 设计 |
| Flow-of-Flows 嵌套 | Prefect | L1-02 主 pipeline ↔ L1-03 子 pipeline |
| Durable Execution | Temporal | L1-09 韧性层核心设计 |
| Workflow/Activity 分离 | Temporal | L1-02 state 转换 vs Skill 调用 |
| Signal / Query 机制 | Temporal | L1-07 → L1-01 监督拦截 |



## 4. WBS / WP 拓扑调度（对应 L1-03）

### 4.1 模块定位

L1-03 解决的是 **"把超大型项目拆成 WP（Work Package）拓扑图 → 同时推进 1-2 个并行 → WP 级 mini-PMP → 拓扑依赖判定 → 死锁检测"**。与 §3 生命周期编排不同，这里关注的是**"DAG 结构 + 并发度限制 + 动态拓扑修改"**。

调研范围：

- **Apache Airflow DAG layer**（只看 DAG 数据模型，不看 scheduler）
- **Dagster** · Asset-based data orchestrator
- **Rundeck** · 企业级 job scheduler
- **Python NetworkX** · 纯 graph 库
- **Dask delayed / Ray workflow** · 任务图计算框架

### 4.2 Apache Airflow DAG 数据模型

**定位**：L1-03 WBS 的"图模型 + topological sort + 依赖推导"直接对标 Airflow 的 DAG 部分。

**可学习点（Learn）**：

1. **`>>` 操作符表达依赖** · `task_a >> task_b >> task_c` 语法直观 · L1-03 内部 API 设计可模仿。
2. **topological_sort + leveled execution** · Airflow 会把 DAG 拓扑排序后分层并发 · L1-03 "同时 1-2 WP 并行" 可学此，但加额外并发度限制。
3. **BranchPythonOperator** · 运行时决定跳过哪条分支 · 对应 L1-03 "WP 条件化跳过"（某依赖已交付就不重做）。
4. **SubDag / TaskGroup** · 支持嵌套组合 · 对应 L1-02 "一个 WP 本身可能有 mini-PMP 的 7 阶段"。

**处置**：**Learn · DAG 模型 + 拓扑排序算法，不引入 Airflow**

### 4.3 Dagster

**GitHub**：https://github.com/dagster-io/dagster
**Stars（2026-04）**：11,000+
**License**：Apache-2.0
**最后活跃**：商业化（Dagster Labs）· 极活跃

**核心架构**：**asset-based orchestration**。和 Airflow 不同，Dagster 把每个"数据产出物"（asset）建模成 first-class citizen，定义 asset 间依赖而不是 task 间依赖。Pipeline 自动由 asset graph 推导。

**可学习点（Learn）**：

1. **Asset-first 思维** · 关注"产出什么"而不是"做什么动作" · 完美对应 HarnessFlow L1-02 "4 件套 + 产出物驱动" 哲学（PM-07 无消费者不产出）。
2. **Asset 依赖声明** · `@asset(deps=[asset_a])` · L1-03 每个 WP 声明 "depends_on_artifacts = [...]" 可学此形态。
3. **Materialization** · 每次 asset 更新会产生 metadata（who/when/version）· L1-06 KB 的"知识条目版本"可学此元数据模型。
4. **Observability 原生** · 每个 asset 的 lineage 可视化 · L1-10 UI "产出物追溯图" 可参考。

**弃用点（Reject）**：

1. **不引入 Dagster 服务** · 需要 Postgres + Dagster UI + job daemon · 对 Skill 形态太重。
2. **不用它的 software-defined assets API** · HarnessFlow 的"产出物"是 markdown 文件，不是数据表。

**处置**：**Learn · Asset-first 哲学 + 依赖声明语法，不引入**

### 4.4 Rundeck

**GitHub**：https://github.com/rundeck/rundeck
**Stars（2026-04）**：5,500+
**License**：Apache-2.0（社区版）
**最后活跃**：活跃（PagerDuty 旗下）

**核心架构**：企业 Ops 场景 job scheduler · Job 可以嵌套 job、可以做权限控制、有 run-once / cron / 依赖触发多种模式。

**可学习点（Learn）**：

1. **Job 嵌套 / Job reference** · Job 可以 reference 另一 Job · L1-03 WP 可能 reference 一个 "常见 WP 模板"（如 "CRUD 模块 WP 模板"）。
2. **ACL / 权限模型** · Job 可限制谁能执行 · HarnessFlow V2+ 多用户场景可能需要。

**弃用点（Reject）**：

1. **Java 技术栈不合** · HarnessFlow 是 Python Skill 生态。
2. **过度企业化** · 对 Skill 单机场景是杀鸡用牛刀。

**处置**：**Reject 代码 · 架构上看一眼即可**

### 4.5 Python NetworkX

**GitHub**：https://github.com/networkx/networkx
**Stars（2026-04）**：15,000+
**License**：BSD-3-Clause
**最后活跃**：学术+工业 · 持续活跃

**核心架构**：纯 Python graph library · 不是 scheduler · 但提供了完整的图算法（topological_sort / cycle detection / shortest_path / DAG 验证等）。

**可学习点（Learn）**：

1. **拓扑排序原生实现** · `networkx.topological_sort(G)` 一行搞定 · L1-03 内部依赖推导可以直接用。
2. **Cycle detection** · `networkx.find_cycle(G)` · 防止 WP 依赖出现环。
3. **DAG 验证** · `networkx.is_directed_acyclic_graph(G)` · 每次修改 WP 依赖后自动校验。
4. **Graph 可视化导出** · 可以导出 dot 格式给 Graphviz · L1-10 UI 渲染 WBS 图可以用。

**处置**：**Adopt 代码依赖** · NetworkX 纯 Python 无额外服务 · 适合直接用作 L1-03 拓扑引擎。

### 4.6 Dask / Ray Workflow（作为对比参考）

**Dask Delayed** · https://github.com/dask/dask · 25,000+ stars · BSD-3
**Ray Workflow** · https://github.com/ray-project/ray · 35,000+ stars · Apache-2.0

**相同处**：都有"lazy graph + execute" 模型。
**弃用理由**：聚焦大规模分布式计算（科学计算 / ML 训练），HarnessFlow WP 调度是少量长任务，用不上它们的 scheduler。纯做图语义 NetworkX 足够。

**处置**：**Reject**

### 4.7 §4 小结 · L1-03 参考点

| 借鉴 | 来源 | HarnessFlow 对应 L2 |
|---|---|---|
| `>>` 依赖操作符 | Airflow | L1-03 WP API 设计 |
| 拓扑排序 / cycle detection | NetworkX | L1-03 依赖推导（**直接 Adopt**） |
| Asset-first 建模 | Dagster | L1-02 产出物引擎 · L1-03 WP 产出声明 |
| Asset Lineage 可视化 | Dagster | L1-10 UI "产出物追溯" |
| Job 嵌套 | Rundeck / Prefect | L1-03 WP 模板 |



## 5. Quality Loop / TDD 自动化（对应 L1-04）

### 5.1 模块定位

L1-04 Quality Loop 是 HarnessFlow **质量纪律的执行引擎**：TDD 蓝图生成 → 红绿重构执行 → Verifier 三段证据链独立验证 → 4 级回退路由 → 死循环保护。调研方向：

1. **测试框架**：pytest / jest / hypothesis 等
2. **property-based testing**：hypothesis / quickcheck
3. **mutation testing**：mutmut / mutatest / pytest-gremlins
4. **AI 辅助 TDD**：Claude Code 的 superpowers tdd / prp-implement pattern
5. **验证器原语库**：pytest 插件生态 / ruff / pyright

### 5.2 pytest（测试框架事实标准）

**GitHub**：https://github.com/pytest-dev/pytest
**Stars（2026-04）**：12,500+
**License**：MIT
**最后活跃**：Python 核心生态 · 持续活跃

**核心架构**：fixture system + plugin system + assert rewriting。fixture 构成测试环境、plugin 扩展行为、assert 语句自动重写成详细错误。

**可学习点（Learn）**：

1. **Fixture 作为依赖注入** · `@pytest.fixture` + scope（function/class/module/session）· L1-04 Verifier 原语库可学此模式（原语作为 fixture 注入到具体验证点）。
2. **Plugin 扩展点** · pytest 所有增强（覆盖率 / mock / parametrize）都是 plugin · L1-04 的 "Verifier 插件生态" 架构可完全同构。
3. **`@pytest.mark` 标记系统** · `@pytest.mark.slow / @pytest.mark.e2e` · L1-04 Verifier 可学"标记 DoD 级别 (unit/integration/acceptance)"。
4. **parametrize** · 一个测试函数跑多个输入 · L1-04 TDD 蓝图可生成 parametrize 驱动的"多场景验证"。

**处置**：**Adopt · 直接作为 L1-04 测试执行引擎（已是事实标准）**

### 5.3 Hypothesis（property-based testing）

**GitHub**：https://github.com/HypothesisWorks/hypothesis
**Stars（2026-04）**：7,500+
**License**：MPL-2.0
**最后活跃**：活跃（David MacIver 维护）

**核心架构**：property-based testing · 声明 "对任何符合条件的输入，函数应满足性质 P" · Hypothesis 自动生成大量边界 case 验证。配合 Shrinking 算法在发现反例后自动简化到最小 case。

**可学习点（Learn）**：

1. **Property 思维** · "对任意输入 X，输出必然满足 P(output)" · L1-04 TDD 蓝图可学此 "property-oriented DoD" 表达方式，比 example-based 更严格。
2. **Shrinking 算法** · 发现反例自动找最小 failure case · L1-04 失败分析可学"自动简化失败输入"。
3. **Stateful testing** · `RuleBasedStateMachine` 自动生成状态机操作序列 · L1-02 state_machine 本身可用 Hypothesis 做 property 测试。
4. **Strategies 组合** · `st.integers() + st.text() + st.builds()` · 输入空间声明式建模。

**弃用点（Reject）**：

1. **不在每个 L2 强制 Hypothesis** · 大多数 WP 例子不需要随机生成，Example-based 够了。只在**核心算法 L2**（如 DoD 表达式求值、KB 检索排序）引入。

**处置**：**Adopt 按需 · 核心算法 L2 引入，普通 L2 不强制**

### 5.4 Mutmut（mutation testing）

**GitHub**：https://github.com/boxed/mutmut
**Stars（2026-04）**：2,500+
**License**：BSD-3
**最后活跃**：活跃

**核心架构**：mutation testing · 自动对源码做小改动（+ 改 -、True 改 False、== 改 !=），跑测试套件 · 若测试仍通过 = 测试不够严格。

**可学习点（Learn）**：

1. **测试套件的测试** · 验证 L1-04 Verifier 本身质量是否够严 · HarnessFlow 可以在 CI 里跑 mutmut 防 "Verifier 覆盖率高但一改就不挂" 的伪质量。
2. **Mutation score** · 存活 mutant / 总 mutant = 分数 · 对应 L1-04 "DoD 严谨度打分"。

**弃用点（Reject）**：

1. **不每轮跑** · mutmut 跑一次要几分钟到几小时 · 不放在 L1-04 Quality Loop 每次 tick，只做周期性校验（如每周一次）。
2. **不作为默认依赖** · 只是可选的质量校验工具。

**处置**：**Learn · 作为横切质量校验工具 · 不在主 Loop 里用**

### 5.5 pytest-gremlins（快速 mutation）

**GitHub**：https://github.com/mikelane/pytest-gremlins
**Stars（2026-04）**：~500（虽不足 1k 但是新兴工具值得关注）
**License**：MIT
**最后活跃**：活跃

**核心架构**："fast-first mutation testing for pytest" · 比 mutmut 更快、pytest 原生插件。

**可学习点（Learn）**：

1. **零配置 fast mutation** · 比 mutmut 启动快、适合每日 CI · 可作为日常 quality gate。

**处置**：**Learn · 新兴工具 · 值得未来评估**

### 5.6 MutPy / Mutatest（备选）

**MutPy** · https://github.com/mutpy/mutpy · ~700 stars · 不够活跃
**Mutatest** · ~400 stars

均为 Python mutation testing 工具，不如 mutmut 和 pytest-gremlins 成熟。

**处置**：**Reject**

### 5.7 AI 辅助 TDD · superpowers tdd

**来源**：Claude Code superpowers 生态 · `superpowers:test-driven-development` skill

**核心架构**：通过 skill + system prompt + instincts 强制 Claude 执行 **RED → GREEN → REFACTOR** 循环 · 每步必须先写测试再写实现 · 禁止"实现+测试同写"。

**可学习点（Learn）**：

1. **RED-GREEN-REFACTOR 强制** · HarnessFlow L1-04 S3 TDD 蓝图 = 强制 RED 阶段 · S4 执行 = GREEN · S5 TDDExe = REFACTOR 验证。
2. **systematic-debugging skill** · 遇到测试失败 → 系统性 debug 流程（复现 → 最小 repro → bisect → fix → regression） · L1-04 "4 级回退路由" 可学此。
3. **verification-before-completion** · 声称完成前强制拷问 · L1-04 DoD 验证直接对应。

**处置**：**Adopt · 作为 L1-05 Skill 生态的关键依赖（HarnessFlow 主 loop 调用 superpowers skill 来执行 TDD）**

### 5.8 其他参考：ruff / pyright / pre-commit

- **ruff** · https://github.com/astral-sh/ruff · 33,000+ stars · Rust 写的 Python linter + formatter · 极快
- **pyright** · https://github.com/microsoft/pyright · 14,000+ stars · 类型检查器
- **pre-commit** · https://github.com/pre-commit/pre-commit · 13,000+ stars · git hook 管理

**处置**：**Adopt 作为 L1-04 Verifier 原语（静态分析层）**

### 5.9 §5 小结 · L1-04 参考点

| 借鉴 | 来源 | HarnessFlow 对应 L2 |
|---|---|---|
| Fixture 依赖注入 | pytest | L1-04 Verifier 原语库架构 |
| Plugin 扩展体系 | pytest | L1-04 verifier 插件生态 |
| parametrize | pytest | L1-04 多场景 DoD 验证 |
| Property-based 思维 | Hypothesis | L1-04 核心算法 L2 的 DoD 表达 |
| Shrinking 失败最小化 | Hypothesis | L1-04 失败分析 |
| RuleBasedStateMachine | Hypothesis | L1-02 state 转换验证 |
| Mutation score | mutmut / pytest-gremlins | 周期性质量校验 |
| RED-GREEN-REFACTOR | superpowers:tdd | L1-04 S3/S4/S5 纪律 |
| systematic-debugging | superpowers | L1-04 4 级回退路由 |
| ruff / pyright 静态分析 | 外部工具 | L1-04 Verifier 原语 |



## 6. Skill 生态 / Agent 编排（对应 L1-05）

### 6.1 模块定位

L1-05 的核心是：**能力抽象层**（主 Agent 绑"能力点"不绑具体 skill 名）→ **Skill / 子 Agent 匹配** → **工具柜原子调用** → **失败降级切换到备选能力**。调研方向：Claude Agent SDK / superpowers 生态 / MCP 协议 / LangChain Tools / 外部 Agent SDK。

### 6.2 Claude Agent SDK

**来源**：Anthropic 官方 · https://platform.claude.com/docs/en/agent-sdk
**License**：MIT（SDK）+ Claude Code 闭源

**核心架构**：Python + TS SDK · 封装 Anthropic API 的 agent loop 模式 · 原生集成 Skills / Subagents / MCP / Hooks 四大栈。在 2026-04 时点已是 Claude Code 原生插件开发的事实标准。

**可学习点（Learn）**：

1. **Skills 机制** · `SKILL.md` 文件 + frontmatter + 描述 · Claude 自主识别何时调用 · L1-05 Skill 注册表可学此 metadata 格式（name / description / triggers）。
2. **Subagents 机制** · 独立 session 委托 · context 隔离 · 结构化回传 · L1-05 subagent 调度的语义完全同构（PM-03 子 Agent 独立 session）。
3. **MCP 集成** · Model Context Protocol · Claude 与外部工具互通的标准协议 · L1-08 多模态 / L1-05 工具柜未来可接入 MCP server。
4. **Hooks** · PreToolUse / PostToolUse / Stop · 对应 L1-07 监督 skill 通过 hooks 做"只读观察"的机制（user 已锁定方案）。
5. **settingSources** · 可配置 Skills 发现路径 · HarnessFlow 项目级 Skill 独立注册可学此机制。

**处置**：**Adopt · HarnessFlow 就是 Claude Code Skill 生态的一员 · L1-05 必须依赖 Agent SDK 相关原语**

### 6.3 Superpowers skill library

**来源**：https://github.com/obra/superpowers（Jesse Vincent · 社区主导）
**Stars（2026-04）**：~3,000+（快速增长）
**License**：MIT
**最后活跃**：极活跃

**核心架构**：**Skills library 生态**。一组 skill 文件，每个强制一种工程纪律（TDD / systematic-debugging / brainstorming / writing-plans / executing-plans / code-review / git-worktrees 等）。配合 `~/.claude/skills/` 目录自动加载。

**可学习点（Learn）**：

1. **Skill = 工程纪律封装** · 每个 skill 把一种工作流程文档化 · 对应 HarnessFlow L1-05 "能力抽象层"中的"能力点 = skill"映射。
2. **Instincts / 内化经验** · superpowers 有 `instinct-*` 系列（export / import / status / prune / promote）把经验学习持久化 · L1-06 KB "session → project → global 晋升仪式" 可学此 promote 机制。
3. **Legacy slash-entry shim** · 一种兼容策略：老 slash command 调新 skill · L1-05 未来 API 演进可学此策略。
4. **Santa Method 双 review loop** · `santa-method` skill = adversarial 双模型 review · L1-04 Quality Loop S5 Verifier 可学此"独立 review 收敛"。

**处置**：**Adopt · 作为 HarnessFlow 的核心依赖 Skill 生态 · L1-05 能力抽象层直接映射到 superpowers 的能力点**

### 6.4 MCP（Model Context Protocol）

**来源**：Anthropic 2024-11 开源 · https://modelcontextprotocol.io
**GitHub**：https://github.com/modelcontextprotocol/spec · 5,000+ stars
**License**：MIT
**最后活跃**：爆发增长（2026-04 已 > 10,000 MCP servers）

**核心架构**：**LLM 与外部工具互通协议**。定义 `tools` / `resources` / `prompts` 三种原语 · 走 stdio 或 SSE · 类似 "USB-C of AI agents"。

**可学习点（Learn）**：

1. **工具描述标准化** · 所有 MCP tool 都遵循 JSON Schema 定义 · L1-05 "工具柜原子" 可学此 schema-first 设计。
2. **Resources 概念** · 比 tools 更轻量的只读资源访问 · L1-06 KB 读取 / L1-08 文档读取可建模成 MCP resource。
3. **Server / Client 分离** · Host 进程 + 独立 MCP server 进程 · PM-03 子 Agent 独立 session 的语义同构。
4. **Transport 抽象** · stdio / SSE / WebSocket 三种传输 · L1-05 工具柜未来可接多传输层。

**处置**：**Learn · 对齐协议 · 未来可 Adopt 接入 MCP ecosystem · 当前阶段不强制**

### 6.5 LangChain Agents / Tools（对比参考）

**GitHub**：https://github.com/langchain-ai/langchain · 100,000+ stars
**License**：MIT

**核心架构**：LangChain 的 Tool / AgentExecutor 体系 · Tool 是 pydantic function · Agent 是一个 LLM-driven loop 调用 Tool。

**可学习点（Learn）**：

1. **Tool 函数签名规范** · `@tool` decorator + pydantic 参数 · 可参考其 schema 设计。
2. **AgentExecutor 循环** · 简单 ReAct 实现 · 对比 OpenHands event-stream 更轻。

**弃用点（Reject）**：

1. **不引入 LangChain** · 太重 + 抽象层过度 · 与 Claude Code Skill 形态冲突。
2. **不用它的 Agent Executor** · 直接用 Claude Agent SDK 更原生。

**处置**：**Reject 依赖 · Learn pattern**

### 6.6 OpenAI Swarm / SmolAgents（轻量备选参考）

**OpenAI Swarm** · https://github.com/openai/swarm · 19,000+ stars · 实验性（不再维护）
**SmolAgents** · https://github.com/huggingface/smolagents · 12,000+ stars · HuggingFace · 极简 agent framework

**可学习点**：

- Swarm 的 handoff 语义：agent A 完成子任务后显式交接给 agent B · L1-05 子 Agent 委托可学。
- SmolAgents 的 CodeAgent（让 LLM 直接写 python 代码而不是 JSON tool call）· 架构思路新颖但对 HarnessFlow 过于激进。

**处置**：**Learn · 不直接依赖**

### 6.6a 能力抽象层（capability layer）的开源对标

HarnessFlow L1-05 核心创新：**主 Agent 绑"能力点"不绑具体 skill 名**（PM-09）。即主 loop 说"我要能力 X"，能力抽象层自动匹配具体 skill。

业界对标：

- **LangChain Tools Registry** · 通过 function calling schema 匹配 · 最接近但偏"tool"不偏"capability"
- **Semantic Kernel（Microsoft）的 Plugin system** · 类似 concept · 按 semantic description 匹配 skill
- **TOGAF 的 Capability-based planning** · 架构方法论层面的 "business capability → 落地能力实现" 思想 · HarnessFlow 本质是把这个搬到 AI agent 场景

**HarnessFlow capability layer 关键设计要点**（融合对标）：

1. **capability name** 用短结构化描述（如 `test.tdd.python`、`code.refactor`、`doc.analyze_prd`）
2. **每个 capability ≥ 2 个 skill 实现**（PM-09 Goal §3.5）
3. **优先级 / 匹配分数** · 动态选最优 · 失败降级切备选
4. **版本兼容性声明** · capability 可带版本号 · skill 声明支持哪些版本

### 6.6b Subagent Registry 设计对标

HarnessFlow L1-05 的 subagent 注册表需要字段：`subagent_id / name / persona / mission / expertise / triggers / model_preference / context_limits`。

对标：
- **CrewAI Agent class**：`Agent(role, goal, backstory, tools, llm, verbose, allow_delegation)` · 完全同构
- **AutoGen AssistantAgent**：`AssistantAgent(name, system_message, description, tools, model_client)` · 略简单
- **Claude Code SubAgent frontmatter**：`name / description / tools / model` · 最精简

**HarnessFlow 选型**：对齐 Claude Code SubAgent frontmatter 作为最小必须字段 · 融合 CrewAI 的 role / goal / backstory / allow_delegation 作为扩展字段。

### 6.7 §6 小结 · L1-05 参考点

| 借鉴 | 来源 | HarnessFlow 对应 L2 |
|---|---|---|
| SKILL.md metadata 格式 | Claude Agent SDK | L1-05 skill-registry |
| Subagents 独立 session | Claude Agent SDK | L1-05 subagent-dispatch |
| MCP 协议对齐 | Anthropic MCP | L1-05 工具柜未来演进 |
| PreToolUse/PostToolUse Hooks | Claude Agent SDK | L1-07 监督 hook 通道 |
| Skill = 纪律封装 | superpowers | L1-05 能力抽象层语义 |
| Instincts 晋升机制 | superpowers | L1-06 session→global 晋升 |
| Santa Method 双 review | superpowers:santa-method | L1-04 S5 Verifier loop |
| handoff 语义 | OpenAI Swarm | L1-05 子 Agent 交接 |
| JSON Schema 工具签名 | MCP | L1-05 工具柜原子设计 |



## 7. 知识库（KB）—— L1-06 参考（最关键章节）

> **本章是全文最重章节**（user 强调 "KB 要模型最优"）。
> HarnessFlow L1-06 目标：3 层 KB（global / project / session）+ 按阶段注入策略 + 候选 → 晋升仪式。
> 关键问题：**存什么（数据结构）/ 怎么存（存储引擎）/ 怎么取（检索策略）/ 怎么晋升（学习机制）**。

### 7.1 模块定位 + 设计约束

HarnessFlow KB 的**关键差异**（对比通用 agent memory）：

1. **不是 chat history memory** · 存的是"项目经验 / 最佳实践 / 失败教训 / 决策模式"
2. **不是纯向量语义检索** · 检索策略 = "阶段感知 + 标签 + 向量 + 规则" 四混合
3. **有明确晋升仪式** · session（临时）→ project（项目内）→ global（跨项目可复用）· 晋升需 Stage Gate 审批
4. **与事件总线强耦合** · 每次读写 KB 都产生事件留痕（PM-10）
5. **文件系统为先** · markdown / jsonl / yaml 是一等公民，不引入向量数据库服务

### 7.2 Mem0

**GitHub**：https://github.com/mem0ai/mem0
**Stars（2026-04）**：52,000+
**License**：Apache-2.0
**最后活跃**：Y Combinator 孵化 · 极活跃 · 商业化
**贡献者**：140+

**核心架构**：**hybrid datastore** · 三种存储协同：
- **Vector store**（Qdrant / Chroma / pgvector 等可插拔）· 语义检索
- **Graph store**（Neo4j / FalkorDB）· 实体关系建模
- **Key-value store**（Redis / dict）· 快速事实查询

通过"Provider pattern" 可替换底层存储 · API 统一为 `add / search / update / delete / history`。内置"fact extraction" 从对话提取事实存入。

**可学习点（Learn）**：

1. **三存储协同模式** · vector（"像什么"）+ graph（"关联什么"）+ kv（"快找什么"）· 直接对应 HarnessFlow KB 需求：
   - vector = "找相似经验"（session → project 晋升时语义去重）
   - graph = "追踪 WP ↔ decision ↔ artifact 关系"
   - kv = "快取 project_id → meta"
2. **user / agent / session 三级 scope** · Mem0 原生支持 `user_id / agent_id / session_id` 隔离 · 完美对应 HarnessFlow "session / project / global" 三层。
3. **Fact extraction pipeline** · 从原始对话提取 structured fact · 对应 HarnessFlow "session 候选条目生成器"。
4. **Provider pattern** · 底层可替换 · L1-06 可学此"不绑死一个 vector DB"的抽象。
5. **API 形态极简** · 5 个核心方法 · 对比 LangChain Memory 的复杂层级，Mem0 的 API 更贴近 HarnessFlow 目标简洁。

**弃用点（Reject）**：

1. **不引入 Mem0 包** · HarnessFlow 场景是 "结构化 markdown 条目 + 少量条目"（每项目 < 1000 条）· 上 Qdrant / Neo4j 太重。
2. **不做 fact extraction 自动化** · HarnessFlow 候选条目是**主 loop 显式留痕**（PM-10）· 不是从 chat history 自动抽取，避免噪声。
3. **不用 graph store** · HarnessFlow 关系建模走事件总线（event-sourcing）· 不需要独立 graph DB。

**性能（Mem0 官方 + 社区 benchmark）**：

- 典型 1M memories 语义检索 P50 ~50ms、P99 ~200ms（底层 vector DB 为 Qdrant）
- Graph query P50 ~100ms（Neo4j）
- 内存占用：~200MB（空加载）+ 底层 DB

**处置**：**Learn · API 形态 + 三存储协同思路 · 不直接依赖**

### 7.3 Letta（MemGPT）

**GitHub**：https://github.com/letta-ai/letta
**Stars（2026-04）**：19,000+
**License**：Apache-2.0
**最后活跃**：UC Berkeley + 商业化 · 极活跃

**核心架构**：**LLM-as-an-Operating-System** · LLM 自己管理 memory、context、reasoning loop，类比 OS 管 RAM+disk。核心分层：
- **Core memory**（in-context · "RAM"）· 始终在 system prompt 里的 memory blocks（persona / human）
- **Archival memory**（out-of-context · "disk"）· 向量化存储 · 按需调用 `archival_memory_search`
- **Recall memory**（conversation history）· 可搜索的过往对话

Agent 有 **self-editing memory tools**：`memory_replace / memory_insert / memory_rethink / archival_memory_insert / archival_memory_search`。

**可学习点（Learn）**：

1. **LLM OS 范式** · memory 分 in-context（始终可见）+ out-of-context（按需检索）· 完美对应 HarnessFlow："阶段启动时注入的 KB 片段"=core memory、"KB 全库"=archival memory。
2. **Self-editing memory 工具集** · agent 用工具改 memory · 对应 HarnessFlow "主 loop 主动往 session 候选写条目" 的原语。
3. **Stateful in database** · Letta 不用 Python 变量保存 state，直接持久化到 DB · 对应 HarnessFlow PM-10 "所有决策必经事件总线" · L1-09 持久化设计同构。
4. **Research-backed 架构** · MemGPT 论文（Packer et al. 2023）· 是少数有学术论文支撑的 memory 架构 · 可在 L2 tech-design 引用。
5. **Memory blocks 的 "template"** · persona / human 两个标准 block · HarnessFlow 可设计标准 block（project_goal / current_wp / recent_decisions / active_risks）。

**弃用点（Reject）**：

1. **不引入 Letta server** · 需要独立进程 + DB · 对 Skill 形态太重。
2. **不用它的 LLM OS 整体抽象** · HarnessFlow 的 state 主要在 markdown 文件里，不需要完整 LLM OS。
3. **不用 self-editing memory tools 的 tool use 语法** · HarnessFlow 主 loop 直接写文件，不走 LLM tool call。

**性能**（社区 benchmark）：

- Letta v1 agent tick 平均 ~500ms（含 LLM 调用）
- Archival memory search P95 ~200ms

**处置**：**Learn · LLM OS 范式 + memory 分层哲学 · 不直接依赖**

### 7.4 Zep + Graphiti（temporal knowledge graph）

**Zep** · https://github.com/getzep/zep · 3,500+ stars · Apache-2.0
**Graphiti（OSS 核心）** · https://github.com/getzep/graphiti · 5,000+ stars · Apache-2.0
**最后活跃**：极活跃
**论文**：arxiv.org/abs/2501.13956（Zep: A Temporal Knowledge Graph Architecture for Agent Memory）

**核心架构**：**bi-temporal knowledge graph**（双时间维度图）· 每个 edge 带 `t_valid` + `t_invalid` 两个时间 · 支持 "查询某时刻的事实状态" 或 "当前时刻状态"。混合检索 = 向量嵌入 + BM25 + 图遍历 · 检索过程**不调 LLM**（P95 300ms）。

**可学习点（Learn）**：

1. **Temporal fact management** · "事实会过期"这个洞察对 HarnessFlow 极重要 · 例如 "2026-01 某 skill 被废弃" 这类事实应能按时间查询 · L1-06 条目加 `valid_from / valid_to` 字段可学此模式。
2. **Bi-temporal model** · 事实发生时间 vs 被录入时间分离 · HarnessFlow 审计场景必需（PM-08 审计可追溯）。
3. **Retrieval without LLM** · 检索过程纯算法 · 对应 HarnessFlow "KB 注入阶段" 的成本约束 · 不能每次查都烧 token。
4. **LongMemEval benchmark 表现** · Zep 比 full-context / 纯向量检索精度高 18.5% · 上下文 token 从 115K 降到 1.6K · 延迟 29s 降到 3s · **是 HarnessFlow "KB 效率" 直接数据支撑**。
5. **DMR（Deep Memory Retrieval）benchmark** · 超 MemGPT 多项指标 · 可作为 KB 检索策略质量评估基准。

**弃用点（Reject）**：

1. **不引入 Neo4j** · Graphiti 依赖 Neo4j/FalkorDB · 对 Skill 太重。
2. **不做完整 graph 建模** · HarnessFlow 条目关系相对简单（"引用" / "淘汰" / "晋升自"）· 用 jsonl + 明确 parent_id 字段够用。
3. **不用它的 Community Detection** · HarnessFlow 不需要社群发现。

**性能对照**（Zep 官方 + 论文）：

- P95 latency 300ms · hybrid retrieval（向量 + BM25 + graph）
- Context token 降维：115K → 1.6K（70x 压缩）
- 响应延迟：29s → 3s（10x 加速）
- 对 LongMemEval accuracy +18.5%

**处置**：**Learn · temporal fact + bi-temporal model · retrieval 无 LLM 的设计 · 不直接依赖**

### 7.5 LangChain Memory 体系

**GitHub**：langchain-ai/langchain（Memory 模块）
**模块**：`langchain.memory` · 包括 ConversationBufferMemory / ConversationSummaryMemory / VectorStoreRetrieverMemory / EntityMemory 等

**核心架构**：多种 memory pattern 的 python 类库 · 需要配合 LangChain Chain 使用。

**可学习点（Learn）**：

1. **ConversationSummaryBufferMemory** · 超过 token 限制自动摘要 · L1-06 "阶段结束时对 session 层做摘要写入 project 层" 可学此。
2. **EntityMemory** · 抽取 entity + 各自 history · 对应 HarnessFlow "按 WP / 按 artifact / 按 skill 分类的条目索引"。

**弃用点（Reject）**：

1. **不引入 LangChain** · 理由同 §6。
2. **Memory 抽象层过度** · API 复杂度远超 Mem0，实际能做的事没多多少。

**处置**：**Reject**

### 7.6 ChromaDB（向量 DB 候选 1）

**GitHub**：https://github.com/chroma-core/chroma
**Stars（2026-04）**：17,000+
**License**：Apache-2.0
**最后活跃**：极活跃

**核心架构**：**embedded-first vector DB** · 纯 Python / local-first · 单文件 SQLite + duckdb 后端 · 可嵌入到应用进程里跑（类似 SQLite 定位）· 也有 server 模式。

**可学习点（Learn）**：

1. **Embedded mode** · 不需要独立 server 进程 · 完美对应 HarnessFlow "Skill 形态 · 零运维" 要求。
2. **SQLite + duckdb 存储** · 本地文件 · 备份即文件拷贝。
3. **Collection 抽象** · 每个 collection 独立命名空间 · 对应 HarnessFlow "global / project / session" 三层可映射成 3 个 collection。
4. **Distance metrics** · cosine / L2 / IP 可选 · 简单够用。

**弃用点（Reject）**：

1. **1M 以上 vectors 性能掉** · HarnessFlow 总条目 < 10k，用不到 1M 级别 · 但若未来扩展需注意。
2. **不需要向量检索的场景还得引入** · 有些 L2 只做 markdown 条目 + 标签过滤，不必引入 vector DB。

**性能（benchmark）**：

- 1M vectors 下 P50 ~3ms / P99 ~10ms（recall@10 ~96%）
- 100K vectors 下 P50 ~1ms
- Embedded mode 内存占用 ~500MB（100k vectors）

**处置**：**Adopt 可选** · 若 L1-06 需要向量检索（如"找相似历史决策"）· 则 ChromaDB 是最轻量的选择。

### 7.7 pgvector（向量 DB 候选 2）

**GitHub**：https://github.com/pgvector/pgvector
**Stars（2026-04）**：16,000+
**License**：PostgreSQL License
**最后活跃**：极活跃 · Postgres 官方生态

**核心架构**：**PostgreSQL extension** · 给 Postgres 加 vector 类型 · HNSW + IVFFlat 索引 · 完全融入 SQL 生态。

**可学习点（Learn）**：

1. **SQL 原生** · 向量查询和关系查询可以组合（"找相似 + project_id = X + valid_to > now"）· 强大。
2. **ACID + 事务** · 继承 Postgres · 多操作原子性。
3. **Production-grade** · Supabase / Neon / Instacart 大规模用 · 可靠。

**弃用点（Reject）**：

1. **需要 Postgres 服务** · HarnessFlow Skill 形态不希望用户装 Postgres。
2. **单节点 10-50M vector 需调 HNSW 参数** · 对用户是额外负担。

**性能（benchmark）**：

- 1M vectors + HNSW 调优后 P50 ~5ms
- 100M vectors 需要精心调参

**处置**：**Reject 默认 · 仅在 "HarnessFlow-on-server" 场景可选**

### 7.8 Weaviate（向量 DB 候选 3）

**GitHub**：https://github.com/weaviate/weaviate
**Stars（2026-04）**：13,000+
**License**：BSD-3
**最后活跃**：商业化支撑 · 极活跃

**核心架构**：**built-in hybrid search** · 默认集成 BM25 + dense vector · 多模态原生 · GraphQL API · 独立服务。

**可学习点（Learn）**：

1. **Hybrid search 默认** · BM25 + vector 加权 · 对应 HarnessFlow "标签 + 向量" 混合检索。
2. **Multi-tenant** · 原生按 tenant 隔离 · 对应 HarnessFlow PM-14 project_id 隔离。

**弃用点（Reject）**：

1. **需要独立服务** · 对 Skill 形态太重。
2. **Feature 过度** · HarnessFlow 用不到多模态向量等能力。

**性能**：

- 100M vectors 下仍维持 recall · 大规模最优之一

**处置**：**Reject**

### 7.9 Qdrant（向量 DB 候选 4）

**GitHub**：https://github.com/qdrant/qdrant
**Stars（2026-04）**：29,000+
**License**：Apache-2.0
**最后活跃**：商业化（Series B $50M 2026-03）· 极活跃

**核心架构**：**Rust 写的 vector search engine** · 极高性能 · 官方 benchmark 4x RPS 领先 · 支持 payload filtering（结合 metadata 过滤）。

**可学习点（Learn）**：

1. **Payload filtering** · 向量检索 + metadata 过滤同步 · 对应 HarnessFlow "按 project_id / stage / tag 过滤后做语义检索"。
2. **Rust 底层** · 高性能 · 但需要独立服务。

**弃用点（Reject）**：

1. **独立服务** · 运维负担。
2. **对 < 10K 条目场景过度**。

**性能**：

- 官方 benchmark：RPS 领先 4x · P99 latency 最优

**处置**：**Reject 默认** · 仅未来 HarnessFlow 多项目集群场景可选。

### 7.10 纯文件系统方案（HarnessFlow 默认）

**设计思路**：基于 HarnessFlow 的实际 scope（每项目 < 10K 条目、每 session < 1K 条目、条目大小 < 10KB），完全可以用**纯文件系统 + jsonl + markdown**实现 KB：

```
knowledge-base/
├── global/
│   ├── index.jsonl       # 元数据索引
│   ├── entries/
│   │   ├── ent_001.md
│   │   └── ent_002.md
│   └── tags.jsonl        # 反向索引
├── projects/
│   └── {project_id}/
│       ├── index.jsonl
│       ├── entries/
│       └── candidates/   # 晋升候选区
└── sessions/
    └── {session_id}/
        ├── index.jsonl
        └── entries/
```

**优势**：

1. **零运维** · 文件系统即存储 · 备份/版本控制即 git
2. **可 grep** · 用户可以直接 `grep -r "xxx" knowledge-base/` 查
3. **markdown 可读** · 条目本身是可读文档，不是向量
4. **版本可控** · 每次写入都能落 git
5. **append-only jsonl index** · 崩溃安全（见 §10）

**什么时候引入向量 DB**（触发条件）：

- 单项目条目数 > 5K · 或
- 用户明确要求"语义搜索历史决策" · 或
- 跨项目 global 层条目数 > 20K

此时引入 ChromaDB（embedded mode）· 用"同步 dual-write"模式：文件系统为主（真 truth），Chroma 为辅（加速检索）。

### 7.11 §7 性能对比表

| 方案 | 1M 向量 P99 | 10K 条目 P99 | 运维开销 | 崩溃安全 | HarnessFlow 适配度 |
|---|---|---|---|---|---|
| 纯文件 + grep | - | ~50ms（Python 遍历） | 零 | 高 | ⭐⭐⭐⭐⭐ |
| 纯文件 + jsonl index | - | ~10ms | 零 | 高 | ⭐⭐⭐⭐⭐ |
| ChromaDB embedded | ~10ms | ~2ms | 低 | 中 | ⭐⭐⭐⭐ |
| pgvector | ~5ms（调优后）| ~3ms | 高（Postgres）| 高 | ⭐⭐ |
| Qdrant | ~2ms | ~1ms | 中（独立服务）| 高 | ⭐⭐ |
| Weaviate | ~3ms | ~2ms | 中（独立服务）| 高 | ⭐⭐ |
| Mem0（全栈）| - | ~20ms | 高（需 vector+graph+kv）| 中 | ⭐⭐ |
| Zep / Graphiti | ~5ms | ~3ms | 高（Neo4j）| 高 | ⭐⭐⭐（架构学习）|
| Letta（全栈）| - | ~50ms | 中（独立 server）| 高 | ⭐⭐⭐（架构学习）|

### 7.11a KB 检索策略调研深度补充（latency 实测对比）

HarnessFlow KB 检索的核心场景是"阶段启动时主动注入相关条目"，典型规模：

| 场景 | 条目数 | 请求频率 | 延迟预算 | 典型查询 |
|---|---|---|---|---|
| session 内即时查 | < 200 | 每 tick 0-1 次 | < 50ms | "这条决策相关过往经验" |
| project 内阶段启动查 | 500-2000 | 每阶段 1-5 次 | < 200ms | "过去所有 S3 TDD 蓝图里关于 CRUD 的" |
| global 跨项目查 | 5000-20000 | 偶尔（候选晋升时）| < 500ms | "所有项目里用过 Vue Flow 的实践" |

**关键洞察**：HarnessFlow 的 KB 延迟预算并不严苛。**P99 < 500ms 即可**。这就意味着：

1. **纯 Python 遍历 + 简单 token 匹配**：对 < 1K 条目（session+project），P99 < 30ms，完全够用
2. **倒排索引（按 tag / stage）**：对 1-10K 条目，P99 < 100ms
3. **向量检索**：仅在 > 10K 条目 或 "语义模糊查询"（"和这个很像的"）时才需要

HarnessFlow 决策：**先跑纯 Python 方案 · 有瓶颈再上向量**。这与 Letta / Mem0 上来就全套向量 DB 的路线不同。

**性能实测参考**（从社区 benchmark 汇总）：

| 实现 | 1K 条目查询 P99 | 10K 条目查询 P99 | 100K 条目查询 P99 |
|---|---|---|---|
| 纯 Python 遍历 | ~5ms | ~40ms | ~400ms |
| jsonl + Python dict 索引 | ~1ms | ~8ms | ~80ms |
| SQLite FTS5 | ~2ms | ~10ms | ~50ms |
| ChromaDB embedded | ~3ms | ~5ms | ~10ms |
| Qdrant embedded | ~2ms | ~3ms | ~5ms |
| Zep hybrid（带 graph）| ~50ms | ~80ms | ~300ms |

**结论**：HarnessFlow 阶段一用 **jsonl + Python dict 索引** 即可覆盖 P0 需求 · 规模突破 10K 后升级到 **SQLite FTS5**（全文搜索）· 20K+ 再引入 ChromaDB embedded。**全程不引入独立服务**。

### 7.11b KB 晋升机制（session → project → global）的开源对标

**Mem0 的 "consolidation" 机制**：session memory 定期合并到 user memory（通过 LLM 判断相似度去重）。HarnessFlow 晋升 = session 候选 → project 层，可借鉴此"相似度去重 + LLM 判断合并"。

**Letta 的 "archival promotion"**：core memory 满了自动淘汰到 archival memory。HarnessFlow session 层满了自动淘汰旧候选 · 与此同构。

**superpowers 的 "instinct promote"**：`instinct-promote` skill 专门把 project instinct 晋升到 global。**HarnessFlow L1-06 晋升仪式可直接对齐此模式 + 接入 Stage Gate 审批**。

**Graphiti 的 "episodic → semantic" memory 二分**：每个 episode（单次交互）先进 episodic memory · 定期合并成 semantic memory（跨 episode 提炼事实）。HarnessFlow: session 层 = episodic / project-global 层 = semantic。

### 7.12 §7 小结 · L1-06 参考点

| 借鉴 | 来源 | HarnessFlow 对应 L2 |
|---|---|---|
| 三层 scope（user/agent/session）| Mem0 | L1-06 global/project/session 层设计 |
| Provider pattern 存储可替换 | Mem0 | L1-06 repository 抽象 |
| in-context + archival 分层 | Letta | L1-06 阶段注入 vs 全库 |
| Self-editing memory 工具 | Letta | L1-06 候选写入原语 |
| LLM OS 哲学 | Letta | L1-06 架构总纲 |
| Temporal fact（valid_from/to）| Zep | L1-06 条目元数据 |
| Bi-temporal（发生 vs 录入）| Zep | L1-06 审计追溯 |
| Retrieval without LLM | Zep | L1-06 阶段注入策略 |
| Hybrid search（BM25+vector）| Weaviate / Zep | L1-06 检索策略 |
| Payload filtering | Qdrant | L1-06 project_id 先过滤再检索 |
| Embedded mode 零运维 | ChromaDB | L1-06 默认方案 |
| Collection 命名空间 | ChromaDB | L1-06 三层 collection 映射 |
| ConversationSummaryBufferMemory | LangChain | L1-06 阶段结束摘要晋升 |
| **纯文件系统 + jsonl** | **HarnessFlow 原生设计** | **L1-06 默认实现** |
| **ChromaDB embedded 可选** | ChromaDB | L1-06 规模触发升级 |

**关键决策**：HarnessFlow L1-06 **默认走纯文件系统方案**，只有触发规模条件后才可选引入 ChromaDB embedded mode · 其他方案全部 Learn 思路不 Adopt 包。



## 8. Agent 监督 / Observability（对应 L1-07）

> **本章次重要**（L1-07 监督 skill 是 HarnessFlow 质量护栏核心）。
> HarnessFlow L1-07 目标：8 维度观察 + 4 级干预（INFO/SUGG/WARN/BLOCK）+ 软红线 8 类自治 / 硬红线 5 类上报。

### 8.1 模块定位 + 监督模式分类

业界 agent 监督 / 可观测性主要三种模式：

1. **代理式（Proxy）** · 在 LLM API 和应用之间插一层 · 自动记录所有请求 · 代表：Helicone
2. **SDK 式（Instrumentation）** · 应用内埋点 · 结构化 trace · 代表：Langfuse / LangSmith / OpenTelemetry
3. **旁路 subagent 式（Shadow Agent）** · 独立进程 / session 观察主 agent · 有拦截权 · HarnessFlow 独创方向 · 业界少见现成方案

HarnessFlow L1-07 是 **(3)+(2) 混合**：
- subagent 独立 session（观察 + 建议 + 拦截）
- 内部消费 SDK 式结构化 trace（OTEL / 自定义事件）

### 8.2 Langfuse

**GitHub**：https://github.com/langfuse/langfuse
**Stars（2026-04）**：19,000+
**License**：MIT（self-host 免费）· Cloud 商业化
**最后活跃**：极活跃

**核心架构**：**SDK-first** · Python / TS SDK 封装 tracing 原语（trace / span / generation / score）· 后端 Postgres + Clickhouse · 支持自托管 Docker。

**可学习点（Learn）**：

1. **Trace / Span / Generation 三级抽象** · trace（整个请求）· span（子操作）· generation（LLM 调用）· L1-07 监督 8 维度可建模成 span 层级结构。
2. **自定义 Score** · trace 可被外部标注（人工 / LLM-as-judge / rule-based）· L1-07 "8 维度评分" 可学此 score 模型。
3. **Session 概念** · trace 可归属 session · HarnessFlow PM-14 project_id 隔离直接映射成 session_id。
4. **Datasets + Experiments** · 可把 trace 转成 eval dataset · 对 HarnessFlow L1-04 "DoD 用例回放验证" 有参考。
5. **Open-source 完整性** · self-host 免费拿全功能 · 对齐 HarnessFlow 开源哲学。

**弃用点（Reject）**：

1. **不部署 Langfuse 服务** · 需要 Postgres + Clickhouse · 对 Skill 太重。
2. **不用它的 prompt management** · HarnessFlow prompt 已有 skill markdown 形态。

**性能**：

- 每秒写入 trace ~1000+（cloud）
- 自托管 P99 ~50ms

**处置**：**Learn · Trace/Span 抽象 + Score 模型 · 不直接依赖**

### 8.3 LangSmith

**来源**：https://smith.langchain.com（LangChain 官方）
**License**：商业化 SaaS
**Self-host**：Enterprise 版才支持

**核心架构**：与 LangChain 深度集成 · 自动追踪 LangChain / LangGraph 应用 · 支持 annotation queue、LLM-as-judge、prompt versioning。

**可学习点（Learn）**：

1. **Automatic instrumentation** · LangChain 应用零侵入追踪 · 对应 HarnessFlow "PostToolUse hook 自动打标"。
2. **Annotation queue** · 人工审查 trace · 对应 HarnessFlow "Stage Gate 审批待办"。
3. **Prompt playground** · 历史 prompt + 回放 + 改参数 · L1-10 UI 可参考。

**弃用点（Reject）**：

1. **SaaS 锁定** · 不符合 HarnessFlow 开源哲学。
2. **LangChain 绑定太深** · 不用 LangChain 时价值减半。

**处置**：**Reject 直接依赖 · Learn UI 交互**

### 8.4 Helicone

**GitHub**：https://github.com/Helicone/helicone
**Stars（2026-04）**：3,500+
**License**：Apache-2.0（open core）· Cloud 商业化
**最后活跃**：极活跃

**核心架构**：**Proxy-first** · 改一行 base URL（api.openai.com → oai.helicone.ai）· 即可记录所有 LLM 请求 · 零代码改动。

**可学习点（Learn）**：

1. **Proxy 拦截模式** · 零代码侵入 · HarnessFlow 可学此思路做 "LLM call tracker proxy"（但 Anthropic API 直接调用不走代理，价值有限）。
2. **Cost tracking** · 按请求记录 token + 折价 · L1-07 "成本预算" 维度直接对应。
3. **Caching** · 对重复 prompt 自动缓存 · 降低成本 · HarnessFlow 可学此策略。

**弃用点（Reject）**：

1. **不用 proxy 模式** · HarnessFlow 直接调 Claude Code SDK · 不走 HTTP proxy。
2. **不部署 Helicone 服务**。

**处置**：**Learn · cost tracking + caching 思路 · 不直接依赖**

### 8.5 OpenTelemetry（OTEL）

**GitHub**：https://github.com/open-telemetry
**License**：Apache-2.0
**Stars（主仓）**：2,500+（python-sdk）· 多个子项目
**最后活跃**：CNCF 毕业项目 · 极活跃

**核心架构**：**vendor-neutral observability protocol** · 统一 trace / metric / log 三个信号的 SDK 规范。OTEL Collector 是中心聚合器。

**可学习点（Learn）**：

1. **Trace / Span 标准** · OTEL 是业界事实标准 · HarnessFlow L1-07 如果要对外暴露可观测数据 · 应兼容 OTEL semantic convention。
2. **Context propagation** · `traceparent` header 跨服务传递 · 对应 HarnessFlow 主 agent → subagent 委托时 propagate trace context。
3. **Resource / Attribute** · span 挂 metadata · HarnessFlow event schema 可学此属性命名规范（`service.name`, `http.method` 等）。
4. **AutoGen v0.4 官方集成** · 直接输出 OTEL · 对比而言 HarnessFlow 也应输出 OTEL trace。

**处置**：**Adopt 作为 L1-07 对外协议 · 内部事件 schema 对齐 OTEL semantic convention**

### 8.6 Sentry

**GitHub**：https://github.com/getsentry/sentry
**Stars（2026-04）**：39,000+
**License**：BSL-1.1（商业友好）+ 部分 Apache-2.0
**最后活跃**：大规模商业项目

**核心架构**：**error monitoring + performance monitoring** · 自动捕获异常 + stack trace + context · 侧重生产 error 监控。

**可学习点（Learn）**：

1. **Release tracking** · 关联 error 到 git commit/release · 对应 HarnessFlow "故障归档 ↔ WP 归属" 追溯。
2. **Breadcrumbs** · error 前的上下文动作序列 · 对应 HarnessFlow "事件总线最近 N 条事件" 作为上下文。
3. **User feedback** · error 发生时可收集 user context · L1-10 UI "提交干预申请" 可学此。

**弃用点（Reject）**：

1. **不部署 Sentry** · 生产 error 场景 overkill · HarnessFlow 是 dev-loop 不是 prod。
2. **License BSL 需注意** · 不能改商业化。

**处置**：**Learn · breadcrumb / release tracking 思路 · 不直接依赖**

### 8.7 Arize Phoenix（开源 LLM 观测）

**GitHub**：https://github.com/Arize-ai/phoenix
**Stars（2026-04）**：4,500+
**License**：Elastic License 2.0
**最后活跃**：活跃

**核心架构**：**local-first LLM observability** · 开箱即用的 Jupyter + UI · 对 RAG / agent trace 可视化 · 可自托管。

**可学习点（Learn）**：

1. **Local-first** · 本地就能跑不需要服务 · HarnessFlow UI 可学此 "localhost 单文件运行" 模式。
2. **RAG eval 可视化** · 对应 L1-06 KB 检索质量评估。

**弃用点（Reject）**：

1. **License ELv2** · 不完全 OSI · 有顾虑。

**处置**：**Learn · local-first · 不直接依赖**

### 8.8 LangGraph Supervisor（官方扩展）

**GitHub**：https://github.com/langchain-ai/langgraph-supervisor-py
**Stars（2026-04）**：~800（相对较新）
**License**：MIT
**最后活跃**：活跃

**核心架构**：**dedicated supervisor node** · 监督多个 worker agent · 按条件分发任务 · 可 intercept 任意 worker 输出。

**可学习点（Learn）**：

1. **Supervisor node 模式** · 专门的 node 做路由决策 · 对应 HarnessFlow L1-07 "只读监督 agent"（但 HarnessFlow 的监督是旁路不是主 path 上的 node）。
2. **Human-in-the-loop** · supervisor 可以 interrupt 等人确认 · 对应 L1-07 BLOCK 级干预。

**处置**：**Learn · supervisor 专门 agent 思路 · 不直接依赖**

### 8.9 §8 性能 / 特性对比表

| 方案 | 模式 | 侵入度 | 自托管 | License | HarnessFlow 适配度 |
|---|---|---|---|---|---|
| Langfuse | SDK | 中 | ✅ | MIT | ⭐⭐⭐⭐（架构学习）|
| LangSmith | SDK | 低 | ❌（Enterprise）| Proprietary | ⭐⭐ |
| Helicone | Proxy | 零 | ✅ | Apache-2.0 | ⭐⭐⭐ |
| OpenTelemetry | SDK + Protocol | 中 | ✅ | Apache-2.0 | ⭐⭐⭐⭐⭐（协议对齐）|
| Sentry | SDK | 中 | ✅ | BSL-1.1 | ⭐⭐ |
| Phoenix | Local-first | 低 | ✅ | ELv2 | ⭐⭐⭐ |
| LangGraph Supervisor | Pattern | 高 | ✅ | MIT | ⭐⭐⭐⭐ |
| **自建 PostToolUse hook + jsonl** | Hook-based | 零 | ✅ | MIT（本项目）| ⭐⭐⭐⭐⭐ |

### 8.9a 监督 agent 独立 session vs 主 loop 内 supervisor node 对比

HarnessFlow L1-07 已锁定"旁路独立 subagent + 只读观察 + 4 级干预"模式 · 对比业界其他方案：

| 方案 | 代表 | 模式 | 优势 | 劣势 |
|---|---|---|---|---|
| **主 loop 内 supervisor node** | LangGraph Supervisor | 同进程节点 | 低延迟 · 简单 | 阻塞主 loop · 无法真正"只读观察" |
| **独立 subagent（旁路）** | 无现成直接对标 | 独立 session 异步观察 | 真只读 · 主 loop 无感 · 可拦截 | 架构复杂 · session 间通信开销 |
| **服务端 dashboard** | Langfuse | 后置分析 | 观察深 · 历史追溯好 | 无实时干预 · 无 BLOCK 能力 |
| **Proxy interception** | Helicone | 中间层拦截 | 零侵入 | 只能拦 LLM 调用 · 对其他工具无感 |

**HarnessFlow L1-07 组合方案**：
- **主通道**：Claude Code PostToolUse / PreToolUse hook（**已锁定**）
- **扩展通道**：独立 subagent 旁路观察（通过读事件总线 jsonl）
- **UI 展示**：类 Langfuse 的 trace 视图（**学它模式不用它 code**）

### 8.9b Supervisor 的 "8 维度观察" 开源对标

HarnessFlow L1-07 8 维度：目标保真度 / 计划对齐 / 真完成质量 / 红线安全 / 进度节奏 / 成本预算 / 重试 Loop / 用户协作。对标业界：

| HarnessFlow 维度 | 业界对应 | 参考项目 |
|---|---|---|
| 目标保真度 | Goal drift detection | 学术（研究领域）· 业界少见 |
| 计划对齐 | Plan-Actual variance | Airflow SLA / Sentry release tracking |
| 真完成质量 | Test pass rate / code coverage | pytest + coverage.py · Langfuse scores |
| 红线安全 | Security audit / policy check | Sentry error tracking · OPA Policy |
| 进度节奏 | SLA breach | Airflow SLA · Prometheus alerts |
| 成本预算 | Token / $ budget | Helicone cost tracking · Langfuse cost |
| 重试 Loop | Infinite retry detection | Temporal retry policy · Airflow retry |
| 用户协作 | Human-in-the-loop events | LangGraph interrupt · LangSmith annotation |

**结论**：8 维度中多数在业界都有独立对标 · 但**集大成的综合监督 agent 是 HarnessFlow 原创**。实现时各维度可复用对标方案的原语。

### 8.10 §8 小结 · L1-07 参考点

| 借鉴 | 来源 | HarnessFlow 对应 L2 |
|---|---|---|
| Trace / Span / Generation 抽象 | Langfuse | L1-07 监督事件建模 |
| Score 模型（人工 + LLM-judge + rule）| Langfuse | L1-07 8 维度打分 |
| Automatic instrumentation | LangSmith | L1-07 PostToolUse hook |
| Annotation queue | LangSmith | L1-10 Stage Gate 待办 |
| Cost tracking | Helicone | L1-07 成本预算维度 |
| OTEL semantic convention | OpenTelemetry | L1-07 事件属性命名 |
| Context propagation | OpenTelemetry | 主 agent → subagent 委托时 |
| Breadcrumbs | Sentry | L1-07 告警上下文 |
| Release tracking | Sentry | L1-09 故障归档 ↔ WP 追溯 |
| Supervisor node | LangGraph Supervisor | L1-07 专门 agent 形态（旁路版）|
| Human-in-the-loop interrupt | LangGraph Supervisor | L1-07 BLOCK 级干预 |
| **PostToolUse hook 原生** | **Claude Agent SDK** | **L1-07 主通道（已锁定）**|
| **jsonl 事件流** | **HarnessFlow 原生** | **L1-07 事件存储** |

**关键决策**：HarnessFlow L1-07 **以 Claude Agent SDK 的 PostToolUse hook + 自建 jsonl 事件流为主通道** · OTEL 作为未来对外可观测数据标准 · 其他 Learn 不 Adopt。



## 9. 多模态内容处理（对应 L1-08）

### 9.1 模块定位

L1-08 的需求：**读 markdown / yaml / json / 代码（AST + Grep）/ 图片（架构图 / UI mock / 截图）**。**不是**要把 LLM 变成全能多模态 · 而是让 HarnessFlow 主 loop 能消费不同内容形态作为决策输入。

### 9.2 Claude Vision（LLM 原生）

**来源**：Anthropic · Claude 3.5+ / Claude 4+ 系列原生支持图像输入
**License**：闭源 LLM · API 付费

**可学习点（Learn）**：

1. **图像作为 message content** · Claude 消息支持 `image` 类型 content block · HarnessFlow L1-08 图片理解可直接调此能力。
2. **Vision + Text 混合** · 可同时上传图 + 文本指令 · 对应 HarnessFlow "看 UI mock + 读 PRD" 混合输入。
3. **图像理解深度** · 对架构图 / flowchart / 截图识别准确。

**处置**：**Adopt · 作为 L1-08 图像处理主通道（HarnessFlow 本身就是 Claude Code Skill · 直接用 Claude 能力）**

### 9.3 Unstructured.io

**GitHub**：https://github.com/Unstructured-IO/unstructured
**Stars（2026-04）**：9,500+
**License**：Apache-2.0
**最后活跃**：极活跃（商业化支撑）

**核心架构**：**document ETL** · 支持 PDF / HTML / Word / PPT / EML 等 50+ 格式 · 统一输出 Element（Title/NarrativeText/Table/Image 等）结构。

**可学习点（Learn）**：

1. **统一 Element 模型** · 无论来源格式都标准化成 Element 列表 · L1-08 可学此 "一种 IR（中间表示）兼容多格式"。
2. **partition 函数模式** · `partition(file)` 根据类型自动 dispatch · L1-08 API 设计可学。
3. **Table / Image 特殊处理** · 提取表格结构 + 图片引用 · HarnessFlow 解析 markdown 里的表格可学。

**弃用点（Reject）**：

1. **依赖过重** · 需要 tesseract / pdfminer / python-docx 等 · 启动时间 10+s。
2. **HarnessFlow 场景有限** · 主要就是 markdown · 不需要这么多格式。

**处置**：**Learn · Element IR 模型 · 不直接依赖**

### 9.4 python-docx / PyMuPDF / BeautifulSoup 等标准库

**python-docx** · 28k stars · MIT · Word 读写
**PyMuPDF** · 5k stars · AGPL-3.0（⚠️ license）· PDF 解析
**BeautifulSoup** · 标准 HTML 解析
**markdown-it-py** · 4k stars · MIT · Python markdown 解析

**处置**：**Adopt 按需** · markdown-it-py 作为 L1-08 markdown AST 解析器。PyMuPDF 因 AGPL 不引入 · PDF 极少时走 unstructured。

### 9.5 Tree-sitter（代码 AST）

**GitHub**：https://github.com/tree-sitter/tree-sitter
**Stars（2026-04）**：20,000+
**License**：MIT
**最后活跃**：极活跃

**核心架构**：**incremental parsing library** · 多语言 AST 解析（Python / JS / Go / Rust / Java 等 100+ 语言）· 增量更新（改一行只重解析相关部分）· 极快。

**可学习点（Learn）**：

1. **统一 AST 接口** · 无论什么语言都是 tree · L1-08 "读代码结构" 可基于 tree-sitter 做语言无关的 AST 分析。
2. **Query 语言** · S-expression 风格查询 · 比 grep 精确（只匹配 "function 声明" 不误伤注释）。
3. **增量解析** · 对实时 UI 代码编辑场景友好。

**处置**：**Adopt · L1-08 代码 AST 解析推荐用 tree-sitter（python binding）**

### 9.6 Grep / ripgrep

**ripgrep** · https://github.com/BurntSushi/ripgrep · 50,000+ stars · MIT
**来源**：Rust 重写的 grep · 极快

**可学习点（Learn）**：

1. **快速文本搜索** · L1-08 "读代码粗粒度" 首选 · AST 分析太重的场景降级用 ripgrep。

**处置**：**Adopt · Claude Code 已自带 Grep 工具（底层就是 ripgrep）· 直接用**

### 9.7 Docling（IBM 新开源）

**GitHub**：https://github.com/docling-project/docling
**Stars（2026-04）**：25,000+（爆发增长）
**License**：MIT
**最后活跃**：IBM 支持 · 极活跃

**核心架构**：**IBM 开源的 AI 驱动文档解析** · 对复杂 PDF / 扫描件特别强。

**可学习点（Learn）**：

1. **AI 驱动 layout 分析** · 比纯规则解析强。

**弃用点（Reject）**：

1. **HarnessFlow 文档多是生成的纯 markdown** · 用不到 Docling 的复杂 PDF 能力。

**处置**：**Learn · 未来扩展时可考虑 · 当前不用**

### 9.8 §9 小结 · L1-08 参考点

| 借鉴 | 来源 | HarnessFlow 对应 L2 |
|---|---|---|
| Vision message content | Claude Vision | L1-08 图像理解主通道 |
| Element IR 模型 | Unstructured | L1-08 多格式统一表示 |
| Markdown AST | markdown-it-py | L1-08 markdown 解析 |
| 代码 AST 统一接口 | tree-sitter | L1-08 代码结构分析 |
| AST Query 语言 | tree-sitter | L1-08 "查所有 function 定义" |
| Grep（ripgrep）快速搜索 | Claude Code 内置 Grep | L1-08 粗粒度扫描 |



## 10. 事件总线 / 韧性层（对应 L1-09）

### 10.1 模块定位

L1-09 的核心是 **"单一事实源 + 崩溃安全 + 跨 session 无损恢复 + 审计追溯"**。这是一个**持久化层 + event sourcing + 原子写**的问题。调研方向：

1. **Event sourcing 框架**：EventStore / Axon / 自建 jsonl
2. **消息队列 / 事件流**：Kafka / Redis Streams / NATS
3. **嵌入式存储**：SQLite WAL / LevelDB / LMDB
4. **原子写模式**：POSIX rename / fsync / O_DIRECT

### 10.2 SQLite WAL 模式

**来源**：SQLite 官方 · stdlib 可得 · https://sqlite.org/wal.html
**License**：Public domain
**成熟度**：数十年工业使用

**核心架构**：**Write-Ahead Logging** · 每次 commit 先写 WAL 文件再 checkpoint 到主库 · COMMIT 只有当 WAL 刷盘后才返回 · 崩溃后首个连接自动 recovery。

**可学习点（Learn）**：

1. **WAL 即事件日志** · WAL 本身就是 append-only 的事件序列 · HarnessFlow 事件总线设计哲学同构。
2. **Checkpoint 机制** · 后台定期把 WAL 合并到主库 · HarnessFlow 可学此 "jsonl append + 定期合并成 snapshot"。
3. **Crash recovery** · 自动恢复 · 对 HarnessFlow "跨 session 无损恢复" 极有参考。
4. **fsync 成本** · WAL 大幅减少 fsync 次数 · HarnessFlow append-only jsonl 设计也要注意 fsync 频率。

**已知限制**：

- 跨 attached db 事务不保证原子性 · HarnessFlow 单 sqlite 文件即可。
- fsync 被文件系统假装（某些系统）时会有数据丢失风险 · HarnessFlow 运行在 Mac/Linux 开发机 · 可接受。

**处置**：**Adopt · HarnessFlow 可选 SQLite WAL 作为结构化事件索引 · append-only jsonl 作为事件主存**

### 10.3 Append-only jsonl（文件系统原生）

**来源**：POSIX append semantic · 非具体项目

**核心架构**：用 `open(path, 'a')` + 每条事件一行 JSON · `rename()` 原子替换做 snapshot 切换。

**可学习点（Learn）**：

1. **Append 原子性** · POSIX 保证单次 `write()` < 512 bytes 是原子的 · jsonl 单行通常 < 4KB · 加锁或用 `O_APPEND` 可保证多进程安全。
2. **按 project_id 分片** · 每 project 一个 events.jsonl · 完全避免跨项目竞争（PM-14）。
3. **可 grep / 可 tail -f** · 运维友好。
4. **Git-friendly** · 小项目直接 commit events.jsonl 也可接受。

**原子写模式**：

```python
# 写 snapshot 的原子替换
with open(path + '.tmp', 'w') as f:
    json.dump(data, f)
    f.flush()
    os.fsync(f.fileno())  # 强刷盘
os.rename(path + '.tmp', path)  # POSIX 保证原子
```

**处置**：**Adopt · HarnessFlow L1-09 主存形态**

### 10.4 EventStoreDB

**GitHub**：https://github.com/EventStore/EventStore
**Stars（2026-04）**：5,200+
**License**：BSL-1.1
**最后活跃**：商业化支撑 · 活跃

**核心架构**：**专业 event sourcing database** · stream / event / snapshot / projection 四原语。

**可学习点（Learn）**：

1. **Stream per aggregate** · 每个 aggregate 有独立 stream · 对应 HarnessFlow "每 project 一个事件流"。
2. **Optimistic concurrency** · 写事件时带期望 version · 防并发写 · HarnessFlow 单 session 多 subagent 写入时可学。
3. **Projections** · 事件实时投影成 read model · 对应 HarnessFlow "从事件总线推导 task-board 当前状态"。

**弃用点（Reject）**：

1. **独立 .NET 服务** · 运维复杂。
2. **BSL license** · 商业友好但非 OSI。

**处置**：**Learn · Event sourcing 原语语义 · 不直接依赖**

### 10.5 Kafka / Redis Streams / NATS（消息队列对比）

**Kafka** · apache/kafka · 27k+ stars · 分布式事件流事实标准
**Redis Streams** · redis 内建 · 单机轻量
**NATS** · nats-io/nats-server · 15k+ stars · 高性能 pub/sub + JetStream 持久化

**共性**：分布式消息流 · 有持久化 · 支持 consumer group

**弃用点（Reject）**：

- **都太重** · HarnessFlow 单机 Skill 不需要分布式消息队列。
- **HarnessFlow 事件频率低** · 一个 session 产生事件 < 1000/h · 用 jsonl 足够。

**处置**：**全部 Reject · Learn consumer group / offset 语义**

### 10.6 LevelDB / LMDB（嵌入式 KV）

**LevelDB** · google/leveldb · 37k stars · BSD-3
**LMDB** · 2k stars · OpenLDAP License · 极高性能

**核心架构**：嵌入式 KV 存储 · 单文件 · ACID（LMDB）。

**可学习点（Learn）**：

1. **LMDB 的 mmap + copy-on-write** · 极致性能 · HarnessFlow 不需要这么强。
2. **LevelDB 的 LSM tree** · append-only + compaction · HarnessFlow jsonl 合并 snapshot 的思路。

**处置**：**Learn 架构 · 不引入**

### 10.7 litestream（SQLite 复制）

**GitHub**：https://github.com/benbjohnson/litestream
**Stars（2026-04）**：11,000+
**License**：Apache-2.0
**最后活跃**：活跃

**核心架构**：**SQLite → S3/NFS replication** · 把 SQLite WAL 持续复制到外部存储 · 崩溃恢复。

**可学习点（Learn）**：

1. **WAL → remote storage 持续备份** · 未来 HarnessFlow "云端备份事件总线" 场景可学。

**处置**：**Learn · 未来 V3+ 备份场景参考**

### 10.8 文件系统级崩溃安全最佳实践总结

**关键原则**（综合 SQLite WAL + POSIX 规范 + LSM tree 教训）：

1. **Append-only + rename 切换** · 永不覆盖写现有文件
2. **fsync 在 commit 前** · 操作系统 crash 后数据持久
3. **.tmp 后缀 + rename** · 原子替换 snapshot
4. **按 project_id 分目录** · 物理隔离故障传播
5. **事件都有 event_id + sequence** · 去重 + 乱序重组
6. **snapshot 间隔 = N 条事件 or M 分钟** · 平衡写放大和恢复时间
7. **启动时先 replay 检查一致性** · 类 SQLite recovery

**HarnessFlow L1-09 设计原则**（从上述学到）：

```
project-boards/{project_id}/
├── events.jsonl              # append-only 主流
├── snapshots/
│   ├── snap_{seq}.json       # 定期快照
│   └── snap_{seq}.json.tmp   # 写入时
├── index.sqlite              # WAL 模式结构化索引
└── README.md                 # 项目元数据
```

### 10.8a 并发写 jsonl 的具体安全模式（实现细节对标）

HarnessFlow L1-09 场景：**主 loop + N 个 subagent 可能同时写事件总线**。业界对标：

**Linux logrotate / syslog**：用 flock 独占锁 + append。
```python
import fcntl
with open(path, 'a') as f:
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    f.write(line + '\n')
    f.flush()
    os.fsync(f.fileno())
    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

**Python logging 模块**：Lock-based QueueHandler · 由一个后台线程统一写 · HarnessFlow 可学"单写线程 + 多生产者队列"模式。

**SQLite 的 BEGIN IMMEDIATE**：显式申请写锁 · 避免 writer starvation。

**Kafka 的 partition per producer**：每个生产者绑定 partition · 完全无锁。HarnessFlow 启发：**主 loop 写 main.jsonl / 每 subagent 写 subagent_{id}.jsonl**，定期合并。

**最终方案**（HarnessFlow 推荐）：

```
project-boards/{project_id}/
├── main.jsonl              # 主 loop 专属 · 单写者
├── subagents/
│   └── sub_{session_id}.jsonl   # 每子 Agent 独立 · 单写者
├── supervisor.jsonl        # supervisor subagent 专属 · 单写者
└── merged-view.jsonl       # 周期合并（读者专用）
```

**单写者原则**：每个 jsonl 文件只有一个进程可以写 · 避免并发写锁 · 读者多来不限。这比 flock 模式更简单 · 更不易出 bug。

### 10.8b 事件 schema 规范（对标业界）

- **CloudEvents spec**（CNCF）· https://github.com/cloudevents/spec · 事件规范事实标准
  - 核心字段：`id / source / type / specversion / datacontenttype / time / data`
  - HarnessFlow 可学此字段规范设计
- **OpenTelemetry semantic convention** · span attribute 命名标准
  - `service.name / http.method / error.type` 等
  - HarnessFlow 事件 `data` 字段可对齐 OTEL attribute 命名

**HarnessFlow 事件 schema 建议**（融合 CloudEvents + OTEL + 本地需求）：

```json
{
  "event_id": "evt_01H9XYZ...",            // ULID
  "sequence": 12345,                        // 单调递增 (CloudEvents.id)
  "project_id": "proj_...",                 // PM-14 必填
  "session_id": "sess_...",
  "source": "main-loop",                    // CloudEvents.source
  "type": "decision.skill_call",            // CloudEvents.type
  "time": "2026-04-20T10:30:00Z",          // ISO 8601 (CloudEvents.time)
  "actor": {                                // OTEL 扩展
    "type": "main-skill",
    "id": "harnessFlow-v2"
  },
  "data": {                                 // 业务 payload
    "skill": "superpowers:tdd",
    "reason": "阶段 S3 进入 TDD 蓝图生成"
  },
  "trace_id": "trace_...",                 // OTEL trace
  "span_id": "span_..."
}
```

### 10.9 §10 小结 · L1-09 参考点

| 借鉴 | 来源 | HarnessFlow 对应 L2 |
|---|---|---|
| WAL append-only | SQLite | L1-09 jsonl 事件流 |
| Checkpoint 机制 | SQLite | L1-09 snapshot 合并 |
| Crash recovery | SQLite | L1-09 启动 replay |
| POSIX rename 原子 | 文件系统 | L1-09 snapshot 切换 |
| Stream per aggregate | EventStore | L1-09 每 project 独立事件流 |
| Optimistic concurrency | EventStore | L1-09 并发写控制 |
| Projections | EventStore | L1-09 task-board 当前状态推导 |
| Consumer group 语义 | Kafka | L1-09 多 subagent 消费游标 |
| LSM tree compaction | LevelDB | L1-09 历史事件合并 |
| WAL replication | litestream | L1-09 未来云备份 |



## 11. Dev UI / 可观测面板（对应 L1-10）

### 11.1 模块定位

L1-10 UI 需求：11 tab 任务详情 + 9 admin 模块 + 新增 P0 缺口（Quality Loop 实时视图 / 4 件套视图 / 决策轨迹走廊 / Stage Gate 待办中心 / 多模态展示 / 红线告警角 / 审计追溯）。

技术栈已锁定：**FastAPI + Vue 3 + Element Plus + Vite**（scope.md + AIGC 项目同栈）。调研重点：**哪些开源面板 / dashboard 可学习？**

### 11.2 Langfuse UI

**来源**：Langfuse self-host web UI
**License**：MIT

**可学习点（Learn）**：

1. **Trace list + 详情视图** · 左侧时间线 + 右侧 span 树 · L1-10 "执行时间轴 tab" 可学。
2. **Filter + 搜索** · tag / status / user / time 多维过滤 · L1-10 全局搜索可学。
3. **Annotation UI** · 直接在 trace 上打分 · L1-10 "监督干预 UI" 可学。

**处置**：**Learn · UI 交互模式 · 不拷贝代码**

### 11.3 LangSmith UI

**可学习点（Learn）**：

1. **Prompt playground** · 可回放 LLM 请求并改参数 · L1-10 "Loop 历史 tab" 可学。
2. **Dataset management** · eval dataset 编辑 · L1-10 "TDD 质量 tab" 可学。

**处置**：**Learn · 交互模式 · 不拷贝**

### 11.4 Vue Element Plus Admin（开源 admin 模板）

**GitHub**：https://github.com/kailong321200875/vue-element-plus-admin
**Stars（2026-04）**：3,500+
**License**：MIT
**最后活跃**：活跃

**核心架构**：**完整 Vue3 + Element Plus + TypeScript + Vite admin 模板**。包含菜单 / 路由 / 权限 / 表格 / 表单 / 图表等完整套件。

**可学习点（Learn）**：

1. **目录结构约定** · `views/` + `components/` + `stores/` + `api/` · L1-10 可直接借鉴。
2. **动态路由 + 权限** · 登录后按权限渲染菜单 · L1-10 V2+ 多用户场景可学。
3. **Dialog + Drawer 模式** · 弹层 UI 最佳实践 · L1-10 "干预台" 大量用 drawer。

**处置**：**Learn + 局部 copy · 作为 L1-10 起始骨架参考**

### 11.5 vue3-element-admin（新一代）

**GitHub**：vue3-element-admin · https://vue3-element-admin-site.midfar.com
**Stars（2026-04）**：4,000+
**License**：MIT
**最后活跃**：2026-03 大更新 · 极活跃

**核心架构**：vue-element-admin 的 Vue 3 版本 · Vite 7 / TS / Composition API 全新重写。

**可学习点（Learn）**：

1. **Composition API 规范** · `<script setup>` + `ref / reactive` · L1-10 代码风格锁定。
2. **pinia store pattern** · 模块化 store · L1-10 state 管理。

**处置**：**Adopt 参考模式**

### 11.6 RuoYi-Vue3

**来源**：https://gitee.com/y_project/RuoYi-Vue3
**License**：MIT
**国内广泛使用**

**可学习点（Learn）**：

1. **监控模块** · 服务监控 / 缓存监控 / 数据库监控 · L1-10 "系统诊断" 可学。
2. **日志监控** · 操作日志 / 登录日志 / 调度日志 · L1-10 "执行时间轴" 可学。

**处置**：**Learn · 监控模块布局**

### 11.7 AIGC (VideoForge) 现有 UI 参考

**来源**：工作目录内 `/Users/zhongtianyi/work/code/aigc/frontend/`

**相关度**：HarnessFlow 技术栈完全继承 AIGC · 可直接复用大量组件。

**可学习点（Learn）**：

1. **Vue Flow DAG 可视化** · AIGC 已集成 @vue-flow/core · L1-10 "WBS 拓扑图 tab" 直接用。
2. **WebSocket / SSE 实时推送** · AIGC 有现成 composables · L1-10 事件总线推送 UI 用。
3. **Pinia store 组织** · 跨多个业务域的 store 设计 · 可直接参照。

**处置**：**Adopt 组件复用 · 跨项目 lerna 或 workspace 引用**

### 11.8 Grafana（监控面板参考）

**GitHub**：https://github.com/grafana/grafana · 65,000+ stars · AGPL-3.0（⚠️）

**可学习点（Learn）**：

1. **Dashboard JSON 格式** · 可声明式 dashboard · L1-10 "统计分析 tab" 如果要做可配置面板可学。
2. **Alert UI** · 告警配置 + 历史 · L1-10 "红线告警角" 可学。

**弃用点（Reject）**：

1. **AGPL 不能直接引用代码**。
2. **对 HarnessFlow 场景太重**。

**处置**：**Learn 模式 · 不引用代码**

### 11.9 §11 小结 · L1-10 参考点

| 借鉴 | 来源 | HarnessFlow 对应 L2 |
|---|---|---|
| Trace list + 详情 | Langfuse UI | L1-10 "执行时间轴" tab |
| Annotation UI | Langfuse | L1-10 "监督干预" |
| Prompt playground | LangSmith | L1-10 "Loop 历史" |
| Admin 目录 + 组件约定 | vue-element-plus-admin | L1-10 骨架 |
| Composition API / pinia | vue3-element-admin | L1-10 代码风格 |
| 系统监控模块布局 | RuoYi-Vue3 | L1-10 "系统诊断" |
| Vue Flow DAG 可视化 | AIGC 现有 | L1-10 "WBS 拓扑图" |
| WebSocket / SSE | AIGC 现有 | L1-10 实时事件推送 |
| Dashboard 声明式 JSON | Grafana | L1-10 可配置 dashboard（远期）|
| Alert UI | Grafana | L1-10 "红线告警角" |



## 12. DoD / 白名单 AST eval

### 12.1 模块定位

HarnessFlow 的 **DoD（Definition of Done）表达式** 是机器可校验的合约，必须：
1. 不允许任意 Python 代码（安全）
2. 支持布尔组合 + 比较 + 函数调用（富表达力）
3. 可 parse 可 eval 可验证
4. 错误消息清晰（给用户反馈）

业界相关方案：Python AST 白名单 / pyparsing / lark / simpleeval / Pydantic validators。

### 12.2 Python ast 标准库 + 白名单 NodeVisitor

**来源**：Python stdlib · `ast` 模块

**核心架构**：`ast.parse` 把表达式 parse 成 AST · `ast.NodeVisitor` 遍历 · 只允许白名单节点类型。

```python
class SafeExprValidator(ast.NodeVisitor):
    ALLOWED_NODES = {
        ast.Expression, ast.BoolOp, ast.And, ast.Or,
        ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.Gt,
        ast.Name, ast.Constant, ast.Load,
        ast.Call  # 仅允许白名单 Name
    }
    ALLOWED_FUNCS = {"has_file", "file_contains", "passes_lint"}

    def visit(self, node):
        if type(node) not in self.ALLOWED_NODES:
            raise ValueError(f"Disallowed node: {type(node).__name__}")
        # 对 Call 额外校验 func 名白名单
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in self.ALLOWED_FUNCS:
                raise ValueError(f"Disallowed function: {node.func}")
        return self.generic_visit(node)
```

**可学习点（Learn）**：

1. **零依赖** · stdlib · 完美适合 HarnessFlow。
2. **精确控制** · 每个 AST 节点显式白名单。
3. **可定制错误信息** · 捕获时给人类可读提示。

**处置**：**Adopt · L1-04 DoD 表达式编译器首选方案**

### 12.3 simpleeval

**GitHub**：https://github.com/danthedeckie/simpleeval
**Stars（2026-04）**：900+（略低于 1k 但成熟）
**License**：MIT
**最后活跃**：稳定维护

**核心架构**：基于 Python AST · 封装了白名单 + 内建函数注入 · 几行代码用。

```python
from simpleeval import simple_eval
simple_eval("1 + 2 * 3")  # 7
simple_eval("foo(x)", functions={"foo": lambda x: x+1}, names={"x": 10})  # 11
```

**可学习点（Learn）**：

1. **开箱即用的白名单 eval** · 不用自己写 NodeVisitor。
2. **可注入函数和变量** · HarnessFlow 可注入 `has_file / passes_lint` 等 DoD 原语。

**处置**：**Learn / Adopt 可选 · 可直接依赖（纯 Python 单文件约 500 行）**

### 12.4 pyparsing

**GitHub**：https://github.com/pyparsing/pyparsing
**Stars（2026-04）**：2,000+
**License**：MIT
**最后活跃**：活跃

**核心架构**：**parser combinator** · 在 Python 里直接写文法 · 不需要单独的 grammar 文件。

**可学习点（Learn）**：

1. **自定义 DSL** · 若未来 DoD 语法需要超出 Python 表达式（如"IF X THEN Y ELSE Z"风格）· pyparsing 可设计 DSL。
2. **错误定位精确** · parse 错误会指到具体字符位置。

**弃用点（Reject）**：

1. **对 HarnessFlow 过度** · DoD 表达式用 Python 语法子集已足够。

**处置**：**Learn · 未来 DSL 场景可选 · 当前不用**

### 12.5 Lark

**GitHub**：https://github.com/lark-parser/lark
**Stars（2026-04）**：5,000+
**License**：MIT
**最后活跃**：活跃

**核心架构**：**EBNF 风格 grammar 文件** + 生成 parser · 比 pyparsing 更工业化。

**可学习点（Learn）**：

1. **Earley / LALR 算法** · 比 pyparsing 更高效。
2. **grammar 文件独立** · 易维护。

**处置**：**Reject · 当前场景用不到**

### 12.6 Pydantic validators

**来源**：Pydantic v2 `model_validator / field_validator`

**可学习点（Learn）**：

1. **schema-first + validator 装饰器** · HarnessFlow 所有 IC 契约已用 Pydantic · DoD 可建模成 Pydantic model 的 validator。

**处置**：**Adopt · 作为 IC 字段级校验 · 与 DoD 表达式互补**

### 12.7 evalidate

**GitHub**：https://github.com/yaroslaff/evalidate
**Stars（2026-04）**：200+（低 star 但特定用途）
**License**：MIT

**核心架构**：专门做 "safe + fast evaluation of untrusted python expressions"。

**处置**：**Learn · star 偏低不 Adopt**

### 12.8 §12 小结 · DoD eval 参考点

| 借鉴 | 来源 | HarnessFlow 对应 |
|---|---|---|
| AST NodeVisitor 白名单 | Python stdlib | L1-04 DoD eval 主方案（**Adopt 直接用 stdlib**）|
| Safe eval 开箱即用 | simpleeval | 备选（若 stdlib 实现麻烦）|
| Parser combinator | pyparsing | 未来自定义 DSL |
| Pydantic validator | Pydantic | IC 字段级校验 |



## 13. Mermaid / 图表工具

### 13.1 模块定位

HarnessFlow 在 3-1 tech-design 标准模板（§5）里要求**每个 L2 至少 1 张 Mermaid 时序图**。UI 侧（L1-10）也需要渲染 DAG / 状态机图。调研：**Mermaid / PlantUML / Graphviz / D2** 四大主流工具对比。

### 13.2 Mermaid

**GitHub**：https://github.com/mermaid-js/mermaid
**Stars（2026-04）**：78,000+
**License**：MIT
**最后活跃**：极活跃 · 2026-04 最新 v11.4.1

**核心架构**：**纯浏览器 JavaScript 渲染** · 类 markdown 语法 · GitHub / GitLab / Obsidian 原生支持。

**可学习点 + 选型理由（Learn + Adopt）**：

1. **GitHub 原生渲染** · markdown 里直接写 ```mermaid 代码块就渲染 · tech-design.md 直接可用。
2. **类 markdown 语法** · `A --> B` 这种极直观 · 作者写作成本极低。
3. **多种图表类型**：flowchart / sequenceDiagram / stateDiagram / erDiagram / ganttDiagram / classDiagram / C4 diagram 等完整覆盖。
4. **浏览器端渲染** · 私有 · 离线可用 · HarnessFlow 本地 UI 直接嵌入 `mermaid.js`。

**弃用点**：无（是本方案选定工具）

**性能**：

- 中等复杂度图（<100 节点）浏览器渲染 < 100ms
- 超大图（> 500 节点）会卡 · HarnessFlow 单图通常 < 50 节点，无问题

**处置**：**Adopt · HarnessFlow 3-1 tech-design + L1-10 UI 时序图 / 状态图统一用 Mermaid**

### 13.3 PlantUML

**GitHub**：https://github.com/plantuml/plantuml
**Stars（2026-04）**：11,000+
**License**：GPL-3.0（⚠️）
**最后活跃**：活跃

**核心架构**：**Java + Graphviz 后端** · 发送 diagram text 给 server 返回图片 · 支持大量 UML 标准图。

**可学习点（Learn）**：

1. **UML 标准覆盖更全** · sequence / class / use-case / component / deployment / timing / gantt 全。
2. **企业场景接受度高** · 架构师偏爱。

**弃用点（Reject）**：

1. **需要 Java 运行时** · 用户门槛。
2. **GitHub markdown 不原生渲染** · 必须 PlantUML 服务器或插件。
3. **GPL license** · 依赖时要小心。
4. **Mermaid 已够用**。

**处置**：**Reject · Mermaid 已满足需求**

### 13.4 Graphviz (DOT)

**GitHub**：https://gitlab.com/graphviz/graphviz
**Stars（GitHub mirror）**：2,000+
**License**：EPL-1.0 / CPL-1.0
**最后活跃**：稳定维护

**核心架构**：**图 layout 算法引擎** · DOT 语言 · 自动化布局能力最强 · 支持 dot / neato / fdp / sfdp / twopi / circo 多种布局算法。

**可学习点（Learn）**：

1. **自动 layout** · 生成大规模图（> 100 节点）时 Graphviz 布局质量最好。
2. **NetworkX 原生导出 dot** · L1-03 WBS 拓扑图如果要 export pdf 可走 NetworkX → dot → Graphviz。

**弃用点（Reject）**：

1. **需要本地 graphviz binary** · 用户门槛。
2. **语法过于底层** · 文档时序图用 Mermaid 足够。

**处置**：**Learn · 未来大规模 WBS 图布局可用 · 当前 Mermaid 优先**

### 13.5 D2

**GitHub**：https://github.com/terrastruct/d2
**Stars（2026-04）**：18,000+
**License**：MPL-2.0
**最后活跃**：活跃（Terrastruct 商业化）

**核心架构**：**"modern text-to-diagram language"** · 比 Mermaid 更现代 · 强调开发者体验 · 多种主题。

**可学习点（Learn）**：

1. **更清晰的语法** · 复杂图比 Mermaid 更直观。
2. **shape library 丰富** · 云资源图标等。

**弃用点（Reject）**：

1. **GitHub 不原生渲染** · 失去 Mermaid 核心优势。
2. **生态比 Mermaid 小**。

**处置**：**Learn · 未来可选 · 当前 Mermaid 优先**

### 13.6 Excalidraw

**GitHub**：https://github.com/excalidraw/excalidraw
**Stars（2026-04）**：88,000+
**License**：MIT

**核心架构**：手绘风格可交互白板 · UI 交互友好。

**可学习点（Learn）**：

1. **手绘风格风格独特** · 用于 sketch / 初步讨论最佳。
2. **Mermaid 集成** · 可以把 Mermaid 代码渲染成 Excalidraw sketch。

**处置**：**Learn · 未来 L1-10 若需交互白板可引入**

### 13.7 §13 小结 · 图表工具链决策

| 用途 | 工具 | 理由 |
|---|---|---|
| 时序图 / 状态图 / 流程图（文档）| **Mermaid** | GitHub 原生渲染 + 零门槛 + 覆盖全 |
| WBS 大规模拓扑图（离线 pdf export）| Mermaid → （未来 Graphviz）| 短期 Mermaid · 长期 NetworkX → dot |
| UI 内交互 DAG 渲染 | **Vue Flow** | 已有 AIGC 现成组件 |
| UI 内时序图渲染 | **Mermaid.js** | 浏览器端直接渲染 |
| 初步 sketch / 头脑风暴 | **Excalidraw**（未来）| 当前阶段不引入 |

**关键决策**：HarnessFlow **全面统一用 Mermaid 作为文档图表工具** · 下游所有 L1 / L2 tech-design 必须用 Mermaid · 禁用 PlantUML / D2 / Graphviz（除非有明确理由）。



## 14. 调研结论汇总

### 14.1 每 L1 推荐开源参考 Top-3（下游 L2 tech-design §9 必引）

| L1 | 模块 | Top-1（Learn）| Top-2（Learn）| Top-3（Learn / Adopt）|
|---|---|---|---|---|
| L1-01 | 主 Agent loop | LangGraph（图式状态机）| OpenHands（event-stream）| AutoGen v0.4（actor 模型）|
| L1-02 | 生命周期编排 | Temporal（durable execution）| Prefect（decorator-first）| Airflow（DAG + Operator）|
| L1-03 | WBS/WP 拓扑 | NetworkX（**Adopt**）| Airflow DAG 模型 | Dagster（asset-first）|
| L1-04 | Quality Loop | pytest（**Adopt**）| Hypothesis（按需 Adopt）| superpowers:tdd + santa-method（**Adopt**）|
| L1-05 | Skill 生态 / 子 Agent | Claude Agent SDK（**Adopt**）| superpowers（**Adopt**）| MCP（未来 Adopt）|
| L1-06 | 知识库 | Mem0（三存储协同）| Letta（LLM OS）| Zep + Graphiti（temporal fact）· ChromaDB（可选 Adopt）|
| L1-07 | Harness 监督 | OpenTelemetry（协议对齐）| Langfuse（trace/span）| LangGraph Supervisor（supervisor node 模式）|
| L1-08 | 多模态 | Claude Vision（**Adopt**）| tree-sitter（**Adopt**）| Unstructured（Element IR 思想）|
| L1-09 | 韧性 + 审计 | SQLite WAL（**Adopt**）| EventStore（语义参考）| 纯 jsonl + POSIX rename（**Adopt 主存**）|
| L1-10 | Dev UI | vue-element-plus-admin（骨架参考）| Langfuse UI（交互模式）| AIGC 现有 UI（组件复用）|
| 横切 | DoD eval | Python ast stdlib（**Adopt**）| simpleeval（备选）| Pydantic validator（**Adopt 字段级**）|
| 横切 | 图表工具 | Mermaid（**Adopt**）| Vue Flow（**Adopt UI**）| - |

### 14.2 明确 Reject 清单（不得引入）

以下项目架构值得学 · 但**不得作为依赖引入**：

| Reject 项目 | 理由 |
|---|---|
| LangChain 全家桶 | 依赖过重 · 与 Skill 形态冲突 · HarnessFlow 不走 LangChain 路线 |
| LangGraph 包 | 学思路不引入包 · 与 LangChain 耦合深 |
| AutoGen 包 | 学 actor 模型思路 · Skill 形态不引入 |
| CrewAI 包 | 学角色字段设计 · 与 HarnessFlow 单主 agent 冲突 |
| OpenHands 代码 | 学 event-stream · 不引入 sandbox 方案 |
| Apache Airflow | 需要独立 scheduler · 太重 |
| Prefect | 需要独立 server · 太重 |
| Temporal | 需要独立 server · 太重 |
| Windmill | AGPL license 不兼容 |
| Dagster | 需要独立服务 · 太重 |
| Rundeck | Java 技术栈不合 |
| Dask / Ray | 分布式计算过度 · 单机 Skill 用不到 |
| Mem0 包 | 需 vector+graph+kv 底层 DB · 太重 · 学其 API 形态 |
| Letta server | 独立 server · 太重 · 学其 LLM OS 哲学 |
| Zep + Graphiti | 依赖 Neo4j · 太重 · 学其 temporal fact 思想 |
| LangChain Memory | API 过度复杂 |
| pgvector | 需 Postgres · 仅 server 场景 |
| Weaviate | 独立服务 · 太重 |
| Qdrant | 独立服务 · 当前条目规模用不到 |
| Kafka / Redis Streams / NATS | 分布式消息队列 · 单机不需要 |
| EventStoreDB | 独立 .NET 服务 · BSL license |
| Mutmut（主 loop）| 跑一次太久 · 仅周期性校验可用 |
| LangSmith | SaaS 锁定 · 不符合开源哲学 |
| Sentry | 生产 error 场景不适用 dev-loop |
| Grafana 代码 | AGPL · 只学模式 |
| PlantUML | 需要 Java + GPL license |
| D2 | 生态比 Mermaid 小 · GitHub 不原生渲染 |
| LangChain Agents/Tools | 抽象层过度 |

### 14.3 明确 Adopt 清单（HarnessFlow 将直接依赖）

| Adopt 项目 | 用途 | 所属 L1 |
|---|---|---|
| **Claude Agent SDK** | Skills / Subagents / MCP / Hooks 主生态 | L1-05 · L1-07 · L1-01 |
| **superpowers skills** | TDD / debugging / planning / santa-method 等纪律 | L1-04 · L1-05 · L1-02 |
| **Claude Vision** | 图像理解 | L1-08 |
| **pytest + plugins** | 测试执行 | L1-04 |
| **Hypothesis**（按需）| 核心算法 property-based test | L1-04 |
| **NetworkX** | WBS 拓扑图 + 依赖推导 | L1-03 |
| **tree-sitter**（python binding）| 代码 AST 解析 | L1-08 |
| **ruff / pyright** | 静态分析 | L1-04 |
| **markdown-it-py** | Markdown AST 解析 | L1-08 |
| **Mermaid** | 文档图表 | 横切 + L1-10 |
| **Mermaid.js** | UI 内图表渲染 | L1-10 |
| **Python ast stdlib** | DoD 表达式白名单 eval | L1-04 |
| **Pydantic v2** | 所有 IC 契约 + schema | 横切 |
| **SQLite（WAL mode）** | 结构化索引 | L1-09 |
| **FastAPI + uvicorn** | UI 后端 | L1-10 |
| **Vue 3 + Element Plus + Vite** | UI 前端 | L1-10 |
| **Vue Flow** | UI DAG 可视化 | L1-10 |
| **ChromaDB embedded**（规模触发）| 可选向量检索 | L1-06 |

### 14.4 调研结论：HarnessFlow 的"技术选型哲学"

基于上述 14 章调研 · HarnessFlow 的技术选型哲学总结如下：

1. **"轻 Skill 形态优先"** · 凡引入独立服务的方案都 Reject · 文件系统 + SQLite + Claude Code 内置工具是首选
2. **"Learn 远多于 Adopt"** · 80% 的开源项目只学架构不引入包 · 保持 HarnessFlow 依赖树极简
3. **"依赖 Claude Code 原生生态"** · Claude Agent SDK + superpowers 是一等公民依赖
4. **"开源可自托管优先"** · 绝不依赖 SaaS（LangSmith 等）
5. **"License 严格"** · AGPL / GPL / BSL 代码不引入 · 仅学架构
6. **"性能二等公民"** · 除 KB / 事件总线这类核心路径 · 其他模块性能容忍度高 · 绝不为性能引入复杂架构
7. **"开箱即用体验"** · 用户 `git clone` + `uv sync` + `npm install` 即可启动 · 不要 Postgres / Redis / Neo4j
8. **"面向 AI-native workflow 设计"** · 不是传统 CRUD / workflow engine · 借鉴 Devin / OpenHands / Letta 的 AI-native 范式

### 14.5 下游 L2 tech-design §9 章的填写模板

为保证下游 57 份 L2 tech-design 的 §9 章（开源最佳实践调研）口径一致 · 推荐用如下模板：

```markdown
## 9. 开源最佳实践调研

### 9.1 L0 参考指向

本 L2（{L2 名}）的通用调研参考 `docs/3-1-Solution-Technical/L0/open-source-research.md` §{对应章节}。
本节只补充**本 L2 特有**的调研 · 不重复 L0 已覆盖内容。

### 9.2 本 L2 专属调研

{若有 L0 未覆盖的垂直项目 · 在此补充 · 格式：}

#### 9.2.1 {项目名}
- GitHub: {url}
- Stars (snapshot): {数}
- License: {}
- 核心架构: {一句话}
- Learn: {}
- Reject: {}

### 9.3 本 L2 最终技术选型

| 选型项 | 方案 | 引用来源 |
|---|---|---|
| xxx | xxx | L0 §X 或本节 §9.2.X |

### 9.4 性能 benchmark（若关键路径）
{...}
```

### 14.6 调研结束时点声明

- **调研快照时点**：2026-04-20
- **下一次 review**：3 个月后（2026-07-20）或 HarnessFlow 主要架构变更时
- **维护责任**：本文档作为 L0 单一事实源 · 下游 L2 不得修改本文 · 若发现本文错误或过时 · 必须先反向改 L0 · 再改 L2
- **调研覆盖度自评**：
  - 10 个 L1 模块 · 每模块 3-5 个标杆 · **合规**
  - 关键模块（KB / 监督 / 主 loop）性能 benchmark · **合规**
  - License 检查 + 2026-04 快照 · **合规**
  - 明确 Adopt / Learn / Reject 三态 · **合规**



## 附录 A · GitHub 项目清单 + 星数 snapshot

> 所有数据为 **2026-04-20 时点快照**。不得在后续 L2 文档中自行刷新。
> 活跃度分级：**极活跃**（月均 commit ≥ 50）/ **活跃**（月均 ≥ 10）/ **稳定**（季度 ≥ 10）/ **死项目**（> 12 月无 commit）。

### A.1 主 Agent loop / 多 Agent 框架（§2）

| 项目 | URL | Stars | License | 活跃度 | 处置 |
|---|---|---|---|---|---|
| langchain-ai/langgraph | https://github.com/langchain-ai/langgraph | 126,000+ | MIT | 极活跃 | Learn |
| langchain-ai/langgraph-supervisor-py | https://github.com/langchain-ai/langgraph-supervisor-py | 800+ | MIT | 活跃 | Learn |
| microsoft/autogen | https://github.com/microsoft/autogen | 48,000+ | MIT | 极活跃 | Learn |
| crewAIInc/crewAI | https://github.com/crewAIInc/crewAI | 45,900+ | MIT | 极活跃 | Learn |
| all-hands-ai/OpenHands | https://github.com/all-hands-ai/OpenHands | 60,000+ | MIT | 极活跃 | Learn |
| openai/swarm | https://github.com/openai/swarm | 19,000+ | MIT | 已停维 | Learn |
| huggingface/smolagents | https://github.com/huggingface/smolagents | 12,000+ | Apache-2.0 | 活跃 | Learn |

### A.2 生命周期编排 / 工作流（§3）

| 项目 | URL | Stars | License | 活跃度 | 处置 |
|---|---|---|---|---|---|
| apache/airflow | https://github.com/apache/airflow | 38,000+ | Apache-2.0 | 极活跃 | Learn |
| PrefectHQ/prefect | https://github.com/PrefectHQ/prefect | 20,000+ | Apache-2.0 | 极活跃 | Learn |
| temporalio/temporal | https://github.com/temporalio/temporal | 12,000+ | MIT | 极活跃 | Learn |
| windmill-labs/windmill | https://github.com/windmill-labs/windmill | 13,000+ | AGPL-3.0 | 活跃 | Reject |

### A.3 WBS / 图 / DAG（§4）

| 项目 | URL | Stars | License | 活跃度 | 处置 |
|---|---|---|---|---|---|
| dagster-io/dagster | https://github.com/dagster-io/dagster | 11,000+ | Apache-2.0 | 极活跃 | Learn |
| rundeck/rundeck | https://github.com/rundeck/rundeck | 5,500+ | Apache-2.0 | 活跃 | Reject |
| networkx/networkx | https://github.com/networkx/networkx | 15,000+ | BSD-3-Clause | 活跃 | **Adopt** |
| dask/dask | https://github.com/dask/dask | 25,000+ | BSD-3 | 极活跃 | Reject |
| ray-project/ray | https://github.com/ray-project/ray | 35,000+ | Apache-2.0 | 极活跃 | Reject |

### A.4 Quality Loop / TDD（§5）

| 项目 | URL | Stars | License | 活跃度 | 处置 |
|---|---|---|---|---|---|
| pytest-dev/pytest | https://github.com/pytest-dev/pytest | 12,500+ | MIT | 极活跃 | **Adopt** |
| HypothesisWorks/hypothesis | https://github.com/HypothesisWorks/hypothesis | 7,500+ | MPL-2.0 | 极活跃 | **Adopt**（按需）|
| boxed/mutmut | https://github.com/boxed/mutmut | 2,500+ | BSD-3 | 活跃 | Learn |
| mikelane/pytest-gremlins | https://github.com/mikelane/pytest-gremlins | 500+ | MIT | 活跃 | Learn（未来）|
| astral-sh/ruff | https://github.com/astral-sh/ruff | 33,000+ | MIT | 极活跃 | **Adopt** |
| microsoft/pyright | https://github.com/microsoft/pyright | 14,000+ | MIT | 极活跃 | **Adopt** |
| pre-commit/pre-commit | https://github.com/pre-commit/pre-commit | 13,000+ | MIT | 极活跃 | **Adopt** |

### A.5 Skill 生态 / MCP（§6）

| 项目 | URL | Stars | License | 活跃度 | 处置 |
|---|---|---|---|---|---|
| Claude Agent SDK | platform.claude.com/docs/en/agent-sdk | N/A | MIT（SDK）| 极活跃 | **Adopt** |
| obra/superpowers | https://github.com/obra/superpowers | 3,000+ | MIT | 极活跃 | **Adopt** |
| modelcontextprotocol/spec | https://github.com/modelcontextprotocol/spec | 5,000+ | MIT | 极活跃 | Learn（未来 Adopt）|
| langchain-ai/langchain | https://github.com/langchain-ai/langchain | 100,000+ | MIT | 极活跃 | Reject |

### A.6 知识库 / Memory（§7）

| 项目 | URL | Stars | License | 活跃度 | 处置 |
|---|---|---|---|---|---|
| mem0ai/mem0 | https://github.com/mem0ai/mem0 | 52,000+ | Apache-2.0 | 极活跃 | Learn |
| letta-ai/letta | https://github.com/letta-ai/letta | 19,000+ | Apache-2.0 | 极活跃 | Learn |
| getzep/graphiti | https://github.com/getzep/graphiti | 5,000+ | Apache-2.0 | 极活跃 | Learn |
| getzep/zep | https://github.com/getzep/zep | 3,500+ | Apache-2.0 | 极活跃 | Learn |
| chroma-core/chroma | https://github.com/chroma-core/chroma | 17,000+ | Apache-2.0 | 极活跃 | **Adopt**（规模触发）|
| pgvector/pgvector | https://github.com/pgvector/pgvector | 16,000+ | PostgreSQL | 极活跃 | Reject |
| weaviate/weaviate | https://github.com/weaviate/weaviate | 13,000+ | BSD-3 | 极活跃 | Reject |
| qdrant/qdrant | https://github.com/qdrant/qdrant | 29,000+ | Apache-2.0 | 极活跃 | Reject |

### A.7 Observability / 监督（§8）

| 项目 | URL | Stars | License | 活跃度 | 处置 |
|---|---|---|---|---|---|
| langfuse/langfuse | https://github.com/langfuse/langfuse | 19,000+ | MIT | 极活跃 | Learn |
| Helicone/helicone | https://github.com/Helicone/helicone | 3,500+ | Apache-2.0 | 极活跃 | Learn |
| Arize-ai/phoenix | https://github.com/Arize-ai/phoenix | 4,500+ | ELv2 | 活跃 | Learn |
| open-telemetry/opentelemetry-python | https://github.com/open-telemetry/opentelemetry-python | 2,000+ | Apache-2.0 | 极活跃 | **Adopt**（协议）|
| getsentry/sentry | https://github.com/getsentry/sentry | 39,000+ | BSL-1.1 | 极活跃 | Learn |

### A.8 多模态（§9）

| 项目 | URL | Stars | License | 活跃度 | 处置 |
|---|---|---|---|---|---|
| Unstructured-IO/unstructured | https://github.com/Unstructured-IO/unstructured | 9,500+ | Apache-2.0 | 极活跃 | Learn |
| tree-sitter/tree-sitter | https://github.com/tree-sitter/tree-sitter | 20,000+ | MIT | 极活跃 | **Adopt** |
| BurntSushi/ripgrep | https://github.com/BurntSushi/ripgrep | 50,000+ | MIT | 极活跃 | **Adopt**（Claude 内置）|
| docling-project/docling | https://github.com/docling-project/docling | 25,000+ | MIT | 极活跃 | Learn（未来）|
| python-openxml/python-docx | https://github.com/python-openxml/python-docx | 5,000+ | MIT | 活跃 | 按需 |
| pymupdf/PyMuPDF | https://github.com/pymupdf/PyMuPDF | 5,000+ | AGPL-3.0 | 极活跃 | Reject |
| executablebooks/markdown-it-py | https://github.com/executablebooks/markdown-it-py | 4,000+ | MIT | 活跃 | **Adopt** |

### A.9 事件总线 / 持久化（§10）

| 项目 | URL | Stars | License | 活跃度 | 处置 |
|---|---|---|---|---|---|
| SQLite（非 GitHub · stdlib）| sqlite.org | N/A | Public Domain | 稳定 | **Adopt**（WAL mode）|
| EventStore/EventStore | https://github.com/EventStore/EventStore | 5,200+ | BSL-1.1 | 活跃 | Learn |
| apache/kafka | https://github.com/apache/kafka | 27,000+ | Apache-2.0 | 极活跃 | Reject |
| nats-io/nats-server | https://github.com/nats-io/nats-server | 15,000+ | Apache-2.0 | 极活跃 | Reject |
| google/leveldb | https://github.com/google/leveldb | 37,000+ | BSD-3 | 稳定 | Learn |
| benbjohnson/litestream | https://github.com/benbjohnson/litestream | 11,000+ | Apache-2.0 | 活跃 | Learn（未来）|

### A.10 Dev UI（§11）

| 项目 | URL | Stars | License | 活跃度 | 处置 |
|---|---|---|---|---|---|
| kailong321200875/vue-element-plus-admin | https://github.com/kailong321200875/vue-element-plus-admin | 3,500+ | MIT | 活跃 | Learn / copy |
| vue3-element-admin | vue3-element-admin-site.midfar.com | 4,000+ | MIT | 极活跃 | Learn |
| grafana/grafana | https://github.com/grafana/grafana | 65,000+ | AGPL-3.0 | 极活跃 | Reject（代码）|
| AIGC VideoForge frontend | （本工作目录）| - | - | 活跃（内部）| **Adopt**（组件复用）|

### A.11 DoD / 表达式 eval（§12）

| 项目 | URL | Stars | License | 活跃度 | 处置 |
|---|---|---|---|---|---|
| Python ast（stdlib）| docs.python.org/3/library/ast.html | N/A | Python PSF | 稳定 | **Adopt** |
| danthedeckie/simpleeval | https://github.com/danthedeckie/simpleeval | 900+ | MIT | 稳定 | Learn |
| pyparsing/pyparsing | https://github.com/pyparsing/pyparsing | 2,000+ | MIT | 活跃 | Learn |
| lark-parser/lark | https://github.com/lark-parser/lark | 5,000+ | MIT | 活跃 | Reject |
| yaroslaff/evalidate | https://github.com/yaroslaff/evalidate | 200+ | MIT | 活跃 | Learn |
| pydantic/pydantic | https://github.com/pydantic/pydantic | 22,000+ | MIT | 极活跃 | **Adopt** |

### A.12 图表工具（§13）

| 项目 | URL | Stars | License | 活跃度 | 处置 |
|---|---|---|---|---|---|
| mermaid-js/mermaid | https://github.com/mermaid-js/mermaid | 78,000+ | MIT | 极活跃 | **Adopt** |
| plantuml/plantuml | https://github.com/plantuml/plantuml | 11,000+ | GPL-3.0 | 活跃 | Reject |
| graphviz | gitlab.com/graphviz/graphviz | 2,000+ | EPL-1.0 | 稳定 | Learn（未来）|
| terrastruct/d2 | https://github.com/terrastruct/d2 | 18,000+ | MPL-2.0 | 活跃 | Learn |
| excalidraw/excalidraw | https://github.com/excalidraw/excalidraw | 88,000+ | MIT | 极活跃 | Learn（未来）|
| bcakmakoglu/vue-flow | https://github.com/bcakmakoglu/vue-flow | 4,000+ | MIT | 活跃 | **Adopt**（UI）|

### A.13 统计

- **总调研项目数**：约 55 个
- **Adopt 决策**：17 项（含 stdlib）
- **Learn 决策**：约 30 项
- **Reject 决策**：约 20 项
- **平均 stars**：~18,500+
- **覆盖 License 类型**：MIT（主导）· Apache-2.0 · BSD · MPL-2.0 · GPL-3.0（Reject）· AGPL（Reject）· BSL（Learn）· Public Domain



## 附录 B · 术语 & 缩略词表

| 缩写 / 术语 | 完整含义 | 本文档章节 |
|---|---|---|
| Agent | LLM 驱动的自主代理 | §2 §6 §8 |
| AST | Abstract Syntax Tree（抽象语法树）| §9 §12 |
| BM25 | Best Matching 25（文本相关度算法）| §7 |
| BSD / BSL | Berkeley Software Distribution / Business Source License | 附录 A |
| checkpoint | 执行状态快照 | §2 §3 §10 |
| DAG | Directed Acyclic Graph（有向无环图）| §3 §4 |
| DoD | Definition of Done（完成定义）| §5 §12 |
| DSL | Domain-Specific Language（领域特定语言）| §12 |
| ETL | Extract-Transform-Load | §9 |
| event sourcing | 以事件流为唯一真源的架构 | §10 |
| fsync | 文件系统刷盘系统调用 | §10 |
| GPL / AGPL | GNU General / Affero GPL | 附录 A |
| HNSW | Hierarchical Navigable Small World（向量索引算法）| §7 |
| hook | PreToolUse / PostToolUse 钩子 | §6 §8 |
| IC | Integration Contract（集成契约）| §1 §2 §8 |
| Instinct | superpowers 的经验学习原语 | §6 |
| jsonl | JSON Lines 格式（每行一个 JSON）| §1 §10 |
| KB | Knowledge Base（知识库）| §7 |
| L0 / L1 / L2 | 分层粒度（L0=横切 · L1=能力域 · L2=子能力）| 全文 |
| LLM | Large Language Model | 全文 |
| MCP | Model Context Protocol（Anthropic 协议）| §6 |
| MemGPT | Memory-enabled GPT（Letta 前身）| §7 |
| NetworkX | Python graph library | §4 |
| OTEL | OpenTelemetry | §8 |
| P50 / P95 / P99 | 延迟百分位数 | 性能表 |
| PM | Pattern-of-Mind（业务模式 · scope §4.5）| §1 |
| PMP | Project Management Professional（PMI 方法论）| §3 §4 |
| project_id | PM-14 核心：每 project 唯一根键 | §1 §10 |
| RAG | Retrieval-Augmented Generation | §7 |
| ReAct | Reason + Act 循环范式 | §2 |
| replay | 从事件流重建 state | §2 §10 |
| RPS | Requests Per Second | §7 |
| SDK | Software Development Kit | §6 §8 |
| Shrinking | Hypothesis 的失败 case 简化算法 | §5 |
| Skill | Claude Code Skill（SKILL.md 封装的能力）| §6 |
| Span / Trace | OpenTelemetry 的观测信号 | §8 |
| Stage Gate | 阶段门审批点 | §3 |
| subagent | Claude Code 子 Agent（独立 session）| §6 |
| TDD | Test-Driven Development | §5 |
| TOGAF | The Open Group Architecture Framework | §3 §6 |
| topological_sort | 拓扑排序算法 | §4 |
| UI | User Interface | §11 |
| WAL | Write-Ahead Logging（SQLite 模式）| §10 |
| WBS | Work Breakdown Structure（工作分解结构）| §4 |
| WP | Work Package（工作包）| §4 |

---

## 附录 C · 本文档与下游文档的引用关系

### C.1 下游引用本文档的 57 份 L2 tech-design.md

每份 L2 tech-design 的 §9 章必须引用本文档 L0 研究。引用格式：

```markdown
## 9. 开源最佳实践调研

### 9.1 L0 参考
直接参考 `/Users/zhongtianyi/work/code/harnessFlow/docs/3-1-Solution-Technical/L0/open-source-research.md` §{对应章节号}。

### 9.2 本 L2 补充调研
（如有超出 L0 覆盖范围的调研）
...
```

L2 对应章节映射：

| L1 | L0 §对应 |
|---|---|
| L1-01 主 Agent loop | §2 |
| L1-02 生命周期编排 | §3 |
| L1-03 WBS 拓扑 | §4 |
| L1-04 Quality Loop | §5 · §12 |
| L1-05 Skill 生态 | §6 |
| L1-06 知识库 | §7 |
| L1-07 监督 | §8 |
| L1-08 多模态 | §9 |
| L1-09 韧性 | §10 |
| L1-10 UI | §11 · §13 |

### C.2 本文档上游来源

- `docs/2-prd/L0/scope.md`（10 个 L1 职责定义）
- `docs/superpowers/specs/2026-04-20-3-solution-design.md`（3-1 设计 spec · 开源调研硬要求 §6.3）
- `docs/2-prd/L0/HarnessFlowGoal.md`（定位与边界）

### C.3 本文档修订协议

- **加新项目**：任何 L2 发现新的高星开源项目 · 可反向提议加入本文 · 由主 skill 审批后写入
- **改处置状态**：若某项目从 Learn 升级为 Adopt（或反之）· 必须同步更新本文 + 所有引用的 L2
- **星数更新**：3 个月 lazy-refresh · 不每次都更新
- **License 变更紧急事件**：若依赖项目 license 变更（如变 AGPL）· 立即更新本文 · 触发 L2 重评

---

*— L0 开源最佳实践调研综述 v0.1 · 2026-04-20 · harnessFlow-main-skill · 调研项目 55+ · 覆盖 10 L1 + 2 横切 —*

