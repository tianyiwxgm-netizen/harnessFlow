"""Supervisor wake heuristics for harnessFlow PostToolUse hook chain.

Decide when to fire a supervisor sidecar pulse, with 5-minute deduplication
to avoid rapid-fire pulses. State is persisted per task_id at
archive/supervisor_wake/state/<task_id>.json.

Triggers (priority order):
  CLAUDE_MD_TOUCH    Edit/Write to a CLAUDE.md
  STATE_TRANSITION   task-board.current_state diverged from last seen
  TOOL_CALL_N        ≥ TOOL_CALL_THRESHOLD tool calls since last pulse
  INITIAL            first invocation for this task

Failure mode: never raise from should_pulse(); return should_pulse=False on
unknown errors so the hook never blocks the user's tool stream.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

DEDUP_WINDOW_SEC = 300  # 5 minutes
TOOL_CALL_THRESHOLD = 20  # pulse every N tool calls when nothing else fires
PULSE_CODES = ("CLAUDE_MD_TOUCH", "STATE_TRANSITION", "TOOL_CALL_N", "INITIAL")


def _load_state(state_file: Path) -> dict[str, Any]:
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state_file: Path, state: dict[str, Any]) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_file.with_suffix(state_file.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(tmp, state_file)


def _read_task_board_state(task_board_path: Path) -> str | None:
    if not task_board_path.exists():
        return None
    try:
        tb = json.loads(task_board_path.read_text(encoding="utf-8"))
        return tb.get("current_state")
    except (json.JSONDecodeError, OSError):
        return None


def should_pulse(
    task_id: str,
    payload: dict[str, Any] | None,
    state_dir: Path,
    task_boards_dir: Path,
    now: float | None = None,
) -> dict[str, Any]:
    """Decide whether to fire a supervisor pulse.

    Returns:
        dict with keys:
          should_pulse: bool
          reason: str
          code: str | None  (one of PULSE_CODES if should_pulse is True)
    """
    if now is None:
        now = time.time()

    state_file = state_dir / f"{task_id}.json"
    state = _load_state(state_file)

    last_pulse_ts = state.get("last_pulse_ts", 0)
    in_dedup = (now - last_pulse_ts) < DEDUP_WINDOW_SEC

    payload = payload or {}
    tool_name = payload.get("tool_name", "") if isinstance(payload, dict) else ""
    tool_input = payload.get("tool_input", {}) if isinstance(payload, dict) else {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    file_path = tool_input.get("file_path", "")

    triggers: list[tuple[str, str]] = []

    if tool_name in ("Edit", "Write") and isinstance(file_path, str) and file_path.endswith("CLAUDE.md"):
        triggers.append(("CLAUDE_MD_TOUCH", f"CLAUDE.md edited via {tool_name}"))

    tb_path = task_boards_dir / f"{task_id}.json"
    current_state = _read_task_board_state(tb_path)
    last_state_seen = state.get("last_state_seen")
    if current_state and current_state != last_state_seen:
        triggers.append((
            "STATE_TRANSITION",
            f"task-board state {last_state_seen!r} -> {current_state!r}",
        ))
        state["last_state_seen"] = current_state

    state["tool_call_count"] = state.get("tool_call_count", 0) + 1
    if state["tool_call_count"] >= TOOL_CALL_THRESHOLD:
        triggers.append((
            "TOOL_CALL_N",
            f"reached {TOOL_CALL_THRESHOLD} tool calls since last pulse",
        ))

    if not state.get("initial_pulse_done"):
        triggers.append(("INITIAL", "first pulse for this task"))

    if not triggers:
        _save_state(state_file, state)
        return {"should_pulse": False, "reason": "no_trigger", "code": None}

    if in_dedup:
        _save_state(state_file, state)
        codes = ", ".join(c for c, _ in triggers)
        return {
            "should_pulse": False,
            "reason": (
                f"dedup_window ({int(now - last_pulse_ts)}s < {DEDUP_WINDOW_SEC}s); "
                f"would have triggered: {codes}"
            ),
            "code": None,
        }

    code, reason = triggers[0]
    state["last_pulse_ts"] = now
    state["tool_call_count"] = 0
    state["initial_pulse_done"] = True
    _save_state(state_file, state)

    return {"should_pulse": True, "reason": reason, "code": code}


class SupervisorWakeState:
    """Helper around the per-task wake state file."""

    def __init__(self, state_dir: Path, task_id: str):
        self.path = state_dir / f"{task_id}.json"

    def read(self) -> dict[str, Any]:
        return _load_state(self.path)

    def write(self, state: dict[str, Any]) -> None:
        _save_state(self.path, state)

    def reset(self) -> None:
        if self.path.exists():
            self.path.unlink()
