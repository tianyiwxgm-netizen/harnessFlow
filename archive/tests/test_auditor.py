"""Unit tests for archive/auditor.py."""

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from archive.auditor import audit, need_audit  # noqa: E402


def _write_entries(path, entries):
    path.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n")


def _base_entry(route="C", outcome="failed", size="XL", tt="视频出片"):
    return {
        "task_id": "x",
        "date": "2026-04-17",
        "ts": "2026-04-17T00:00:00Z",
        "project": "aigcv2",
        "task_type": tt,
        "size": size,
        "risk": "中",
        "route": route,
        "node": "verifier",
        "error_type": "DOD_GAP",
        "missing_subcontract": [],
        "retry_count": 0,
        "retry_levels_used": [],
        "final_outcome": outcome,
        "frequency": 1,
        "root_cause": "x",
        "fix": "x",
        "prevention": "x",
    }


def test_need_audit_below_interval(tmp_path):
    arc = tmp_path / "a.jsonl"
    _write_entries(arc, [_base_entry() for _ in range(5)])
    assert need_audit(arc, interval=20) is False


def test_need_audit_exact_interval(tmp_path):
    arc = tmp_path / "a.jsonl"
    _write_entries(arc, [_base_entry() for _ in range(20)])
    assert need_audit(arc, interval=20) is True


def test_need_audit_multiple_of_interval(tmp_path):
    arc = tmp_path / "a.jsonl"
    _write_entries(arc, [_base_entry() for _ in range(40)])
    assert need_audit(arc, interval=20) is True


def test_need_audit_not_multiple(tmp_path):
    arc = tmp_path / "a.jsonl"
    _write_entries(arc, [_base_entry() for _ in range(21)])
    assert need_audit(arc, interval=20) is False


def test_need_audit_empty(tmp_path):
    arc = tmp_path / "a.jsonl"
    assert need_audit(arc, interval=20) is False


def test_downweight_on_high_failure_rate(tmp_path):
    arc = tmp_path / "a.jsonl"
    _write_entries(arc, [_base_entry(route="C", outcome="failed") for _ in range(5)])
    matrix = tmp_path / "m.json"
    matrix.write_text(json.dumps({"XL": {"视频出片": [["C", 1.0, []], ["A", 0.5, []]]}}))
    out = tmp_path / "audit"
    rep = audit(archive_path=arc, routing_matrix_path=matrix, output_dir=out, min_samples_per_cell=3)
    downs = [s for s in rep.suggestions if s.route == "C" and s.direction == "down"]
    assert len(downs) == 1
    assert downs[0].sample_count == 5
    assert downs[0].failure_rate == 1.0
    assert downs[0].suggested_weight == 0.8


def test_upweight_capped_at_one(tmp_path):
    arc = tmp_path / "a.jsonl"
    _write_entries(arc, [_base_entry(route="B", outcome="success", size="L", tt="后端feature") for _ in range(12)])
    matrix = tmp_path / "m.json"
    matrix.write_text(json.dumps({"L": {"后端feature": [["B", 1.0, []]]}}))
    rep = audit(archive_path=arc, routing_matrix_path=matrix, output_dir=None, min_samples_per_cell=3)
    ups = [s for s in rep.suggestions if s.route == "B" and s.direction == "up"]
    assert len(ups) == 1
    assert ups[0].suggested_weight == 1.0  # capped


def test_below_min_samples_skipped(tmp_path):
    arc = tmp_path / "a.jsonl"
    _write_entries(arc, [_base_entry(route="D", outcome="failed") for _ in range(2)])
    rep = audit(archive_path=arc, output_dir=None, min_samples_per_cell=3)
    assert rep.suggestions == []


def test_report_writes_to_output_dir(tmp_path):
    arc = tmp_path / "a.jsonl"
    _write_entries(arc, [_base_entry(route="C", outcome="failed") for _ in range(5)])
    out = tmp_path / "audits"
    audit(archive_path=arc, routing_matrix_path=None, output_dir=out, min_samples_per_cell=3)
    files = list(out.glob("audit-*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["interval"] == 20
    assert len(data["suggestions"]) >= 1


def test_tail_only_limits_entries(tmp_path):
    arc = tmp_path / "a.jsonl"
    # 30 success followed by 5 failed — tail_only should only see last 20 (success dominates)
    success_entries = [_base_entry(route="C", outcome="success") for _ in range(25)]
    fail_entries = [_base_entry(route="C", outcome="failed") for _ in range(5)]
    _write_entries(arc, success_entries + fail_entries)
    rep = audit(
        archive_path=arc, routing_matrix_path=None, output_dir=None,
        interval=20, min_samples_per_cell=3, tail_only=True,
    )
    # Tail of 20: 15 success + 5 failed → failure_rate 0.25 → no suggestion
    downs = [s for s in rep.suggestions if s.direction == "down"]
    assert len(downs) == 0


def test_mixed_outcomes_no_suggestion_near_threshold(tmp_path):
    arc = tmp_path / "a.jsonl"
    entries = [_base_entry(route="C", outcome="failed") for _ in range(2)]
    entries += [_base_entry(route="C", outcome="success") for _ in range(3)]
    _write_entries(arc, entries)
    rep = audit(archive_path=arc, output_dir=None, min_samples_per_cell=3)
    # failure_rate=0.4 — between thresholds, no suggestion
    assert not any(s.route == "C" for s in rep.suggestions)
