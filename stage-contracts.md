# stage-contracts.md

**版本**: v1.1 (2026-04-17) — harnessFlow v1.1 Stage Contract 首版
**Status**: NORMATIVE（Phase 9 产出，作为 flow-catalog / state-machine 的运行时合约绑定层）
**Readers**: 主 skill (§ 5 `validate_stage_io`) / Supervisor (DOD_GAP_ALERT 判断) / Verifier（交叉校验 DoD） / Stop gate（收口前兜底） / 贡献者
**Schema**: [`schemas/stage-contract.schema.json`](schemas/stage-contract.schema.json)

> 本文档是 harnessFlow 的**阶段级契约**。`flow-catalog.md` 定每条路线"按什么顺序调什么 skill"，本文档定**每个阶段必须拿到什么（inputs）+ 必须产出什么（outputs）+ 进下一阶段的闸口（gate_predicate）**。
>
> 核心不变量：**上游阶段的 outputs = 下游阶段的 inputs**。任一阶段缺输入或缺输出 → Supervisor 判 `DOD_GAP_ALERT` 红线 → `PAUSED_ESCALATED`。

---

## § 1 Artifact Catalog（22 个符号化产物）

每个 artifact_ref 在整个 harnessFlow 生命周期中**唯一**。一次只由 **一个** producer stage 产出，后续多个 stage 可消费。

| artifact_ref | format | 典型位置 / 形态 | producer stage_id | 主要 consumers |
|---|---|---|---|---|
| `user_input_raw` | text | task-board.initial_user_input | external | *-CLARIFY |
| `clarified_task_description` | text | task-board.clarified_description | *-CLARIFY | *-ROUTE_SELECT, *-PLAN |
| `task_dimensions` | json | task-board.{size,task_type,risk} | *-CLARIFY | *-ROUTE_SELECT |
| `goal_anchor_hash` | sha256_hex | task-board.goal_anchor.hash + CLAUDE.md block | *-CLARIFY | ALL（invariant，resume 校验） |
| `route_id` | text (enum A-F) | task-board.route_id | *-ROUTE_SELECT | *-PLAN, *-IMPL |
| `dod_expression` | text (Python bool) | task-board.dod_expression | *-PLAN（A 路线用 default 模板，不单独产出） | *-VERIFY |
| `prp_prd_doc` | markdown | `docs/prds/<task>.md` | C-CLARIFY-PRD（仅 C） | C-PLAN |
| `prp_plan_doc` | markdown | `plans/<task>.plan.md` | *-PLAN（B/C/D/E） | *-IMPL |
| `graph_diff_md` | markdown | `plans/<task>.graph_diff.md` | E-PLAN-GRAPHDIFF（仅 E） | E-IMPL |
| `session_checkpoint_ref` | path | `sessions/<task>-<n>.json` | *-CHECKPOINT_SAVE / *-MID_CHECKPOINT | RESUMING |
| `impl_diff` | diff | `git diff` 产出 + task-board.artifacts[] | *-IMPL | *-VERIFY, *-COMMIT |
| `code_review_report` | json | task-board.artifacts[] entry | *-IMPL-CODEREVIEW（parallel） | *-VERIFY |
| `test_report` | text+json | `pytest.xml` / `artifacts/test-report.json` | *-IMPL（作为 IMPL 子步） | *-VERIFY |
| `screenshot_artifacts` | png | `artifacts/*.png` | D-UI_SCREENSHOT（仅 D） | D-VERIFY |
| `research_findings_md` | markdown | `research/<task>-findings.md` | F-RESEARCH（仅 F） | F-DECISION_LOG |
| `decision_log_md` | markdown | `decisions/<task>-decision.md` | F-DECISION_LOG（仅 F） | F-VERIFY, F-RETRO_CLOSE |
| `verifier_report` | json | `verifier_reports/<task>.json` | *-VERIFY（Verifier subagent 独立产出） | *-COMMIT, *-SANTA_LOOP, *-RETRO_CLOSE |
| `santa_loop_trace` | json | task-board.santa_loop_rounds[] | *-SANTA_LOOP（仅 B/C/D/E FAIL 时） | *-VERIFY（re-entry） |
| `commit_sha` | sha256_hex | task-board.commit_sha | *-COMMIT | *-RETRO_CLOSE |
| `pr_url` | url | task-board.pr_url | *-COMMIT-PR（仅 size ≥ M） | *-RETRO_CLOSE |
| `retro_md` | markdown | `retros/<task>.md`（11 段 / A 路线豁免） | *-RETRO_CLOSE | CLOSED |
| `archive_entry_ref` | text | `failure-archive.jsonl#L<n>` | *-RETRO_CLOSE（A 豁免） | CLOSED, auditor |

**invariant artifact**：`goal_anchor_hash` 一旦写入，被**所有下游阶段**隐式消费（read-only），任何 Edit/Write 改 CLAUDE.md 对应 block 都会触发 PostToolUse hook 重算 hash → diff != 0 → `DRIFT_CRITICAL`。

---

## § 2 Route A — 零 PRP 直改提交（4 stages）

### A-CLARIFY

```yaml
stage_id: A-CLARIFY
route: A
state: CLARIFY
phase_label: "@clarify"
skill_invoked: "SP:brainstorming"
inputs_required:
  - {from_stage: external, artifact_ref: user_input_raw, must_exist: true}
outputs_produced:
  - {artifact_ref: task_dimensions, format: json}
  - {artifact_ref: clarified_task_description, format: text}
  - {artifact_ref: goal_anchor_hash, format: sha256_hex, validation_primitive: fs.sha256_of_block}
gate_predicate: "task_dimensions.size == 'XS' AND task_dimensions.risk in ['低','中'] AND goal_anchor_hash != null"
on_input_missing: ABORT
on_output_missing: BLOCK
notes: "A 路线最多 1 轮澄清；如三维不匹配 XS/低-中 → 立即升级 B（flow-catalog § 8.1）。"
```

### A-IMPL

