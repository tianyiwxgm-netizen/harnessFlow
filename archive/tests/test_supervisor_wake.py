"""Tests for supervisor wake heuristics (archive/supervisor_wake/wake.py)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from archive.supervisor_wake import (
    DEDUP_WINDOW_SEC,
    SupervisorWakeState,
    TOOL_CALL_THRESHOLD,
    should_pulse,
)


@pytest.fixture
def workspace(tmp_path: Path):
    state_dir = tmp_path / "state"
    boards_dir = tmp_path / "boards"
    state_dir.mkdir()
    boards_dir.mkdir()
    return state_dir, boards_dir


def write_board(boards_dir: Path, task_id: str, state: str) -> None:
    (boards_dir / f"{task_id}.json").write_text(
        json.dumps({"task_id": task_id, "current_state": state})
    )


def test_initial_pulse_fires_on_first_invocation(workspace):
    state_dir, boards_dir = workspace
    write_board(boards_dir, "T1", "INIT")
    r = should_pulse("T1", {"tool_name": "Read"}, state_dir, boards_dir, now=1000.0)
    assert r["should_pulse"] is True
    assert r["code"] in {"INITIAL", "STATE_TRANSITION", "CLAUDE_MD_TOUCH"}


def test_dedup_window_blocks_second_pulse(workspace):
    state_dir, boards_dir = workspace
    write_board(boards_dir, "T2", "IMPL")
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "x/CLAUDE.md"}}
    r1 = should_pulse("T2", payload, state_dir, boards_dir, now=2000.0)
    assert r1["should_pulse"] is True
    r2 = should_pulse(
        "T2", payload, state_dir, boards_dir, now=2000.0 + DEDUP_WINDOW_SEC - 10
    )
    assert r2["should_pulse"] is False
    assert "dedup_window" in r2["reason"]


def test_dedup_clears_after_window(workspace):
    state_dir, boards_dir = workspace
    write_board(boards_dir, "T3", "IMPL")
    should_pulse("T3", {"tool_name": "Read"}, state_dir, boards_dir, now=3000.0)
    write_board(boards_dir, "T3", "VERIFY")
    r = should_pulse(
        "T3",
        {"tool_name": "Read"},
        state_dir,
        boards_dir,
        now=3000.0 + DEDUP_WINDOW_SEC + 10,
    )
    assert r["should_pulse"] is True


def test_claude_md_edit_triggers_pulse(workspace):
    state_dir, boards_dir = workspace
    write_board(boards_dir, "T4", "IMPL")
    sw = SupervisorWakeState(state_dir, "T4")
    sw.write(
        {
            "last_pulse_ts": 4000.0 - DEDUP_WINDOW_SEC - 1,
            "initial_pulse_done": True,
            "last_state_seen": "IMPL",
            "tool_call_count": 0,
        }
    )
    r = should_pulse(
        "T4",
        {"tool_name": "Write", "tool_input": {"file_path": "CLAUDE.md"}},
        state_dir,
        boards_dir,
        now=4000.0,
    )
    assert r["should_pulse"] is True
    assert r["code"] == "CLAUDE_MD_TOUCH"


def test_state_transition_detected(workspace):
    state_dir, boards_dir = workspace
    write_board(boards_dir, "T5", "IMPL")
    sw = SupervisorWakeState(state_dir, "T5")
    sw.write(
        {
            "last_pulse_ts": 5000.0 - DEDUP_WINDOW_SEC - 1,
            "initial_pulse_done": True,
            "last_state_seen": "CLARIFY",
            "tool_call_count": 0,
        }
    )
    r = should_pulse("T5", {"tool_name": "Read"}, state_dir, boards_dir, now=5000.0)
    assert r["should_pulse"] is True
    assert r["code"] == "STATE_TRANSITION"


def test_n_tool_calls_threshold(workspace):
    state_dir, boards_dir = workspace
    write_board(boards_dir, "T6", "IMPL")
    sw = SupervisorWakeState(state_dir, "T6")
    sw.write(
        {
            "last_pulse_ts": 6000.0 - DEDUP_WINDOW_SEC - 1,
            "initial_pulse_done": True,
            "last_state_seen": "IMPL",
            "tool_call_count": TOOL_CALL_THRESHOLD - 1,
        }
    )
    r = should_pulse("T6", {"tool_name": "Read"}, state_dir, boards_dir, now=6000.0)
    assert r["should_pulse"] is True
    assert r["code"] == "TOOL_CALL_N"


def test_no_trigger_when_quiet(workspace):
    state_dir, boards_dir = workspace
    write_board(boards_dir, "T7", "IMPL")
    sw = SupervisorWakeState(state_dir, "T7")
    sw.write(
        {
            "last_pulse_ts": 7000.0 - DEDUP_WINDOW_SEC - 1,
            "initial_pulse_done": True,
            "last_state_seen": "IMPL",
            "tool_call_count": 1,
        }
    )
    r = should_pulse("T7", {"tool_name": "Read"}, state_dir, boards_dir, now=7000.0)
    assert r["should_pulse"] is False
    assert r["code"] is None


def test_pulse_resets_tool_call_count(workspace):
    state_dir, boards_dir = workspace
    write_board(boards_dir, "T8", "IMPL")
    sw = SupervisorWakeState(state_dir, "T8")
    sw.write(
        {
            "last_pulse_ts": 8000.0 - DEDUP_WINDOW_SEC - 1,
            "initial_pulse_done": True,
            "last_state_seen": "IMPL",
            "tool_call_count": TOOL_CALL_THRESHOLD - 1,
        }
    )
    r = should_pulse("T8", {"tool_name": "Read"}, state_dir, boards_dir, now=8000.0)
    assert r["should_pulse"] is True
    assert sw.read()["tool_call_count"] == 0


def test_state_persists_across_calls(workspace):
    state_dir, boards_dir = workspace
    write_board(boards_dir, "T9", "IMPL")
    should_pulse("T9", {"tool_name": "Read"}, state_dir, boards_dir, now=9000.0)
    should_pulse("T9", {"tool_name": "Read"}, state_dir, boards_dir, now=9001.0)
    s = SupervisorWakeState(state_dir, "T9").read()
    assert "last_pulse_ts" in s
    assert s.get("initial_pulse_done") is True


def test_state_dir_auto_created(tmp_path: Path):
    state_dir = tmp_path / "deep" / "nested" / "state"
    boards_dir = tmp_path / "boards"
    boards_dir.mkdir()
    write_board(boards_dir, "T10", "INIT")
    should_pulse("T10", {"tool_name": "Read"}, state_dir, boards_dir, now=10000.0)
    assert state_dir.exists()
    assert (state_dir / "T10.json").exists()


def test_invalid_payload_no_crash(workspace):
    state_dir, boards_dir = workspace
    write_board(boards_dir, "T11", "INIT")
    r = should_pulse("T11", None, state_dir, boards_dir, now=11000.0)
    assert "should_pulse" in r


def test_corrupt_state_file_recovers(workspace):
    state_dir, boards_dir = workspace
    write_board(boards_dir, "T12", "INIT")
    (state_dir / "T12.json").write_text("not json {{{")
    r = should_pulse("T12", {"tool_name": "Read"}, state_dir, boards_dir, now=12000.0)
    assert r["should_pulse"] is True


def test_missing_task_board_no_state_transition(workspace):
    state_dir, boards_dir = workspace
    sw = SupervisorWakeState(state_dir, "T13")
    sw.write(
        {
            "last_pulse_ts": 13000.0 - DEDUP_WINDOW_SEC - 1,
            "initial_pulse_done": True,
            "tool_call_count": 0,
        }
    )
    r = should_pulse("T13", {"tool_name": "Read"}, state_dir, boards_dir, now=13000.0)
    assert r["should_pulse"] is False
