# harnessFlow

> Claude Code 总编排 / 总监督 / 总路由器 — 让点菜后餐厅自动把真能吃的菜端到嘴边

## Problem Statement

深度使用 Claude Code 的高级用户（已装 Superpowers + Everything Claude Code + gstack 三套生态）面对长流程 / 多模块 / 多阶段任务时，没有任何一个组件扛"端到端真完成保障 + 总编排"的角色：现有 `method3.md` 只是命令速查表（"小任务别上重流程"等口号），缺显式判断逻辑、缺真完成 gate、缺主动监督、缺纠偏机制、缺自我进化。结果：方案 C 跑 P20 没真出片就汇报完成（菜放锅里就说好了）、中途被 skill 反复问"水泥到了要不要砌墙"型废问题、跨会话目标漂移、相同假完成陷阱反复踩。

## Evidence

- **真实失败案例（2026-04-16）**：aigcv2 P20 任务用 method3 方案 C，没做端到端出片验证（无 mp4 / 无 OSS key / 服务未起）就宣告完成 — 用户截图反馈「先用 ECC `e2e` + SP `verification-before-completion` 手工验一次再说」
- **method3.md 现状**：35 行 / 2.7KB 速查表，只到"体量→命令"映射 + 3 条经验硬规则，没有 DoD / Verifier / 纠偏 / 进化任何机制
- **三套库覆盖率调研**：SP 14 + ECC 183 + gstack 9 个能力，覆盖 ~60% 真完成 / 纠偏 / 进化 / 编排所需，但缺 5 处关键桥接（routing matrix 版本化、假完成 trap catalog、task-level state machine、路由决策引擎、`pre:task:complete` hook）
- **公开方案验证（LangGraph / AutoGen / CrewAI / Devin / OpenHands）**：所有公开 multi-agent harness 都未内置 failure archive；AutoGen `is_termination_msg` 依赖 LLM 自报 "TERMINATE" 是典型假完成反模式；最接近 Supervisor 的公开实现 = LangGraph sidecar interrupt + AWS Step Functions heartbeat
- **memory 累积反馈**：`feedback_workflow_scheme_c.md` (aigcv2 长周期推进经验)、`feedback_real_completion.md` (真完成原则)、`feedback_prp_flow.md` (PRP 流程纠偏)

## Proposed Solution

构建 `harnessFlow` — 一个**只编排不造轮**的总指挥 skill，外加一个**全程在线只读不写**的 Supervisor subagent 副驾，加三大保障引擎（真完成 / 纠偏 / 进化）。

主 skill 在用户调 `/harnessFlow` 后做 2~3 轮澄清 → 识别任务体量(XS-XXL+)/类型 → 推荐编排路线 → 用户确认 → 调度现有 SP/ECC/gstack 能力按路线执行 → Supervisor 全程跟进 → 末端独立 Verifier 用机器可执行 DoD 表达式收口 → post-mortem 写回结构化 failure-archive 驱动下一次进化。

为什么这个方案 vs 替代方案：
- ❌ 写新 skill 框架 — 违反"只编排不造轮"硬约束 + 与 SP/ECC/gstack 重复
- ❌ 全 LLM 黑盒路由 (CrewAI Hierarchical 模式) — 不可审计 + 易漂移 + 失败案例多
- ❌ 完全静态 SOP (MetaGPT / ChatDev) — 灵活性差不适合动态分支
- ✅ 确定性 DAG 骨架 + LLM 路由仅用于真分叉 + 机器可验证 DoD + Supervisor 主动监督 + 结构化 failure archive — 公开方案验证的工程化最佳实践组合

## Key Hypothesis

我们相信 **harnessFlow（编排器 + Supervisor + 三引擎）** 能把单人 Claude Code 用户的非平凡任务 **假完成率从 ~30% 降到 0%** 且 **中途废问题数降到 ≤1 次/任务**。我们会用 **真出片 P20 任务 + aigc 后端 feature + Vue 页面** 三个测试任务的端到端结果（artifact 存在 + 行为验证 + 质量 diff 全 PASS）来证明。

## What We're NOT Building

