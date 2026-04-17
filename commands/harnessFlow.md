---
description: harnessFlow 总编排 / 总监督 / 总路由器 — 2-3 轮澄清 → 42-cell 路由推荐 Top-2 → 用户选 → 挂 Supervisor 监听 → Verifier 收口 → retro + 归档。防"假完成"元技能。
argument-hint: <任务描述>
---

# /harnessFlow

你现在**加载 harnessFlow 主 skill prompt**并按其完整流程处理 `$ARGUMENTS`。

## 触发协议

1. **严格遵循** `harnessFlow /harnessFlow-skill.md` 里的所有 prompt 规则。先 `Read` 该文件（或通过 `Skill(skill="harnessFlow")` 加载），再开始任何动作。
2. 同时背景载入以下 7 份**规则文档**（按需 `Read`，不必一次全读）：
   - `harnessFlow /method3.md` § 1.1 真完成 + § 7 收口 + § 8 反模式
   - `harnessFlow /harnessFlow.md` § 3-4 三引擎 + Supervisor
   - `harnessFlow /flow-catalog.md` A-F 6 路线
   - `harnessFlow /routing-matrix.md` 42-cell 决策
   - `harnessFlow /state-machine.md` § 1 + § 7 状态机
   - `harnessFlow /task-board-template.md` § 1 字段 schema
   - `harnessFlow /delivery-checklist.md` § 0 + § 3 + § 7.2 收口 DoD
3. 4 个 subagent 通过 `Agent(subagent_type="harnessFlow:<name>")` 形式 spawn：
   - `harnessFlow:supervisor` — 任务全程侧挂监听
   - `harnessFlow:verifier` — VERIFY 状态独立 spawn，eval DoD 布尔表达式
   - `harnessFlow:retro-generator` — RETRO_CLOSE 产 11 段 markdown
   - `harnessFlow:failure-archive-writer` — 写结构化 jsonl + 可能触发 audit
4. 2 个 hooks 已在 `.claude/settings.local.json` 注册，自动在 Edit/Write 和 Stop 时触发（不需显式调）。
5. 工作产物写入 `harnessFlow /task-boards/<task_id>.json`（运行时），每次状态转移必须写 `state_history`。

## 用户输入

$ARGUMENTS

## 第一步

如果 `$ARGUMENTS` 为空：问用户他要做什么任务。

否则按 `harnessFlow-skill.md § 1-2` 启动流程：
1. **Generate task_id**（`p-<短描述>-<ts>` 格式）
2. **初始化 task-board.json** (INIT 态)
3. **进入 CLARIFY 阶段**：问 2-3 轮澄清问题识别 `(size, task_type, risk)` 三维
4. 其余流程 严格按 harnessFlow-skill.md 走（**不要省略 Verifier / retro / archive**）

## 硬约束

- **3 红线**（DRIFT_CRITICAL / DOD_GAP_ALERT / IRREVERSIBLE_HALT）任一触发立即进 `PAUSED_ESCALATED`，禁止 COMMIT
- **A 路线豁免**仅限 `size=XS` 且 `route=A`
- 进化边界硬线：`auditor` 只产建议，**永不自动改** `routing-matrix.json`
- 真完成第一原则：任务完成 ≡ 用户可直接消费的 artifact，**非** "pipeline 无 error"
- 不要自己写新 skill / 造新 subagent，只编排既有的（Superpowers / ECC / gstack / 以及本项目 4 个 subagent）