```yaml
stage_id: A-IMPL
route: A
state: IMPL
phase_label: "@impl"
skill_invoked: "native:Edit"
inputs_required:
  - {from_stage: A-CLARIFY, artifact_ref: clarified_task_description, must_exist: true}
  - {from_stage: A-CLARIFY, artifact_ref: task_dimensions, must_exist: true}
  - {from_stage: "*invariant*", artifact_ref: goal_anchor_hash, must_exist: true}
outputs_produced:
  - {artifact_ref: impl_diff, format: diff, path_pattern: "git diff HEAD"}
  - {artifact_ref: test_report, format: text, validation_primitive: test_tools.pytest_exit_code}
gate_predicate: "diff_lines_net(impl_diff) < 50 AND no_public_api_breaking_change(impl_diff) AND pytest_exit_code(test_report) == 0"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "A 路线 gate 超 50 行 → 回 A-CLARIFY 升级 B（flow-catalog § 8.1）"
```

### A-VERIFY

```yaml
stage_id: A-VERIFY
route: A
state: VERIFY
phase_label: "@verify"
skill_invoked: "harnessFlow:verifier"
inputs_required:
  - {from_stage: A-IMPL, artifact_ref: impl_diff, must_exist: true}
  - {from_stage: A-IMPL, artifact_ref: test_report, must_exist: true}
outputs_produced:
  - {artifact_ref: verifier_report, format: json, path_pattern: "verifier_reports/*.json", schema_ref: "task-board-template.md#2.1"}
gate_predicate: "verifier_report.verdict == 'PASS' AND len(verifier_report.red_lines_detected) == 0"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "A 路线 Verifier FAIL → X6 → PAUSED_ESCALATED（无 santa-loop），见 state-machine § 7 P2。"
```

### A-COMMIT

```yaml
stage_id: A-COMMIT
route: A
state: COMMIT
phase_label: "@commit"
skill_invoked: "ECC:prp-commit"
inputs_required:
  - {from_stage: A-VERIFY, artifact_ref: verifier_report, must_exist: true, validation: schema.schema_valid}
  - {from_stage: A-IMPL, artifact_ref: impl_diff, must_exist: true}
outputs_produced:
  - {artifact_ref: commit_sha, format: sha256_hex}
gate_predicate: "commit_sha != null AND precommit_hook_exit_code == 0"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "A 路线豁免 retro + failure-archive（delivery-checklist § 7.2），CLOSED 直接发生在 COMMIT 之后。"
```

---

## § 3 Route B — 轻 PRP 快速交付（8 stages）

### B-CLARIFY

```yaml
stage_id: B-CLARIFY
route: B
state: CLARIFY
phase_label: "@clarify"
skill_invoked: "SP:brainstorming"
inputs_required:
  - {from_stage: external, artifact_ref: user_input_raw, must_exist: true}
outputs_produced:
  - {artifact_ref: task_dimensions, format: json}
  - {artifact_ref: clarified_task_description, format: text}
  - {artifact_ref: goal_anchor_hash, format: sha256_hex, validation_primitive: fs.sha256_of_block}
gate_predicate: "task_dimensions.size in ['S','M'] AND goal_anchor_hash != null"
on_input_missing: ABORT
on_output_missing: BLOCK
notes: "B 澄清 ≤ 2 轮；若超轮或发现跨模块 → 升 C（flow-catalog § 3 切换条件）。"
```

### B-ROUTE_SELECT

```yaml
stage_id: B-ROUTE_SELECT
route: B
state: ROUTE_SELECT
phase_label: "@plan"
skill_invoked: "harnessFlow (internal routing-matrix lookup)"
inputs_required:
  - {from_stage: B-CLARIFY, artifact_ref: task_dimensions, must_exist: true}
outputs_produced:
  - {artifact_ref: route_id, format: text}
gate_predicate: "route_id == 'B'"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "用户 pick 或自动选（top-1 score ≥ 0.9）。见 harnessFlow-skill § 4."
```

### B-PLAN

```yaml
stage_id: B-PLAN
route: B
state: PLAN
phase_label: "@plan"
skill_invoked: "ECC:prp-plan"
inputs_required:
  - {from_stage: B-CLARIFY, artifact_ref: clarified_task_description, must_exist: true}
  - {from_stage: B-ROUTE_SELECT, artifact_ref: route_id, must_exist: true}
outputs_produced:
  - {artifact_ref: prp_plan_doc, format: markdown, path_pattern: "plans/*.plan.md", min_lines: 30}
  - {artifact_ref: dod_expression, format: text, validation_primitive: "python_ast.parse"}
gate_predicate: "file_exists(prp_plan_doc) AND wc_lines(prp_plan_doc) >= 30 AND dod_expression != null"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "dod_expression 锁定后禁改（harnessFlow-skill § 10.12）；B 路线 DoD 至少 3 条硬条件（pytest + code_review + diff_lines）。"
```

### B-CHECKPOINT_SAVE

```yaml
stage_id: B-CHECKPOINT_SAVE
route: B
state: CHECKPOINT_SAVE
phase_label: "@plan"
skill_invoked: "ECC:save-session"
inputs_required:
  - {from_stage: B-PLAN, artifact_ref: prp_plan_doc, must_exist: true}
  - {from_stage: B-PLAN, artifact_ref: dod_expression, must_exist: true}
outputs_produced:
  - {artifact_ref: session_checkpoint_ref, format: path, path_pattern: "sessions/*.json"}
gate_predicate: "file_exists(session_checkpoint_ref)"
on_input_missing: BLOCK
on_output_missing: WARN
notes: "B 路线 optional（单会话可省），XL/C 强制。"
optional: true
```

### B-IMPL

