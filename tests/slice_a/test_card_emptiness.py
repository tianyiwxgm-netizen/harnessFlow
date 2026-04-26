"""Tests for pipelines.card_emptiness — 6 dashboard cards emptiness check."""
from __future__ import annotations

from pipelines.card_emptiness import is_card_empty, derive_card_states, CARD_NODE_MAP


def test_card_node_map_has_six_entries():
    assert set(CARD_NODE_MAP.keys()) == {
        "delivery_goal", "scope", "project_library",
        "tdd", "supervision", "wbs",
    }


def test_delivery_goal_empty_when_locked_goal_missing(empty_task_board):
    assert is_card_empty("delivery_goal", empty_task_board) is True


def test_delivery_goal_filled(empty_task_board):
    empty_task_board["_derived"] = {"delivery_goal": {"locked_goal": "X"}}
    assert is_card_empty("delivery_goal", empty_task_board) is False


def test_project_library_empty_when_under_3_total(empty_task_board):
    empty_task_board["_derived"] = {"project_library": {"docs": [{"x": 1}], "repos": []}}
    assert is_card_empty("project_library", empty_task_board) is True


def test_project_library_filled_when_total_ge_3(empty_task_board):
    empty_task_board["_derived"] = {
        "project_library": {"docs": [{}, {}], "repos": [{}], "process_docs": []}
    }
    assert is_card_empty("project_library", empty_task_board) is False


def test_wbs_empty_when_array_empty(empty_task_board):
    empty_task_board["_derived"] = {"wbs": []}
    assert is_card_empty("wbs", empty_task_board) is True


def test_supervision_empty_when_no_interventions(empty_task_board):
    empty_task_board["supervisor_interventions"] = []
    empty_task_board["red_lines"] = []
    assert is_card_empty("supervision", empty_task_board) is True


def test_derive_card_states_returns_six_entries(empty_task_board):
    states = derive_card_states(empty_task_board)
    assert len(states) == 6
    assert all("card_id" in s and "is_empty" in s and "waiting_for_node" in s for s in states)
