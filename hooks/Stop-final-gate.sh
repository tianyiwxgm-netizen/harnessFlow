#!/usr/bin/env bash
#
# harnessFlow Stop hook — final gate.
#
# Triggered when Claude Code is about to stop. Enforces
# delivery-checklist.md § 7.2 门卫清单:
#   1. Active task-board must be in a terminal state
#      (CLOSED / ABORTED / PAUSED_ESCALATED).
#   2. For CLOSED:
#        - red_lines[] == []
#        - verifier_report is not null
#        - verifier_report.red_lines_detected == []
#        - artifacts[] non-empty (F route carves out: decision_log artifact)
#        - final_outcome ∈ {success, failed, aborted, false_complete_reported}
#        - retro_link present for non-A routes
#        - Phase 7 additions:
#            * retros/<task_id>.md must contain all 11 section titles
#              (## 1. through ## 11.) matching schemas/retro-template.md
#            * archive_entry_link must be present (non-A route)
#            * the pointed jsonl line validates against
#              schemas/failure-archive.schema.json (when jsonschema+python avail)
#
# Exit codes:
#   0  clean stop
#   2  gate failed — Claude Code surfaces this to the user

set -u

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOARDS_DIR="$HARNESS_DIR/task-boards"
RETROS_DIR="$HARNESS_DIR/retros"
ARCHIVE_PATH="$HARNESS_DIR/failure-archive.jsonl"
SCHEMA_PATH="$HARNESS_DIR/schemas/failure-archive.schema.json"

if [ ! -d "$BOARDS_DIR" ]; then
  exit 0
fi

fail_count=0
msg_file=$(mktemp)
trap 'rm -f "$msg_file"' EXIT

