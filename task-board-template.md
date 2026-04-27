# task-board-template.md

**版本**: v1.0 (2026-04-16)
**Status**: DRAFT（Phase 4 产出）
**Readers**: 主 skill (Phase 5) / Supervisor (Phase 6) / Verifier (Phase 6) / retro 模板

> 本文档定义 `task-board.json` 的字段 schema + 写入/读取协议 + 跨会话 invariants + 2 个完整示例。主 skill 在 Phase 5 按本文档 schema 序列化任务状态；Supervisor/Verifier 按本文档 read_by 列读取。

---

## § 1 字段 schema（完整表）

### 1.1 核心字段（必需）

| 字段 | 类型 | 默认 | 写入方 | 写入时机 | 读取方 | 用途 |
|---|---|---|---|---|---|---|
| `task_id` | string (UUID) | 必填 | 主 skill `@INIT` | 任务启动瞬间 | 全部 | 全局唯一 ID，跨 session 追踪 |
| `created_at` | ISO 8601 UTC | `now()` | 主 skill `@INIT` | 启动时 | retro / audit | 生命周期起点 |
| `goal_anchor` | object `{text, hash, claude_md_path}` | 必填 | 主 skill `@CLARIFY → ROUTE_SELECT` | 澄清收尾 | Supervisor / resume guard | 不可变目标 + CLAUDE.md block hash，drift 检测锚 |
| `route_id` | enum `A \| B \| C \| C-lite \| D \| D-mini \| E \| E-lite \| F` | 必填 | 主 skill `@ROUTE_SELECT` | 用户 pick 后 | 主 skill / Supervisor / checklist | 决定调度序列 |
| `size` | enum `XS \| S \| M \| L \| XL \| XXL+` | 必填 | 主 skill `@CLARIFY` | 三维打标 | routing-matrix + checklist | 查表决策维度 1 |
| `task_type` | enum `纯代码 \| 后端 feature \| UI \| agent graph \| 文档 \| 重构 \| 研究` | 必填 | 主 skill `@CLARIFY` | 三维打标 | routing-matrix + checklist | 查表决策维度 2 |
| `risk` | enum `低 \| 中 \| 高 \| 不可逆` | 必填 | 主 skill `@CLARIFY` | 三维打标 | routing-matrix + Supervisor | 查表决策维度 3 + IRREVERSIBLE_HALT 触发 |
| `current_state` | enum（见 § 1.7 闭合枚举，20 个值） | `INIT` | 主 skill | 每次状态转移 | 主 skill / resume | 状态机当前位置 |
| `stage` | enum `@clarify \| @plan \| @impl \| @verify \| @commit \| @retro` | `@clarify` | 主 skill | 阶段切换 | Supervisor | 粗粒度阶段 |
| `dod_expression` | string (Python boolean) | 必填 | 主 skill `@PLAN` | 生成 plan 时 | Verifier | 机器可 eval 的 DoD |
| `verifier_report` | object（§ 2.1） | `null` | Verifier `@VERIFY` | eval 结束 | 主 skill / Stop hook | 收口裁定 |
| `artifacts[]` | array of `{kind, path, created_at, evidence_checks[]}` | `[]` | 主 skill `@IMPL/@VERIFY` | 产物生成时 | Verifier / retro | 物理存在证据 |

### 1.2 轨迹字段（append-only）

