"""Unit tests for scripts/backfill_node_id_in_stage_artifacts.py.

5 测试覆盖：13-node 推导 / append-when-empty / skip-already-tagged / idempotent / N11-commit_sha。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from backfill_node_id_in_stage_artifacts import (  # noqa: E402
    apply_backfill,
    derive_per_node_artifacts,
    is_already_backfilled,
)


MIN_TB: dict = {
    "task_id": "test-min-20260427T0000Z",
    "current_state": "CLOSED",
    "size": "S",
    "task_type": "重构",
    "risk": "低",
    "route_id": "B",
    "goal_anchor": {
        "text": "demo goal lorem ipsum",
        "hash": "deadbeef0123",
        "claude_md_path": "/path/to/CLAUDE.md#goal-anchor-test-min",
    },
    "dod_expression": "exists('foo.py') AND pytest_pass",
    "state_history": [
        {"state": "INIT", "timestamp": "2026-04-27T05:00:00Z"},
        {"state": "CLARIFY", "timestamp": "2026-04-27T05:01:00Z"},
        {"state": "PLAN", "timestamp": "2026-04-27T05:02:00Z"},
        {"state": "IMPL", "timestamp": "2026-04-27T05:03:00Z"},
        {"state": "VERIFY", "timestamp": "2026-04-27T05:04:00Z"},
        {"state": "COMMIT", "timestamp": "2026-04-27T05:05:00Z"},
        {"state": "CLOSED", "timestamp": "2026-04-27T05:06:00Z"},
    ],
    "stage_artifacts": [],
    "verifier_report": {"overall": "PASS", "evidence_checks": []},
    "supervisor_interventions": [{"level": "INFO", "code": "X", "message": "ok"}],
    "commit_sha": "abc1234",
    "retro_link": "retros/test-min-20260427T0000Z.md",
    "final_outcome": "success",
    "artifacts": [{"path": "foo.py", "kind": "code"}],
}


def test_derive_per_node_artifacts_returns_13():
    out = derive_per_node_artifacts(MIN_TB)
    assert len(out) == 13
    assert [a["node_id"] for a in out] == [f"N{i}" for i in range(1, 14)]
    for a in out:
        assert "outputs" in a and isinstance(a["outputs"], dict)
        assert "stage_id" in a
        assert "name" in a


def test_apply_backfill_appends_when_empty():
    tb = json.loads(json.dumps(MIN_TB))
    new_tb, n_added = apply_backfill(tb)
    assert n_added == 13
    assert len(new_tb["stage_artifacts"]) == 13
    node_ids = [sa["node_id"] for sa in new_tb["stage_artifacts"]]
    assert "N11" in node_ids


def test_apply_backfill_skips_already_tagged():
    tb = json.loads(json.dumps(MIN_TB))
    tb["stage_artifacts"] = [{"node_id": f"N{i}", "outputs": {"x": 1}} for i in range(1, 14)]
    assert is_already_backfilled(tb) is True
    _, n_added = apply_backfill(tb)
    assert n_added == 0


def test_idempotent_second_run_no_change():
    tb = json.loads(json.dumps(MIN_TB))
    tb1, n1 = apply_backfill(tb)
    assert n1 == 13
    tb2, n2 = apply_backfill(tb1)
    assert n2 == 0
    assert len(tb2["stage_artifacts"]) == 13


def test_n11_outputs_includes_commit_sha():
    out = derive_per_node_artifacts(MIN_TB)
    n11 = next(a for a in out if a["node_id"] == "N11")
    assert "commit_sha" in n11["outputs"]
    assert n11["outputs"]["commit_sha"] == "abc1234"


def test_partial_existing_tags_only_appends_missing():
    """If task-board already has N1, N3, only the other 11 get added."""
    tb = json.loads(json.dumps(MIN_TB))
    tb["stage_artifacts"] = [
        {"node_id": "N1", "outputs": {"prior": True}},
        {"node_id": "N3", "outputs": {"prior": True}},
    ]
    new_tb, n_added = apply_backfill(tb)
    assert n_added == 11
    node_ids = [sa["node_id"] for sa in new_tb["stage_artifacts"]]
    assert node_ids.count("N1") == 1
    assert node_ids.count("N3") == 1
    n1 = next(sa for sa in new_tb["stage_artifacts"] if sa["node_id"] == "N1")
    assert n1["outputs"].get("prior") is True


def test_n13_outputs_includes_retro_link_and_final_outcome():
    out = derive_per_node_artifacts(MIN_TB)
    n13 = next(a for a in out if a["node_id"] == "N13")
    assert n13["outputs"]["retro_link"] == "retros/test-min-20260427T0000Z.md"
    assert n13["outputs"]["final_outcome"] == "success"


def test_n4_skipped_for_b_route():
    out = derive_per_node_artifacts(MIN_TB)
    n4 = next(a for a in out if a["node_id"] == "N4")
    assert n4["outputs"].get("charter_status") == "SKIPPED_FOR_B_ROUTE"