```yaml
stage_id: B-IMPL
route: B
state: IMPL
phase_label: "@impl"
skill_invoked: "ECC:prp-implement"
parallel_with: [B-IMPL-CODEREVIEW]
inputs_required:
  - {from_stage: B-PLAN, artifact_ref: prp_plan_doc, must_exist: true}
  - {from_stage: B-PLAN, artifact_ref: dod_expression, must_exist: true}
  - {from_stage: "*invariant*", artifact_ref: goal_anchor_hash, must_exist: true}
outputs_produced:
  - {artifact_ref: impl_diff, format: diff}
  - {artifact_ref: test_report, format: text, validation_primitive: test_tools.pytest_exit_code}
gate_predicate: "diff_lines_net(impl_diff) < 500 AND pytest_exit_code(test_report) == 0"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "diff > 500 行 → 升 C（flow-catalog § 8.1）。"
```

### B-IMPL-CODEREVIEW

```yaml
stage_id: B-IMPL-CODEREVIEW
route: B
state: IMPL
phase_label: "@impl"
skill_invoked: "ECC:code-reviewer"
parallel_with: [B-IMPL]
inputs_required:
  - {from_stage: B-IMPL, artifact_ref: impl_diff, must_exist: true}
outputs_produced:
  - {artifact_ref: code_review_report, format: json, schema_ref: "schemas/code-review.schema.json"}
gate_predicate: "code_review_report.verdict in ['PASS','PASS_WITH_COMMENT']"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "连续 3 次 FAIL → 升 C（flow-catalog § 3 切换条件）"
```

### B-VERIFY

```yaml
stage_id: B-VERIFY
route: B
state: VERIFY
phase_label: "@verify"
skill_invoked: "harnessFlow:verifier"
inputs_required:
  - {from_stage: B-PLAN, artifact_ref: dod_expression, must_exist: true}
  - {from_stage: B-IMPL, artifact_ref: impl_diff, must_exist: true}
  - {from_stage: B-IMPL, artifact_ref: test_report, must_exist: true}
  - {from_stage: B-IMPL-CODEREVIEW, artifact_ref: code_review_report, must_exist: true}
outputs_produced:
  - {artifact_ref: verifier_report, format: json, path_pattern: "verifier_reports/*.json"}
gate_predicate: "verifier_report.verdict == 'PASS' AND len(verifier_report.red_lines_detected) == 0"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "FAIL → santa-loop（see state-machine § 7 P2）"
```

### B-COMMIT

```yaml
stage_id: B-COMMIT
route: B
state: COMMIT
phase_label: "@commit"
skill_invoked: "ECC:prp-commit"
inputs_required:
  - {from_stage: B-VERIFY, artifact_ref: verifier_report, must_exist: true}
outputs_produced:
  - {artifact_ref: commit_sha, format: sha256_hex}
gate_predicate: "commit_sha != null"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

### B-RETRO_CLOSE

```yaml
stage_id: B-RETRO_CLOSE
route: B
state: RETRO_CLOSE
phase_label: "@retro"
skill_invoked: "harnessFlow:retro-generator + harnessFlow:failure-archive-writer"
inputs_required:
  - {from_stage: B-VERIFY, artifact_ref: verifier_report, must_exist: true}
  - {from_stage: B-COMMIT, artifact_ref: commit_sha, must_exist: true}
outputs_produced:
  - {artifact_ref: retro_md, format: markdown, path_pattern: "retros/*.md", min_lines: 50}
  - {artifact_ref: archive_entry_ref, format: text, validation_primitive: schema.schema_valid}
gate_predicate: "file_exists(retro_md) AND archive_entry_ref matches /failure-archive.jsonl#L\\d+/"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "B 路线 retro 可用轻量版（不强制 11 项全填），但仍必经（harnessFlow-skill § 8.6）"
```

---

## § 4 Route C — 全 PRP 重验证（15 stages）

### C-CLARIFY

```yaml
stage_id: C-CLARIFY
route: C
state: CLARIFY
phase_label: "@clarify"
skill_invoked: "SP:brainstorming"
inputs_required:
  - {from_stage: external, artifact_ref: user_input_raw, must_exist: true}
outputs_produced:
  - {artifact_ref: task_dimensions, format: json}
  - {artifact_ref: clarified_task_description, format: text}
  - {artifact_ref: goal_anchor_hash, format: sha256_hex, validation_primitive: fs.sha256_of_block}
gate_predicate: "task_dimensions.size in ['L','XL','XXL+'] AND goal_anchor_hash != null"
on_input_missing: ABORT
on_output_missing: BLOCK
notes: "C 最多 3 轮澄清（harnessFlow-skill § 3.2）。"
```

### C-CLARIFY-PRD

```yaml
stage_id: C-CLARIFY-PRD
route: C
state: CLARIFY
phase_label: "@clarify"
skill_invoked: "ECC:prp-prd"
inputs_required:
  - {from_stage: C-CLARIFY, artifact_ref: clarified_task_description, must_exist: true}
outputs_produced:
  - {artifact_ref: prp_prd_doc, format: markdown, path_pattern: "docs/prds/*.md", min_lines: 100}
gate_predicate: "file_exists(prp_prd_doc) AND wc_lines(prp_prd_doc) >= 100"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "C 路线独有；B/D/E/F 不产 prp_prd_doc。"
```

### C-PLAN

```yaml
stage_id: C-PLAN
route: C
state: PLAN
phase_label: "@plan"
skill_invoked: "ECC:prp-plan"
inputs_required:
  - {from_stage: C-CLARIFY-PRD, artifact_ref: prp_prd_doc, must_exist: true}
  - {from_stage: C-CLARIFY, artifact_ref: task_dimensions, must_exist: true}
outputs_produced:
  - {artifact_ref: prp_plan_doc, format: markdown, path_pattern: "plans/*.plan.md", min_lines: 80}
  - {artifact_ref: dod_expression, format: text, validation_primitive: "python_ast.parse"}
gate_predicate: "file_exists(prp_plan_doc) AND wc_lines(prp_plan_doc) >= 80 AND grep_count('DoD', prp_plan_doc) >= 3"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "视频出片任务 DoD 必含 method3 § 6.1 模板①或②的 artifact 级断言（mp4 exists / oss_head / playback）。"
```

### C-CHECKPOINT_SAVE

```yaml
stage_id: C-CHECKPOINT_SAVE
route: C
state: CHECKPOINT_SAVE
phase_label: "@plan"
skill_invoked: "ECC:save-session"
inputs_required:
  - {from_stage: C-PLAN, artifact_ref: prp_plan_doc, must_exist: true}
  - {from_stage: C-PLAN, artifact_ref: dod_expression, must_exist: true}