| 字段 | 类型 | 默认 | 写入方 | 写入时机 | 读取方 | 用途 |
|---|---|---|---|---|---|---|
| `state_history[]` | array of `{state, timestamp, trigger, from_state}` | `[]` | 主 skill | 每次转移 | retro / audit | 状态机审计轨迹 |
| `routing_events[]` | array of `{event, from_route, to_route, reason, timestamp, decided_by}` | `[]` | 主 skill / LLM 真分叉 | 路由决策 | retro / evolution | 真分叉记录 |
| `supervisor_interventions[]` | array of `{severity, code, diagnosis, suggested_action, evidence, timestamp}` | `[]` | Supervisor | 每次 INFO/WARN/BLOCK | 主 skill / retro | 干预轨迹 |
| `retries[]` | array of `{level, state, err_class, trigger, outcome, timestamp}` | `[]` | 主 skill | 每次 retry ladder 触发 | retro / evolution / state-machine § 4.3 `count_by_level()` | retry 审计（每 entry 为一次 retry 动作；级别计数 = `count_by_level(retries)`，**不维护独立 L0/L1/L2 计数字段**） |
| `red_lines[]` | array of `{code, triggered_at, context, resolution}` | `[]` | Supervisor / 主 skill | 红线触发时 | retro | 红线事件 |
| `route_changes[]` | array of `{from_route, to_route, reason, approved_by, timestamp}` | `[]` | 主 skill / Supervisor | 路线切换 | retro / evolution | 路线切换审计（含降级） |
| `skills_invoked[]` | array of `{source, name, at_state, timestamp}` | `[]` | 主 skill（每次 tool call 前写） | tool call 前 | retro | 调用轨迹（来源前缀见 flow-catalog § 1.2） |
| `stage_artifacts[]` | array of `{stage_id, produced_at, artifacts[{artifact_ref, location, size_bytes, schema_valid}], gate_eval{predicate, result, evaluated_at}}` | `[]` | 主 skill（每阶段退出时写） | stage exit | Verifier / Supervisor / Stop gate | **v1.1 新增**：stage-contract 产物追踪（stage-contracts.md § 10），`validate_stage_io` 的输入；任一 `artifacts[].missing` 或 `gate_eval.result==false` → Supervisor `DOD_GAP_ALERT` |
| `pipeline_graph` | object `{schema_version, emitted_at, nodes[], edges[]}` | `null` | 主 skill `@PIPELINE_EMIT`（ROUTE_SELECT 后） | `pipelines.contract_loader.emit_pipeline_graph()` 一次性 emit | dashboard / Supervisor / Verifier | **Slice A 新增**：13-节点 PMP 蓝图，节点完成时 `nodes[i].status` += `passed/running/failed/rolled_back`；edges 含 forward/parallel_split/converge/rollback/augment |
| `supervision_graph` | object | `null` | （Slice C 落地） | — | — | **Slice C 占位**：6-节点监督流水线，本片仅 schema 占位不写入 |
| `prd` | object `{背景, 目标, 用户故事[], 功能[], 验收标准[], 原型链接, 技术方案, 风险[]}` | `null` | 主 skill `@PLAN`（C/E 路线） | N5 节点完成时 | dashboard / retro | **Slice A 新增**：阿里风 PRD 八段；A/B/D/F 路线 null |
| `execution_plan` | object `{wbs_ref, gantt[{wp_id, start, end, depends_on[]}]}` | `null` | 主 skill `@PLAN` | N10 节点完成时 | dashboard / retro | **Slice A 新增**：WBS 时间+顺序+依赖 |
| `tdd_cases.definitions[]` | array of `{case_id, given, when, then, priority}` | `[]` | 主 skill `@PLAN` | N6 节点完成时 | Verifier / dashboard TDD 卡 | **Slice A 拆分**：原 `tdd_cases[]` 的"定义"段，写在 N6 |
| `tdd_cases.execution_results[]` | array of `{case_id, status, evidence_path, executed_at}` | `[]` | 主 skill `@IMPL` / Verifier `@VERIFY` | N11 节点 loop 内 + N12 验证时 | retro | **Slice A 拆分**：原 `tdd_cases[]` 的"执行"段，写在 N11/N12 |

#### § 1.2.1 pipeline_graph 详细 schema（Slice A 新增）

```json
{
  "pipeline_graph": {
    "schema_version": "1.0",
    "emitted_at": "2026-04-26T18:30:00Z",
    "nodes": [
      {
        "node_id": "N3",
        "step": 3,
        "phase": "initiating",
        "name": "目标分析+锁定",
        "owner_skill": "superpowers:brainstorming",
        "layout": {"x": 255, "y": 170, "w": 105, "h": 60},
        "writes_to_field": ["goal_anchor", "_derived.delivery_goal.locked_goal"],
        "status": "passed",
        "started_at": "2026-04-26T18:31:10Z",
        "completed_at": "2026-04-26T18:33:42Z"
      }
    ],
    "edges": [
      {"from": "N5", "to": "N6", "kind": "parallel_split", "label": null},
      {"from": "N6", "to": "N8", "kind": "converge", "label": null},
      {"from": "N12", "to": "N11", "kind": "rollback", "label": "FAIL → 重 loop"}
    ]
  }
}
```

`nodes[i].status` 取值：`pending | running | passed | failed | rolled_back | augmenting`。

每节点完成时，主 skill 同时 append 一条 `state_history[]`（已存在）+ 写
`pipeline_graph.nodes[i]` 状态/时间戳，并触发 `supervisor_pulse_code`（见
`pipelines/13_node_contract.yaml`）spawn 一次 Supervisor pulse。

任一节点 `validate_node_io(phase='exit')` 返 BLOCK → `current_state →
PAUSED_ESCALATED`，节点 status 标 `failed`，Supervisor 写
`DOD_GAP_ALERT` 红线。

### 1.3 度量与预算字段

| 字段 | 类型 | 默认 | 写入方 | 写入时机 | 读取方 | 用途 |
|---|---|---|---|---|---|---|
| `warn_counter` | int | 0 | Supervisor | 每条 WARN 写入时 +1 | 主 skill（判降级阈值） | WARN 降级（routing-matrix § 5.1） |
| `cost_budget` | object `{token_used, token_cap, cost_usd, cost_cap_usd}` | `{}` | 主 skill | 每步估算 | Supervisor | budget guard |
| `time_budget` | object `{started_at, elapsed_sec, cap_sec}` | `{started_at: now()}` | 主 skill | 持续 | Supervisor | 超时检测 |
| `context_budget` | object `{tokens_in_context, threshold}` | `{}` | 主 skill | PostToolUse hook | Supervisor | context 临界预警 |

