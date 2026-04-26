#!/usr/bin/env bash
# harnessFlow Supervisor wake hook.
#
# Fires a supervisor pulse instruction (via hookSpecificOutput.additionalContext)
# when archive/supervisor_wake/wake.py decides it's time. Heuristics: edits to
# CLAUDE.md, task-board state transitions, every 20 tool calls, and an initial
# pulse — all subject to a 5-minute dedup window.
#
# Failure mode: NEVER block the user. Any error -> exit 0 silently.

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "/Users/zhongtianyi/work/code/harnessFlow")"

PAYLOAD="$(cat 2>/dev/null || true)"
if [ -z "${PAYLOAD:-}" ]; then exit 0; fi

# Pick the most recent active (not CLOSED/ABORTED) task-board.
TASK_ID=""
if [ -d "$REPO_ROOT/task-boards" ]; then
    TASK_ID=$(
        cd "$REPO_ROOT" && python3 - <<'PY' 2>/dev/null
import json, os, sys
from pathlib import Path
boards = sorted(
    Path("task-boards").glob("*.json"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)
for b in boards:
    try:
        d = json.loads(b.read_text())
    except Exception:
        continue
    state = d.get("current_state", "")
    if state and state not in ("CLOSED", "ABORTED"):
        print(b.stem)
        sys.exit(0)
PY
    )
fi

if [ -z "${TASK_ID:-}" ]; then exit 0; fi

RESULT="$(
    printf '%s' "$PAYLOAD" \
        | (cd "$REPO_ROOT" && python3 -c "
import signal, runpy, sys
signal.signal(signal.SIGALRM, lambda *a: sys.exit(0))
signal.alarm(5)
sys.argv = ['cli', '--task-id', '$TASK_ID']
runpy.run_module('archive.supervisor_wake.cli', run_name='__main__')
") 2>/dev/null
)"
if [ -z "${RESULT:-}" ]; then exit 0; fi

SHOULD=$(printf '%s' "$RESULT" | python3 -c 'import sys,json
try: d=json.load(sys.stdin)
except: d={}
print(d.get("should_pulse", False))' 2>/dev/null)
if [ "$SHOULD" != "True" ]; then exit 0; fi

# Emit additionalContext for the main skill to act on.
TASK_ID="$TASK_ID" RESULT="$RESULT" python3 - <<'PY' 2>/dev/null
import json, os, sys
task_id = os.environ["TASK_ID"]
try:
    d = json.loads(os.environ["RESULT"])
except Exception:
    d = {}
code = d.get("code", "")
reason = d.get("reason", "")
ctx = (
    f"[harnessFlow:supervisor-wake] PULSE TRIGGER ({code}): {reason} | "
    f"task_id={task_id}. "
    "Action: spawn Agent(subagent_type='harnessFlow:supervisor', "
    f"prompt='task_id={task_id}, mode=pulse, read task-boards/{task_id}.json + "
    f"skills-invoked/{task_id}.jsonl tail, run § 3 detections, append "
    f"INFO/WARN/BLOCK to supervisor-events/{task_id}.jsonl, exit on completion'). "
    "Honor 3 red-line monitoring (DRIFT_CRITICAL / DOD_GAP_ALERT / IRREVERSIBLE_HALT)."
)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": ctx,
    }
}))
PY
exit 0