outputs_produced:
  - {artifact_ref: session_checkpoint_ref, format: path, path_pattern: "sessions/*.json"}
gate_predicate: "file_exists(session_checkpoint_ref)"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "C 路线强制 checkpoint；XL 每阶段再 checkpoint 一次（见 C-MID_CHECKPOINT）。"
```

### C-IMPL

```yaml
stage_id: C-IMPL
route: C
state: IMPL
phase_label: "@impl"
skill_invoked: "ECC:prp-implement"
parallel_with: [C-IMPL-CODEREVIEW]
inputs_required:
  - {from_stage: C-PLAN, artifact_ref: prp_plan_doc, must_exist: true}
  - {from_stage: C-PLAN, artifact_ref: dod_expression, must_exist: true}
  - {from_stage: C-CHECKPOINT_SAVE, artifact_ref: session_checkpoint_ref, must_exist: true}
  - {from_stage: "*invariant*", artifact_ref: goal_anchor_hash, must_exist: true}
outputs_produced:
  - {artifact_ref: impl_diff, format: diff}
  - {artifact_ref: test_report, format: text, validation_primitive: test_tools.pytest_exit_code}
gate_predicate: "impl_diff != '' AND pytest_exit_code(test_report) == 0"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

### C-IMPL-CODEREVIEW

```yaml
stage_id: C-IMPL-CODEREVIEW
route: C
state: IMPL
phase_label: "@impl"
skill_invoked: "ECC:code-reviewer"
parallel_with: [C-IMPL]
inputs_required:
  - {from_stage: C-IMPL, artifact_ref: impl_diff, must_exist: true}
outputs_produced:
  - {artifact_ref: code_review_report, format: json}
gate_predicate: "code_review_report.verdict in ['PASS','PASS_WITH_COMMENT']"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

### C-MID_CHECKPOINT

```yaml
stage_id: C-MID_CHECKPOINT
route: C
state: MID_CHECKPOINT
phase_label: "@impl"
skill_invoked: "ECC:save-session"
inputs_required:
  - {from_stage: C-IMPL, artifact_ref: impl_diff, must_exist: true}
outputs_produced:
  - {artifact_ref: session_checkpoint_ref, format: path, path_pattern: "sessions/*-mid-*.json"}
gate_predicate: "file_exists(session_checkpoint_ref)"
on_input_missing: WARN
on_output_missing: WARN
notes: "L 强制一次；XL 每阶段一次。"
```

### C-MID_RETRO

```yaml
stage_id: C-MID_RETRO
route: C
state: MID_RETRO
phase_label: "@impl"
skill_invoked: "ECC:retro"
optional: true
inputs_required:
  - {from_stage: C-IMPL, artifact_ref: impl_diff, must_exist: true}
  - {from_stage: C-MID_CHECKPOINT, artifact_ref: session_checkpoint_ref, must_exist: true}
outputs_produced:
  - {artifact_ref: retro_md, format: markdown, path_pattern: "retros/*-mid.md", min_lines: 30}
gate_predicate: "file_exists(retro_md)"
on_input_missing: WARN
on_output_missing: WARN
notes: "仅 XL 任务强制；L 可跳过。"
```

### C-VERIFY

```yaml
stage_id: C-VERIFY
route: C
state: VERIFY
phase_label: "@verify"
skill_invoked: "harnessFlow:verifier"
inputs_required:
  - {from_stage: C-PLAN, artifact_ref: dod_expression, must_exist: true}
  - {from_stage: C-IMPL, artifact_ref: impl_diff, must_exist: true}
  - {from_stage: C-IMPL, artifact_ref: test_report, must_exist: true}
  - {from_stage: C-IMPL-CODEREVIEW, artifact_ref: code_review_report, must_exist: true}
outputs_produced:
  - {artifact_ref: verifier_report, format: json, path_pattern: "verifier_reports/*.json"}
gate_predicate: "verifier_report.verdict == 'PASS' AND len(verifier_report.red_lines_detected) == 0 AND len(verifier_report.evidence_checks) >= 3"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "C 路线 Verifier 必须 3 段证据链（存在 + 行为 + 质量，见 delivery-checklist § 0）。"
```

### C-SANTA_LOOP

```yaml
stage_id: C-SANTA_LOOP
route: C
state: SANTA_LOOP
phase_label: "@verify"
skill_invoked: "ECC:santa-loop"
optional: true
inputs_required:
  - {from_stage: C-VERIFY, artifact_ref: verifier_report, must_exist: true, validation: "verdict==FAIL"}
outputs_produced:
  - {artifact_ref: santa_loop_trace, format: json}
  - {artifact_ref: impl_diff, format: diff}
gate_predicate: "santa_loop_trace.rounds <= 4 AND santa_loop_trace.converged == True"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "封顶 4 级 ladder（method3 § 5.3）；超 4 → E13 → PAUSED_ESCALATED。"
```

### C-COMMIT

```yaml
stage_id: C-COMMIT
route: C
state: COMMIT
phase_label: "@commit"
skill_invoked: "ECC:prp-commit"
inputs_required:
  - {from_stage: C-VERIFY, artifact_ref: verifier_report, must_exist: true, validation: "verdict==PASS"}
outputs_produced:
  - {artifact_ref: commit_sha, format: sha256_hex}
gate_predicate: "commit_sha != null AND precommit_hook_exit_code == 0"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

### C-COMMIT-PR