- **多人协作 / 团队场景** — v1 只单人单会话；多人协调留 v2
- **CI/CD 集成（webhook / GH Action）** — 留 v2
- **完全无人值守** — 真分叉/不可逆动作必须由用户决策
- **harness 自动改自己代码** — 进化只输出"建议进化点"等用户审批，自动写代码不可控
- **多 LLM / 跨模型路由** — v1 只 Claude Code
- **重新发明 SP/ECC/gstack 已有能力** — 严格只编排不造轮，仅 5 处空白做最小桥接

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| 真完成率 | 100% | 任意路线宣告完成时 Verifier 必须 PASS（artifact 存在 + 行为验证命令成功 + DoD 布尔表达式 eval=True）|
| 中途废问题数 | ≤1 次/任务 | task-board 记录所有 user-prompt 事件，按"真分叉/不可逆动作/原意冲突"分类，非红线打断 = 废问题 |
| 假完成 trap 命中率 | ≥95% | 内置 trap catalog 对历史失败案例（如 P20）回放，验 Supervisor + Verifier 能拦下 |
| 路线选准率 | ≥80% | 推荐路线被用户接受 vs 改路线 |
| 跨会话目标保真 | 100% | goal-anchor 在 session resume 后与原始一致（diff = 0）|
| 9 类输出物全产出 | 100% | harnessFlow.md / method3.md / flow-catalog.md / routing-matrix.md / state-machine.md / task-board-template.md / delivery-checklist.md / README.md + 主 skill prompt |

## Open Questions

- [ ] DoD 表达式语法用 Python boolean / JSON Schema / 自定义 DSL? — 倾向 Python boolean (Verifier subagent eval)，需实测
- [ ] Supervisor 加在 PostToolUse hook 是否会显著增加每步延迟和 token 成本? — 需实测，可考虑事件触发为主 + 周期 wake-up 为辅
- [ ] gstack 的 "Skill routing" 优先级机制 vs harnessFlow 主 skill 是否冲突? — 需在 CLAUDE.md 显式声明 harnessFlow > gstack > ECC > SP
- [ ] failure-archive.jsonl 跨项目共享 vs 每项目独立? — 倾向每项目独立 + 全局只读视图
- [ ] Supervisor "准实时"（PostToolUse hook 触发）对"忘开火"型干预够不够? 某些场景需要在 PreToolUse 拦
- [ ] MVP 是否只跑通路线 C，B/D 仅文档化，A/E/F 留 v1.1? — 建议是

---

## Users & Context

**Primary User**
- **Who**: 单人深度 Claude Code 用户（用户本人 + 同类）；同时装 SP/ECC/gstack 三套生态；工作流横跨 aigc 后端、aigc 前端 (Vue)、aigcv2 视频出片 LangGraph、aipdd PyQt6、化学课件 Python、Skill 库维护
- **Current behavior**: 接到任务 → 自己回忆"用 method3 哪条规则" → 手动选 skill 序列 → 中途被 skill 反复打断问废问题 → 任务复杂时跨会话目标飘走 → 完成时凭感觉报，缺端到端验证 → 出问题后无统一 retro 写回机制
- **Trigger**: 接到一个非平凡任务 / bug / feature / 出片 / 重构，意识到"这个任务要协调多个 skill 但我懒得想"
- **Success state**: 调 `/harnessFlow` → 简短 2~3 轮澄清 → harness 自动跑完 → 拿到能直接消费的 artifact（mp4 路径、可访问 URL、可执行命令、screenshot）+ 简短 retro

**Job to Be Done**
When 我接到一个非平凡任务（修 bug / 加 feature / 重构 / 出片）不想自己想用哪些 skill 怎么串、不想被问废问题、不想最后发现没真完成，
I want to 把任务交给 harnessFlow 让它自动分诊+路由+监督+收口，
so I can 直接拿到可消费 artifact，全程只在真分叉/真卡死时被打断。

**Non-Users**
- 没装 SP/ECC/gstack 的用户（依赖太多）
- 单次 XS 级小修任务用户（harness 启动成本 > 任务成本）
- 想完全不参与决策的纯托管用户（harness 仍需 2~3 轮澄清 + 真分叉时仍要用户决策）
- 团队多人协作场景（v1 不支持）

---

## Solution Detail

### Top-level Architecture

