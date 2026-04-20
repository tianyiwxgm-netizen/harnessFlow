# v2 Supervisor/Orchestrator — 行业调研 findings

> 日期：2026-04-18
> 任务：v1.3 scope 被用户超越升级到 v2（orchestrator-level supervisor with goal persistence + plan-vs-progress alignment loop + auto-replan on drift）
> 路线：F（研究 → decision log）
> 调研深度：6 个顶级行业 reference + 2 arxiv 论文

---

## § 1 核心问题

用户原话（2026-04-18）:
> "要有 1 个监督程序：这个监督程序里有原始需求、原始目标，然后有整体阶段的规划计划和实施路径，然后规划计划和实施路径、进度是不定时的跟原始需求原始目标对齐，当发现有偏离就提示流程做 loop 改进计划和实施路径方案和计划，一直到完成原始需求和原始目标。"

翻译成 agent harness 术语：**Long-horizon goal persistence + plan-progress alignment loop + auto-replan on drift**。这恰好是 2024-2026 行业所有顶级 harness 的**共同关注点**。

---

## § 2 行业主流 pattern（6 个顶级 reference）

### 2.1 Anthropic 官方"Effective harnesses for long-running agents"（最权威，因为是我们运行环境）

核心组件：
- **`feature_list.json`** — canonical plan；200+ 测试项，每项含 `{category, description, steps, passes: bool}`；**只允许改 `passes` 字段**，不允许删/改 description
- **`claude-progress.txt`** — session 叙事；portable long-term memory；"lab notes" 式记录
- **Git commit 作 checkpoint** — 每个有意义单元 commit + push；可 revert + 切机器
- **`init.sh` 可复现环境**
- **端到端测试**（Puppeteer MCP）做**drift detection** — "Claude 报 code 改了但 e2e 没过" 就是 drift 信号（不依赖 agent 自报）
- **Two-agent 设计**：Initializer Agent + Coding Agent（coding agent 每 session 做"incremental progress"）
- **Server-side compaction** 自动摘要 oldest context（30+ 小时会话）

### 2.2 Manus（"todo.md recitation" — 最便宜 trick）

- 核心 mechanic：**每步重写 `todo.md`**，把 goal "push into recent attention"，避免 lost-in-the-middle
- 无架构 trick，纯 prompt engineering — 通过"natural language bias"让模型自己保持聚焦
- 3 agent 架构（Planner / Executor / Verification）**但 blog 只说不做详细架构**

### 2.3 LangChain Plan-and-Execute（经典 3-node 图）

```
Planner Node → Executor Node(s) → Replanner Node
                                      ↓
                                  finish? → Final Answer
                                  refine? → back to Executor
```

- **Replanner 每 step 后触发**
- decision：`finish` (return answer) vs `refine` (generate follow-up plan)
- state 跨迭代保留 `past_steps`

### 2.4 Plan-and-Act（arxiv 2503.09572，WebArena 57.58% SOTA）

- **Planner 每 action 后 replan**（不只是 Executor 失败才 replan）
- Planner 输入：current state + previous plans + previous actions + user instruction
- 动态信息（search result, transaction history）被纳入 evolving plan
- 失败模式：dynamic content 分析不行 → 用 CoT + 5000 synthetic examples 补

### 2.5 TDP（Task-Decoupled Planning，arxiv 2601.07577 — 最工程化）

**最相关**（最接近 harnessFlow 当前架构）：

- **Supervisor** — 全局 DAG 分解 + topological scheduling（≈ harnessFlow 的 flow-catalog 路线骨架）
- **Planner-Executor pair** — 节点级执行；strict context isolation（每节点只看自己的 spec + 前置节点输出）
- **Self-Revision module** — 完成一批 node 后重评依赖图：
  - 违反 assumption 的节点 → 改其 spec 或删
  - 新信息 propagate 到下游节点 tighten constraint
  - **偏离只在 active node 内 replan，不传播** → 防 error cascade
- **82% token 减少** vs Plan-and-Act（工程意义巨大）
- benchmark：TravelPlanner / HotpotQA / ScienceWorld SOTA

### 2.6 Devin 2025 失败教训（Cognition blog）

- **ambiguous requirements** → 走偏；需要前期**scoping** 更严
- **mid-task 改 spec** 让 Devin 变差（vs 人类能 adapt）
- **judgment-required** 任务必须人监督
- Cognition 响应：让 engineer 做更好 initial scoping，**而不是改架构**（说明 architectural approach 有边界）

### 2.7 OpenHands SDK（bonus）

- **event-sourced state** 可 replay + fault recovery
- **immutable component design** 防 config drift
- 平均 29 iterations / 任务

---

## § 3 pattern 统一抽象（4 个必须件）

所有上述 harness 都围绕这 4 件事：

