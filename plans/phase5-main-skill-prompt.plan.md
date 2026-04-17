# Phase 5 Plan — 主 skill prompt

**版本**: v1.0 (2026-04-16)
**Depends on**: Phase 1-4（method3 + harnessFlow.md + flow-catalog + routing-matrix + state-machine + task-board + delivery-checklist）
**Parallel with**: Phase 6（Supervisor + Verifier subagent）
**Output**: `harnessFlow-skill.md`（主 skill 提示词全文 + 调度 DSL）

## Goal

把前 4 期产出装配成**一个可直接粘进 `.claude/skills/harnessFlow/SKILL.md` 的 Claude Code skill 提示词**。主 skill 在用户调 `/harnessFlow` 时：

1. 启动拉起 → 读 CLAUDE.md + memory + 分配 task_id
2. 2-3 轮澄清（引 SP:brainstorming）收齐三维 `(size, task_type, risk)`
3. 查 `routing-matrix` → 呈现 top-2 路线 + 等用户 pick
4. 按 `flow-catalog` 对应路线调度 SP/ECC/gstack 已有能力（只编排不造轮）
5. 挂 Supervisor sidecar（Phase 6 subagent）全程监听
6. 每次状态转移按 `state-machine` 写 `task-board`
7. 进 `@VERIFY` 时调 Verifier subagent（Phase 6）走 `delivery-checklist` 三段证据链
8. PASS → COMMIT → RETRO_CLOSE → CLOSED；任一红线 → PAUSED_ESCALATED

关键工程约束：主 skill 提示词**长度可控（目标 ≤ 1200 行）+ 规则外化**——具体路由表、DoD 原语、checklist 条目全部引用外部 md，不在 prompt 内重复。

## Acceptance Criteria

### harnessFlow-skill.md 结构

- [ ] 符合 Claude Code skill 文件格式：YAML frontmatter（`name` / `description` / `allowed-tools` 可选）+ markdown body
- [ ] ≥ 600 行（≤ 1200 行上限）
- [ ] 分块清晰（≥ 9 章节对应 9 个职责）
- [ ] 所有外部引用用相对路径（`harnessFlow /state-machine.md § 1` 等）

### 必含章节

- [ ] § 1 激活时机 + 职责边界（总编排 / 不造轮 / SP/ECC/gstack 优先级）
- [ ] § 2 启动 bootstrap 协议（INIT → CLARIFY 的具体 step）
- [ ] § 3 澄清轮协议（2-3 轮 brainstorm + 三维打标 + 超 5 轮降级规则）
- [ ] § 4 路由决策协议（查 routing-matrix + top-2 呈现 + 用户 pick / 自动选 top-1 的条件）
- [ ] § 5 执行调度（按 flow-catalog 调度，分 A-F 六路线伪代码 / DSL）
- [ ] § 6 Supervisor sidecar 协议（如何拉起 + INFO/WARN/BLOCK 处理）
- [ ] § 7 状态机执行协议（何时写 task-board / 何时 save-session / goal drift 检测）
- [ ] § 8 收口协议（调 Verifier + 三态 verdict 分支 + COMMIT gate）
- [ ] § 9 异常与恢复（PAUSED_ESCALATED / ABORTED / resume-session）

### 工程要求

- [ ] 每章节开头一行交代"这章回答什么问题"
- [ ] 所有硬编码规则用"引用 + 一行说明"的形式，不在 prompt 内复述
- [ ] 含至少 3 个"决策伪代码"示例（澄清判停 / 路由选择 / verdict 分支）
- [ ] 含"反模式 / 不要做" 清单（≥ 6 条）
- [ ] 含"日志与可观测性"说明（skills_invoked / state_history / routing_events 怎么写）

### 与 Phase 4 文档交叉引用

- [ ] 引 `state-machine.md § 1.7 current_state 闭合 enum` 强约束状态转移
- [ ] 引 `state-machine.md § 7` 三态 verdict 决策树（红线 P0 优先）
- [ ] 引 `task-board-template.md § 6.2 GATE_PREDICATES` 进 COMMIT/CLOSED 前置
- [ ] 引 `delivery-checklist.md §` 各路线清单
- [ ] 引 `routing-matrix.md § 2.2 主表 + § 3.1 RISK_ADJUSTMENT`
- [ ] 引 `flow-catalog.md §` 六路线调度序列
- [ ] 引 `method3.md § 5.3` 纠偏四级 ladder

## Out of Scope

- Supervisor subagent 提示词（Phase 6）
- Verifier subagent 提示词 + DoD 原语库（Phase 6）
- failure-archive schema（Phase 7）
- Stop hook / PostToolUse hook 具体 bash 脚本（Phase 6 配套 subagent 一起落）
- 部署到 `.claude/skills/harnessFlow/SKILL.md`（用户决定后单独动作）

## Risks

- **prompt 过长 → LLM 决策质量下降**：规则外化 + 硬上限 1200 行 + 章节独立
- **调度 DSL vs 伪代码 vs 自然语言**：MVP 用"伪代码 + 自然语言注释"，避免引入新 DSL 语法负担
- **与 Supervisor subagent 职责边界模糊**：本 skill 只"调用 Supervisor"，不内联 Supervisor 逻辑；Phase 6 同步时再对齐
- **Context 压力**：prompt 自身占用 context + skills_invoked/tool-call 输出占用，容易超 cap；每状态 transition 后提示用户 /compact 或自动 save-session

## Tasks

1. 起草 harnessFlow-skill.md 骨架（frontmatter + 9 章节）
2. 填 § 1-3（激活 / bootstrap / 澄清）
3. 填 § 4-5（路由 / 执行调度）
4. 填 § 6-7（Supervisor / 状态机）
5. 填 § 8-9（收口 / 异常恢复）
6. 补反模式清单 + 日志与可观测性
7. 独立 reviewer 审查（dispatch general-purpose agent）
8. 修 P0+P1
9. 更新 PRD Phase 5 → complete
10. commit