```
       ┌─ Supervisor Agent (用户的眼睛+大脑, 全程在线, 主动)
       │     目标锚定 / 实时进度 / 主动提醒 / 前瞻分析
       │              ↓ 持续看着
harnessFlow 主 skill ──┬─ 真完成引擎: DoD布尔表达式 + 独立Verifier + 三段证据链 + trap catalog
       (总指挥)        ├─ 纠偏引擎: 三层雷达 + 多源信号 + 4级retry ladder + 审计
       │              └─ 进化引擎: 强制retro + 结构化failure-archive + matrix版本化 + 人审批
       │
       └─ 客人点菜入口: 2~3轮澄清 → 体量/类型识别 → 路由推荐 → 用户选 → 执行 → 收口
```

### 三引擎（核心机制）

**1) 真完成引擎**
- **DoD 布尔表达式**（机器可执行，不依赖 LLM 自报）
  - 例: `(artifact.path exists) AND (curl http://localhost:8000/produce returns 200) AND (mp4.duration > 0) AND (pytest exit_code == 0)`
  - 按任务类型预置模板库（视频出片 / 后端 feature / UI feature / 文档 / 重构）
- **独立 Verifier subagent**（执行/审查分离）
  - 不参与执行，只接 DoD 表达式 + 完成证据 → eval → PASS/FAIL
  - 强制做：物理存在校验 / 重跑 DoD 命令 / 关键路径 sample 抽测
  - FAIL → 任务**禁止汇报完成**，强制打回执行者
- **三段证据链**（缺一不可）：存在证据 + 行为证据 + 质量证据
- **假完成 trap catalog**（基于失败案例归纳，结构化 jsonl）
  - "代码 push 完了" / "build green" / "Phase X 通过" / "测试全过" / LLM 说 "TERMINATE" / Phase 4 通过即报完成 → 触发警报

**2) 纠偏引擎**
- **三层偏航雷达**

| 层 | 信号 | 处理 | 打断用户 |
|---|---|---|---|
| L1 微 | 单步 test fail / 工具错 / 超时 50%+ | retry-same（≤2 次） | 否 |
| L2 中 | 阶段 timeout / artifact 不符 / 多次 L1 失败 / context 临界 | switch-skill / scope down | 否（除决策） |
| L3 大 | 多次 L2 失败 / DoD 不可达 / Verifier 反复 FAIL / 路线根本错 | 暂停+报告"切路线 Y / 改 DoD" | **是** |

- **4 级 retry ladder**：L0 retry-same → L1 retry-tweaked + scope down → L2 switch-skill / interrupt+HITL → L3 force finalize degraded OR escalate-user
- **多源信号**：hook 输出 / subagent status / Verifier 中间评估 / context budget watcher / time budget watcher / cost budget watcher
- **纠偏审计**：每次纠偏写入 task-board（触发信号 / 层级 / 动作 / 结果）

**3) 进化引擎**
- **强制 post-mortem**：任务收口前必跑，产出 retro report（DoD 实际 diff / 路线偏差 / 纠偏次数 / Verifier FAIL 次数 / 用户打断次数 / 耗时成本 vs 估算 / 新 trap / 新有效组合）
- **三类记忆分级写回**：route-outcome（路线 × 任务类型 × 体量 → 成功率/耗时/gap）/ anti-pattern（新 trap → 喂 Verifier）/ combination（新有效组合 → 喂路由器）
- **routing-matrix 版本化**：matrix.json 带版本号，每 N 次任务触发 review，权重数据驱动 + 人审批 + PR
- **failure-archive.jsonl**（最高优先级输入）：结构化字段 `{node, error_type, input_hash, retry_count, final_outcome, frequency, root_cause, fix, prevention}`
- **进化边界**：harness 不自动改自己代码，只输出"建议进化点"等用户审批合入下一版

### Supervisor Agent（架构级第 4 块）

- **定位**：用户的眼睛+大脑全程在线；不执行不写代码不调工具，专做"看+想+提醒"
- **部署**：subagent + PostToolUse hook + 周期 wake-up；只读权限
- **4 大职责**：目标锚定（goal-anchor 不可变）/ 实时进度跟踪 / 主动提醒 / 前瞻分析（看接下来 1-3 步）
- **6 类干预**：忘开火 / 漏菜 / 走偏 / 节奏失衡 / 顺序错 / 冗余
- **3 种打断红线**（其他不打断）：
  1. DRIFT_CRITICAL（任务方向偏离原意）
  2. DOD_GAP_ALERT（关键 DoD 项被跳过）
  3. IRREVERSIBLE_HALT（即将做不可逆动作但前置缺失）
