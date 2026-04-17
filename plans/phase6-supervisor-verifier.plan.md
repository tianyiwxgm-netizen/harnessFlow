# Phase 6 Plan — Supervisor + Verifier subagent + DoD 原语库

**版本**: v1.0 (2026-04-16)
**Depends on**: Phase 1-5（method3 + harnessFlow.md + flow-catalog + routing-matrix + state-machine + task-board + delivery-checklist + harnessFlow-skill.md）
**Parallel with**: 无（Phase 5 已完成，Phase 6 进串行）
**Output**:
- `harnessFlow /subagents/supervisor.md`（Supervisor 提示词）
- `harnessFlow /subagents/verifier.md`（Verifier 提示词）
- `harnessFlow /verifier_primitives/`（原语库，Python 实现）
- `harnessFlow /subagents/failure-archive-writer.md`（失败归档写手，简化版）
- `harnessFlow /hooks/`（Stop hook + PostToolUse hook 脚本）

## Goal

把 Phase 5 主 skill 里占位的三个 subagent（`harnessFlow:supervisor` / `harnessFlow:verifier` / `harnessFlow:failure-archive-writer`）变成**可由 Claude Code Agent tool 加载并执行的真正 subagent 定义**，并把 method3 § 6.1 五个 DoD 模板里的**占位原语**（`file_exists` / `ffprobe_duration` / `oss_head` / `pytest_exit_code` 等 20+ 条）**落到 Python 可直接调用**的层次。

关键目标：

1. **Supervisor** = 全程 sidecar 监听，读 task-board / state_history / routing_events → 发 INFO/WARN/BLOCK 事件；判 3 条红线（DRIFT_CRITICAL / DOD_GAP_ALERT / IRREVERSIBLE_HALT）
2. **Verifier** = 独立收口 agent，**不看 LLM 自评**，只看 task-board.dod_expression + 原语库 eval 结果 → 输出 PASS / FAIL / INSUFFICIENT_EVIDENCE
3. **DoD 原语库** = 用 Python 实现 method3 § 6.1 表里的 20+ 个 primitive，Verifier 直接 `import` 调用，不手拼 bash 命令
4. **Stop hook / PostToolUse hook** = 把 state-machine § 5.4（运行时 goal drift）和 delivery-checklist § 7.2（Stop 前门卫）落成**真实的 shell 脚本**
5. **假完成回放单元测试** = 拿 P20 假完成案例（`file_exists` 绿但 `oss_head` 红）跑一次，验证 Verifier 必须拦下

## Acceptance Criteria

### Supervisor subagent (`subagents/supervisor.md`)

- [ ] 符合 Claude Code subagent 文件格式：YAML frontmatter（`name` / `description` / `tools`）+ markdown body
- [ ] ≥ 300 行（≤ 600 行）
- [ ] 明确 **只读权限**（tools 仅 Read / Grep / Glob / Bash 但 Bash 限白名单 pytest/curl/ffprobe 等，不能 Edit / Write / git push）
- [ ] § 1 激活时机（由主 skill `Agent(subagent_type="harnessFlow:supervisor", run_in_background=true)` 拉起，CLARIFY→ROUTE_SELECT 锁 goal_anchor 之后）
- [ ] § 2 监听数据源（轮询 `task-boards/<task_id>.json` / `routing_events.jsonl` / `sessions/<task_id>.json`）
- [ ] § 3 6 类干预（v1 先实现 3 类：drift_detected / stuck_in_state / token_budget_warn，其余 3 类占位）
- [ ] § 4 3 条红线（DRIFT_CRITICAL / DOD_GAP_ALERT / IRREVERSIBLE_HALT）触发逻辑 + 对应 state-machine edges
- [ ] § 5 事件输出格式（jsonl append 到 `supervisor_events.jsonl`，字段：ts / level / code / task_id / state / evidence / suggested_action）
- [ ] § 6 终止时机（task_board.current_state ∈ {CLOSED, ABORTED, PAUSED_ESCALATED} 时自行退出）
- [ ] § 7 反模式（不要做）清单 ≥ 5 条

### Verifier subagent (`subagents/verifier.md`)

- [ ] YAML frontmatter 完整（tools 需含 Bash 以调原语库 + Read 以读 task-board）
- [ ] ≥ 250 行（≤ 500 行）
- [ ] § 1 激活时机（由主 skill 在 `@VERIFY` 状态调；接收 `task_id` 为唯一输入）
- [ ] § 2 eval 协议（读 task-board.dod_expression → 分解为原语调用 → 逐条走 `verifier_primitives/*.py` → 聚合布尔）
- [ ] § 3 三态 verdict 决策（PASS / FAIL / INSUFFICIENT_EVIDENCE）严格对齐 state-machine § 7 + delivery-checklist § 7.1 P0-P3
- [ ] § 4 证据链格式（三段：存在证据 / 行为证据 / 质量证据；每条含 primitive 名 + 命令 + 输出 + 返回值 + ts）
- [ ] § 5 输出文件 `verifier_reports/<task_id>.json`（含 verdict / evidence_chain / failed_conditions / red_lines / priority）
- [ ] § 6 反模式（禁用 LLM 自判、禁修改 dod_expression、禁用自我豁免）