```yaml
stage_id: C-COMMIT-PR
route: C
state: COMMIT
phase_label: "@commit"
skill_invoked: "ECC:prp-pr"
inputs_required:
  - {from_stage: C-COMMIT, artifact_ref: commit_sha, must_exist: true}
outputs_produced:
  - {artifact_ref: pr_url, format: url}
gate_predicate: "pr_url matches /https:\\/\\/github\\.com\\/.+\\/pull\\/\\d+/"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "size ≥ M 强制；size = S 可省（harnessFlow-skill § 8.5）。"
```

### C-RETRO_CLOSE

```yaml
stage_id: C-RETRO_CLOSE
route: C
state: RETRO_CLOSE
phase_label: "@retro"
skill_invoked: "harnessFlow:retro-generator + harnessFlow:failure-archive-writer"
inputs_required:
  - {from_stage: C-VERIFY, artifact_ref: verifier_report, must_exist: true}
  - {from_stage: C-COMMIT, artifact_ref: commit_sha, must_exist: true}
  - {from_stage: C-COMMIT-PR, artifact_ref: pr_url, must_exist: false}
outputs_produced:
  - {artifact_ref: retro_md, format: markdown, path_pattern: "retros/*.md", min_lines: 100, validation_primitive: "grep_count('^## ', retro_md) >= 11"}
  - {artifact_ref: archive_entry_ref, format: text, validation_primitive: schema.schema_valid}
gate_predicate: "file_exists(retro_md) AND grep_count('^## ', retro_md) >= 11 AND archive_entry_ref != null"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "C 路线 retro 必须 11 段全填（method3 § 7.1）；缺段 → Stop gate 拒放行（delivery-checklist § 7.2）。"
```

---

## § 5 Route D — UI 视觉专线（9 stages）

### D-CLARIFY

```yaml
stage_id: D-CLARIFY
route: D
state: CLARIFY
phase_label: "@clarify"
skill_invoked: "SP:brainstorming"
inputs_required:
  - {from_stage: external, artifact_ref: user_input_raw, must_exist: true}
outputs_produced:
  - {artifact_ref: task_dimensions, format: json}
  - {artifact_ref: clarified_task_description, format: text}
  - {artifact_ref: goal_anchor_hash, format: sha256_hex}
gate_predicate: "task_dimensions.task_type == 'UI' AND goal_anchor_hash != null"
on_input_missing: ABORT
on_output_missing: BLOCK
notes: "D 路线 task_type 必须 UI；否则转 B/C。"
```

### D-ROUTE_SELECT

```yaml
stage_id: D-ROUTE_SELECT
route: D
state: ROUTE_SELECT
phase_label: "@plan"
skill_invoked: "harnessFlow (internal routing-matrix lookup)"
inputs_required:
  - {from_stage: D-CLARIFY, artifact_ref: task_dimensions, must_exist: true}
outputs_produced:
  - {artifact_ref: route_id, format: text}
gate_predicate: "route_id == 'D'"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

### D-PLAN

```yaml
stage_id: D-PLAN
route: D
state: PLAN
phase_label: "@plan"
skill_invoked: "ECC:gan-design"
inputs_required:
  - {from_stage: D-CLARIFY, artifact_ref: clarified_task_description, must_exist: true}
  - {from_stage: D-ROUTE_SELECT, artifact_ref: route_id, must_exist: true}
outputs_produced:
  - {artifact_ref: prp_plan_doc, format: markdown, path_pattern: "plans/*.plan.md", min_lines: 30}
  - {artifact_ref: dod_expression, format: text}
gate_predicate: "file_exists(prp_plan_doc) AND grep_count('screenshot', prp_plan_doc) >= 1"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "dod_expression 必须含 vite_started + screenshot_has_content（method3 § 6.1 模板③）。"
```

### D-IMPL

```yaml
stage_id: D-IMPL
route: D
state: IMPL
phase_label: "@impl"
skill_invoked: "native:Edit"
inputs_required:
  - {from_stage: D-PLAN, artifact_ref: prp_plan_doc, must_exist: true}
  - {from_stage: D-PLAN, artifact_ref: dod_expression, must_exist: true}
outputs_produced:
  - {artifact_ref: impl_diff, format: diff}
gate_predicate: "impl_diff != '' AND diff_paths_match(impl_diff, ['*.vue','*.ts','*.css','*.scss'])"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

### D-UI_SCREENSHOT

```yaml
stage_id: D-UI_SCREENSHOT
route: D
state: UI_SCREENSHOT
phase_label: "@verify"
skill_invoked: "gstack:browse + native:Bash playwright-screenshot"
inputs_required:
  - {from_stage: D-IMPL, artifact_ref: impl_diff, must_exist: true}
outputs_produced:
  - {artifact_ref: screenshot_artifacts, format: png, path_pattern: "artifacts/*.png", validation_primitive: "screenshot.screenshot_has_content"}
gate_predicate: "len(screenshot_artifacts) >= 1 AND all(screenshot_has_content(s) for s in screenshot_artifacts)"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "screenshot 前必须 playwright_wait_for 或 ≥ 3s 延迟避免异步渲染漏验（flow-catalog § 5 风险点）。"
```

### D-VERIFY

```yaml
stage_id: D-VERIFY
route: D
state: VERIFY
phase_label: "@verify"
skill_invoked: "harnessFlow:verifier"
inputs_required:
  - {from_stage: D-PLAN, artifact_ref: dod_expression, must_exist: true}
  - {from_stage: D-UI_SCREENSHOT, artifact_ref: screenshot_artifacts, must_exist: true}
  - {from_stage: D-IMPL, artifact_ref: impl_diff, must_exist: true}
outputs_produced:
  - {artifact_ref: verifier_report, format: json}
gate_predicate: "verifier_report.verdict == 'PASS' AND len(verifier_report.red_lines_detected) == 0"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

### D-COMMIT

```yaml
stage_id: D-COMMIT
route: D
state: COMMIT
phase_label: "@commit"
skill_invoked: "ECC:prp-commit"
inputs_required:
  - {from_stage: D-VERIFY, artifact_ref: verifier_report, must_exist: true}
outputs_produced:
  - {artifact_ref: commit_sha, format: sha256_hex}
gate_predicate: "commit_sha != null"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