- **结构化输出**：`{status, diagnosis, suggested_action, severity, evidence}` 主 skill 机器可解析
- **进化反哺**：所有提醒/中断进 retro，"同类任务连续报警"→ 调 routing matrix 权重

### Core Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | `/harnessFlow` 主 skill (2~3 轮澄清 + 路由 + 监督 + 收口) | 命门 |
| Must | Supervisor subagent (6 类干预 / 3 红线 / 只读) | 架构补全 |
| Must | DoD 布尔表达式模板库 (视频/后端/UI 三类) + Verifier subagent | 真完成 |
| Must | task-board.json + failure-archive.jsonl + goal-anchor | 状态持续 |
| Must | 路线 C 端到端跑通 (XL 级 PRP 全链重构版) | MVP 验证 |
| Must | 重构 method3.md 为方法论文档 (真完成第一原则) | 用户硬要求 |
| Must | 9 类输出物全产出（顶层架构 / method3 / flow-catalog / routing-matrix / state-machine / task-board-template / delivery-checklist / README + 主 skill prompt） | 需求文档第九条 |
| Should | 路线 A/B/D（XS-L 体量）+ routing-matrix.json 第一版 | 覆盖常用任务 |
| Should | 纠偏 4 级 retry ladder + post-mortem 自动化 | 闭环 |
| Should | Supervisor 6 类干预全开（v1 先做忘开火/漏菜/走偏 3 类） | 增量增强 |
| Could | 路线 E/F（特殊场景）+ Supervisor 时间触发周期 check + cost budget guard + cross-session resume | 锦上添花 |
| Won't | 团队/CI/无人值守/自改代码/多 LLM | v2+ |

### MVP Scope

- 主 skill + Supervisor + Verifier subagent 三个核心 prompt
- 路线 C 端到端跑通 + DoD 模板（视频出片 + 后端 feature 两类）
- task-board.json + failure-archive.jsonl 落地 schema
- Supervisor 实现"忘开火 / 漏菜 / 走偏" 3 类干预
- 重构 method3.md 为以"真完成"为根的方法论
- harnessFlow.md 顶层架构文档
- README.md 入口
- **MVP 验收**：拉一次 P20 真出片任务全程跑 harnessFlow → Verifier PASS（mp4 + OSS key 都能贴）→ retro 自动生成 → 用户打断次数 ≤1

### User Flow（关键路径）

```
用户: /harnessFlow
  ↓
主 skill: 2~3 轮澄清 (任务目标/交付物/类型/体量/风险/验证强度)
  ↓
主 skill: 识别 → 推荐 ≥2 候选路线 + 推荐第一选
  ↓
用户: 选路线 (or 用主 skill 推荐)
  ↓
主 skill: 锁 goal-anchor + 生成 DoD 表达式 + 初始化 task-board + 拉起 Supervisor
  ↓
主 skill: 按路线调度 SP/ECC/gstack 能力 (确定性 DAG + 真分叉用 LLM 路由)
  ↓ ←─┐
Supervisor 持续看 (PostToolUse hook + 周期) → INFO/WARN/BLOCK
  ↓ →─┘ (BLOCK → 主 skill 暂停 / 提醒用户)
末端: Verifier subagent eval DoD → PASS/FAIL
  ↓ (FAIL → 纠偏 ladder → 重跑)
PASS → post-mortem 强制 → 写回 retro / failure-archive / matrix
  ↓
主 skill: 收口汇报 (artifact 路径 + 行为命令 + 质量 diff)
```

---

## Technical Approach

**Feasibility**: HIGH for MVP (~60% 现成能力可直接复用) / MEDIUM for full (~40% 桥接需自建但都是文档/schema/小 wrapper，无需新 framework)

