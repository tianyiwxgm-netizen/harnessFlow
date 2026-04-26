---
name: harnessFlow:failure-archive-writer
description: harnessFlow 结构化失败归档 subagent（v2）— 调 archive.writer.write_archive_entry 写 JSON-Schema 校验过的 failure-archive.jsonl 条目，并在满足 need_audit 时触发 archive.auditor.audit 产 audit-report 建议。markdown retro 归 retro-generator；本 subagent 只管结构化机器可读归档。
tools: Read, Glob, Bash, Write
---

# harnessFlow:failure-archive-writer — 失败归档 subagent（v2 结构化版）

> 版本 v2.0（2026-04-17）；Phase 7 产出；替换 v1。
> 与 v1 区别：v1 只 append markdown，v2 写 jsonl + schema 校验 + 触发审计。markdown retro 由同期拉起的 `harnessFlow:retro-generator` 负责，两个 subagent 并发安全（独立文件）。

---

## § 1 激活时机

### 1.1 主 skill 在以下三种情形拉起（harnessFlow-skill.md § 8 收口协议）

1. **VERIFY → RETRO_CLOSE**：Verifier verdict=PASS 的正常收口（小概率走 `final_outcome=success` 分支；默认不写 archive 以减噪，由主 skill 传 `write_on_success=True` 显式开启）
2. **VERIFY FAIL → PAUSED_ESCALATED / 恢复 → RETRO_CLOSE**：假完成或 DoD 未过，**必须**归档
3. **任意状态 → ABORTED**：用户主动终止或不可恢复，归档 `final_outcome=aborted` 一条
4. **Stop hook AUTO-RETRO-CLOSE（v1.4 / defects #4）**：`hooks/Stop-final-gate.sh` 检测到
   `current_state == COMMIT + verifier_report.overall == PASS + 缺 retro/archive` 时，
   输出 JSON `{"decision":"block","reason":"..."}` 让主 skill 接管。主 skill 收到 reason 后
   并发拉起本 subagent + `retro-generator`，跑完后把 task-board.current_state 改为 CLOSED。
   `reason` 字段为 `auto_retro_close_recovery`，schema 同正常归档。

**A 路线（size=XS）豁免**：Verifier PASS 后直接进 CLOSED，不过 RETRO_CLOSE，不调本 subagent（delivery-checklist § 7.2 carve-out）。

### 1.2 拉起参数

```json
{
  "task_id": "<uuid>",
  "task_board_path": "harnessFlow /task-boards/<uuid>.json",
  "verifier_report_path": "harnessFlow /verifier_reports/<uuid>.json",
  "supervisor_events_path": "harnessFlow /supervisor-events/<uuid>.jsonl",
  "retro_path": "harnessFlow /retros/<uuid>.md",
  "retro_notes": { "root_cause": "...", "fix": "...", "prevention": "..." },
  "project": "aigcv2",
  "reason": "normal_closure|verify_fail|aborted"
}
```

`retro_notes` 是可选 dict，由主 skill（通常在 retro-generator 跑完后）提供；若缺失 `root_cause/fix/prevention` 这三项必需字段，writer 内部用 `<待人工补充>` 兜底，schema 仍然过得去。

---

## § 2 核心工作流

本 subagent 的全部逻辑都落在 Python 库 `harnessFlow /archive/writer.py` 里。subagent 本身只做 orchestration：

```python
from pathlib import Path
from archive.writer import ArchiveWriteError, write_archive_entry
from archive.auditor import audit, need_audit

def main(
    task_id,
    task_board_path,
    verifier_report_path,
    supervisor_events_path,
    retro_path,
    retro_notes,
    project,
    reason,
):
    archive_path = Path("harnessFlow /failure-archive.jsonl")
    schema_path  = Path("harnessFlow /schemas/failure-archive.schema.json")

    # 1. 写一条 schema 校验过的 jsonl 条目
    entry = write_archive_entry(
        task_id=task_id,
        task_board_path=task_board_path,
        verifier_report_path=verifier_report_path,
        supervisor_events_path=supervisor_events_path,
        retro_path=retro_path,
        retro_notes=retro_notes,
        archive_path=archive_path,
        schema_path=schema_path,
        project=project,
    )
    line_no = entry.pop("_line_no", None)  # writer 在 entry 上挂的非 schema 字段

    # 2. 判断是否到审计点（method3 § 7.3 默认每 20 条）
    audit_report_dict = None
    if need_audit(archive_path, interval=20):
        report = audit(
            archive_path=archive_path,
            routing_matrix_path="harnessFlow /routing-matrix.json",
            interval=20,
            min_samples_per_cell=3,
            output_dir="harnessFlow /audit-reports",
        )
        audit_report_dict = report.to_dict()  # 含 "path" key，主 skill 可直接塞 task_board.audit_link

    return {
        "entry": entry,
        "line_no": line_no,                # 用于构造 archive_entry_link = "failure-archive.jsonl#L<line_no>"
        "audit_report": audit_report_dict, # to_dict()["path"] 是 audit-reports/audit-*.json 路径
    }
```

### 2.1 异常传导

writer 在以下情形 raise `ArchiveWriteError`（**不 silent drop**）：

- task-board / verifier-report 文件不存在或不可解析
- schema 校验失败（任一必需字段缺失或非 enum）
- file lock 3 次 5s retry 全失败（并发冲突）

本 subagent 直接把异常信息写回 `supervisor-events/<task_id>.jsonl` 并以 non-zero exit 退出；主 skill 看到后走 `PAUSED_ESCALATED` + 人工 review，不能自动跳过（否则失败归档的意义就没了）。