### 1.4 跨会话字段

| 字段 | 类型 | 默认 | 写入方 | 写入时机 | 读取方 | 用途 |
|---|---|---|---|---|---|---|
| `cross_session_ids[]` | array of `{session_id, entered_at, exited_at, reason}` | `[]` | 主 skill | 每次 save/resume | resume guard | 跨 session 追踪 |
| `session_current` | string (session_id) | 当前 session | 主 skill | session 切换 | 全部 | 当前活动 session |
| `checkpoint_refs[]` | array of `{session_id, snapshot_path, at_state, timestamp}` | `[]` | 主 skill | 每次 save-session | resume / retro | 快照恢复点索引 |

### 1.5 收口与进化字段

| 字段 | 类型 | 默认 | 写入方 | 写入时机 | 读取方 | 用途 |
|---|---|---|---|---|---|---|
| `commit_sha` | string | `null` | 主 skill `@COMMIT` | commit 生成后 | retro | 代码落地证据 |
| `pr_url` | string | `null` | 主 skill `@COMMIT` | prp-pr 后 | retro | PR 链接 |
| `retro_link` | string (path) | `null` | 主 skill `@RETRO_CLOSE` | retro 写完后 | audit | retro 文档路径 |
| `failure_archive_refs[]` | array of entry id | `[]` | failure-archive-writer | 有失败时 | evolution | 失败归档引用 |
| `archive_entry_link` | string `"failure-archive.jsonl#L<n>"` | `null` | 主 skill `@RETRO_CLOSE` | failure-archive-writer 返回 `line_no` 后 | Stop gate / audit | Phase 7：非 A 路线必填；Stop gate § 7.2 校验其存在且可 schema 校验 |
| `audit_link` | string (path) | `null` | 主 skill `@RETRO_CLOSE` | 触发审计且 audit_report.path 非空时 | 人工 review | Phase 7：`audit-reports/audit-*.json` 路径，由 `archive/auditor.py` 产出，**只建议不改 matrix** |
| `evolution_suggestions[]` | array of `{kind, target, diff, approved}` | `[]` | retro / evolution | retro 产出 | 人审批 | 进化候选（matrix 权重 / trap 规则 / 新组合） |

### 1.6 关闭字段

| 字段 | 类型 | 默认 | 写入方 | 写入时机 | 读取方 | 用途 |
|---|---|---|---|---|---|---|
| `closed_at` | ISO 8601 UTC | `null` | Stop hook / 主 skill | 进 CLOSED 状态 | audit | 生命周期终点 |
| `final_outcome` | enum `success \| failed \| aborted \| false_complete_reported` | `null` | 主 skill | 终态写入 | evolution | 结果分类；`false_complete_reported` 为 Phase 7 新增，专记 P20 类"agent 自报 success 但 Verifier 复核 FAIL"事件（与 failure-archive schema enum 对齐） |
| `abort_reason` | string | `null` | 主 skill | 进 ABORTED 时 | retro | 中止原因 |
| `insufficient_evidence_count` | int | 0 | 主 skill `@VERIFY` | Verifier 返回 INSUFFICIENT_EVIDENCE 时 +1 | 状态机 § 7 P3 分支 | 防 IMPL↔VERIFY 死循环（cap = 2） |

### 1.7 `current_state` 闭合枚举

完整值域（20 个，对应 state-machine § 1）：

```json
{
  "core_15": [
    "INIT", "CLARIFY", "ROUTE_SELECT", "PLAN", "CHECKPOINT_SAVE",
    "IMPL", "MID_CHECKPOINT", "MID_RETRO", "VERIFY", "SANTA_LOOP",
    "COMMIT", "RETRO_CLOSE", "CLOSED", "PAUSED_ESCALATED", "ABORTED"
  ],
  "route_specific_5": [
    "UI_SCREENSHOT",   // D 路线
    "NODE_UNIT_TEST",  // E 路线
    "GRAPH_COMPILE",   // E 路线
    "RESEARCH",        // F 路线
    "DECISION_LOG"     // F 路线
  ]
}
```

Schema 校验：任何 `current_state` 不在此 20 值范围内，Supervisor 立即写 BLOCK + abort。

### 1.8 写入方冲突规则（append-only 字段）

以下字段为 append-only 列表，多方可写但需遵循**单写入者 per entry** 规则（一个 entry 由唯一主体写入；多主体读，不得修改他者 entry）：

