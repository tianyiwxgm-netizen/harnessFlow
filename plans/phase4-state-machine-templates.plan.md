# Phase 4 Plan — 状态机 + 模板

**版本**: v1.0 (2026-04-16)
**Depends on**: Phase 2 (harnessFlow.md) + Phase 3 (flow-catalog + routing-matrix)
**Output**: `state-machine.md` + `task-board-template.md` + `delivery-checklist.md`

## Goal

落实三件事：
1. **state-machine.md** — 任务从启动到收口的全部状态 + 允许的转移边 + 每条边的 guard（前置条件） + retry ladder 集成点 + save-session 后的 re-entry 语义。覆盖所有 6 条路线（A-F）共用的状态骨架 + 路线特有补丁。
2. **task-board-template.md** — `task-board.json` 的字段 schema + 示例 JSON + 每个字段的写入方 / 读取方 / 写入时机 / 审计要求。
3. **delivery-checklist.md** — 按路线分组的 DoD 校验清单 + 三段证据链表 + retro 触发 gate（缺失证据禁止 commit）。

## Acceptance Criteria

### state-machine.md
- [ ] ≥ 400 行
- [ ] 列出所有状态（≥ 10 个）+ ASCII 状态图
- [ ] 每条转移边含：`from → to` / trigger event / guard condition / on-transition side effects / 允许回滚与否
- [ ] 集成 retry ladder L0-L3（method3 § 5.3）：每 retry 级别在哪些状态触发
- [ ] 涵盖 save-session / resume-session re-entry：恢复时如何复算状态 + goal-anchor diff 校验
- [ ] 6 路线状态复用情况：A 简化版 / C 完整版 / D/E/F 特殊状态
- [ ] Supervisor INFO/WARN/BLOCK 事件如何触发状态转移
- [ ] Verifier PASS/FAIL → 下一状态决策树

### task-board-template.md
- [ ] ≥ 300 行
- [ ] 完整 JSON schema（每字段 type + required + default + 写入方）
- [ ] 核心字段 ≥ 20 项：task_id / goal_anchor / route_id / current_state / stage / skills_invoked / routing_events[] / supervisor_interventions[] / verifier_report / retries[] / red_lines[] / artifacts[] / dod_expression / dod_eval_log / route_changes[] / warn_counter / cost_budget / time_budget / cross_session_ids[] / retro_link / failure_archive_refs[]
- [ ] 至少 2 个完整示例 JSON（典型 C 路线 + P20 失败回放）
- [ ] 每字段写入/读取 table（谁写 / 何时写 / 读方用途）
- [ ] 跨 session 恢复协议：哪些字段必须一致（invariants）

### delivery-checklist.md
- [ ] ≥ 250 行
- [ ] 每路线一张 checklist（A/B/C/D/E/F 至少 6 张）
- [ ] 每 checklist 含：artifact 存在证据 + 行为证据 + 质量证据 + retro 完整性证据
- [ ] 视频出片专属 checklist（method3 § 6.1 模板①对齐）
- [ ] 后端 feature 专属 checklist（含 uvicorn + curl + schema_valid）
- [ ] UI 专属 checklist（vite + playwright + screenshot 非空）
- [ ] retro trigger gate：证据缺失 → 阻断 commit 的具体路径
- [ ] 与 routing-matrix § 3.2 IRREVERSIBLE_HALT 前置检查交叉引用

## Out of Scope

- 不写代码（Phase 5/6 落地 Python 状态机 + subagent）
- 不做 JSON validator（Phase 7 产 failure-archive schema 时再补）
- 不写主 skill prompt（Phase 5）

## Risks

- state-machine 和 flow-catalog § 4 C 路线 15 步的对齐压力：用表格双向交叉引用
- task-board 字段过多导致复杂度失控：MVP 收敛到 20 个必需字段，其余标 optional v1.1+
- delivery-checklist 与 method3 § 6.1 DoD 模板库重复：本文档只给"checklist 视图"，表达式库引 method3

## Tasks

1. 起草 state-machine.md 骨架 + ASCII 图
2. 填充转移边表 + guard + retry ladder 映射
3. save-session re-entry 协议
4. 起草 task-board schema
5. 写 2 个示例 JSON
6. 起草 6 张路线 checklist
7. 三段证据链交叉引用 method3 § 6.1
8. 独立 review 3 份文档
9. 修 P0+P1
10. 更新 PRD Phase 4 → complete
11. commit
