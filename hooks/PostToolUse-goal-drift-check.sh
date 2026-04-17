#!/usr/bin/env bash
#
# harnessFlow PostToolUse hook — goal-drift detection.
#
# Wired to Edit|Write; self-filters by reading the tool input from stdin so
# only tool calls touching CLAUDE.md run the full check. All other tool
# calls return 0 immediately with O(1) work.
#
# Enable by adding to ~/.claude/settings.json:
#
#   "hooks": {
#     "PostToolUse": [
#       {
#         "matcher": "Edit|Write",
#         "command": "bash '/Users/zhongtianyi/work/code/harnessFlow /hooks/PostToolUse-goal-drift-check.sh'"
#       }
#     ]
#   }
#
# Exit codes:
#   0  no drift (or unrelated tool call)
#   2  drift detected → Claude Code surfaces a BLOCK event to the main skill
#
# Claude Code passes a JSON payload on stdin:
#   { "tool_input": { "file_path": "/abs/path/..." }, ... }
# We only proceed if file_path endswith CLAUDE.md.

set -u

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOARDS_DIR="$HARNESS_DIR/task-boards"
EVENTS_DIR="$HARNESS_DIR/supervisor-events"

mkdir -p "$EVENTS_DIR"

# ---- 1. self-filter by tool input ----
STDIN_PAYLOAD="$(cat 2>/dev/null || true)"
TARGET_FILE="$(printf '%s' "$STDIN_PAYLOAD" | python3 -c '
import json, sys
try:
    data = json.loads(sys.stdin.read() or "{}")
except Exception:
    data = {}
fp = (data.get("tool_input") or {}).get("file_path") or ""
print(fp)
' 2>/dev/null)"

if [ -z "$TARGET_FILE" ]; then
  # No target from stdin → keep legacy behavior of checking CLAUDE.md in CWD
  TARGET_FILE="${CLAUDE_PROJECT_DIR:-$(pwd)}/CLAUDE.md"
fi

case "$TARGET_FILE" in
  *CLAUDE.md) ;;    # proceed
  *) exit 0 ;;      # unrelated tool call
esac

CLAUDE_MD="$TARGET_FILE"

# ---- 2. find the single active task-board ----
if [ ! -d "$BOARDS_DIR" ]; then
  exit 0
fi

ACTIVE_COUNT=0
TB=""
for tb in "$BOARDS_DIR"/*.json; do
  [ -f "$tb" ] || continue
  state=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('current_state',''))" "$tb" 2>/dev/null)
  if [ -n "$state" ] && [ "$state" != "CLOSED" ] && [ "$state" != "ABORTED" ]; then
    ACTIVE_COUNT=$((ACTIVE_COUNT + 1))
    TB="$tb"
  fi
done

if [ "$ACTIVE_COUNT" -eq 0 ]; then
  exit 0
fi

if [ "$ACTIVE_COUNT" -gt 1 ]; then
  echo "goal-drift-check: multiple active task-boards; skipping (v1 limitation)" >&2
  exit 0
fi
TASK_ID=$(basename "$TB" .json)

EXPECTED_HASH=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('goal_anchor',{}).get('hash',''))" "$TB" 2>/dev/null)
if [ -z "$EXPECTED_HASH" ]; then
  exit 0
fi

emit_event() {
  # args: level code red_line suggested_action evidence_json
  python3 - "$EVENTS_DIR/$TASK_ID.jsonl" "$TASK_ID" "$1" "$2" "$3" "$4" "$5" <<'PY'
import json, sys, datetime
events_path, task_id, level, code, red_line, action, evidence_json = sys.argv[1:8]
try:
    evidence = json.loads(evidence_json)
except Exception:
    evidence = {"raw": evidence_json}
evt = {
  "ts": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
  "task_id": task_id,
  "level": level,
  "code": code,
  "state": "<runtime>",
  "evidence": evidence,
  "suggested_action": action,
  "red_line": red_line or None,
}
with open(events_path, "a", encoding="utf-8") as f:
    f.write(json.dumps(evt, ensure_ascii=False)+"\n")
PY
}

if [ ! -f "$CLAUDE_MD" ]; then
  emit_event "BLOCK" "claude_md_missing" "DRIFT_CRITICAL" \
    "主 skill 转 PAUSED_ESCALATED + 问用户是否恢复 CLAUDE.md" \
    "{\"claude_md_path\":\"$CLAUDE_MD\"}"
  exit 2
fi

# ---- 3. extract goal-anchor block + hash ----
BLOCK=$(python3 - "$CLAUDE_MD" "$TASK_ID" <<'PY'
import re, sys
path, tid = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8", errors="replace").read()
pat = re.compile(rf"<!--\s*goal-anchor-{re.escape(tid)}\s*-->(.*?)<!--\s*/goal-anchor-{re.escape(tid)}\s*-->", re.DOTALL)
m = pat.search(text)
print(m.group(1).strip() if m else "")
PY
)

if [ -z "$BLOCK" ]; then
  emit_event "BLOCK" "goal_anchor_missing" "DRIFT_CRITICAL" \
    "主 skill 转 PAUSED_ESCALATED + 问用户是否修复 goal-anchor block" \
    "{\"claude_md_path\":\"$CLAUDE_MD\"}"
  exit 2
fi

# ---- 4. hash + compare (cross-platform) ----
if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL_HASH=$(printf "%s" "$BLOCK" | sha256sum | awk '{print $1}')
elif command -v shasum >/dev/null 2>&1; then
  ACTUAL_HASH=$(printf "%s" "$BLOCK" | shasum -a 256 | awk '{print $1}')
else
  echo "goal-drift-check: no sha256 tool on PATH (sha256sum/shasum)" >&2
  exit 0
fi

if [ "$ACTUAL_HASH" != "$EXPECTED_HASH" ]; then
  emit_event "BLOCK" "drift_detected" "DRIFT_CRITICAL" \
    "主 skill 转 PAUSED_ESCALATED + 问用户是否修复 goal" \
    "{\"expected\":\"$EXPECTED_HASH\",\"actual\":\"$ACTUAL_HASH\"}"
  exit 2
fi

exit 0