**Architecture Notes**
- 主 skill = 总指挥 + 客人点菜入口；本身只做调度 + 路由 DSL，规则放在 routing-matrix.json / state-machine.md 文档而不是塞进 skill prompt（避免主 skill 过长 LLM 决策质量下降）
- Supervisor = sidecar subagent，由主 skill 在路线启动时拉起；触发节奏 = PostToolUse hook + 周期 wake-up
- 三引擎 = 调度现有能力 + harnessFlow 自定义桥接（5 处空白：routing-matrix 版本化 / trap catalog / state machine / 路由决策引擎 / `pre:task:complete` hook）
- 状态持久化 = `task-board.json` (任务级) + CLAUDE.md goal-anchor block (跨会话 anchor) + ECC `save-session/resume-session`
- DoD = Python boolean expression 字符串，Verifier subagent 用 eval（沙盒）执行
- failure-archive = `harnessFlow /failure-archive.jsonl` 每项目独立 + 全局只读视图

**集成现有生态（Phase 3 调研）**

| 层 | 复用能力 | 来源 |
|---|---|---|
| 编排/澄清 | brainstorming / prp-prd / prp-plan | SP / ECC |
| 真完成 | verification-before-completion / e2e-runner / agent-eval / verification-loop / browser-qa / tdd-guide / *-build-resolver / code-reviewer | SP + ECC |
| 纠偏 | loop-operator / harness-optimizer / autonomous-agent-harness / continuous-agent-loop / careful / hooks (block-no-verify, commit-quality) | ECC + gstack |
| 进化 | continuous-learning-v2 / learn / learn-eval / retro / episodic-memory / learnings.jsonl | ECC + SP + gstack |
| 状态持续 | save-session / resume-session / using-git-worktrees / gstack-timeline-log | ECC + SP + gstack |
| Gates | plan-CEO/Design/DevEx/Eng-review / ship / qa / review / document-release / quality-gate | gstack + ECC |

**Technical Risks**

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| subagent 不能真实时监听 → Supervisor 反应延迟 | M | PostToolUse hook + 周期 wake-up + 关键事件优先；准实时不是真实时是接受范围 |
| gstack/ECC/SP 三套库版本升级不兼容 | M | routing-matrix.json 版本锁 + 每月回归 + failure-archive 监控 |
| 主 skill prompt 过长 → LLM 决策质量下降 | H | 主 skill 只装调度逻辑 + 路由 DSL，规则放外部文档；规则用 routing-matrix.json 数据驱动而非长 prompt |
| Supervisor 报警太多 → 用户疲劳 | M | INFO/WARN/BLOCK 三级，只 BLOCK 红线打断用户；其他对主 skill 提醒主 skill 自处理 |
| DoD 表达式写不好 → 假完成依然漏 | H | 按任务类型预置 DoD 模板库 + Verifier 必须重跑命令 + trap catalog 兜底 |
| gstack "Skill routing" 与主 skill 优先级冲突 | M | CLAUDE.md 显式声明 harnessFlow > gstack > ECC > SP；主 skill 启动时检测并报告冲突 |
| 全局 token / cost 超预算 | M | budget guard 在 Supervisor 监听，临界时强制 force finalize degraded |

---

## Implementation Phases

<!--
  STATUS: pending | in-progress | complete
  PARALLEL: phases that can run concurrently (e.g., "with 3" or "-")
  DEPENDS: phases that must complete first
  PRP: link to generated plan file once created
-->

| # | Phase | Description | Status | Parallel | Depends | PRP Plan |
|---|-------|-------------|--------|----------|---------|----------|
| 1 | 重构 method3.md | 速查表 → 真完成第一原则方法论 | complete | - | - | plans/method3-refactor.plan.md |
| 2 | 顶层架构 harnessFlow.md | 三引擎 + Supervisor + 与 SP/ECC/gstack 边界 | complete | with 3 | 1 | plans/harnessFlow-architecture.plan.md |
| 3 | 6 路线设计 flow-catalog.md + routing-matrix.md | A~F 路线 + 路由矩阵第一版 | complete | with 2 | 1 | plans/flow-catalog-routing-matrix.plan.md |
| 4 | 状态机 + 模板 | state-machine.md + task-board-template.md + delivery-checklist.md | complete | - | 2, 3 | plans/phase4-state-machine-templates.plan.md |
| 5 | 主 skill prompt | 客人点菜 + 2~3 轮澄清 + 路由 + 监督收口 | complete | with 6 | 4 | plans/phase5-main-skill-prompt.plan.md |
| 6 | Supervisor + Verifier subagent | DoD 模板库 + 6 类干预 + 3 红线 | complete | with 5 | 4 | plans/phase6-supervisor-verifier.plan.md |
| 7 | failure-archive schema + auto-retro | 结构化 jsonl + retro 模板 + 路由权重审计 | complete | - | 5, 6 | plans/phase7-failure-archive-auto-retro.plan.md |
| 8 | 端到端验证 | self-test + archive CLI + P20 handoff（不污染 aigc）| complete | - | 7 | plans/phase8-e2e-validation.plan.md + phase8-validation-report.md |