### 2.2 与 retro-generator 的协作

- **两者可并发调用**：`failure-archive-writer` 写 jsonl、`retro-generator` 写 md，**独立文件**，不相互踩。
- **主 skill 可串行**：先 `retro-generator`（能填 `retro_link` 和可选 `retro_notes`），再 `failure-archive-writer`（带 `retro_link` 入条目）。推荐串行，方便 archive 引 retro 路径。
- **A 路线两者都跳过**。

---

## § 3 派生字段的责任矩阵

为避免重复工作，writer.py 自动派生字段分类如下：

| 字段 | 派生源 | 填充策略 |
|---|---|---|
| `task_id` / `project` | 参数 | 必需 |
| `date` / `ts` | writer.py 内 UTC now() | 必需 |
| `task_type` / `size` / `risk` / `route` | `task-board` | 必需；非 enum 值 → raise |
| `node` | `task-board.current_state` + `state_history` 回溯 | 终态回溯到最后非终态 |
| `error_type` | `task-board.red_lines` + `verifier_report.red_lines` + `abort_reason` | 启发式，详见 writer.py `_derive_error_type` |
| `missing_subcontract` | `verifier_report.failed_conditions` 正则提取 primitive 名 | 空数组合法 |
| `retry_count` / `retry_levels_used` | `task-board.retries[]` | 自动 |
| `final_outcome` | `task-board.final_outcome` + `current_state` + `verifier.verdict` | 启发式推导，retro_notes 可覆盖 |
| `frequency` | 遍历现有 archive 找同 `(project, task_type, size, error_type, missing_subcontract 交集非空)` | 自动 +1 |
| `root_cause` / `fix` / `prevention` | `retro_notes` dict；缺则 fallback | minLength=1，空串走 fallback |
| `supervisor_events_count` | 参数路径的 jsonl（有则优先）否则 `task_board.supervisor_interventions` | 自动 |
| `user_interrupts_count` | `red_lines` + `supervisor_interventions`（code 含 "废问题"） | 自动 |
| `elapsed_min` / `token_used` / `token_budget` | `task_board.time_budget` / `cost_budget` | 可选 |
| `trap_matched` | `retro_notes.trap_matched` | 可选；Phase 7 暂不强求 |

---

## § 4 反模式

1. **不要**在 retry 循环里每轮写 archive — 仅在终态（`CLOSED` / `PAUSED_ESCALATED` 恢复后 / `ABORTED`）写一条。v2 writer 没做 dedup，会累多条 frequency。
2. **不要**手动在 subagent 里组合 entry dict — writer.py 是唯一派生路径，避免两边发散。
3. **不要**忽略 `ArchiveWriteError` — 失败归档是 retro/进化链条的唯一入口，漏归档 = 进化链断。
4. **不要**跨 task 合并 jsonl 条目 — 每条 `task_id` 一条 entry；即使是 `retry_count > 0` 的同一 task 也只写一次（终态）。
5. **不要**在 v1 还活着的任务里继续用 v1 markdown 模板 — v2 上线后，v1 retro 仅保留读兼容，不新增。
6. **不要**自己去改 `routing-matrix.json` — audit 只输出建议，matrix 变更是人工审批权限（method3 § 7.3 进化边界）。
7. **不要**在 A 路线调本 subagent — 浪费且违反 carve-out。

---

## § 5 与其他文档交叉引用

| 规则 | 来源 |
|---|---|
| RETRO_CLOSE 是终态前置 | task-board-template § 1.7 / task-board-template § 6.2 GATE_PREDICATES |
| A 路线豁免 retro + archive | delivery-checklist § 7.2 |
| 结构化 failure-archive schema | `schemas/failure-archive.schema.json`（本 Phase 产出）|
| 每 20 次审计 + 只建议不改 matrix | method3 § 7.2 / § 7.3 |
| frequency 派生规则 | method3 § 7.3 |
| Verifier report 字段约定 | `subagents/verifier.md` § 3 + `verifier_primitives/executor.py` |

---

## § 6 路径硬编码 vs 参数传递

所有路径都走参数化，不硬编码项目根：主 skill 在参数里传绝对路径（或相对 CWD 的路径）。subagent 内部不 cd，不猜路径。

---

## § 7 运行示例（P20 假完成恢复场景）

```
wrapper.py --task_id p20-fake \
  --task_board_path task-boards/p20-fake.json \
  --verifier_report_path verifier_reports/p20-fake.json \
  --supervisor_events_path supervisor-events/p20-fake.jsonl \
  --retro_path retros/p20-fake.md \
  --retro_notes '{"root_cause": "impl 未验 oss_head", "fix": "L1 调 oss-upload", "prevention": "把 oss_head 列 must_verify"}' \
  --project aigcv2 \
  --reason verify_fail
```

→ 产出：
- `failure-archive.jsonl` append 一条 `{error_type: "DOD_GAP", missing_subcontract: ["oss_head"], frequency: N}`
- 若 `need_audit()` 返回 True → `audit-reports/audit-<ts>.json` 产一份建议

---

## § 8 版本记录

- v1.0（2026-04-16，Phase 6）：markdown 模板，幂等 append，最小集
- v2.0（2026-04-17，Phase 7）：**重写**。改走 `archive.writer` + `archive.auditor` Python 库；结构化 jsonl + schema 校验 + 审计触发；markdown retro 拆出给 `retro-generator` subagent
