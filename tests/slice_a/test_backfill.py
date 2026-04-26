"""Tests for scripts/backfill_pipeline_graph.py — historical task replay."""
from __future__ import annotations

from scripts.backfill_pipeline_graph import backfill_one


def test_backfill_closed_marks_all_nodes_passed(closed_task_board):
    out = backfill_one(closed_task_board)
    pg = out["_derived"]["pipeline"]
    assert pg is not None
    assert all(n["status"] == "passed" for n in pg["nodes"])


def test_backfill_aborted_marks_last_node_failed():
    tb = {
        "task_id": "x", "size": "M", "task_type": "后端 feature", "risk": "中",
        "current_state": "ABORTED",
        "state_history": [
            {"state": "INIT", "timestamp": "t0"},
            {"state": "IMPL", "timestamp": "t1"},
            {"state": "ABORTED", "timestamp": "t2"},
        ],
        "stage_artifacts": [],
        "_derived": {},
    }
    out = backfill_one(tb)
    pg = out["_derived"]["pipeline"]
    # IMPL was the last real state before ABORTED → step 11 (state_to_step["IMPL"]) is the failed node.
    assert any(n["step"] == 11 and n["status"] == "failed" for n in pg["nodes"])


def test_backfill_size_xs_skips():
    tb = {
        "task_id": "y", "size": "XS", "task_type": "纯代码", "risk": "低",
        "current_state": "CLOSED",
        "state_history": [], "stage_artifacts": [],
    }
    out = backfill_one(tb)
    assert out["_derived"].get("pipeline") is None