| 字段 | 允许的写入方 | 冲突解决 |
|---|---|---|
| `state_history[]` | 仅主 skill | - |
| `routing_events[]` | 主 skill（常规）/ LLM 分叉节点（真分叉） | 按 timestamp 单调递增 |
| `supervisor_interventions[]` | 仅 Supervisor | - |
| `retries[]` | 仅主 skill | - |
| `red_lines[]` | Supervisor（触发时）+ 主 skill（E13 L3 触发） | 以 `code + triggered_at` 去重 |
| `artifacts[]` | 主 skill（记录产出）/ Verifier（补 evidence_checks） | Verifier 只允许 append `evidence_checks[]` 到已有 entry，不新建 entry |
| `skills_invoked[]` | 仅主 skill | tool call 前同步写 |
| `cross_session_ids[]` | 仅主 skill（resume/save 边界） | - |
| `checkpoint_refs[]` | 仅主 skill | - |

**原子性**：所有写入经 `<task_id>.lock` 文件序列化（见 § 5.2）。

---

## § 2 嵌套对象 schema

### 2.1 `verifier_report`

```json
{
  "overall": "PASS | FAIL | INSUFFICIENT_EVIDENCE",
  "evaluated_at": "2026-04-16T12:34:56Z",
  "evaluator": "harnessFlow:verifier",
  "dod_expression": "<same as task-board.dod_expression>",
  "primitives_resolved": [
    {"primitive": "file_exists", "args": ["media/p20.mp4"], "result": true, "evidence": "ls -la media/p20.mp4 → 3.4MB"},
    {"primitive": "ffprobe_duration", "args": ["media/p20.mp4"], "result": 42.7, "threshold": "> 0", "pass": true},
    {"primitive": "oss_head", "args": ["s3://.../p20.mp4"], "result": 200, "pass": true}
  ],
  "pass_all": true,
  "failed_conditions": [],
  "red_lines_detected": [],
  "notes": "All 3 artifact-level checks PASS."
}
```

### 2.2 `artifacts[]` entry

```json
{
  "kind": "mp4 | oss_object | pr | decision_log | screenshot | pytest_report | eval_report",
  "path": "media/p20.mp4 | https://... | PR#123 | docs/decision.md",
  "created_at": "ISO 8601",
  "size_bytes": 3567890,
  "evidence_checks": [
    {"check": "file_exists", "pass": true},
    {"check": "size > 0", "pass": true},
    {"check": "ffprobe_duration > 0", "pass": true}
  ],
  "linked_state": "VERIFY"
}
```

### 2.3 `supervisor_interventions[]` entry

```json
{
  "severity": "INFO | WARN | BLOCK",
  "code": "DRIFT_WARNING | COST_BUDGET | IS_STUCK | IRREVERSIBLE_HALT | ...",
  "diagnosis": "Supervisor 观察到 3 次相同 tool 调用未产出新 artifact",
  "suggested_action": "switch skill B → C 或 等用户决策",
  "evidence": ["tool_call_1", "tool_call_2", "tool_call_3"],
  "timestamp": "ISO 8601",
  "triggered_transition": "IMPL → IMPL (L1 retry)"
}
```

---

## § 3 完整示例 JSON

### 3.1 示例 A — 典型 C 路线成功（aigc 后端加 Product Hunt 素材源）

