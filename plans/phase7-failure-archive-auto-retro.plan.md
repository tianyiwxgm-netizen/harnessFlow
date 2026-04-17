# Phase 7 Plan — failure-archive schema + auto-retro

**版本**: v1.0 (2026-04-17)
**Depends on**: Phase 1-6（method3 § 7.1/7.2/7.3 + state-machine § 7 + delivery-checklist § 7.2 + task-board-template + harnessFlow-skill.md 收口协议 + verifier_primitives）
**Parallel with**: 无（必须在 Phase 6 之后，Phase 8 之前）
**Output**:
- `harnessFlow /schemas/failure-archive.schema.json`（JSON Schema draft-07）
- `harnessFlow /schemas/retro-template.md`（11 项自动 retro 模板）
- `harnessFlow /archive/`（Python 写入/审计/渲染库）
  - `writer.py` — 结构化 jsonl 写入
  - `auditor.py` — 每 N 次任务审计路由权重
  - `retro_renderer.py` — 按模板渲染 retro markdown
  - `__init__.py`
- `harnessFlow /subagents/failure-archive-writer.md`（v2 结构化版，替换 v1）
- `harnessFlow /subagents/retro-generator.md`（新 subagent，产 11 项 retro）
- `harnessFlow /archive/tests/`（pytest 单测）
- 主 skill 收口协议补丁（`harnessFlow-skill.md` § 8 补 archive + audit 触发）
- delivery-checklist.md § 7.2 补 "archive + retro 必过门"

## Goal

把 method3 § 7.1/7.2/7.3 定义的三条进化链条**落到机器可执行**：

1. **结构化 failure-archive.jsonl** — 13+ 字段的 JSON Schema，每次 FAIL/ABORTED/false_complete_reported 事件都写一条，Verifier red_lines + task-board 状态 + supervisor_events 自动填充
2. **自动 retro 11 项** — method3 § 7.1 列的 11 项（DoD diff / 路线偏差 / 纠偏次数 / Verifier FAIL 次数 / 用户打断次数 / 耗时 / 成本 / 新 trap / 新组合 / 进化建议 / 下次推荐），从 task-board + verifier_report + supervisor_events + retro_notes 机器派生
3. **路由权重审计** — 每 20 次任务（method3 § 7.3 默认）读 archive.jsonl → 算 `(size, task_type)` cell 的失败率 → 产 audit-report 建议 `routing-matrix.json` 权重调整（只建议、不自动改，method3 § 7.3 进化边界）
4. **收口强制触发** — 主 skill `VERIFY → RETRO_CLOSE → CLOSED` 路径必过 archive + retro，A 路线保留豁免（delivery-checklist § 7.2 carve-out）

关键目标：Phase 6 的 failure-archive-writer v1 只做 markdown append，**没有**结构化 jsonl，**没有**审计触发，**没有** 11 项 retro 自动派生。Phase 7 把这三块补全并替换 v1。

## Acceptance Criteria

### 1. failure-archive JSON Schema (`schemas/failure-archive.schema.json`)

- [ ] JSON Schema draft-07，`$schema` / `$id` / `title` / `description` 元字段齐
- [ ] 必需字段（严格对齐 method3 § 7.3）：
  - `task_id` (string, UUID/ULID)
  - `date` (string, ISO 8601 date)
  - `ts` (string, ISO 8601 datetime UTC)
  - `project` (string, e.g. "aigcv2", "harnessFlow")
  - `task_type` (enum: `视频出片` / `后端feature` / `UI_feature` / `文档` / `重构` / `研究` / `其他`)
  - `size` (enum: `XS` / `S` / `M` / `L` / `XL`)
  - `risk` (enum: `低` / `中` / `高` / `不可逆`)
  - `route` (enum: `A` / `B` / `C` / `D` / `E` / `F`)
  - `node` (enum: `clarify` / `route_select` / `plan` / `impl` / `verifier` / `supervisor` / `retro` / `other`)
  - `error_type` (enum: `DOD_GAP` / `DRIFT` / `IRREVERSIBLE_HALT` / `STUCK` / `TOKEN_BUDGET` / `DEPENDENCY_MISSING` / `USER_ABORT` / `OTHER`)
  - `missing_subcontract` (array of string, e.g. `["mp4.duration", "oss_key"]`)
  - `retry_count` (integer, ≥0)
  - `retry_levels_used` (array of enum: `["L0"|"L1"|"L2"|"L3"]`)
  - `final_outcome` (enum: `success` / `failed` / `aborted` / `false_complete_reported`)
  - `frequency` (integer, ≥1 — 同类累计次数)
  - `root_cause` (string, 人类可读)
  - `fix` (string, 人类可读)
  - `prevention` (string, 人类可读)
