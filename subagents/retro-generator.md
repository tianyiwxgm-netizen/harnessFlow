---
name: harnessFlow:retro-generator
description: harnessFlow 11 项 retro 自动生成 subagent — 在 RETRO_CLOSE 拉起，调 archive.retro_renderer.render_retro 按模板渲染 11 项 markdown 到 retros/<task_id>.md，数据源为 task-board + verifier_report + supervisor_events + 可选 retro_notes.json。不判 verdict、不改 archive entry、不覆盖已有 retro block。
tools: Read, Glob, Bash, Write
---

# harnessFlow:retro-generator — 11 项 retro 生成 subagent（Phase 7 新增）

> 版本 v1.0（2026-04-17）；Phase 7 产出。
> 与 `failure-archive-writer` v2 并列：本 subagent 负责**人可读 markdown retro**，前者负责**机器可读 jsonl archive**。两者独立文件，并发安全。

---

## § 1 激活时机

### 1.1 主 skill 在以下情形拉起本 subagent

1. `VERIFY PASS → RETRO_CLOSE`：正常收口，写一份 retro 记录实际路径 / DoD diff / 纠偏次数等
2. `VERIFY FAIL → PAUSED_ESCALATED`：红线触发或 DoD 未过，保留现场供用户和下次迭代参考
3. `任意状态 → ABORTED`：用户主动终止或不可恢复，也写 retro（标记 `final_outcome=aborted`）
4. `PAUSED_ESCALATED 恢复后 → RETRO_CLOSE`：恢复路径也要一份 retro 收口
5. **`Stop hook AUTO-RETRO-CLOSE 自动触发`（v1.4 / defects #4）**：当用户准备退出 Claude Code，
   `hooks/Stop-final-gate.sh` 检测到 task `current_state == COMMIT` 且 `verifier_report.overall == PASS`
   但缺 retro 或 archive 时，会输出 JSON `{"decision":"block","reason":"AUTO-RETRO-CLOSE: ..."}`
   阻止 Stop。主 skill 下一轮收到 reason 后**必须**为命中的每个 task 并发拉起本 subagent
   + `failure-archive-writer`，跑完后把 task-board.current_state 改为 CLOSED + 写 closed_at +
   final_outcome，再让用户重新触发 Stop。这条路径的目的是兜底"用户敲 ESC / 关 Claude Code 时
   半成品 task 没收口"导致下次启动被 Stop hook 阻塞的孤儿任务问题。

### 1.2 A 路线豁免

`route == "A"` 且 `size == "XS"` 时，主 skill 不调本 subagent（delivery-checklist § 7.2 carve-out 与 Phase 6 保持一致）。

### 1.3 拉起参数

```json
{
  "task_id": "<uuid>",
  "task_board_path": "harnessFlow /task-boards/<uuid>.json",
  "verifier_report_path": "harnessFlow /verifier_reports/<uuid>.json",
  "supervisor_events_path": "harnessFlow /supervisor-events/<uuid>.jsonl",
  "routing_events_path":    "harnessFlow /routing-events/<uuid>.jsonl",
  "retro_notes_path":       "harnessFlow /retros/<uuid>.notes.json",
  "audit_report_link":      "audit-reports/audit-20260417T000000Z.json",
  "out_dir":                "harnessFlow /retros"
}
```

`retro_notes_path` 指向**用户可选补充的 notes 文件**（8-11 项 `new_traps / new_combinations / evolution_suggestions / next_recommendation`）。若不存在，renderer 把对应字段填 `<待人工补充>`，不 crash。

---

## § 2 核心工作流

```python
from archive.retro_renderer import render_retro

def main(
    task_id,
    task_board_path,
    verifier_report_path,
    supervisor_events_path,
    routing_events_path,
    retro_notes_path,
    audit_report_link,
    out_dir="harnessFlow /retros",
):
    path = render_retro(
        task_id=task_id,
        task_board_path=task_board_path,
        verifier_report_path=verifier_report_path,
        supervisor_events_path=supervisor_events_path,
        routing_events_path=routing_events_path,
        retro_notes_path=retro_notes_path,
        audit_report_link=audit_report_link,
        template_path="harnessFlow /schemas/retro-template.md",
        out_dir=out_dir,
    )
    return {"retro_link": path, "sections": 11}
```

### 2.1 幂等 append 语义

- **同 `task_id` 多次调用** → 每次写一个新的 `<!-- retro-<id>-<ts> -->` block，**不覆盖**已有 block
- `ts` 精度到秒，两次调用间隔 ≥ 1s 保证不同 block（主 skill 默认行为；若 < 1s 连续调，两 block 共用同 ts，本 subagent 仍 append，用户自行辨识）
- 已存在文件 → 以 `\n\n---\n\n` 分隔符 append，保持 markdown 可读
- `render_retro` 内部不做"同 ts 去重"，因为去重语义落在主 skill 的 `invoke once per terminal transition` 上

### 2.2 与 failure-archive-writer v2 的协作

推荐串行：**先 retro-generator，再 failure-archive-writer**。理由：

1. retro-generator 产生 `retro_link` (path)，可作为 archive entry 的 `retro_link` 可选字段
2. retro 文件里可能引 `audit-report` 路径（§ 10 进化建议段），由 archive audit 产生的 audit-report 可先挂到 retro；但审计触发在 archive 写完才判——这里有循环依赖

破局：