### D-RETRO_CLOSE

```yaml
stage_id: D-RETRO_CLOSE
route: D
state: RETRO_CLOSE
phase_label: "@retro"
skill_invoked: "harnessFlow:retro-generator + harnessFlow:failure-archive-writer"
inputs_required:
  - {from_stage: D-VERIFY, artifact_ref: verifier_report, must_exist: true}
  - {from_stage: D-COMMIT, artifact_ref: commit_sha, must_exist: true}
outputs_produced:
  - {artifact_ref: retro_md, format: markdown, path_pattern: "retros/*.md", min_lines: 50}
  - {artifact_ref: archive_entry_ref, format: text}
gate_predicate: "file_exists(retro_md) AND archive_entry_ref != null"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

---

## § 6 Route E — agent graph 专线（11 stages）

### E-CLARIFY

```yaml
stage_id: E-CLARIFY
route: E
state: CLARIFY
phase_label: "@clarify"
skill_invoked: "SP:brainstorming"
inputs_required:
  - {from_stage: external, artifact_ref: user_input_raw, must_exist: true}
outputs_produced:
  - {artifact_ref: task_dimensions, format: json}
  - {artifact_ref: clarified_task_description, format: text}
  - {artifact_ref: goal_anchor_hash, format: sha256_hex}
gate_predicate: "task_dimensions.task_type == 'agent graph' AND goal_anchor_hash != null"
on_input_missing: ABORT
on_output_missing: BLOCK
notes: "E 澄清含 graph 目标 + 节点 schema 预期（flow-catalog § 6 调度序列步 1）。"
```

### E-ROUTE_SELECT

```yaml
stage_id: E-ROUTE_SELECT
route: E
state: ROUTE_SELECT
phase_label: "@plan"
skill_invoked: "harnessFlow (internal routing-matrix lookup)"
inputs_required:
  - {from_stage: E-CLARIFY, artifact_ref: task_dimensions, must_exist: true}
outputs_produced:
  - {artifact_ref: route_id, format: text}
gate_predicate: "route_id == 'E'"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

### E-PLAN-GRAPHDIFF

```yaml
stage_id: E-PLAN-GRAPHDIFF
route: E
state: PLAN
phase_label: "@plan"
skill_invoked: "native:Read + native:Write"
inputs_required:
  - {from_stage: E-CLARIFY, artifact_ref: clarified_task_description, must_exist: true}
outputs_produced:
  - {artifact_ref: graph_diff_md, format: markdown, path_pattern: "plans/*.graph_diff.md", min_lines: 40}
gate_predicate: "file_exists(graph_diff_md) AND grep_count('before', graph_diff_md) >= 1 AND grep_count('after', graph_diff_md) >= 1"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "E 路线独有；必须含 before/after graph ASCII + 节点 schema diff（flow-catalog § 6 调度序列步骤 3）。"
```

### E-PLAN

```yaml
stage_id: E-PLAN
route: E
state: PLAN
phase_label: "@plan"
skill_invoked: "ECC:prp-plan"
inputs_required:
  - {from_stage: E-PLAN-GRAPHDIFF, artifact_ref: graph_diff_md, must_exist: true}
  - {from_stage: E-CLARIFY, artifact_ref: clarified_task_description, must_exist: true}
outputs_produced:
  - {artifact_ref: prp_plan_doc, format: markdown, path_pattern: "plans/*.plan.md", min_lines: 40}
  - {artifact_ref: dod_expression, format: text}
gate_predicate: "file_exists(prp_plan_doc) AND wc_lines(prp_plan_doc) >= 40"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

### E-CHECKPOINT_SAVE

```yaml
stage_id: E-CHECKPOINT_SAVE
route: E
state: CHECKPOINT_SAVE
phase_label: "@plan"
skill_invoked: "ECC:save-session"
inputs_required:
  - {from_stage: E-PLAN, artifact_ref: prp_plan_doc, must_exist: true}
  - {from_stage: E-PLAN, artifact_ref: dod_expression, must_exist: true}
outputs_produced:
  - {artifact_ref: session_checkpoint_ref, format: path, path_pattern: "sessions/*.json"}
gate_predicate: "file_exists(session_checkpoint_ref)"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

### E-IMPL

```yaml
stage_id: E-IMPL
route: E
state: IMPL
phase_label: "@impl"
skill_invoked: "ECC:prp-implement + ECC:tdd-guide"
parallel_with: [E-IMPL-CODEREVIEW]
inputs_required:
  - {from_stage: E-PLAN, artifact_ref: prp_plan_doc, must_exist: true}
  - {from_stage: E-PLAN, artifact_ref: dod_expression, must_exist: true}
  - {from_stage: E-CHECKPOINT_SAVE, artifact_ref: session_checkpoint_ref, must_exist: true}
  - {from_stage: "*invariant*", artifact_ref: goal_anchor_hash, must_exist: true}
outputs_produced:
  - {artifact_ref: impl_diff, format: diff}
  - {artifact_ref: test_report, format: text, validation_primitive: test_tools.pytest_exit_code}
gate_predicate: "impl_diff != '' AND pytest_exit_code(test_report) == 0"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "E 路线节点级 TDD 强制（flow-catalog § 6）。"
```

### E-IMPL-CODEREVIEW

```yaml
stage_id: E-IMPL-CODEREVIEW
route: E
state: IMPL
phase_label: "@impl"
skill_invoked: "ECC:code-reviewer"
parallel_with: [E-IMPL]
inputs_required:
  - {from_stage: E-IMPL, artifact_ref: impl_diff, must_exist: true}
outputs_produced:
  - {artifact_ref: code_review_report, format: json}
gate_predicate: "code_review_report.verdict in ['PASS','PASS_WITH_COMMENT']"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

### E-EVAL

```yaml
stage_id: E-EVAL
route: E
state: VERIFY
phase_label: "@verify"
skill_invoked: "ECC:eval 或 ECC:gan-evaluator"
inputs_required:
  - {from_stage: E-IMPL, artifact_ref: impl_diff, must_exist: true}
  - {from_stage: E-PLAN-GRAPHDIFF, artifact_ref: graph_diff_md, must_exist: true}