- [ ] 可选字段：
  - `verifier_report_link` (string, 路径)
  - `retro_link` (string, 路径)
  - `supervisor_events_count` (object: `{INFO: int, WARN: int, BLOCK: int}`)
  - `user_interrupts_count` (object: `{DRIFT: int, DOD_GAP: int, IRREVERSIBLE: int, 废问题: int}`)
  - `elapsed_min` / `token_used` / `token_budget` (number)
  - `trap_matched` (array of string, 命中的 trap-catalog ID)
- [ ] schema 自验：一条合格样本 JSON（P20 假完成事件，method3 § 8.1）通过 `jsonschema.validate`
- [ ] README 说明：如何 append / 为什么不是 db（append-only 文件好审计 + git diff 友好）

### 2. 自动 retro 模板 (`schemas/retro-template.md`)

- [ ] method3 § 7.1 十一项全覆盖，每项一个 markdown section：
  - `## 1. DoD 实际 diff`（表：子条件 → 预期 / 实际 / PASS|FAIL）
  - `## 2. 路线偏差`（初始推荐 vs 实际走的路线 vs 原因）
  - `## 3. 纠偏次数`（按 L0/L1/L2/L3 分级计数）
  - `## 4. Verifier FAIL 次数`（按子契约分类）
  - `## 5. 用户打断次数`（按 DRIFT/DOD_GAP/IRREVERSIBLE/废问题 分类）
  - `## 6. 耗时 vs 估算`
  - `## 7. 成本 vs 估算`
  - `## 8. 新发现的 trap`
  - `## 9. 新发现的有效组合`
  - `## 10. 进化建议`（matrix 权重调整 / 新 skill 引入 / 反模式补充）
  - `## 11. 下次推荐`
- [ ] 每项都使用 Python `string.Template` 安全占位符（`${var_name}`，不用 f-string 防注入）
- [ ] 已知渲染数据源矩阵：
  - 项 1 → `verifier_report.evidence_chain` + `task_board.dod_expression`
  - 项 2 → `task_board.route` + `task_board.initial_route_recommendation` + `routing_events.jsonl`
  - 项 3 → `task_board.retries[]` group by level
  - 项 4 → `verifier_report.failed_conditions` 历次快照（Verifier 可能被调多次）
  - 项 5 → 用户 `PAUSED_ESCALATED` → 恢复 的次数（task_board.state_history 过滤）
  - 项 6/7 → `task_board.time_budget` / `task_board.token_budget`
  - 项 8/9/10/11 → 来自 `retro_notes_json`（用户在 retro subagent 里填的自由文本；空则 renderer 写 `<待人工补充>`）
- [ ] 头尾有 `<!-- retro-<task_id>-<ts> -->` / `<!-- /retro-<task_id>-<ts> -->` 边界注释（保持 v1 习惯，幂等 re-append 能识别）

### 3. archive/writer.py

- [ ] `write_archive_entry(task_id, task_board_path, verifier_report_path, supervisor_events_path, retro_path, archive_path="harnessFlow /failure-archive.jsonl") -> dict`
  - 读 task-board + verifier_report + supervisor_events 三源
  - 派生 13 字段 + 可选字段
  - 用 `schemas/failure-archive.schema.json` 自校验（失败 → raise `ArchiveWriteError`，**不 silent drop**）
  - append 到 `archive_path`（带 file lock，防并发写；lock 用 `fcntl.flock` 非阻塞 + 最多 3 次 5s retry）
  - 返回 entry dict（调用方可 log）
- [ ] `frequency` 派生：遍历现有 archive 找同 `(project, task_type, size, error_type, missing_subcontract 交集非空)` 条目计数 +1
- [ ] 失败情形（文件不存在 / schema 不通过 / lock 失败）都 raise 具名异常，不 silent
- [ ] 单元测试：P20 假完成场景（fixture task-board + fixture verifier_report 用 Phase 6 的 P20 测试数据复用）→ 产一条 archive entry → schema 校验通过 + 字段值正确