1. **Goal Anchor** — 原始需求的 durable、结构化、不可删除存储
   - Anthropic: `feature_list.json`（200 items, only passes changes）
   - Manus: `todo.md` 每步重写
   - harnessFlow: `goal_anchor` block in CLAUDE.md + sha256 hash ✅ 已有

2. **Plan / Execution Trace** — 当前 plan + 已执行步的可读 log
   - Anthropic: `claude-progress.txt` + git log
   - Plan-and-Execute: `state.past_steps[]`
   - harnessFlow: `task-board.state_history[]` + `stage_artifacts[]` + `skills_invoked[]` ✅ 已有

3. **Drift Detector** — 实时检测"偏离 goal"的机制
   - Anthropic: **end-to-end test**（最硬，不依赖 agent 自报）
   - Plan-and-Act: Planner 每 step 后 re-diff
   - TDP: Self-Revision 在 batch 完成后重评
   - harnessFlow: **收口 Verifier only**（❌ 只有末端兜底，**中途无 detector**）← **v2 要补的核心**

4. **Replan Loop** — 发现偏离时自动修正 plan
   - Plan-and-Execute: Replanner node finish/refine 决策
   - TDP: Self-Revision 改 node spec / 加删 node
   - Anthropic: 靠 coding agent 读 progress 文件 + feature list 自己 replan
   - harnessFlow: **santa-loop** 只在 Verifier FAIL 时触发（❌ 即"末端触发"，**中途 drift 不触发 replan**）← **v2 要补的核心**

---

## § 4 harnessFlow v2 的缺口映射

| 能力 | 已有 | 缺失 |
|---|---|---|
| Goal anchor | `goal_anchor` CLAUDE.md block + hash | 无 "todo.md recitation" 式每步提醒 |
| Plan trace | `task-board.json` 轨迹字段齐全 | 无 "progress file" 高层 narrative（task-board 是机器可读，不直观） |
| Drift detector | Verifier @末端 + Stop hook @末端 | **无中途 drift 检测**（行业 must-have） |
| Replan loop | santa-loop @VERIFY FAIL | **无中途 replan**（只在末端失败时） |
| Goal recitation | 静态锚 | 无"每 N 轮把 goal 推进 recent attention" |
| Context isolation per stage | 部分（flow-catalog 定骨架） | 无 strict per-node context（TDP 式） |

**结论：**
> harnessFlow 当前 = **骨架式 Supervisor + 末端 Verifier** 的组合。缺的是**中途 live-aware 的 Supervisor + 动态 replanner + goal recitation 机制**。

---

## § 5 v2 设计锚点（基于调研 + 用户需求）

### 最小可行 v2（MVP）= 下面 4 组件一起工作

**1. `supervisor-state/<task_id>.md`（新增 durable state）**

按 Anthropic `claude-progress.txt` + `feature_list.json` 混合体：

```markdown
# task_id: <...>

## Original Intent (goal_anchor — frozen, hash-locked)
<原始需求原话>

## Original DoD (Definition of Done — frozen)
<DoD 布尔表达式>

## Current Plan (revision N, updated YYYY-MM-DDTHH:MMZ)
- [x] step 1 done
- [ ] step 2 in progress
- [ ] step 3 pending
...

## Progress Narrative
<claude-progress.txt 式的 session narrative>

## Drift Log
- YYYY-MM-DDTHH:MMZ | WARN | step 2 diff > 500 行，疑似 scope 爆炸
- YYYY-MM-DDTHH:MMZ | INFO | replan triggered by supervisor tick #3, revision N+1

## Replan History
- Rev 1 → Rev 2 (trigger: user pivot)
- Rev 2 → Rev 3 (trigger: drift @ step 4)
```

**这是 goal anchor + plan + progress + drift 一个文件全装的"monolithic state"** — 让 Supervisor spawn 时只读一个文件就能 reconstruct 全部上下文。

**2. 三类 trigger 拉起 Supervisor subagent（pulse-based）**

| trigger | 作用 | 实现 |
|---|---|---|
| **Key event** | CLAUDE.md Edit / state 转移 / 大 diff / IRREVERSIBLE 前 | PostToolUse hook + 条件判断 |
| **Periodic tick** | 每 N 次 tool call（如 N=20）兜底 | PostToolUse hook + counter |
| **Explicit** | 主 skill 在关键 gate 显式调 | 主 skill 代码里 `Agent(subagent_type="...")` |

**3. Supervisor subagent 职责（短脉冲每次 spawn）**

读入：`supervisor-state/<task_id>.md` + 最近 20 条 tool call + `task-board.json`
输出到：`supervisor-events/<task_id>.jsonl` + append `supervisor-state.Drift Log`

判断 4 层：
- `OK` — 没问题，记一笔 INFO 继续
- `WARN` — 小偏差（如超 budget 50%+），记一笔 WARN + counter++
- `BLOCK` — 3 红线（DRIFT_CRITICAL / DOD_GAP_ALERT / IRREVERSIBLE_HALT），主 skill 立即 PAUSED_ESCALATED
- `REPLAN` — 非红线但发现 plan 明显偏离 goal → 写 "Replan triggered" 到 drift log + 等用户或主 skill 拉起 replanner

