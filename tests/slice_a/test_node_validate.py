"""Tests for validate_node_io enter/exit + gate_predicate enforcement."""
from __future__ import annotations

import pytest

from pipelines.contract_loader import validate_node_io


def test_validate_enter_missing_required_input_blocks(empty_task_board):
    # N3 requires goal_anchor.hash and initial_user_input
    empty_task_board.pop("goal_anchor", None)
    empty_task_board.pop("initial_user_input", None)
    verdict, violations = validate_node_io(empty_task_board, "N3", phase="enter")
    assert verdict == "BLOCK"
    assert any("initial_user_input" in v.get("field", "") for v in violations) or \
           any("goal_anchor" in v.get("field", "") for v in violations)


def test_validate_enter_with_inputs_returns_ok(empty_task_board):
    empty_task_board["initial_user_input"] = "做个坦克游戏"
    verdict, _ = validate_node_io(empty_task_board, "N3", phase="enter")
    assert verdict == "OK"


def test_validate_exit_gate_predicate_fail_blocks(empty_task_board):
    """N3 exit gate fails when delivery_goal.locked_goal is empty."""
    empty_task_board["initial_user_input"] = "x"
    empty_task_board["_derived"] = {"delivery_goal": {"locked_goal": ""}}
    verdict, violations = validate_node_io(empty_task_board, "N3", phase="exit")
    assert verdict == "BLOCK"
    assert any("gate_predicate" in v.get("reason", "") for v in violations)


def test_validate_exit_gate_predicate_pass_returns_ok(empty_task_board):
    empty_task_board["_derived"] = {
        "delivery_goal": {"locked_goal": "做个坦克大战网页小游戏"}
    }
    verdict, _ = validate_node_io(empty_task_board, "N3", phase="exit")
    assert verdict == "OK"