```json
{
  "task_id": "4c2e0d3a-1b2f-4e5d-9f3a-1234567890ab",
  "created_at": "2026-04-17T09:00:00Z",
  "goal_anchor": {
    "text": "aigc 后端新增 Product Hunt 素材源采集，复用 Reddit 采集器骨架",
    "hash": "sha256:abc123...",
    "claude_md_path": "aigc/backend/CLAUDE.md#goal-anchor-4c2e0d3a"
  },
  "route_id": "C",
  "size": "L",
  "task_type": "后端 feature",
  "risk": "中",
  "current_state": "CLOSED",
  "stage": "@retro",
  "dod_expression": "(pytest_exit_code('tests/test_producthunt.py') == 0) AND (uvicorn_started('localhost:8000')) AND (curl_status('http://localhost:8000/materials/producthunt') == 200) AND (schema_valid(curl_json('http://localhost:8000/materials/producthunt'), 'schemas/material_ph.json')) AND (code_review_verdict == 'PASS')",
  "verifier_report": {
    "overall": "PASS",
    "evaluated_at": "2026-04-17T13:42:00Z",
    "evaluator": "harnessFlow:verifier",
    "primitives_resolved": [
      {"primitive": "pytest_exit_code", "args": ["tests/test_producthunt.py"], "result": 0, "pass": true},
      {"primitive": "uvicorn_started", "args": ["localhost:8000"], "result": true, "pass": true},
      {"primitive": "curl_status", "args": ["http://localhost:8000/materials/producthunt"], "result": 200, "pass": true},
      {"primitive": "schema_valid", "args": ["...", "schemas/material_ph.json"], "result": true, "pass": true},
      {"primitive": "code_review_verdict", "args": [], "result": "PASS", "pass": true}
    ],
    "pass_all": true,
    "failed_conditions": [],
    "red_lines_detected": []
  },
  "artifacts": [
    {"kind": "pytest_report", "path": "reports/pytest-producthunt.xml", "created_at": "2026-04-17T13:40:00Z", "evidence_checks": [{"check": "file_exists", "pass": true}], "linked_state": "VERIFY"},
    {"kind": "pr", "path": "PR#456", "created_at": "2026-04-17T13:55:00Z", "evidence_checks": [], "linked_state": "COMMIT"}
  ],
  "state_history": [
    {"state": "INIT", "timestamp": "2026-04-17T09:00:00Z", "trigger": "user /harnessFlow", "from_state": null},
    {"state": "CLARIFY", "timestamp": "2026-04-17T09:01:00Z", "trigger": "E1", "from_state": "INIT"},
    {"state": "ROUTE_SELECT", "timestamp": "2026-04-17T09:15:00Z", "trigger": "E2", "from_state": "CLARIFY"},
    {"state": "PLAN", "timestamp": "2026-04-17T09:20:00Z", "trigger": "E3", "from_state": "ROUTE_SELECT"},
    {"state": "CHECKPOINT_SAVE", "timestamp": "2026-04-17T10:10:00Z", "trigger": "E4", "from_state": "PLAN"},
    {"state": "IMPL", "timestamp": "2026-04-17T10:12:00Z", "trigger": "E5", "from_state": "CHECKPOINT_SAVE"},
    {"state": "MID_CHECKPOINT", "timestamp": "2026-04-17T12:30:00Z", "trigger": "E6", "from_state": "IMPL"},
    {"state": "VERIFY", "timestamp": "2026-04-17T13:40:00Z", "trigger": "E9", "from_state": "MID_CHECKPOINT"},
    {"state": "COMMIT", "timestamp": "2026-04-17T13:50:00Z", "trigger": "E10", "from_state": "VERIFY"},
    {"state": "RETRO_CLOSE", "timestamp": "2026-04-17T14:00:00Z", "trigger": "E14", "from_state": "COMMIT"},
    {"state": "CLOSED", "timestamp": "2026-04-17T14:10:00Z", "trigger": "E15", "from_state": "RETRO_CLOSE"}
  ],
  "routing_events": [],
  "supervisor_interventions": [
    {"severity": "INFO", "code": "PROGRESS_OK", "diagnosis": "实施进度符合 plan", "timestamp": "2026-04-17T12:00:00Z"}
  ],
  "retries": [],
  "red_lines": [],
  "route_changes": [],
  "skills_invoked": [
    {"source": "SP", "name": "brainstorming", "at_state": "CLARIFY", "timestamp": "2026-04-17T09:02:00Z"},
    {"source": "ECC", "name": "prp-prd", "at_state": "CLARIFY", "timestamp": "2026-04-17T09:10:00Z"},
    {"source": "ECC", "name": "prp-plan", "at_state": "PLAN", "timestamp": "2026-04-17T09:20:00Z"},
    {"source": "ECC", "name": "save-session", "at_state": "CHECKPOINT_SAVE", "timestamp": "2026-04-17T10:10:00Z"},
    {"source": "ECC", "name": "prp-implement", "at_state": "IMPL", "timestamp": "2026-04-17T10:15:00Z"},
    {"source": "ECC", "name": "code-reviewer", "at_state": "IMPL", "timestamp": "2026-04-17T12:20:00Z"},
    {"source": "harnessFlow", "name": "verifier", "at_state": "VERIFY", "timestamp": "2026-04-17T13:40:00Z"},
    {"source": "ECC", "name": "prp-commit", "at_state": "COMMIT", "timestamp": "2026-04-17T13:50:00Z"},
    {"source": "ECC", "name": "retro", "at_state": "RETRO_CLOSE", "timestamp": "2026-04-17T14:00:00Z"}
  ],
  "warn_counter": 0,
  "cost_budget": {"token_used": 180000, "token_cap": 500000, "cost_usd": 1.2, "cost_cap_usd": 10.0},
  "time_budget": {"started_at": "2026-04-17T09:00:00Z", "elapsed_sec": 18600, "cap_sec": 28800},
  "cross_session_ids": [
    {"session_id": "sess-001", "entered_at": "2026-04-17T09:00:00Z", "exited_at": "2026-04-17T14:10:00Z", "reason": "normal_close"}
  ],
  "session_current": "sess-001",
  "checkpoint_refs": [
    {"session_id": "sess-001", "snapshot_path": ".claude/sessions/sess-001-ckpt-1.json", "at_state": "CHECKPOINT_SAVE", "timestamp": "2026-04-17T10:10:00Z"},
    {"session_id": "sess-001", "snapshot_path": ".claude/sessions/sess-001-ckpt-2.json", "at_state": "MID_CHECKPOINT", "timestamp": "2026-04-17T12:30:00Z"}
  ],
  "commit_sha": "a1b2c3d",
  "pr_url": "https://github.com/.../pull/456",
  "retro_link": "harnessFlow /retros/4c2e0d3a-retro.md",
  "failure_archive_refs": [],
  "evolution_suggestions": [],
  "closed_at": "2026-04-17T14:10:00Z",
  "final_outcome": "success",
  "abort_reason": null
}
```