### Phase Details

**Phase 1 — 重构 method3.md**
- **Goal**: 把速查表升级为以"真完成"为根的方法论文档
- **Scope**: 第一原则（真完成 + 客人点菜 + 不重复造轮）/ 任务分诊规则 / 路由规则 / 编排路线规则 / 监督推进规则 / 验证 QA review gate 规则 / 交付收口规则
- **Success signal**: 文档 ≥ 旧版 5 倍体量，每条原则有"Why + How to apply + 反例"，旧 6 条经验规则全部升级为显式判断逻辑

**Phase 2 — 顶层架构 harnessFlow.md**
- **Goal**: 写顶层架构文档说明 harnessFlow 是什么 / 边界 / 协同方式
- **Scope**: 三引擎详解 / Supervisor 详解 / 与 SP/ECC/gstack 边界 / 与 Claude Code 原生能力（subagent / hooks / skill / MCP / memory）协同 / 5 处自定义桥接列表
- **Success signal**: 任意读者能在 10 分钟内理解 harnessFlow 是什么、调度什么、为什么不重复造轮

**Phase 3 — 6 路线 flow-catalog.md + routing-matrix.md**
- **Goal**: A~F 编排路线 + 任务类型 × 体量 → 路线推荐矩阵
- **Scope**: 每条路线含简称(2~3 词) / 定位 / 适用 / 调度顺序 / 优点 / 缺点 / 切换条件 / 风险控制点 + G+ 预留扩展位 + 路由矩阵分规划/执行/验证/QA/review/delivery 层
- **Success signal**: 任意 XS-XXL 任务类型组合都能在矩阵里找到推荐路线 + ≥1 备选

**Phase 4 — 状态机 + 模板**
- **Goal**: state-machine.md（任务流转） + task-board-template.md（状态字段） + delivery-checklist.md（交付清单）
- **Scope**: state machine 含路线启动 → 阶段切换 → 偏航处理 → 收口；task-board 字段含任务名/目标/交付物/类型/复杂度/路线/阶段/skill/agent/下一 gate/风险/测试/review/QA/交付/偏航/结论/下一步；delivery-checklist 含强制 DoD 验证清单
- **Success signal**: 模板能直接 fork 用于一个真任务

**Phase 5 — 主 skill prompt（与 6 并行）**
- **Goal**: harnessFlow 主 skill 提示词草案
- **Scope**: 启动提问 / 2~3 轮澄清 / 体量识别 / 类型识别 / 路由逻辑 / 推荐逻辑 / 用户选择逻辑 / 执行监督逻辑 / 防跑偏逻辑 / 交付收口逻辑
- **Success signal**: skill 能跑通 P20 任务从澄清到推荐路线

**Phase 6 — Supervisor + Verifier subagent（与 5 并行）**
- **Goal**: Supervisor agent prompt + Verifier agent prompt + DoD 表达式模板库
- **Scope**: Supervisor 6 类干预（v1 先 3 类）+ 3 红线 + 结构化输出；Verifier eval 协议；DoD 模板库（视频出片 / 后端 feature / UI feature / 文档 / 重构 5 类）
- **Success signal**: 单元测试 — 拿 P20 假完成案例回放，Supervisor + Verifier 必须拦下