for tb in "$BOARDS_DIR"/*.json; do
  [ -f "$tb" ] || continue

  python3 - "$tb" "$RETROS_DIR" "$msg_file" "$ARCHIVE_PATH" "$SCHEMA_PATH" <<'PY'
import json, os, re, sys
from datetime import datetime, timezone, timedelta
tb_path, retros_dir, msg_path, archive_path, schema_path = sys.argv[1:6]
task_id = os.path.splitext(os.path.basename(tb_path))[0]

def emit(m):
    with open(msg_path, "a", encoding="utf-8") as f:
        f.write(m + "\n")

try:
    tb = json.load(open(tb_path, encoding="utf-8"))
except Exception as exc:
    emit(f"task {task_id}: task-board JSON invalid ({exc})")
    sys.exit(1)

state = tb.get("current_state", "UNKNOWN")
route = tb.get("route", "-")
if route == "-":
    route = tb.get("route_id", "-")

# v1.1 P9-P2 修 #3: 跨 session 过滤
# 历史 CLOSED/ABORTED task-board（closed_at 早于本 session 或 1 小时前）不重复校验
# 避免老 Phase 8 p8-* 或跨项目遗留 board 每次 Stop 都误阻
closed_at_str = tb.get("closed_at")
if state in ("CLOSED", "ABORTED") and closed_at_str:
    try:
        ca = datetime.fromisoformat(closed_at_str.rstrip("Z")).replace(tzinfo=timezone.utc)
        env_start = os.environ.get("HARNESSFLOW_SESSION_START")
        if env_start:
            cutoff = datetime.fromisoformat(env_start.rstrip("Z")).replace(tzinfo=timezone.utc)
        else:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        if ca < cutoff:
            sys.exit(0)  # 历史终态，不重扫
    except (ValueError, TypeError):
        pass  # 解析失败走默认 full check（保守）

if state == "PAUSED_ESCALATED":
    # 人工 review 中，不强制 archive（恢复后会重新进 RETRO_CLOSE 补写）
    sys.exit(0)
if state == "ABORTED":
    # Phase 7 补强：ABORTED 也要归档一条（subagent md § 1.1 规定）。放行条件：
    #   - A 路线：豁免
    #   - 非 A 路线：archive_entry_link 必填；不强制 retro 11 段（ABORTED 可能没跑完 retro）
    if route != "A":
        archive_entry_link = tb.get("archive_entry_link")
        if not archive_entry_link:
            emit(f"task {task_id} [{route}/ABORTED]: archive_entry_link missing (Phase 7 non-A route requires final_outcome=aborted entry)")
            sys.exit(1)
    sys.exit(0)
if state != "CLOSED":
    emit(f"task {task_id}: not terminal (state={state}) — please CLOSED/ABORTED/PAUSED before stop")
    sys.exit(1)

# state == CLOSED: run the full § 7.2 checklist
errors = []

red_lines = tb.get("red_lines", []) or []
if red_lines:
    errors.append(f"red_lines non-empty: {red_lines}")

vr = tb.get("verifier_report")
if vr in (None, {}, ""):
    errors.append("verifier_report is null/empty")
else:
    rld = (vr or {}).get("red_lines_detected") or []
    if rld:
        errors.append(f"verifier_report.red_lines_detected non-empty: {rld}")

artifacts = tb.get("artifacts", []) or []
if not artifacts and route != "F":
    errors.append("artifacts[] empty (non-F route must have hard artifacts)")

final_outcome = tb.get("final_outcome")
if final_outcome not in ("success", "failed", "aborted", "false_complete_reported"):
    errors.append(
        f"final_outcome must be one of success/failed/aborted/false_complete_reported (got {final_outcome!r})"
    )

if route != "A":
    retro_link_field = tb.get("retro_link")
    retro_path = os.path.join(retros_dir, f"{task_id}.md")
    retro_present = os.path.isfile(retro_path) or (retro_link_field and os.path.isfile(retro_link_field))
    if not retro_present:
        errors.append(f"retro missing (retros/{task_id}.md absent and retro_link empty; non-A route)")
    else:
        # Phase 7: retros/<task_id>.md must contain all 11 section titles
        md = retro_link_field if (retro_link_field and os.path.isfile(retro_link_field)) else retro_path
        try:
            content = open(md, encoding="utf-8").read()
        except Exception as exc:
            errors.append(f"retro unreadable ({exc})")
        else:
            found = len(re.findall(r"^## \d+\. ", content, flags=re.MULTILINE))
            if found < 11:
                errors.append(
                    f"retro {md!r} has only {found}/11 section titles (Phase 7 requires all 11)"
                )

    archive_entry_link = tb.get("archive_entry_link")
    if not archive_entry_link:
        errors.append("archive_entry_link missing (Phase 7: non-A route must write failure-archive.jsonl)")
    elif os.path.isfile(archive_path) and os.path.isfile(schema_path):
        # Try schema-validate the referenced jsonl line(s) if jsonschema is available
        try:
            import jsonschema  # noqa: F401
            schema = json.load(open(schema_path, encoding="utf-8"))
            validator = jsonschema.Draft7Validator(schema)
            line_no = None
            m = re.search(r"#L(\d+)", archive_entry_link)
            if m:
                line_no = int(m.group(1))
            lines = open(archive_path, encoding="utf-8").read().splitlines()
            if line_no and 1 <= line_no <= len(lines):
                try:
                    entry = json.loads(lines[line_no - 1])
                except json.JSONDecodeError as exc:
                    errors.append(f"archive_entry_link L{line_no}: invalid JSON ({exc})")
                else:
                    errs = sorted(validator.iter_errors(entry), key=lambda e: e.path)
                    if errs:
                        errors.append(
                            f"archive_entry_link L{line_no}: schema fail: {errs[0].message}"
                        )
        except ImportError:
            pass  # jsonschema not installed — skip; tested in pytest instead

if errors:
    for e in errors:
        emit(f"task {task_id} [{route}/{state}]: {e}")
    sys.exit(1)

sys.exit(0)
PY

  rc=$?
  if [ "$rc" -ne 0 ]; then
    fail_count=$((fail_count + rc))
  fi
done

if [ "$fail_count" -gt 0 ]; then
  printf '[harnessFlow Stop gate] FAIL:\n' >&2
  while IFS= read -r line; do
    printf '  - %s\n' "$line" >&2
  done < "$msg_file"
  exit 2
fi

exit 0