### 3.2 示例 B — P20 失败回放（旧 C 翻车场景）

```json
{
  "task_id": "p20-replay-2026-04-16",
  "created_at": "2026-04-16T08:00:00Z",
  "goal_anchor": {
    "text": "aigcv2 P20 视频端到端出片，mp4 + OSS key + 可播放",
    "hash": "sha256:def456...",
    "claude_md_path": "aigcv2/CLAUDE.md#goal-anchor-p20"
  },
  "route_id": "C",
  "size": "XL",
  "task_type": "agent graph",
  "risk": "不可逆",
  "current_state": "PAUSED_ESCALATED",
  "stage": "@verify",
  "dod_expression": "(file_exists('media/p20.mp4')) AND (ffprobe_duration('media/p20.mp4') > 0) AND (oss_head('s3://.../p20.mp4').status_code == 200) AND (playback_check('media/p20.mp4')) AND (uvicorn_started('localhost:8000')) AND (curl_status('POST /produce') == 200) AND (retro_exists('harnessFlow /retros/p20-retro.md'))",
  "verifier_report": {
    "overall": "FAIL",
    "evaluated_at": "2026-04-16T17:30:00Z",
    "evaluator": "harnessFlow:verifier",
    "primitives_resolved": [
      {"primitive": "file_exists", "args": ["media/p20.mp4"], "result": false, "pass": false, "evidence": "ls: cannot access 'media/p20.mp4'"},
      {"primitive": "uvicorn_started", "args": ["localhost:8000"], "result": false, "pass": false, "evidence": "curl: (7) Failed to connect to localhost port 8000"},
      {"primitive": "oss_head", "args": ["s3://.../p20.mp4"], "result": 404, "pass": false}
    ],
    "pass_all": false,
    "failed_conditions": ["file_exists", "uvicorn_started", "oss_head", "playback_check", "curl_status"],
    "red_lines_detected": ["DOD_GAP_ALERT"],
    "notes": "Core artifacts missing. IMPL 声称完成但无证据。触发 L3 escalate"
  },
  "artifacts": [],
  "state_history": [
    {"state": "INIT", "timestamp": "2026-04-16T08:00:00Z", "trigger": "user /harnessFlow", "from_state": null},
    {"state": "CLARIFY", "timestamp": "2026-04-16T08:02:00Z", "trigger": "E1", "from_state": "INIT"},
    {"state": "ROUTE_SELECT", "timestamp": "2026-04-16T08:20:00Z", "trigger": "E2", "from_state": "CLARIFY"},
    {"state": "PLAN", "timestamp": "2026-04-16T08:25:00Z", "trigger": "E3", "from_state": "ROUTE_SELECT"},
    {"state": "CHECKPOINT_SAVE", "timestamp": "2026-04-16T09:30:00Z", "trigger": "E4", "from_state": "PLAN"},
    {"state": "IMPL", "timestamp": "2026-04-16T09:32:00Z", "trigger": "E5", "from_state": "CHECKPOINT_SAVE"},
    {"state": "VERIFY", "timestamp": "2026-04-16T17:30:00Z", "trigger": "E9a", "from_state": "IMPL"},
    {"state": "SANTA_LOOP", "timestamp": "2026-04-16T17:31:00Z", "trigger": "E11", "from_state": "VERIFY"},
    {"state": "IMPL", "timestamp": "2026-04-16T17:32:00Z", "trigger": "E12", "from_state": "SANTA_LOOP"},
    {"state": "VERIFY", "timestamp": "2026-04-16T18:00:00Z", "trigger": "E9a", "from_state": "IMPL"},
    {"state": "SANTA_LOOP", "timestamp": "2026-04-16T18:01:00Z", "trigger": "E11", "from_state": "VERIFY"},
    {"state": "PAUSED_ESCALATED", "timestamp": "2026-04-16T18:30:00Z", "trigger": "E13", "from_state": "SANTA_LOOP"}
  ],
  "routing_events": [],
  "supervisor_interventions": [
    {"severity": "WARN", "code": "IS_STUCK", "diagnosis": "IMPL 状态下相同 tool 调用 ≥ 3 次无新 artifact", "timestamp": "2026-04-16T14:00:00Z"},
    {"severity": "WARN", "code": "TIME_BUDGET_EXCEEDED", "diagnosis": "elapsed_sec 37800 > cap_sec 28800", "timestamp": "2026-04-16T18:00:00Z"},
    {"severity": "BLOCK", "code": "DOD_GAP_ALERT", "diagnosis": "IMPL 声称完成但 artifacts[] 为空", "timestamp": "2026-04-16T17:30:00Z"}
  ],
  "retries": [
    {"level": "L1", "state": "SANTA_LOOP", "err_class": "dod_fail", "trigger": "verifier FAIL 1", "outcome": "re-impl", "timestamp": "2026-04-16T17:32:00Z"},
    {"level": "L2", "state": "SANTA_LOOP", "err_class": "dod_fail", "trigger": "verifier FAIL 2", "outcome": "switch skill", "timestamp": "2026-04-16T18:01:00Z"}
  ],
  "red_lines": [
    {"code": "DOD_GAP_ALERT", "triggered_at": "2026-04-16T17:30:00Z", "context": "verifier FAIL 1st", "resolution": "pending_user"},
    {"code": "L3_LADDER_EXHAUSTED", "triggered_at": "2026-04-16T18:30:00Z", "context": "verifier FAIL 2nd + ladder 耗尽（L1+L2 各 1 次触顶）", "resolution": "pending_user"}
  ],
  "route_changes": [],
  "skills_invoked": [
    {"source": "SP", "name": "brainstorming", "at_state": "CLARIFY", "timestamp": "2026-04-16T08:03:00Z"},
    {"source": "ECC", "name": "prp-prd", "at_state": "CLARIFY", "timestamp": "2026-04-16T08:10:00Z"},
    {"source": "ECC", "name": "prp-plan", "at_state": "PLAN", "timestamp": "2026-04-16T08:26:00Z"},
    {"source": "ECC", "name": "save-session", "at_state": "CHECKPOINT_SAVE", "timestamp": "2026-04-16T09:30:00Z"},
    {"source": "ECC", "name": "prp-implement", "at_state": "IMPL", "timestamp": "2026-04-16T09:33:00Z"},
    {"source": "harnessFlow", "name": "verifier", "at_state": "VERIFY", "timestamp": "2026-04-16T17:30:00Z"},
    {"source": "ECC", "name": "santa-loop", "at_state": "SANTA_LOOP", "timestamp": "2026-04-16T17:31:00Z"},
    {"source": "harnessFlow", "name": "verifier", "at_state": "VERIFY", "timestamp": "2026-04-16T18:00:00Z"}
  ],
  "insufficient_evidence_count": 0,
  "warn_counter": 4,
  "cost_budget": {"token_used": 420000, "token_cap": 500000, "cost_usd": 8.5, "cost_cap_usd": 10.0},
  "time_budget": {"started_at": "2026-04-16T08:00:00Z", "elapsed_sec": 37800, "cap_sec": 28800},
  "cross_session_ids": [{"session_id": "sess-p20", "entered_at": "2026-04-16T08:00:00Z"}],
  "session_current": "sess-p20",
  "checkpoint_refs": [
    {"session_id": "sess-p20", "snapshot_path": ".claude/sessions/sess-p20-ckpt-1.json", "at_state": "CHECKPOINT_SAVE", "timestamp": "2026-04-16T09:30:00Z"}
  ],
  "commit_sha": null,
  "pr_url": null,
  "retro_link": null,
  "failure_archive_refs": ["fa-p20-001"],
  "evolution_suggestions": [
    {"kind": "trap_catalog", "target": "harnessFlow:verifier", "diff": "新增 trap: IMPL 声称完成但 artifacts[] 为空 → BLOCK", "approved": false}
  ],
  "closed_at": null,
  "final_outcome": "failed",
  "abort_reason": null
}
```

