# harnessFlow · 架构蓝图

> Claude Code 总编排器 harnessFlow 的顶层架构文档 — 回答"是什么、由哪些组件组成、怎么协作、边界在哪"。

**版本**: v1.0 — 2026-04-16 — harnessFlow MVP
**状态**: Draft（PRD Phase 2 产出）
**读者**: 新读者 / 贡献者 / 主 skill 开发者 / Supervisor 与 Verifier subagent 的 prompt 作者

**与 method3.md 的分工**：本文档 = **架构蓝图**（what + who + where），回答"harnessFlow 是什么、由哪些组件组成、各组件在哪、怎么接入"。`method3.md` = **方法论规则**（how to judge），回答"怎么分诊、怎么路由、什么叫完成、什么时候该打断"。两份文档互引不互重 — 架构决策改本文档；规则决策改 method3.md。

---

## § 1 定位与边界

本章回答：harnessFlow 是什么 / 不是什么 / 一句话价值。

### 1.1 是什么

harnessFlow 是 Claude Code 之上的**总编排器 + 总监督 + 总路由器**。

- **总编排器**：用户给任务 → harnessFlow 调度现有 SP / ECC / gstack 能力按路线执行 → 末端收口交付
- **总监督**：Supervisor agent 副驾全程在线（只读），用户的"眼睛+大脑"守护目标不漂移、DoD 不漏、关键前置不缺
- **总路由器**：把任务分诊为「体量 × 类型 × 风险」三维向量 → 从路由矩阵映射到路线 + 具体 skill/command/agent/hook/MCP 组合

### 1.2 不是什么

- ❌ 不是新的 multi-agent 框架（LangGraph / AutoGen / CrewAI 的替代品）
- ❌ 不是新的 skill 库（SP / ECC / gstack 的替代品）
- ❌ 不是 workflow engine（不编排业务逻辑，只编排 Claude Code 任务的完成路径）
- ❌ 不是 multi-agent chat 系统（agent 之间不自由对话，由 harnessFlow 显式路由）
- ❌ 不是 DevOps CI/CD 工具（不做部署流水线，只做任务完成保障）

### 1.3 一句话价值

**让点菜后餐厅自动把真能吃的菜端到嘴边**。

客人（用户）在点菜入口给任务目标 + 交付物形式 → 餐厅（harnessFlow）自动跑完切菜、开火、调味、摆盘、上桌所有标准步骤；中途不问"要不要开火"，只在 3 种红线（走偏 / DoD 漏项 / 即将做不可逆动作但前置缺失）打断用户；端到桌时真的能吃（Verifier 独立校验 DoD 布尔表达式）。

---

## § 2 组件图

本章回答：harnessFlow 由哪些组件组成 / 数据流从哪来到哪去 / 控制流谁决定。

### 2.1 架构图

**图例**：`──` 控制流（skill/agent 调度）；`▼` 执行下钻；`INFO/WARN/BLOCK` 是 Supervisor 信号流（不是控制流）；底部 `artifact ▼` 是产出与验证链路。Supervisor 是**侧挂 sidecar**，通过 PostToolUse hook 与主 skill 异步通信，**不在主 skill → 三引擎的串联路径上**。底座层的"SP/ECC/gstack"与"Claude Code 原生"是两个维度：前者是**外部 skill 库**（被调度的工具集），后者是**平台机制**（subagent/hooks/skill/MCP/memory 本身），共置同框只为节省空间。