**4. Replanner（新 subagent 或 skill 集成）**

当 REPLAN 信号出现时：
- 拉起独立 `Agent(subagent_type="harnessFlow:replanner")`
- 输入：原始 goal_anchor + 当前 plan + drift 证据 + 已完成 steps
- 输出：**revision N+1 的 plan**（写回 `supervisor-state.Current Plan`）
- 主 skill resume 按新 plan 继续

### Non-goal（v2 不做，留 v3）

- 不做全 DAG 动态分解（保留 flow-catalog 6 路线骨架）— TDP 级别复杂度留 v3
- 不做 context isolation per stage（要动主 skill 大改）
- 不做自动 LLM routing（保留确定性 DAG + 手动 LLM 分叉点）

---

## § 6 跟用户原话的对应

| 用户原话 | 调研 pattern 对应 | v2 实现 |
|---|---|---|
| "监督程序里有原始需求、原始目标" | goal anchor (Anthropic / Manus / 所有) | `supervisor-state.Original Intent`（frozen）|
| "整体阶段的规划计划和实施路径" | plan + execution trace | `supervisor-state.Current Plan + Progress Narrative` |
| "不定时跟原始需求对齐" | drift detector | 3 类 trigger 拉起 Supervisor pulse |
| "发现偏离就提示流程做 loop 改进" | replan loop (Plan-and-Act / TDP Self-Revision) | Replanner subagent + revision N+1 循环 |
| "直到完成原始需求" | DoD-based termination（所有） | 已有：Verifier + goal_anchor hash |
| "防止走着走着忘记原始需求" | recitation (Manus) + durable state (Anthropic) | supervisor-state 文件每次 spawn 时被读；pulse 把 goal 重新 push 到 context 末尾 |

**结论：用户的想法 = 2024-2026 行业主流思想的正确描述；没一条在 paper 外。我们要做的就是把这些 pattern 按 harnessFlow 现有骨架工程化落地。**

---

## § 7 决策（待 brainstorming 用户确认）

**建议版本号升级**：v1.3 (只是 wake-hook) → **v2 Supervisor Orchestrator**（完整 goal-persistence + replan loop 套件）。v1.3 的 wake-hook 降格为 v2 的子部件（trigger 机制）。

**最低价值切片**（如果只做一件事能带来最大收益）：

1. **先做 `supervisor-state/<task_id>.md`** — 这是一切的基础 state 容器
2. **再做 pulse trigger + Supervisor subagent** — v1.3 原计划，现成为 v2-B 子步
3. **最后做 Replanner subagent + replan loop** — 收尾

这是 3 个可独立验证的增量，总体量 **XL**，按 C 路线走。

---

## § 8 关键决策问题（回到 brainstorming）

1. **Supervisor-state 文件用单 markdown vs JSON？** — markdown 更易读（Anthropic 做法），JSON 更易程序化
2. **goal_anchor 存在哪？** — 继续 CLAUDE.md block（现状）vs 搬到 supervisor-state 头部？
3. **Replanner 是独立 subagent vs 复用 Supervisor？** — 独立更隔离（TDP 做法），复用更省
4. **drift 阈值怎么定？** — 3 红线硬线（DRIFT_CRITICAL 等）vs 加 soft threshold（diff 超 X%, time budget 超 Y%）
5. **v2 包含用户已 pivot 的 aigcv2 E3 场景吗？** — aigcv2 E3 是**跨项目**（method3 § 8.11）；harnessFlow v2 做机制，aigcv2 E3 在 aigcv2 repo 里用

---

## § 9 Sources

- [Effective harnesses for long-running agents — Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Context Engineering for AI Agents: Lessons from Building Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)
- [Plan-and-Execute Agents — LangChain Blog](https://www.langchain.com/blog/planning-agents)
- [Plan-and-Act (arxiv 2503.09572)](https://arxiv.org/pdf/2503.09572)
- [Task-Decoupled Planning (arxiv 2601.07577)](https://arxiv.org/html/2601.07577v1)
- [Devin 2025 Performance Review — Cognition AI](https://cognition.ai/blog/devin-annual-performance-review-2025)
- [OpenHands Software Agent SDK (arxiv 2511.03690)](https://arxiv.org/abs/2511.03690)
- [Cognition Devin 2.0](https://cognition.ai/blog/devin-2)
- [LangGraph Supervisor pattern — GitHub](https://github.com/langchain-ai/langgraph-supervisor-py)
- [Anthropic Claude Code Sub-Agents docs](https://code.claude.com/docs/en/sub-agents)

---

*findings 完，回 brainstorming Q 系列（见回复主文）*