### 4. archive/auditor.py

- [ ] `audit(archive_path, routing_matrix_path, interval=20, min_samples_per_cell=3) -> AuditReport`
  - 读 archive 最后 `interval × N` 条（`N` = current run count / `interval`）
  - 按 `(size, task_type)` 分组聚合：失败率 / 平均 retry_count / 主导 error_type
  - 对每个 `(size, task_type)` cell：
    - 若 `failure_rate > 0.5` 且 `samples >= min_samples_per_cell` → 建议对应路线降权 `weight *= 0.8`（method3 § 7.2 阈值）
    - 若 `failure_rate < 0.1` 且 `samples >= 10` → 建议升权 `weight *= 1.1`（封顶 1.0）
  - 产出 `AuditReport`：list of `{cell: (size, task_type), current_weights, suggested_weights, reason, sample_count, failure_rate}`
- [ ] **只建议不改**：写 `harnessFlow /audit-reports/<ts>.json`，不 touch `routing-matrix.json`（method3 § 7.3 "输出建议等用户审批" 进化边界）
- [ ] `need_audit(archive_path, interval) -> bool`：若 archive 总条目数 `% interval == 0` 且 ≥ interval，返回 True
- [ ] 单元测试：
  - fixture archive 含 5 条 `(XL, 视频出片, 路线C)` 全 failed → `audit()` 建议 C 权重降到 `0.8 × 当前`
  - fixture archive 含 12 条 `(L, 后端feature, 路线B)` 全 success → 建议 B 权重升到 `1.1 ×`（封顶 1.0）
  - fixture archive 含 2 条（样本不足）→ 不产建议
  - `need_audit(5 条条目, interval=20)` → False；`need_audit(20 条, interval=20)` → True；`need_audit(40 条, interval=20)` → True

### 5. archive/retro_renderer.py

- [ ] `render_retro(task_id, task_board_path, verifier_report_path, supervisor_events_path, retro_notes_path=None, template_path="harnessFlow /schemas/retro-template.md") -> str`
  - 读数据源矩阵（§ 2 AC 列表）
  - 按 `string.Template.safe_substitute` 填模板
  - 未填字段写 `<待人工补充>`（不 raise，让 v1 幂等兼容）
  - 输出到 `harnessFlow /retros/<task_id>.md`（幂等 append，按 `retro-<task_id>-<ts>` 去重）
- [ ] `derive_field_X(...)`：每一项 1-11 对应一个私有 helper，单独可单测
- [ ] 单元测试：
  - P20 假完成 fixture → render → 11 段 section 全在，DoD diff 项正确标 `oss_head PASS/FAIL`
  - 空 retro_notes_path → 8-11 项显示 `<待人工补充>` 不 crash
  - 同一 task_id 连续 render 两次（不同 ts）→ 产两个不重叠的 `<!-- retro-... -->` block

### 6. `subagents/failure-archive-writer.md` v2（替换 v1）

- [ ] 保留 YAML frontmatter（`name: harnessFlow:failure-archive-writer`）
- [ ] 改写工作流：
  - `import archive.writer.write_archive_entry`
  - 调用流程显式：读 task-board → schema 校验 → 调 writer → 若 `need_audit` True → 调 auditor
- [ ] 与 retro-generator 协作：v2 负责结构化 archive，retro-generator 负责 markdown retro；两者可同期被主 skill 拉起（失败归档和 retro 是正交的）
- [ ] 行数 ≥ 150（v1 是 139 行，v2 扩 archive/auditor 协议 + 触发条件说明）
- [ ] 交叉引用更新：`| 结构化 failure-archive | Phase 7（未交付）|` → `| 结构化 failure-archive | archive/writer.py + schemas/failure-archive.schema.json |`

### 7. `subagents/retro-generator.md`（新）