---

## § 4 跨会话 invariants

resume-session 时主 skill 必须比较这些字段，不一致则 PAUSED_ESCALATED（对应 state-machine § 5.3）：

| 字段 | 比较方式 | 不一致动作 |
|---|---|---|
| `task_id` | 字符串相等 | 错误任务，ABORTED |
| `goal_anchor.hash` | sha256 相等 | DRIFT_CRITICAL → PAUSED_ESCALATED |
| `route_id` | 字符串相等（允许 `route_changes[]` 中显式切换） | 未登记切换 → red_line |
| `dod_expression` | 字符串相等 | 锁定后禁改 → DOD_GAP_ALERT |
| `size` / `task_type` / `risk` | 字符串相等 | 三维漂移 → DRIFT_WARNING |

---

## § 5 存储与并发

### 5.1 存储路径

- 本地：`harnessFlow /task-boards/<task_id>.json`
- **任务锁文件**：`harnessFlow /task-boards/<task_id>.lock`（见 § 5.2 协议）
- 会话快照（session snapshot）：`.claude/sessions/sess-<id>-ckpt-<n>.json`（包含 task-board 完整序列化）
- 跨会话索引：`harnessFlow /task-boards/_index.jsonl`（append-only，每任务一行 `{task_id, created_at, final_outcome}`）

### 5.2 写入规则（原子 + 锁）

**原子写（tmp + atomic rename）**：

```python
# 每次写入全量写，不做增量合并
def write_task_board(task_id, data):
    path = f"harnessFlow /task-boards/{task_id}.json"
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(data, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)  # POSIX 原子 rename
```