```
┌──────────────────────────────────────────────────────────────────────┐
│                        用户（客人）— goal + 交付物形式                │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  harnessFlow 主 skill（总指挥 + 点菜入口）                            │
│  - 2~3 轮澄清 → 分诊（体量/类型/风险） → 路由 → 生成 DoD              │
│  - 锁 goal-anchor / 拉起 Supervisor / 初始化 task-board               │
│  - 按路线调度执行（确定性 DAG + 真分叉 LLM 路由）                     │
└─────┬─────────────────────────────────────────────────┬──────────────┘
      │                                                 │
      │          ┌──── Supervisor Agent（第 4 块 / 侧挂）────┐
      │          │  眼睛+大脑 / 全程在线 / 只读 / PostToolUse   │
      │          │  4 职责：锚定 / 进度 / 提醒 / 前瞻           │
      │          │  6 干预 → 3 红线（BLOCK 才打断用户）         │
      │          └────────┬────────┬────────────────────────────┘
      │                   │ INFO/WARN 对主 skill │ BLOCK 对用户
      │                   ▼                      ▼
      ▼                   （主 skill 自处理）   （暂停 + 汇报）
┌─────────────────────────────────────────────────────────────────────┐
│  三引擎（横向并列，主 skill 按需激活）                              │
│                                                                      │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐       │
│  │ 真完成引擎     │  │ 纠偏引擎       │  │ 进化引擎         │       │
│  │ DoD 表达式     │  │ 三层雷达       │  │ 强制 retro       │       │
│  │ Verifier(独立) │  │ 4 级 ladder    │  │ 三类记忆写回     │       │
│  │ 三段证据链     │  │ 6 信号源       │  │ matrix 版本化    │       │
│  │ trap catalog   │  │ 审计到 board   │  │ failure-archive  │       │
│  └────────────────┘  └────────────────┘  └──────────────────┘       │
└────────┬────────────────────────────────────────────────────────────┘
         │  调度（不造轮）
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  底座：SP（Superpowers）/ ECC（Everything Claude Code）/ gstack      │
│  + Claude Code 原生（subagent / hooks / skill / MCP / memory）        │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼ artifact（mp4 / URL / 命令 / screenshot / 文档）
┌─────────────────────────────────────────────────────────────────────┐
│  Verifier（执行/审查分离）→ eval DoD 表达式 → PASS/FAIL              │
│  PASS → 强制 retro → 写回 task-board / failure-archive / matrix     │
│  FAIL → 纠偏 ladder → 重跑 或 降级 或 escalate                      │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼ 收口汇报（artifact 路径 + 行为命令 + 质量 diff）
┌─────────────────────────────────────────────────────────────────────┐
│                        用户（能直接消费）                           │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 主要数据流

```
任务描述 → (澄清) → goal-anchor + DoD 布尔表达式 + 路线选择
        → (执行) → task-board 事件流 + artifact 产出
        → (验证) → Verifier report + 三段证据
        → (收口) → retro report + 三类记忆写回
        → (持久化) → failure-archive.jsonl + routing-matrix.json