### DoD 原语库 (`verifier_primitives/`)

- [ ] `__init__.py` 导出统一入口
- [ ] 至少覆盖 method3 § 6.1 表中 20 个原语，每个 primitive：
  - 一个 Python 函数（signature 对齐文档 `ffprobe_duration(path: str) -> float`）
  - 返回**确定类型**（bool / int / str / float），不抛异常（失败走 INSUFFICIENT_EVIDENCE 路径，return sentinel）
  - 内部 subprocess 调用 shell 命令 + 捕获 stdout/stderr + 解析
- [ ] 每个 primitive 一条 pytest 用例（自检表 `tests/test_primitives.py`）
- [ ] `README.md` 说明：如何新增 primitive、如何注入到 task-board.dod_expression

### failure-archive-writer subagent (`subagents/failure-archive-writer.md`)

- [ ] 简化版（v1 只做 retro 归档 append；结构化 schema 留给 Phase 7）
- [ ] ≥ 100 行（≤ 200 行）
- [ ] 接收 `task_id` → 读 task-board + supervisor_events + verifier_report → 按简单模板 append 到 `harnessFlow /retros/<task_id>.md`

### Hooks (`hooks/`)

- [ ] `PostToolUse-goal-drift-check.sh`：每次 Edit/Write CLAUDE.md 后算 hash，对比 task-board.goal_anchor.hash → 不同 → exit 2 + 写 WARN 到 supervisor_events
- [ ] `Stop-final-gate.sh`：执行 delivery-checklist § 7.2 门卫清单（task_board.current_state 是否合法终态 / red_lines 是否为空 / retro_link 是否就位（A 路线豁免））
- [ ] 两个脚本都放 `harnessFlow /hooks/` 目录，附 README 说明如何挂到 `.claude/settings.json`（用户决定是否启用）

### 假完成回放单元测试

- [ ] `tests/test_p20_fake_completion.py`：构造 fake task-board（dod_expression 含 `file_exists("fake.mp4") AND oss_head("...").status_code == 200`，file 存在但 oss 不可达）→ 调 Verifier 的 eval 函数 → 断言 verdict == "FAIL"，red_lines 含 DOD_GAP_ALERT
- [ ] 再构造一个缺 `ffprobe_duration` 调用权限的 case → verdict == "INSUFFICIENT_EVIDENCE"，count += 1

### 与 Phase 1-5 交叉引用

- [ ] Supervisor 引 state-machine § 4 纠偏 ladder / § 5.4 运行时监控
- [ ] Verifier 引 state-machine § 7 决策树 / delivery-checklist § 7.1 三态口径 / task-board § 6.2 GATE_PREDICATES
- [ ] 原语库引 method3 § 6.1 bootstrap 表
- [ ] Hooks 引 delivery-checklist § 7.2

## Out of Scope

- failure-archive schema 的完整字段 + 自动 retro 模板（Phase 7）
- 端到端三任务真跑（Phase 8）
- Supervisor 6 类干预中后 3 类的完整实现（v1 只做 3 类；后 3 类占位，状态 enum 含 `stub` 标记）
- subagent 的 Claude Code 注册机制（目录放好即 discoverable；用户自己决定是否拷贝到 `.claude/agents/`）
- Hooks 的 `.claude/settings.json` 自动写入（由用户 opt-in）

## Risks

- **subagent 提示词过长 → context 浪费**：每个 subagent 硬上限 600 行；规则外化（引 state-machine / delivery-checklist / method3）
- **原语库 shell 依赖项多（ffprobe / curl / jsonschema / pytest / playwright）**：README 列清单 + 每个 primitive 在缺依赖时 return INSUFFICIENT_EVIDENCE sentinel（不 crash）
- **Hook 脚本破坏用户正常工作流**：两个 hook 都默认 **off**（放目录但不改 `.claude/settings.json`）；附开关说明
- **Verifier 与主 skill 调用语法 TBD**（Phase 5 § 6.1 P1-3 记过）：Phase 6 落地时必须实测 `Agent(subagent_type=..., run_in_background=true)` 是否可用；如不可用，fallback 到 `Agent(..., run_in_background=false)` 同步调 + 注明 context 成本

## Tasks

1. 起草 `subagents/supervisor.md` 骨架（frontmatter + 7 章节）
2. 起草 `subagents/verifier.md` 骨架（frontmatter + 6 章节）
3. 落地 `verifier_primitives/` 20+ primitive + `__init__.py` + pytest 自检
4. 起草 `subagents/failure-archive-writer.md`（简化版）
5. 写 `hooks/PostToolUse-goal-drift-check.sh` + `hooks/Stop-final-gate.sh` + `hooks/README.md`
6. 落地 `tests/test_p20_fake_completion.py` 假完成回放用例
7. 独立 reviewer 审查（dispatch general-purpose agent 读 Phase 1-5 + 本期产出，交叉验证）
8. 修 P0+P1
9. 更新 PRD Phase 6 → complete
10. commit Phase 6