outputs_produced:
  - {artifact_ref: test_report, format: json, validation_primitive: "eval.regression_delta"}
gate_predicate: "eval_regression_delta(test_report) < 0.05"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "E 路线独有；下游节点 schema 回归（flow-catalog § 6 风险点）。"
```

### E-VERIFY

```yaml
stage_id: E-VERIFY
route: E
state: VERIFY
phase_label: "@verify"
skill_invoked: "harnessFlow:verifier"
inputs_required:
  - {from_stage: E-PLAN, artifact_ref: dod_expression, must_exist: true}
  - {from_stage: E-IMPL, artifact_ref: impl_diff, must_exist: true}
  - {from_stage: E-IMPL, artifact_ref: test_report, must_exist: true}
  - {from_stage: E-IMPL-CODEREVIEW, artifact_ref: code_review_report, must_exist: true}
outputs_produced:
  - {artifact_ref: verifier_report, format: json, path_pattern: "verifier_reports/*.json"}
gate_predicate: "verifier_report.verdict == 'PASS' AND len(verifier_report.red_lines_detected) == 0"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

### E-COMMIT

```yaml
stage_id: E-COMMIT
route: E
state: COMMIT
phase_label: "@commit"
skill_invoked: "ECC:prp-commit"
inputs_required:
  - {from_stage: E-VERIFY, artifact_ref: verifier_report, must_exist: true}
outputs_produced:
  - {artifact_ref: commit_sha, format: sha256_hex}
gate_predicate: "commit_sha != null"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

### E-COMMIT-PR

```yaml
stage_id: E-COMMIT-PR
route: E
state: COMMIT
phase_label: "@commit"
skill_invoked: "ECC:prp-pr"
inputs_required:
  - {from_stage: E-COMMIT, artifact_ref: commit_sha, must_exist: true}
outputs_produced:
  - {artifact_ref: pr_url, format: url}
gate_predicate: "pr_url != null"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

### E-RETRO_CLOSE

```yaml
stage_id: E-RETRO_CLOSE
route: E
state: RETRO_CLOSE
phase_label: "@retro"
skill_invoked: "harnessFlow:retro-generator + harnessFlow:failure-archive-writer"
inputs_required:
  - {from_stage: E-VERIFY, artifact_ref: verifier_report, must_exist: true}
  - {from_stage: E-COMMIT, artifact_ref: commit_sha, must_exist: true}
outputs_produced:
  - {artifact_ref: retro_md, format: markdown, path_pattern: "retros/*.md", min_lines: 80}
  - {artifact_ref: archive_entry_ref, format: text}
gate_predicate: "file_exists(retro_md) AND archive_entry_ref != null"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

---

## § 7 Route F — 研究方案探索专线（6 stages）

### F-CLARIFY

```yaml
stage_id: F-CLARIFY
route: F
state: CLARIFY
phase_label: "@clarify"
skill_invoked: "SP:brainstorming"
inputs_required:
  - {from_stage: external, artifact_ref: user_input_raw, must_exist: true}
outputs_produced:
  - {artifact_ref: task_dimensions, format: json}
  - {artifact_ref: clarified_task_description, format: text}
  - {artifact_ref: goal_anchor_hash, format: sha256_hex}
gate_predicate: "task_dimensions.task_type == '研究' AND goal_anchor_hash != null"
on_input_missing: ABORT
on_output_missing: BLOCK
```

### F-ROUTE_SELECT

```yaml
stage_id: F-ROUTE_SELECT
route: F
state: ROUTE_SELECT
phase_label: "@plan"
skill_invoked: "harnessFlow (internal routing-matrix lookup)"
inputs_required:
  - {from_stage: F-CLARIFY, artifact_ref: task_dimensions, must_exist: true}
outputs_produced:
  - {artifact_ref: route_id, format: text}
gate_predicate: "route_id == 'F'"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

### F-RESEARCH

```yaml
stage_id: F-RESEARCH
route: F
state: RESEARCH
phase_label: "@plan"
skill_invoked: "native:Agent(Explore) + native:WebSearch + ECC:docs-lookup + gstack:investigate"
inputs_required:
  - {from_stage: F-CLARIFY, artifact_ref: clarified_task_description, must_exist: true}
outputs_produced:
  - {artifact_ref: research_findings_md, format: markdown, path_pattern: "research/*-findings.md", min_lines: 80}
gate_predicate: "file_exists(research_findings_md) AND wc_lines(research_findings_md) >= 80"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "F 不写代码；brainstorming 封顶 5 轮，超出转 B 做 POC（flow-catalog § 7 风险点）。"
```

### F-DECISION_LOG

```yaml
stage_id: F-DECISION_LOG
route: F
state: DECISION_LOG
phase_label: "@plan"
skill_invoked: "native:Write"
inputs_required:
  - {from_stage: F-RESEARCH, artifact_ref: research_findings_md, must_exist: true}
outputs_produced:
  - {artifact_ref: decision_log_md, format: markdown, path_pattern: "decisions/*-decision.md", min_lines: 200, validation_primitive: "grep_count('^## 选项', f) >= 2 AND grep_count('^## 决策', f) == 1"}
gate_predicate: "file_exists(decision_log_md) AND wc_lines(decision_log_md) >= 200 AND grep_count('^## 选项', decision_log_md) >= 2 AND grep_count('^## 决策', decision_log_md) == 1"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "决策 log 必须含 ≥ 2 选项 + 1 决策（flow-catalog § 7 DoD）。"
```

### F-VERIFY

```yaml
stage_id: F-VERIFY
route: F
state: VERIFY
phase_label: "@verify"
skill_invoked: "harnessFlow:verifier"
inputs_required:
  - {from_stage: F-DECISION_LOG, artifact_ref: decision_log_md, must_exist: true}
outputs_produced:
  - {artifact_ref: verifier_report, format: json}
gate_predicate: "verifier_report.verdict == 'PASS'"
on_input_missing: BLOCK
on_output_missing: BLOCK
notes: "F 路线不走 COMMIT；VERIFY PASS 后直接 RETRO_CLOSE。"
```