```

关键字段的持久化位置：

| 数据 | 持久化位置 | 生命周期 |
|---|---|---|
| goal-anchor | `task-board.json` + CLAUDE.md goal block | 任务期 + 跨会话 |
| DoD 表达式 | `task-board.json` `dod` 字段 | 任务期 |
| Supervisor 信号 | `task-board.json` `supervisor_events[]` | 任务期 |
| Verifier report | `task-board.json` `verifier_report` | 任务期 + 归档 |
| retro report | `harnessFlow /retros/{task_id}.md` | 永久 |
| failure case | `harnessFlow /failure-archive.jsonl` | 永久（按项目） |
| matrix 权重 | `harnessFlow /routing-matrix.json` | 永久（版本化） |

### 2.3 控制流

三层控制流并行工作：

- **一级：确定性 DAG**（默认）— 主 skill 按预定义状态机走：澄清 → 分诊 → 路由 → 执行 → 监督 → 验证 → 收口。状态流转由 `state-machine.md`（Phase 4 产出）驱动，不走 LLM。
- **二级：LLM 路由**（真分叉）— 仅当三维决策命中多条高分规则 / 矩阵无明确推荐 / Supervisor 报 DRIFT_CRITICAL 要切路线时触发。每次 LLM 路由输出必记 `{trigger, candidates, scores, chosen, reason}` 进 task-board，可审计。规则详见 method3.md § 3。
- **三级：Supervisor 信号**（旁路）— Supervisor 发 INFO/WARN 对主 skill（主 skill 自处理），发 BLOCK 走 3 红线（直接打断用户）。规则详见 method3.md § 5.2。

---

## § 3 三引擎详解

本章回答：三引擎分别由哪些组件构成、组件之间怎么协作、与 method3 规则章节怎么对应。**不重抄 method3 的判断规则**，只讲架构组成与协作流程。

### 3.1 真完成引擎

**核心组件**：

| 组件 | 职责 | 实现位置 |
|---|---|---|
| DoD 表达式模板库 | 按任务类型预置 5 类 DoD 模板（视频/后端/UI/文档/重构）| Phase 6 产出 / `harnessFlow/dod-templates/*.md` |
| DoD 原语库 | `file_exists / curl_status / pytest_exit_code / ffprobe_duration` 等校验函数 | Phase 6 产出 / `harnessFlow/verifier_primitives/*.py`（Phase 6 前按 method3 § 6.1 bootstrap 表手动调度）|
| Verifier subagent | 独立审查者，eval DoD + 重跑 DoD 命令 + 关键路径抽测 | Phase 6 产出 / `.claude/agents/verifier.md` |
| 三段证据收集器 | 存在/行为/质量三段证据的产出与归档 | Phase 5 主 skill prompt 收口分支 / `.claude/skills/harnessFlow.md` § "收口" |
| trap catalog | 假完成陷阱的结构化 jsonl + 识别模式 | Phase 7 产出 schema / `harnessFlow/trap-catalog.jsonl` |

**调度示例**（主 skill 声明"即将完成"时的 step-by-step）：
```
1. 主 skill 从 task-board.dod 读出 DoD 表达式
2. 主 skill 调用 Verifier subagent，传入 DoD + artifact 索引
3. Verifier Read 各 artifact 路径（物理存在校验）
4. Verifier Bash 重跑 DoD 里的每个命令条件
5. Verifier 查询 trap catalog，对可能命中的模式做抽测
6. Verifier 写 verifier_report 回 task-board
7. PASS → 主 skill 进收口；FAIL → 主 skill 进纠偏 ladder
```

**规则源头**：`method3.md` § 1.1（真完成定义）+ § 6.1（DoD 表达式）+ § 6.2（Verifier 职责）+ § 6.3（三段证据）+ § 6.4（trap catalog）。

### 3.2 纠偏引擎

**核心组件**：

| 组件 | 职责 | 实现位置 |
|---|---|---|
| 三层雷达 | L1 微偏航（单步错）/ L2 中偏航（阶段失败）/ L3 大偏航（路线根本错）分层识别 | Phase 5 主 skill + Phase 6 Supervisor subagent 协作（`.claude/skills/harnessFlow.md` § "纠偏" + `.claude/agents/supervisor.md`）|
| 4 级 retry ladder | L0 retry-same → L1 retry-tweaked → L2 switch-skill/HITL → L3 force-finalize/escalate | Phase 5 主 skill 调度分支（`.claude/skills/harnessFlow.md` § "ladder"）|
| 信号源收集器 | hook / subagent status / Verifier 中间评估 / context / time / cost 6 类 budget watcher | Phase 6 hook 配置 + Supervisor agent prompt |
| 纠偏审计器 | 每次纠偏写 task-board.correction_events[] + 进 failure-archive | Phase 5 主 skill 持久化分支 / `harnessFlow/task-board.json` schema |

**调度示例**（发现单步失败时的升级流程）：
```
1. PostToolUse hook 捕捉 tool error
2. 主 skill 判定层级（L0/L1/L2/L3）
3. L0: 原参数重试 ≤ 2 次
4. 2 次仍失 → L1: 调整参数（scope down / 换 model）
5. 3 次仍失 → L2: 尝试切换等价 skill（如 e2e-runner → verification-loop）
6. 仍失 → L3: force finalize degraded（记 archive）或 escalate 用户
7. 每一级动作进 task-board + Supervisor 旁观是否该升级 BLOCK
```

**规则源头**：`method3.md` § 5.3（4 级 ladder）+ § 5.4（6 信号源）+ § 8.5（无界 retry 反模式）。

### 3.3 进化引擎

**核心组件**：

| 组件 | 职责 | 实现位置 |
|---|---|---|
| 强制 retro 生成器 | 任务收口前必跑，产 11 项 retro report | Phase 7 `subagents/retro-generator.md` + `archive/retro_renderer.py`（模板：`schemas/retro-template.md`）|
| 三类记忆写回器 | route-outcome / anti-pattern / combination 分流写入对应存储 | Phase 5 主 skill 收口分支 |
| matrix 版本化管理 | routing-matrix.json 语义化版本 + 每 20 次任务触发权重 review（MVP 默认）+ 人审批 PR | Phase 7 `archive/auditor.py`（只产建议，不自动改 matrix）+ `routing-matrix.json` CHANGELOG |
| failure-archive 管理 | 结构化 jsonl schema + 每项目独立文件 + 全局只读视图 | Phase 7 `subagents/failure-archive-writer.md` v2 + `archive/writer.py` + `schemas/failure-archive.schema.json` + `failure-archive.jsonl` |
| 进化边界守护 | harness 只输出"建议进化点"，不自动改自己代码 | Phase 5 主 skill 显式 prompt 约束 + retro 模板固定输出格式 + `auditor.audit()` 硬不写 matrix |

**调度示例**（Verifier PASS 后到写回完毕）：
```
1. 主 skill 调 ECC retro 产 retro.md（11 项）
2. 主 skill 按 retro 字段分流：
   - DoD diff / 路线偏差 → route-outcome
   - 新 trap / 漏项 → anti-pattern
   - 新成功组合 → combination
3. 写入对应存储（matrix.json weight_input / trap-catalog.jsonl / combination-pool.jsonl）
4. 不立即生效：route-outcome 累积 ≥ N 样本才触发 matrix 权重 review
5. matrix review 产出建议 diff → 用户审批 PR → 合入下一版
6. failure-archive.jsonl 同步 append 失败条目
```

**规则源头**：`method3.md` § 7.1（强制 retro 11 项）+ § 7.2（三类记忆）+ § 7.3（failure-archive）+ § 8.6（反模式：post-mortem 遗忘）。

---

## § 4 Supervisor Agent — 架构第 4 块

本章回答：Supervisor 在哪接入 / 什么时候被唤起 / 什么时候打断我 / 怎么和主 skill 通信。**不重抄 method3 § 5 的干预分类细节**，只讲架构接入。

### 4.1 定位

Supervisor 是用户的**眼睛+大脑**副驾。它：
- **不执行**：不写代码、不调写工具、不改文件
- **不决策终止**：终止的唯一信号是 Verifier eval DoD
- **全程在线**：主 skill 拉起后持续在任务生命周期内监听
- **只读**：权限仅 Read / Glob / Grep / 查询原语（curl 只读 / ffprobe）
- **主动而非被动**：不等主 skill 问，自己周期看 + hook 触发看

与三引擎的关系：Supervisor **不属于**三引擎。三引擎都是"动作引擎"（DoD 收口 / 纠偏 / 进化）；Supervisor 是"感知引擎"，只提供信号不提供动作。

### 4.2 部署方式

| 部署维度 | 选择 | 原因 |
|---|---|---|
| 形态 | Claude Code 原生 subagent | 复用现成生命周期管理 |
| 触发 | PostToolUse hook + 周期 wake-up + SubagentStop hook | 准实时（非真实时）足够覆盖"忘开火"型 |
| 权限 | 只读（see § 4.1）| 避免与执行 agent 抢手 + 公开方案 sidecar 模式 |
| 拉起时机 | 主 skill 路线启动后 + goal-anchor 锁定后 | 早于任何执行动作 |
| 终止时机 | Verifier PASS + retro 写完 + 主 skill 收口 | 全程在场 |

### 4.3 4 职责 / 6 干预 / 3 红线（引 method3）

Supervisor 的三层架构角色：

| 维度 | 条目 | 架构角色 / 何时触发 |
|---|---|---|
| **4 职责**（持续做）| 目标锚定 / 实时进度 / 主动提醒 / 前瞻分析（看接下来 1-3 步）| 每个 hook tick 都做；不产生对外事件，只维护 Supervisor 内部状态 |
| **6 干预**（发信号分类）| 忘开火 / 漏菜 / 走偏 / 节奏失衡 / 顺序错 / 冗余 | 4 职责检测到异常时 → 按分类发 INFO/WARN 对主 skill（BLOCK 走 3 红线）|
| **3 红线**（硬阈值打断用户）| DRIFT_CRITICAL / DOD_GAP_ALERT / IRREVERSIBLE_HALT | 干预达到红线阈值时 → 暂停执行 + 结构化汇报用户 + 等决策 |

**规则详见** `method3.md § 5.1` / `§ 5.2` / `§ 5.4`。本章不重复规则，只强调架构接入：三层是**递进关系**（持续做 → 发信号 → 硬阈值打断），不是平级枚举。

### 4.4 结构化输出协议

Supervisor 每次发信号必须返回如下结构（主 skill 按 schema 机器解析）：

```json
{
  "status": "INFO | WARN | BLOCK",
  "category": "忘开火 | 漏菜 | 走偏 | 节奏失衡 | 顺序错 | 冗余",
  "severity_reason": "触发条件的一句话描述",
  "diagnosis": "当前状态 vs 预期状态的 diff",
  "suggested_action": "推荐动作（对主 skill）或红线类型（对用户）",
  "evidence": ["支撑证据 1", "支撑证据 2"],
  "red_line": "DRIFT_CRITICAL | DOD_GAP_ALERT | IRREVERSIBLE_HALT | null"
}
```

主 skill 的 parse 逻辑：
- `status == INFO` → 记 task-board，不改行为
- `status == WARN` → 记 task-board + 调整下一步（如切路线 / scope down）
- `status == BLOCK` 且 `red_line != null` → 暂停执行 + 结构化汇报用户 + 等决策

### 4.5 进化反哺

Supervisor 的所有信号都进 task-board.supervisor_events[]，retro 时汇总：

- 同类任务连续 N 次 `红线 DOD_GAP_ALERT` → matrix 对应路线的"漏 DoD 倾向"权重 +1 → 下次同类任务降权
- 同类任务连续 N 次 `红线 DRIFT_CRITICAL` → goal-anchor 的澄清规则要加强（主 skill 前置问更多）
- 同 trap 命中 N 次 → trap catalog 升级为"高优先级拦截"

这个反哺链路让 Supervisor 从"事后提醒"变"事前预防"，是 harnessFlow 能随任务积累变强的核心机制。

---

## § 5 生态边界

本章回答：SP / ECC / gstack 各管什么 / harnessFlow 为什么只做 5 处桥接 / 绝对不碰什么。

### 5.1 能力映射表

harnessFlow 调度时，各场景优先选用的现成能力：

| 层 | 场景 | 能力名 | 来源 |
|---|---|---|---|
| 编排/澄清 | 需求澄清、头脑风暴 | `brainstorming` | SP |
| 编排/澄清 | 产品需求文档 | `prp-prd` | ECC |
| 编排/澄清 | 实施计划 | `prp-plan` | ECC |
| 编排/执行 | 按 plan 实现 | `prp-implement` | ECC |
| 真完成 | 收口前验证 | `verification-before-completion` | SP |
| 真完成 | 端到端测试 | `e2e-runner` | ECC |
| 真完成 | agent 评估 | `agent-eval` | ECC |
| 真完成 | 验证循环 | `verification-loop` | ECC |
| 真完成 | 浏览器 QA | `browser-qa` | ECC |
| 真完成 | TDD | `tdd-guide` | ECC |
| 真完成 | 构建错误修复 | `python-build-resolver` / `typescript-build-resolver` / `go-build-resolver` 等 | ECC |
| 真完成 | 代码审查 | `code-reviewer`（各语言）| SP + ECC |
| 纠偏 | 循环运维 | `loop-operator` / `continuous-agent-loop` | ECC |
| 纠偏 | harness 优化 | `harness-optimizer` / `autonomous-agent-harness` | ECC |
| 纠偏 | 小心处理 | `careful` | gstack |
| 纠偏 | 阻止无 verify | `pre:bash:block-no-verify` hook | gstack |
| 纠偏 | 提交质量 | `pre:bash:commit-quality` hook | gstack |
| 进化 | 持续学习 | `continuous-learning-v2` / `learn` / `learn-eval` | ECC |
| 进化 | 复盘 | `retro` | ECC |
| 进化 | 记忆 | `episodic-memory` | SP |
| 进化 | 学习日志 | `learnings.jsonl` | gstack |
| 状态持续 | 存会话 | `save-session` / `resume-session` | ECC |
| 状态持续 | git 分支 | `using-git-worktrees` | SP |
| 状态持续 | 时间线日志 | `gstack-timeline-log` | gstack |
| Gates | 规划评审 | `plan-CEO-review` / `plan-Design-review` / `plan-DevEx-review` / `plan-Eng-review` | gstack |
| Gates | 发布 / QA / 评审 | `ship` / `qa` / `review` / `document-release` | gstack |
| Gates | 质量门 | `quality-gate` | ECC |

三套库合计 ~206 个能力覆盖 ~60% 需求。

### 5.2 优先级声明

在项目 CLAUDE.md 中显式声明：

```
Skill routing priority: harnessFlow > gstack > ECC > SP
```

含义：
- 同一触发条件下，harnessFlow 主 skill 优先于 gstack/ECC/SP 拿路由权
- 仅当 harnessFlow 不处理（XS 级小任务 / 用户手动调用特定 skill）时，下游按 gstack > ECC > SP 顺序接管
- 主 skill 启动时检测优先级冲突并汇报

### 5.3 5 处自建桥接（只此五处）

每处桥接含 [why / how / 产出文件 / 影响引擎]：

**① routing-matrix 版本化**
- **Why**: SP/ECC/gstack 无"数据驱动 + 版本化 + 人审批"的路由矩阵
- **How**: `routing-matrix.json` + 语义版本号 + 每 N 次任务触发 review + matrix diff 走 PR 审批
- **产出**: `harnessFlow /routing-matrix.json`（Phase 3 产出）
- **影响**: 路由决策 + 进化引擎 matrix 版本化

**② 假完成 trap catalog**
- **Why**: SP `verification-before-completion` / ECC `verification-loop` 都不是结构化失败模式库
- **How**: `trap-catalog.jsonl` 每条 {识别模式 / 拦截动作 / 命中计数}
- **产出**: `harnessFlow /trap-catalog.jsonl`（Phase 7 产出 schema）
- **影响**: 真完成引擎（Verifier 识别基础）

**③ task-level state machine**
- **Why**: 各 skill 有局部 workflow（plan → implement → commit），但没有任务级的"路线启动 → 阶段 → 偏航 → 收口"状态流转
- **How**: `state-machine.md` 定义节点 + 转换条件 + 非法转换的兜底
- **产出**: `harnessFlow /state-machine.md`（Phase 4 产出）
- **影响**: 主 skill 调度 + Supervisor 顺序错检测

**④ 路由决策引擎**
- **Why**: 现有能力 — ECC `orchestrate` / `plan`、gstack `autoplan`、SP `brainstorming` — 都是**LLM 黑盒决策**（Manager LLM 自主推理调哪个 worker）。harnessFlow 要的是**可审计的规则查表决策**：给定 (size, type, risk) 三维向量，决策路径、候选集、权重分都可 diff 可审计可回放；关键差异点是「黑盒 LLM vs 查表规则」而非"有无路由"
- **How**: 主 skill 内部的决策函数 `route_decide(size, type, risk) → [candidates]`；读 routing-matrix.json 查表 + failure-archive 权重排序；每次决策记 `{trigger, candidates, scores, chosen, reason}` 进 task-board
- **产出**: 主 skill prompt（Phase 5）+ routing-matrix.json 的 query 接口
- **影响**: 路由规则（method3 § 3）的落地实现；进化引擎可用 matrix diff 做版本化

**⑤ 主 skill 收口 gate + Stop hook 兜底（Verifier 门）**
- **Why**: Claude Code 原生 hooks 没有"宣告完成前"这一事件（无 `pre:task:complete`），但"收口前强制走 Verifier"是真完成的关键 checkpoint
- **How**: 双层实现 — (a) 主 skill 内部的**状态转换 gate**：进入"收口状态"前同步调 Verifier subagent，FAIL 拒绝转换；(b) `Stop` / `SubagentStop` hook 做**兜底拦截**：检测 task-board 里 `verifier_report` 未写入即 force escalate，防止主 skill 绕过 gate 直接终止
- **产出**: 主 skill prompt 里的 gate 逻辑（Phase 5）+ `Stop` hook 脚本（Phase 6）
- **影响**: 真完成引擎（强制 Verifier 门，不依赖虚构的 hook 事件）

### 5.4 不重造轮的边界（绝对不碰）

即使 harnessFlow 觉得"自己做可能更整齐"，以下能力一律不重造：

- ❌ e2e runner（ECC `e2e-runner`）
- ❌ verification-before-completion（SP）/ verification-loop（ECC）
- ❌ brainstorming（SP）
- ❌ prp-prd / prp-plan / prp-implement / prp-commit / prp-pr（ECC）
- ❌ save-session / resume-session（ECC）
- ❌ retro / learn / learn-eval / continuous-learning-v2（ECC）
- ❌ code-reviewer（SP / ECC 各语言）
- ❌ build-resolver（ECC 各语言）
- ❌ `using-git-worktrees`（SP）
- ❌ `ship` / `qa` / `review` / `plan-*-review`（gstack）

发现现有能力不完全符合 harnessFlow 需求时，优先：① 组合现有能力；② 通过 hook 前后处理；③ 在 PR 贡献到上游。自己造只允许在 § 5.3 五处桥接里。

---

## § 6 与 Claude Code 原生协同

本章回答：Claude Code 原生 5 种能力（subagent / hooks / skill / MCP / memory）分别怎么被 harnessFlow 使用。

### 6.1 subagent

harnessFlow 用 subagent 的场景：

| subagent | 角色 | 权限 | 引用 |
|---|---|---|---|
| harnessFlow 主 skill | 总指挥 / 点菜入口 | 全权限 | Phase 5 产出 |
| Supervisor | 眼睛+大脑 / 副驾 | 只读 | § 4 + Phase 6 产出 |
| Verifier | 独立审查者 | 只读 | § 3.1 + Phase 6 产出 |
| Build-resolver（python / typescript / go / rust / kotlin / cpp / java / pytorch / dart）| 构建错误修复 | 限定写 | 调用 ECC `*-build-resolver` |
| Code-reviewer（各语言）| 代码审查 | 只读 | 调用 SP / ECC `*-reviewer` |
| Explore / Plan / claude-code-guide | 调研 / 规划 / 查询 | 只读 | Claude Code 内置 |

### 6.2 hooks

harnessFlow 使用和新建的 hooks：

| Hook | 用途 | 来源 |
|---|---|---|
| PreToolUse | Supervisor 前置检查（如 IRREVERSIBLE_HALT 拦截）| 原生 |
| PostToolUse | Supervisor 准实时观测 + trap 识别 + retry 触发 | 原生 |
| Stop | 任务级总结 / retro 触发 + **Verifier 门**（见下） | 原生 |
| SubagentStop | subagent 返回时的信号汇总 + Verifier 门 fallback | 原生 |
| `pre:bash:block-no-verify` | 阻止无验证 bash 动作 | gstack |
| `pre:bash:commit-quality` | 提交质量检查 | gstack |

**Verifier 门的实现说明**：Claude Code 原生 hook 事件仅有 `PreToolUse / PostToolUse / UserPromptSubmit / SessionStart / SessionEnd / Stop / SubagentStop / PreCompact / Notification`，**没有 `pre:task:complete` 事件**。"收口前强制 Verifier" 实际落地方式是**主 skill 内部状态转换 gate**（非独立 hook 事件）— 主 skill 在"即将进入收口状态"时同步调 Verifier，FAIL 则拒绝状态转换；再借 `Stop` / `SubagentStop` hook 做兜底拦截（若主 skill 绕过 gate 直接 Stop，hook 检测 `verifier_report` 未写入则 force escalate）。详见 § 5.3 桥接 ⑤。

### 6.3 skill

- 主 skill = **harnessFlow**（Phase 5 产出的 prompt）
- 调度的下游 skill 全部来自 SP / ECC / gstack（详见 § 5.1）
- 不自造任何领域执行 skill

### 6.4 MCP

| MCP 服务器 | 用途 | 场景 |
|---|---|---|
| context7 | 技术文档查询 | Phase 3 RESEARCH / 外部 lib 用法 |
| playwright | 浏览器自动化 | UI 类任务的 e2e / screenshot |
| github | PR / Issue 操作 | 收口阶段 `/prp-pr` 的底层调用 |
| memory（Anthropic）| 结构化记忆 | failure-archive / matrix 的备份视图（可选）|

### 6.5 memory

harnessFlow 使用的 memory 分类：

| 类型 | 内容 | 当前存储（现状） | harnessFlow 后续扩展 |
|---|---|---|---|
| feedback | 用户对工作方式的反馈（如 `feedback_real_completion` / `feedback_workflow_scheme_c` / `feedback_quality_over_speed`）| `~/.claude/projects/{project}/memory/feedback_*.md` + `MEMORY.md` 索引条目 | 保持现状 |
| project | 项目级持久事实 | 现状只用 `feedback_*.md` + `MEMORY.md` | Phase 5 主 skill 落地 `project_*.md` 命名约定 |
| reference | 外部资源指针 | 现状只用 `feedback_*.md` + `MEMORY.md` | Phase 5 主 skill 落地 `reference_*.md` 命名约定 |
| user | 用户偏好 | 现状只用 `feedback_*.md` + `MEMORY.md` | Phase 5 主 skill 落地 `user_*.md` 命名约定 |
| routing state | 任务级路由状态 | `harnessFlow /task-board.json`（不进 memory，进项目文件）| 保持现状 |
| failure | 失败案例 | `harnessFlow /failure-archive.jsonl`（不进 memory，进项目文件）| 保持现状 |

**现状说明**：`~/.claude/projects/-Users-zhongtianyi-work-code/memory/` 目前只有 `feedback_*.md` 文件 + `MEMORY.md` 索引；不存在 `project_* / reference_* / user_*` 前缀惯例。表格里的 "harnessFlow 后续扩展" 列是 Phase 5 主 skill prompt 要落地的**命名约定**（需在 `using-auto-memory` 类 skill 里加对应写入规则），不是当前事实。

memory 适合存"跨任务稳定事实"；task-board 和 failure-archive 适合存"任务级/项目级结构化数据"。两者分工明确。

---

## § 7 架构风险与兜底

PRD 识别的 7 条技术风险在架构层的兜底机制：

### 7.1 Supervisor 延迟 / 成本

- **风险**: PostToolUse hook 给每次工具调用增加延迟 / token 成本
- **触发条件**: 每任务执行 100+ 工具调用时可能感知延迟 ≥ 5%
- **兜底动作**: 配置 hook 只对关键工具生效（Write / Edit / Bash）+ 周期 wake-up 频率可调 + 准实时（非真实时）策略
- **监控信号**: Supervisor 输出带 `latency_ms` 字段，Supervisor 自检平均延迟 > 阈值则降频

### 7.2 三套库版本升级不兼容

- **风险**: SP / ECC / gstack 独立演进，某次升级打破 harnessFlow 路由矩阵映射
- **触发条件**: CI 检测某能力名 / signature 消失
- **兜底动作**: routing-matrix.json 带版本锁 + 每月回归 + failure-archive 中 `missing_skill` 类失败触发紧急 review
- **监控信号**: 主 skill 启动时校验 matrix 中的 skill 是否都存在，不存在则预警

### 7.3 主 skill prompt 过长

- **风险**: 规则 + 路由逻辑全塞 prompt → LLM 决策质量下降
- **触发条件**: 主 skill prompt 超 N 千 token
- **兜底动作**: 主 skill 只装"调度逻辑 + 路由 DSL"，规则放 routing-matrix.json / state-machine.md（数据驱动而非 prompt 驱动）
- **监控信号**: prompt token 数进 task-board 指标，超阈值告警

### 7.4 DoD 写不好 → 假完成漏

- **风险**: DoD 表达式太弱（如只检查"文件存在"漏"时长 > 0"）导致假完成漏网
- **触发条件**: Verifier PASS 但用户反馈"实际不可用"
- **兜底动作**: DoD 模板库（Phase 6）预置 5 类任务的强 DoD + trap catalog 兜底 + Verifier 关键路径抽测作为三段证据的质量段
- **监控信号**: 用户反馈"假完成"时 Supervisor 记 `post_hoc_false_complete` 进 failure-archive，触发 DoD 模板升级

### 7.5 全局 budget 超预算

- **风险**: token / time / cost 无界累积
- **触发条件**: 任意 budget watcher 触及阈值
- **兜底动作**: 纠偏 L3 强制 force finalize degraded（降 DoD 收口）或 escalate 用户；每任务有预估 budget
- **监控信号**: `context_budget_used / time_elapsed / cost_accumulated` 进 Supervisor 节奏失衡检测

### 7.6 gstack / harnessFlow 优先级冲突

- **风险**: gstack `Skill routing` 机制抢主 skill 控制权
- **触发条件**: 用户触发某条件，gstack 和 harnessFlow 同时响应
- **兜底动作**: CLAUDE.md 显式优先级声明（§ 5.2）+ 主 skill 启动时检测并汇报冲突；冲突仲裁由优先级决定
- **监控信号**: Supervisor 检测 `skill_collision_events[]`，出现 > 0 次则建议用户调整 CLAUDE.md

### 7.7 Supervisor 报警疲劳

- **风险**: Supervisor 发太多 WARN / INFO 让用户忽略真正 BLOCK
- **触发条件**: 单任务 INFO + WARN > 20 次（MVP 默认）
- **兜底动作**（增量，不重复 § 4.3 原则）:
  1. **同类 WARN 5 分钟内去重** — 相同 `category + severity_reason` 的 WARN 首次记入，后续 5 分钟内只更新 count 不再广播
  2. **频次降级** — 单任务累计 WARN > 10 次时，新 WARN 自动降为 INFO（仍记入 task-board，但不再触发主 skill 动作调整），防止信号泛滥淹没真 BLOCK
  3. **retro 强制回顾** — retro 时 `supervisor_signal_count.WARN` 超阈值自动列入"需调优的 Supervisor 规则"章节
- **监控信号**: retro 统计 `supervisor_signal_count[INFO|WARN|BLOCK]`；`WARN/total > 0.6` 触发 Supervisor 规则调优建议

---

*本文档是 harnessFlow 的**架构蓝图**。规则决策去 method3.md；路线具体设计去 flow-catalog.md；路由矩阵去 routing-matrix.json；状态机去 state-machine.md；主 skill / Supervisor / Verifier 具体 prompt 去 Phase 5-6 产出。任何架构级变更必须更新本文档，不允许在下游文档里自行偏离架构。*

*— v1.0 end —*