**Phase 7 — failure-archive schema + auto-retro**
- **Goal**: 结构化 failure-archive.jsonl + post-mortem 自动模板
- **Scope**: jsonl schema (18 必填 + 8 可选 / JSON Schema draft-07) + retro report 11 项模板 + 每任务收口前强制触发逻辑 + 路由权重审计触发条件（每 20 次任务，**只建议不改 matrix**）
- **Delivered (2026-04-17)**:
  - `schemas/failure-archive.schema.json` + `schemas/retro-template.md`
  - `archive/writer.py` (schema 校验 + fcntl lock 3×5s retry) / `archive/auditor.py` (每 20 条审计 42 cell；失败率 >0.5 ≥3 样本 → 降权 0.8×；低失败率 ≥10 样本 → 升权 1.1× 上限 1.0；**只写 audit-reports/ 不改 matrix**) / `archive/retro_renderer.py` (11 helpers + 幂等 append)
  - `subagents/failure-archive-writer.md` v2（调 writer + 可选 audit） + `subagents/retro-generator.md`（新增）
  - `harnessFlow-skill.md § 8.6` 强制链伪代码 + § 10 反模式 14/15/16
  - `delivery-checklist.md § 7.2` + `hooks/Stop-final-gate.sh` Phase 7 门卫（retro 11 段 + archive_entry_link + schema 校验 + ABORTED 归档强制）
  - `method3.md § 7.3` / § 8.8-8.10（进化边界硬线 + 三条 Phase 7 反模式）
  - `task-board-template.md` 补 `archive_entry_link` / `audit_link` 字段 + `final_outcome.false_complete_reported` enum
  - 85 pytest 全绿（Phase 6 31 + Phase 7 54）
- **Success signal**: ✅ P20 假完成案例完整闭环跑通（detect → verify FAIL → retro 11 段 → archive jsonl → audit 可触发建议 → 人审建议 PR）

**Phase 8 — 端到端验证**
- **Goal**: 用 harnessFlow 自己验证 harnessFlow（自举）；给 harnessFlow 达到"可交付"标准（他人全新环境 10 min 内能跑通）
- **Scope**（重新设计后）: ① self-test 脚本（元技能验证 M 可逆 → 路线 B）② archive CLI `python -m archive` list/audit/stats（后端 feature M 中风险 → 路线 B）③ P20 真出片 handoff 脚本（XL 不可逆 → 路线 C；按键触发，消耗 aigc 配额）。**三任务均不污染 aigc**（原 8.1/8.2 改为 harnessFlow 内部任务）
- **Delivered (2026-04-17)**:
  - 激活层：`.claude/skills/harnessFlow.md` + `.claude/agents/harnessFlow-*.md × 4` + `.claude/settings.local.json` hooks × 2
  - 文档层：`README.md` + `QUICKSTART.md` + `phase8-validation-report.md`
  - 脚本层：`setup.sh`（一键安装，幂等）+ `scripts/self-test.sh`（6 模块 11 检查）+ `scripts/run-p20-validation.sh`（9 步触发流水线）+ `scripts/verify-p20-artifacts.py`（DoD_P20 8 子契约 + 自动产四件套）
  - 代码层：`archive/__main__.py` + `archive/tests/test_cli.py`（5 case）
  - 运行时四件套：`task-boards/p8-0-smoke.json` + `p8-1-self-test.json` + `p8-2-archive-cli.json` / `verifier_reports/p8-1-self-test.json` + `p8-2-archive-cli.json`（verdict=PASS）/ `retros/p8-1-self-test.md` + `p8-2-archive-cli.md`（各 11 段）/ `failure-archive.jsonl` L1 + L2
  - Phase 状态：Phase 1-8 全部 complete
- **Success signal**: ✅ 真完成率 2/2=100%（已跑任务）| 用户打断 = 0/任务 | Verifier 全 PASS | retro 全自动生成（11 段）| pytest 85 → 90（+5 CLI test，无回归）| Stop gate 收口 3 次 exit=0 | P20 handoff 脚本就绪（按键触发）

### Parallelism Notes

- Phase 2 + Phase 3 可并行（独立设计文档，依赖 Phase 1 第一原则）
- Phase 5 + Phase 6 可并行（主 skill 和 Supervisor 一起设计降低耦合误差）
- 其他严格顺序

---

