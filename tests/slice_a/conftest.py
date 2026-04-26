"""Shared pytest fixtures for Slice A pipeline_graph tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_BOARDS_DIR = REPO_ROOT / "task-boards"


@pytest.fixture
def empty_task_board() -> dict:
    """A minimum-fields task-board for testing emit logic."""
    return {
        "task_id": "test-task-001",
        "created_at": "2026-04-26T10:00:00Z",
        "size": "M",
        "task_type": "后端 feature",
        "risk": "中",
        "current_state": "ROUTE_SELECT",
        "route_id": "C",
        "goal_anchor": {
            "text": "test goal",
            "hash": "deadbeef",
            "claude_md_path": "CLAUDE.md#goal-anchor-test-task-001",
        },
        "stage_artifacts": [],
        "state_history": [],
        "_derived": {},
    }


@pytest.fixture
def closed_task_board() -> dict:
    """A real CLOSED task-board (tank-battle) for backfill / e2e tests."""
    p = TASK_BOARDS_DIR / "p-tank-battle-20260426T082459Z.json"
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def xs_task_board(empty_task_board) -> dict:
    """size=XS task-board (Route A — should skip pipeline_graph emit)."""
    empty_task_board["size"] = "XS"
    empty_task_board["route_id"] = "A"
    empty_task_board["task_type"] = "纯代码"
    empty_task_board["risk"] = "低"
    return empty_task_board