- 若 `need_audit` 触发：主 skill 流程为 `retro-generator(skip audit_report_link)` → `failure-archive-writer(run audit)` → 把 `audit-report` 路径塞进 task-board.audit_link → **可选**再 `retro-generator` 补一份含 `audit_report_link` 的 block（覆盖需用户显式触发）
- 若不需 audit：常规串行 retro → archive

并发调用也安全：两 subagent 写不同文件（`retros/<id>.md` vs `failure-archive.jsonl`）。

---

## § 3 数据源责任矩阵（与 Phase 7 plan § 2 AC 对齐）

| retro 项 | 数据源 | 渲染 helper |
|---|---|---|
| 1. DoD 实际 diff | `verifier_report.evidence_chain` + `task_board.dod_expression` | `derive_1_dod_diff` |
| 2. 路线偏差 | `task_board.route` + `task_board.initial_route_recommendation` + `routing_events.jsonl` | `derive_2_route_drift` |
| 3. 纠偏次数 | `task_board.retries[]` group by level | `derive_3_retry_breakdown` |
| 4. Verifier FAIL 次数 | `verifier_report.failed_conditions` 正则 + red_lines | `derive_4_verifier_fail` |
| 5. 用户打断次数 | `task_board.red_lines` + `supervisor_interventions` | `derive_5_user_interrupts` |
| 6. 耗时 vs 估算 | `task_board.time_budget.{cap_sec,elapsed_sec}` | `derive_6_time` |
| 7. 成本 vs 估算 | `task_board.cost_budget.{token_used,token_cap,cost_usd}` | `derive_7_cost` |
| 8. 新发现的 trap | `retro_notes.new_traps` | `derive_8_traps` |
| 9. 新发现的有效组合 | `retro_notes.new_combinations` | `derive_9_combos` |
| 10. 进化建议 | `retro_notes.evolution_suggestions` + `audit_report_link` | `derive_10_evolution` |
| 11. 下次推荐 | `retro_notes.next_*` | `derive_11_next` |

项 8-11 依赖**用户或 LLM 事后填写**的 `retro_notes.json`；未填则 `<待人工补充>`。这是进化链条的 handoff 点，不强制也不 silent-skip。

---

## § 4 用户 retro_notes 写回协议

主 skill 在 `PAUSED_ESCALATED`（尤其是 FAIL + 非 trivial）时**可选**让用户手填 notes：

```json
{
  "new_traps": ["P20-oss-silent-skip: impl 报 success 时实际没 oss 上传"],
  "new_combinations": ["seedance + oss-upload + ffprobe_duration 连环校验"],
  "evolution_suggestions": ["降 C 路线 (XL, 视频出片) 权重 *= 0.8", "加 must_verify 子契约"],
  "next_recommendation": "下次相同场景先把 oss_head 作为硬验证条件",
  "next_route_hint": "B",
  "next_must_verify": "oss_head, ffprobe_duration, playback_check",
  "next_traps_to_avoid": "P20-oss-silent-skip"
}
```

写回位置：`retros/<task_id>.notes.json`。主 skill 把路径通过 `retro_notes_path` 参数传入本 subagent，renderer 自动拼进 8-11 项。

**可选**意义：小任务跳过 notes 不影响归档；大任务（XL / 视频出片）强烈推荐填，方便进化审计。

---

## § 5 反模式

1. **不要**自己判 verdict — PASS/FAIL/INSUFFICIENT 由 `harnessFlow:verifier` 决定，retro 只引用不改
2. **不要**改 archive entry — 归档写入归 `failure-archive-writer` v2，本 subagent 只管 md
3. **不要**覆盖已有 retro block — 幂等 append 是硬要求，`render_retro` 默认 append，不 truncate
4. **不要**硬编码 11 项 section 字符串在本 subagent — 模板在 `schemas/retro-template.md`，改模板不改 subagent
5. **不要**在 A 路线调本 subagent — 浪费且违反 carve-out
6. **不要**依赖 `retro_notes.json` 必填 — 缺失时必须能产出完整 11 段（用 `<待人工补充>` 占位）
7. **不要**调 LLM 补 8-11 项自由文本 — Phase 7 不引入额外 LLM 调用；Phase 9+ 再上 LLM 辅助填写

---

## § 6 与其他文档交叉引用

| 规则 | 来源 |
|---|---|
| 11 项 retro 清单 | method3 § 7.1 |
| 三类记忆分级写回 | method3 § 7.2 |
| 数据源矩阵 | `archive/retro_renderer.py` 的 docstring + Phase 7 plan § 2 |
| RETRO_CLOSE 状态 | state-machine § 1.1 / task-board-template § 1.7 |
| retro 边界注释约定（`<!-- retro-id-ts -->`） | Phase 6 v1 习惯保留，Phase 7 renderer 继承 |
| A 路线豁免 | delivery-checklist § 7.2 |

---

## § 7 运行示例

```
wrapper.py --task_id p20-fake \
  --task_board_path task-boards/p20-fake.json \
  --verifier_report_path verifier_reports/p20-fake.json \
  --retro_notes_path retros/p20-fake.notes.json \
  --out_dir retros/
```

→ 产出 `retros/p20-fake.md`，含 11 段 section，`<!-- retro-p20-fake-2026-04-17T03:42:00Z -->` 边界。若再次调用 → 同文件 append 第二个 block。

---

## § 8 版本记录

- v1.0（2026-04-17，Phase 7）：首版。架构：subagent orchestration + Python `archive.retro_renderer` 完成实际渲染。拆分 11 项 helper 方便单测（`archive/tests/test_retro_renderer.py` 覆盖 11 助手 + 幂等 + 空 notes fallback）