- [ ] YAML frontmatter：`name: harnessFlow:retro-generator`，`tools: Read, Write, Bash`
- [ ] 行数 150-300
- [ ] § 1 激活时机：主 skill 在 `RETRO_CLOSE` 状态调用（`VERIFY PASS` 后 + `ABORTED` 后 + `PAUSED_ESCALATED` 恢复后），A 路线豁免
- [ ] § 2 协议：调 `archive.retro_renderer.render_retro` → 把 11 项 markdown 写到 `retros/<task_id>.md` → return path 给主 skill
- [ ] § 3 与 failure-archive-writer 的关系（两者都在 RETRO_CLOSE 被调，并行安全）
- [ ] § 4 用户 retro_notes 写回协议（主 skill 可选让用户在 PAUSED 时手填 8-11 项，存 `retros/<task_id>.notes.json`）
- [ ] § 5 反模式：禁自己判 verdict / 禁改 archive entry / 禁覆盖已有 retro block

### 8. 主 skill 收口协议补丁 (`harnessFlow-skill.md` § 8)

- [ ] 找到 § 8 VERIFY → RETRO_CLOSE → CLOSED 段落
- [ ] 补"Phase 7 RETRO_CLOSE 强制链"：
  1. 调 `harnessFlow:retro-generator` → 写 `retros/<task_id>.md`
  2. 调 `harnessFlow:failure-archive-writer` v2 → append `failure-archive.jsonl` + schema 校验
  3. 调 `archive.auditor.need_audit` → True 则调 `archive.auditor.audit` → 写 `audit-reports/<ts>.json`
  4. `task_board.retro_link = "retros/<task_id>.md"`
  5. `task_board.archive_entry_link = "failure-archive.jsonl#L<n>"`（或 jsonl 的行号引用）
  6. 只有上述 1-4 全 success（5 不强制）才允许 `current_state = CLOSED`
- [ ] A 路线豁免明文：`if route == "A": skip retro-generator + archive-writer`（delivery-checklist § 7.2 carve-out 已定，保持一致）
- [ ] 补 § 反模式一条：`不要在 retry 循环里每轮写 archive；仅在终态写`

### 9. delivery-checklist § 7.2 补丁

- [ ] § 7.2 门卫清单里新增两条：
  - 非 A 路线：`retro_link` 必须存在且 `retros/<task_id>.md` 含 `<!-- retro-... -->` 边界（已有）→ 升级为 "**含 11 项 section**" 检查（grep 11 个 section 标题）
  - `archive_entry_link` 必须存在且对应 jsonl 行能 schema 校验通过（Stop hook 调用 `jsonschema.validate`）
- [ ] 更新 `hooks/Stop-final-gate.sh`：加对 archive entry 的 schema 校验逻辑（python heredoc）

### 10. 单元测试 (`archive/tests/`)

- [ ] `test_schema.py`：schema 合法 JSON 样本全通过；非法样本（缺 `task_id` / `error_type` 非 enum / `frequency` 为 0）全 fail
- [ ] `test_writer.py`：
  - P20 假完成场景 → 写 entry → schema 校验通过
  - `frequency` 累计（已存在 2 条同类 → 新条目 `frequency=3`）
  - 并发写（两个进程同时 append）→ lock 保证顺序，不丢条目
  - verifier_report_path 不存在 → raise `ArchiveWriteError`
- [ ] `test_auditor.py`：
  - 5 条 C 路线 all failed → 建议降权
  - 12 条 B 路线 all success → 建议升权 + 封顶
  - 样本不足 → 无建议
  - `need_audit` 三个阈值点
- [ ] `test_retro_renderer.py`：
  - 11 项 section 全在
  - 空 retro_notes → 8-11 显示 `<待人工补充>`
  - 同 task_id 重复 render → 幂等 append（含不同 ts block）

### 11. 与 Phase 1-6 交叉引用

- [ ] writer / auditor 所有函数的 docstring 顶头注 `# method3 § 7.3` / `# delivery-checklist § 7.2` 出处
- [ ] subagent md 的 § 交叉引用表更新
- [ ] method3 § 7.3 里 "schema（Phase 7 落）" 改为 "schema（见 schemas/failure-archive.schema.json）"
- [ ] harnessFlow.md § 4 里 "失败归档" 一行链 `archive/`

### 12. PRD 更新 + commit

- [ ] `harness-flow.prd.md` Phase 7 → complete
- [ ] `harness-flow.prd.md` Phase 8 → in-progress + plan link（若准备接 Phase 8）
- [ ] commit：`docs(harnessFlow): Phase 7 — failure-archive 结构化 jsonl + auto-retro 11 项 + 路由审计`

## Out of Scope