**文件锁协议（强制）**：

```python
# 任何写入都必须先拿锁
import fcntl
def with_task_lock(task_id):
    lock_path = f"harnessFlow /task-boards/{task_id}.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX)  # 阻塞式独占锁
    try:
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
```

- 每次写入：拿锁 → 读最新 → 修改 → 原子 rename → 放锁
- `session_current` 字段**不是锁**，仅是"最近活动 session" 指示；真正并发保护靠 `.lock` 文件
- resume 时先拿锁 → 比较 `session_current` → 若为 stale session（对应 pid 不存在 / 不是自己） → 强制抢占并更新 `session_current`
- 多 session 指向同一 `task_id`：串行（锁保证）；并发写入被阻塞，不报错

### 5.3 gitignore

- task-board 不入 git（ephemeral 状态）
- 但 `evolution_suggestions` 合入后衍生的 matrix / trap catalog 变更必须走 PR

---

## § 6 字段完整性校验（Phase 5 主 skill 启动时）

主 skill 每次状态转移前运行 schema 校验。把"必填字段列表"与"gate 谓词"**分成两张表**——字段是名词（存在即可），谓词是布尔（取值还要对）。

### 6.1 REQUIRED_FIELDS_BY_STATE（字段名词；缺失 → WARN）

覆盖全部 20 个状态（core 15 + route-specific 5）。继承语义：后继状态必须已有前驱状态写过的字段。

```python
REQUIRED_FIELDS_BY_STATE = {
    # 核心 15
    "INIT":            ["task_id", "created_at"],
    "CLARIFY":         ["task_id", "goal_anchor"],
    "ROUTE_SELECT":    ["goal_anchor", "size", "task_type", "risk"],
    "PLAN":            ["route_id", "dod_expression"],
    "CHECKPOINT_SAVE": ["route_id", "dod_expression", "checkpoint_refs", "cross_session_ids"],
    "IMPL":            ["route_id", "dod_expression", "state_history", "skills_invoked"],
    "MID_CHECKPOINT":  ["checkpoint_refs"],
    "MID_RETRO":       ["artifacts"],  # mid_retro 文件入 artifacts
    "VERIFY":          ["artifacts"],
    "SANTA_LOOP":      ["retries", "verifier_report"],
    "COMMIT":          ["verifier_report", "commit_sha"],
    "RETRO_CLOSE":     ["retro_link", "commit_sha"],
    "CLOSED":          ["commit_sha", "retro_link", "final_outcome", "closed_at"],
    "PAUSED_ESCALATED":["red_lines"],
    "ABORTED":         ["abort_reason", "final_outcome"],
    # 路线专有 5
    "UI_SCREENSHOT":   ["artifacts"],             # 至少一个 screenshot entry
    "NODE_UNIT_TEST":  ["skills_invoked", "artifacts"],
    "GRAPH_COMPILE":   ["artifacts"],             # graph_diff.md 等
    "RESEARCH":        ["skills_invoked"],        # Explore/WebSearch 调用记录
    "DECISION_LOG":    ["artifacts"],             # decision_log.md
}
```

### 6.2 GATE_PREDICATES（进入 gate 状态前必须 True）

```python
GATE_PREDICATES = {
    # 进 COMMIT 前必须：verifier 通过 + 无红线
    "COMMIT": [
        "verifier_report is not None",
        "verifier_report['overall'] == 'PASS'",
        "len(verifier_report.get('red_lines_detected', [])) == 0",
    ],
    # 进 CLOSED 前必须：retro 完整 + final_outcome 写好
    "CLOSED": [
        "retro_link is not None or route_id == 'A'",   # A 路线允许跳过 retro
        "final_outcome in ('success', 'failed', 'aborted')",
        "closed_at is not None",
    ],
    # 进 RETRO_CLOSE 前：commit 已落
    "RETRO_CLOSE": [
        "commit_sha is not None or route_id == 'F'",   # F 路线无 commit
    ],
    # 进 PAUSED_ESCALATED：必须有一个红线条目解释原因
    "PAUSED_ESCALATED": [
        "len(red_lines) > 0",
    ],
}
```

### 6.3 违反处理

- **REQUIRED_FIELDS 缺失** → Supervisor 写 `WARN`（非 BLOCK），主 skill 允许先补再转
- **GATE_PREDICATES 不满足** → 主 skill 拒绝状态转移 + 写 `BLOCK`；Stop hook 另行兜底（delivery-checklist § 7.2）
- 进 `CLOSED` 前主 skill 必须过 `CLOSED` 的 REQUIRED_FIELDS + GATE_PREDICATES（Stop hook 同步校验，双保险）

---

*本文档定义 task-board.json 的 schema 与协议。状态机 § state-machine.md；交付证据清单 § delivery-checklist.md；主 skill 在 Phase 5 按本文档序列化状态。*

*— v1.0 end —*