### F-RETRO_CLOSE

```yaml
stage_id: F-RETRO_CLOSE
route: F
state: RETRO_CLOSE
phase_label: "@retro"
skill_invoked: "harnessFlow:retro-generator + harnessFlow:failure-archive-writer"
inputs_required:
  - {from_stage: F-VERIFY, artifact_ref: verifier_report, must_exist: true}
  - {from_stage: F-DECISION_LOG, artifact_ref: decision_log_md, must_exist: true}
outputs_produced:
  - {artifact_ref: retro_md, format: markdown, path_pattern: "retros/*.md", min_lines: 50}
  - {artifact_ref: archive_entry_ref, format: text}
gate_predicate: "file_exists(retro_md) AND archive_entry_ref != null"
on_input_missing: BLOCK
on_output_missing: BLOCK
```

---

## § 8 Gate Predicate 语法 (EBNF mini)

`gate_predicate` 字符串是一个 Python-like 布尔表达式。支持：

```ebnf
expr       := term ( ( "AND" | "OR" ) term )*
term       := fn_call | literal_cmp | paren
fn_call    := ident "(" args ")" ( CMP literal )?   # verifier_primitive 调用
literal_cmp := ident CMP literal                     # 直接字段比较
paren      := "(" expr ")"
CMP        := "==" | "!=" | "<" | "<=" | ">" | ">=" | "in" | "matches"
```

**允许函数**（来自 `verifier_primitives/`）：`file_exists` / `wc_lines` / `grep_count` / `sha256_of_block` / `pytest_exit_code` / `diff_lines_net` / `diff_paths_match` / `screenshot_has_content` / `schema_valid` / `curl_status` / `oss_head` / `ffprobe_duration` / `playback_check` / `no_public_api_breaking_change` / `eval_regression_delta`。

**禁止**：任意 Python 表达式、import、lambda、eval、exec。Verifier subagent 用白名单 AST 解析（v1.2 真正实现；v1.1 暂为文档契约）。

---

## § 9 主 skill 集成（`validate_stage_io`）

主 skill 在每次状态转移前后调用（伪代码，见 `harnessFlow-skill.md § 5.5`）：

```python
def validate_stage_io(task_board: dict, stage_id: str, phase: str) -> tuple[str, list]:
    """
    phase: 'enter' or 'exit'
    returns: (verdict, violations[])
      verdict: 'OK' | 'BLOCK' | 'WARN'
      violations: list of {artifact_ref, expected_from, reason}
    """
    contract = load_stage_contract(stage_id)  # parse stage-contracts.md YAML block
    if phase == 'enter':
        for req in contract['inputs_required']:
            if req['must_exist'] and not artifact_available(task_board, req['artifact_ref'], req['from_stage']):
                return (contract['on_input_missing'], [{'artifact_ref': req['artifact_ref'],
                                                        'expected_from': req['from_stage'],
                                                        'reason': 'upstream producer has not written it'}])
    elif phase == 'exit':
        for out in contract['outputs_produced']:
            if not artifact_exists_on_disk_or_task_board(task_board, out):
                return (contract['on_output_missing'], [{'artifact_ref': out['artifact_ref'],
                                                         'reason': 'stage did not produce declared output'}])
        # eval gate_predicate (v1.2 will implement; v1.1 logs as documentation)
        gate_result = eval_gate_predicate(contract['gate_predicate'], task_board)
        if not gate_result:
            return ('BLOCK', [{'reason': f"gate_predicate failed: {contract['gate_predicate']}"}])
    return ('OK', [])
```

**BLOCK 返回 → Supervisor 发 `DOD_GAP_ALERT` → 主 skill 转 `PAUSED_ESCALATED`**（state-machine § 7 P3 等效路径）。

---

## § 10 task-board 新字段（v1.1 新增）

`task-board.stage_artifacts[]` append-only 轨迹字段：

```json
{
  "stage_artifacts": [
    {
      "stage_id": "C-IMPL",
      "produced_at": "2026-04-17T20:15:00Z",
      "artifacts": [
        {"artifact_ref": "impl_diff", "location": "git:HEAD vs origin/main", "size_bytes": 14823},
        {"artifact_ref": "test_report", "location": "artifacts/test-report.json", "schema_valid": true}
      ],
      "gate_eval": {"predicate": "impl_diff != '' AND pytest_exit_code == 0", "result": true, "evaluated_at": "2026-04-17T20:15:03Z"}
    }
  ]
}
```

完整 schema 定义已加入 `task-board-template.md § 1.2.x`。

---

## § 11 Coverage 自检

pytest `archive/tests/test_stage_contracts.py` 在每次 CI 运行：

1. **schema valid**：本文档所有 YAML block 通过 `schemas/stage-contract.schema.json` 校验
2. **coverage ≥ 80%**：A-F 6 路线每条至少包含 CLARIFY + (PLAN | RESEARCH) + IMPL/DECISION_LOG + VERIFY 四个必经 stage 的 contract
3. **artifact catalog 闭合**：任何 `inputs_required[].artifact_ref` 必须能在本文件某处作为 `outputs_produced[].artifact_ref` 出现（除 external / invariant）
4. **no circular dependency**：`from_stage` 引用不能形成环

---

## § 12 版本 / 变更记录

- **v1.1** (2026-04-17) — 首版 Stage Contract，覆盖 A-F 六路线共 ~50 stage
- **v1.2**（规划）— 主 skill 真实现 `validate_stage_io` + Supervisor 实时校验 + DOD_GAP_ALERT 自动触发 + Stop gate 兜底

---

*本文档是 harnessFlow v1.1 核心契约层；任何 flow-catalog.md 路线调度序列改动必须同步更新本文件；auditor 不自动改本文件（进化边界硬线）。*

*— v1.1 end —*
