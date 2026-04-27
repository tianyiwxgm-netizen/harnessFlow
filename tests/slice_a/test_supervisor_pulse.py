"""Tests for per-node supervisor pulse helper (Q3=A)."""
from __future__ import annotations

from pipelines.contract_loader import record_supervisor_pulse


def test_record_pulse_appends_intervention(empty_task_board):
    record_supervisor_pulse(empty_task_board, "node_passed_N3", node_id="N3")
    assert "supervisor_interventions" in empty_task_board
    assert len(empty_task_board["supervisor_interventions"]) == 1
    iv = empty_task_board["supervisor_interventions"][0]
    assert iv["code"] == "node_passed_N3"
    assert iv["severity"] == "INFO"
    assert iv["context"]["node_id"] == "N3"


def test_record_pulse_dedup_within_5min(empty_task_board):
    record_supervisor_pulse(empty_task_board, "node_passed_N3", node_id="N3")
    record_supervisor_pulse(empty_task_board, "node_passed_N3", node_id="N3")
    # 5min dedup → second call merges (count incremented), not duplicated
    assert len(empty_task_board["supervisor_interventions"]) == 1
    assert empty_task_board["supervisor_interventions"][0].get("count", 1) == 2


def test_record_pulse_different_codes_not_deduped(empty_task_board):
    record_supervisor_pulse(empty_task_board, "node_passed_N3", node_id="N3")
    record_supervisor_pulse(empty_task_board, "node_passed_N4", node_id="N4")
    assert len(empty_task_board["supervisor_interventions"]) == 2