- Phase 8 端到端三任务真跑（P20 / 后端 feature / Vue 页面）
- `routing-matrix.json` 的**自动**权重改写（Phase 7 只输出 audit-report 建议，人工审批后才改 matrix；method3 § 7.3 进化边界硬约束）
- trap-catalog.jsonl / skill-combination-pool.jsonl 的完整生命周期（Phase 7 只在 retro 项 8、9 的**文本记录**里留 hook，结构化入库留 Phase 9+）
- 跨项目 failure-archive 聚合视图（每项目独立，method3 § 7.3，Phase 9+ 做全局只读 dashboard）
- retro 第 5 项"废问题"自动识别（v1 只记次数，自动识别废问题要 Phase 9+ 上 LLM 分类）
- Phase 6 verifier_primitives 的扩展（Phase 7 不动 primitives）

## Risks

- **schema 字段过紧 → 真跑时条目写不进去**：每个 enum 字段都留 `"其他"` fallback + 非 enum string 字段限 `maxLength=2000`；schema 校验失败必 raise（不 silent），在 Phase 8 真跑时若频繁触发 → Phase 9 调
- **auditor 阈值过激 → 一两次偶然失败把 C 路线打死**：`min_samples_per_cell=3` 硬门 + `weight *= 0.8` 单次降权上限（不是 `× 0.5`）；且 audit-report **只建议**，人工 review 才改 matrix
- **retro_renderer 数据源缺失（Phase 6 task-board 没写 time_budget）→ 项 6、7 一直 `<待人工补充>`**：Phase 6 task-board-template.md § 1.3 已含 time_budget，检查默认值是否全填；若 Phase 6 真跑没填，Phase 7 plan 第 8 任务里补写时机
- **两个 subagent（failure-archive-writer v2 + retro-generator）并发调用 task-board**：都只读，不冲突；但必须都是**独立文件**写（archive.jsonl + retros/<id>.md），不相互踩
- **Stop hook 里做 schema 校验增加退出延迟**：校验单条 ≤ 200ms（jsonschema 对小 schema 非常快）；加缓存：同 archive 文件同次 session 只校验新增条目

## Tasks

1. **写 `schemas/failure-archive.schema.json`**（draft-07，13+ 必需 + 可选字段；P20 样本自校验通过）
2. **写 `schemas/retro-template.md`**（11 项 section，`string.Template` 占位符）
3. **写 `archive/writer.py`**（`write_archive_entry` + `frequency` 派生 + lock + schema 自校验 + 具名异常）
4. **写 `archive/auditor.py`**（`audit` + `need_audit` + audit-report 输出）
5. **写 `archive/retro_renderer.py`**（11 项 helper + `render_retro` + 幂等 append）
6. **写 `archive/tests/test_schema.py` + `test_writer.py` + `test_auditor.py` + `test_retro_renderer.py`**（TDD：先写测试再实现的建议顺序，至少 20 个 case）
7. **跑 pytest 全绿**（Phase 7 新增 + Phase 6 原 31 个不回归）
8. **重写 `subagents/failure-archive-writer.md` v2**（调 writer + auditor 协议）
9. **新建 `subagents/retro-generator.md`**
10. **改 `harnessFlow-skill.md` § 8 收口协议补丁**（RETRO_CLOSE 强制链）
11. **改 `delivery-checklist.md` § 7.2`**（archive_entry_link + 11 项 section 门卫）
12. **改 `hooks/Stop-final-gate.sh`**（加 schema 校验逻辑）
13. **更新 method3.md § 7.3 + harnessFlow.md § 4 引 archive/**
14. **独立 reviewer 审查**（dispatch general-purpose agent 读 Phase 1-6 + 本期产出）
15. **应用 P0 + P1 fixes**
16. **PRD Phase 7 → complete + commit**

## 执行策略

本 plan 按 Phase 6 成功经验：task 1-7 是"产出 + 测试驱动"核心块，task 8-13 是 subagent/文档集成，task 14-16 是 review + 收口。Task 1-6 里**严格 TDD**：先写 test_*.py 再实现对应模块；每个子任务一个 commit 颗粒度太细（太多 churn），phase-level commit 一次搞定（按 Phase 6 commit 节奏）。

Risks 里的"真跑时字段缺失"风险在 Phase 8 端到端验证时才能完全暴露 — Phase 7 plan 主动留 `<待人工补充>` fallback 避免 render crash。