## Decisions Log

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| harnessFlow 是什么 | 总编排 + Supervisor 副驾 + 三引擎 | 新 skill 框架 / 全 LLM 路由 / 静态 SOP | 用户硬约束 + 公开方案验证最佳实践 |
| 是否加 Supervisor Agent | 加 | 只靠三引擎 | 三引擎都被动/事后；Supervisor 主动/全程才能拦"忘开火"型 |
| DoD 形式 | 机器可执行布尔表达式 | LLM 自报清单 / JSON Schema | 反 AutoGen `is_termination_msg` 假完成陷阱 |
| 路由形式 | 确定性 DAG + 真分叉用 LLM | 全 LLM 黑盒 / 全静态 SOP | CrewAI/AutoGen 黑盒不可审计；MetaGPT 太死 |
| 是否重构 method3 | 必须重构（不照搬） | 增量补丁 | 用户硬要求 + 旧版只是速查表 |
| 真完成 vs 路由美感优先级 | 真完成 > 路由美感 > skill 复用率 | 反向 | 用户硬约束 + 方案 C 失败教训 |
| Supervisor 权限 | 只读 | 可写可调工具 | 避免和执行 agent 抢手 + 公开方案 sidecar 模式 |
| MVP 范围 | 路线 C 端到端 + 3 类干预 + 9 输出物 | 6 路线全跑通 | 时间预算 1-2 周 |
| failure-archive 范围 | 每项目独立 + 全局只读视图 | 全局共享 | 项目隔离 + 跨项目可学 |
| 进化边界 | 输出建议等用户审批 | harness 自动改自己代码 | 不可控风险 |

---

## Research Summary

**Market Context**

- **LangGraph**: supervisor + conditional_edge + interrupt + checkpoint — Supervisor agent 模式的工程界最完整参考；本地 aigcv2 `supervisor_graph.py` 已用过
- **AutoGen**: GroupChat + termination 的 `is_termination_msg` 是典型假完成反模式（LLM 为终止对话虚报完成）
- **CrewAI**: hierarchical Manager LLM 全黑盒路由 → 不可审计反例
- **OpenAI Swarm**: handoff 工具显式传递控制 + `input_filter` 截断历史避免 context 污染 — 借鉴
- **MetaGPT/ChatDev**: 硬编码 SOP 流水线 — 灵活性差不适合动态分支
- **Devin/OpenHands**: `is_stuck` 重复动作检测 + git diff artifact 持久化 + budget guard — 借鉴
- **Anthropic Claude Code**: hooks(Pre/Post/Stop/SubagentStop) + sub-agent + skill + memory 是 harnessFlow 的底层操作系统

**Technical Context**

- **现成能力 ~60% 覆盖**：SP 14 + ECC 183 + gstack 9 个能力可直接调度
- **5 处空白需自建桥接**（最小化）：routing-matrix 版本化 / 假完成 trap catalog / task-level state machine / 路由决策引擎 / `pre:task:complete` hook
- **零 major 冲突**：三库领域分工清晰，可同库共存；只需 CLAUDE.md 声明优先级
- **gstack `Skill routing` 检查机制**：harnessFlow 在 CLAUDE.md 显式声明优先级即可
- **吸收的关键设计**（≥7 条）：
  1. 结构化 DoD = 状态字段断言 + 产物存在性，不依赖 LLM 自报
  2. 两级路由 = 确定性 DAG（结构化顺序）+ LLM 路由（仅真分叉），每次 LLM 路由记 `reason`
  3. 4 级 retry ladder + escalation
  4. Proactive Supervisor = 目标锚定 thread + PostToolUse hook 触发式 interrupt
  5. failure archive 结构化字段 + 路由权重自动调
  6. 跨会话 artifact = checkpoint + OSS 双写 + 版本号
  7. PostToolUse hook 实现 schema 自动验证门
- **规避的反模式**（≥4 条）：
  1. LLM 自报完成（AutoGen `is_termination_msg`）
  2. 全流程 LLM 路由（CrewAI/AutoGen 黑盒）
  3. 无界 retry 循环（耗 budget 不终止）
  4. post-mortem 遗忘（无 failure archive 重蹈覆辙）

---

*Generated: 2026-04-16*
*Status: DRAFT - 待 /prp-plan 拆解为各 Phase 的实施计划*
