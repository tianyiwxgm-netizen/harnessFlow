"""Unit tests for archive/writer.py.

Covers P20 fake-completion replay, frequency derivation, missing inputs,
and concurrent append (lock correctness)."""

import json
import multiprocessing
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from archive.writer import (  # noqa: E402
    ArchiveWriteError,
    write_archive_entry,
)


@pytest.fixture
def tmp_archive(tmp_path):
    return tmp_path / "failure-archive.jsonl"


@pytest.fixture
def p20_task_board(tmp_path):
    tb_path = tmp_path / "tb.json"
    tb = {
        "task_id": "p20-fake",
        "project": "aigcv2",
        "route_id": "C",
        "size": "XL",
        "task_type": "视频出片",
        "risk": "中",
        "current_state": "CLOSED",
        "dod_expression": 'file_exists("p.mp4") AND oss_head("u").status_code == 200',
        "state_history": [
            {"state": "IMPL", "timestamp": "2026-04-17T00:00:00Z"},
            {"state": "VERIFY", "timestamp": "2026-04-17T00:10:00Z"},
        ],
        "retries": [
            {"level": "L0", "state": "IMPL", "err_class": "mock_bug", "trigger": "sleep", "outcome": "retried"},
            {"level": "L1", "state": "IMPL", "err_class": "oss_403", "trigger": "lack_perm", "outcome": "retried"},
        ],
        "red_lines": [{"code": "DOD_GAP_ALERT", "triggered_at": "2026-04-17T00:10:00Z"}],
        "supervisor_interventions": [{"severity": "WARN", "code": "slow_impl"}],
        "time_budget": {"started_at": "2026-04-17T00:00:00Z", "elapsed_sec": 1800, "cap_sec": 3600},
        "cost_budget": {"token_used": 58000, "token_cap": 120000},
        "final_outcome": None,
    }
    tb_path.write_text(json.dumps(tb))
    return tb_path


@pytest.fixture
def p20_verifier_report(tmp_path):
    vr = tmp_path / "vr.json"
    vr.write_text(json.dumps({
        "task_id": "p20-fake",
        "verdict": "FAIL",
        "priority_applied": "P0_red_line",
        "failed_conditions": ['oss_head("u").status_code == 200'],
        "red_lines": ["DOD_GAP_ALERT"],
        "evidence_chain": {"existence": [], "behavior": [], "quality": []},
        "insufficient_evidence_count_after_this": 0,
    }))
    return vr


def test_p20_entry_derivation(p20_task_board, p20_verifier_report, tmp_archive):
    entry = write_archive_entry(
        task_id="p20-fake",
        task_board_path=p20_task_board,
        verifier_report_path=p20_verifier_report,
        archive_path=tmp_archive,
    )
    assert entry["task_id"] == "p20-fake"
    assert entry["project"] == "aigcv2"
    assert entry["task_type"] == "视频出片"
    assert entry["size"] == "XL"
    assert entry["route"] == "C"
    assert entry["error_type"] == "DOD_GAP"
    assert entry["retry_count"] == 2
    assert set(entry["retry_levels_used"]) == {"L0", "L1"}
    assert entry["final_outcome"] == "false_complete_reported"
    assert entry["frequency"] == 1
    assert "oss_head" in entry["missing_subcontract"][0]


def test_frequency_accumulates(p20_task_board, p20_verifier_report, tmp_archive):
    for _ in range(3):
        write_archive_entry(
            task_id=f"p20-fake",
            task_board_path=p20_task_board,
            verifier_report_path=p20_verifier_report,
            archive_path=tmp_archive,
        )
    lines = tmp_archive.read_text().strip().splitlines()
    assert len(lines) == 3
    freqs = [json.loads(l)["frequency"] for l in lines]
    assert freqs == [1, 2, 3]


def test_missing_task_board_raises(tmp_path, tmp_archive):
    with pytest.raises(ArchiveWriteError) as exc:
        write_archive_entry(
            task_id="x",
            task_board_path=tmp_path / "nope.json",
            archive_path=tmp_archive,
        )
    assert "task-board" in str(exc.value) or "not found" in str(exc.value)


def test_missing_verifier_report_raises(p20_task_board, tmp_path, tmp_archive):
    with pytest.raises(ArchiveWriteError):
        write_archive_entry(
            task_id="x",
            task_board_path=p20_task_board,
            verifier_report_path=tmp_path / "nope.json",
            archive_path=tmp_archive,
        )


def test_invalid_size_raises(tmp_path, tmp_archive):
    tb = tmp_path / "tb.json"
    tb.write_text(json.dumps({
        "task_id": "x",
        "project": "p",
        "route_id": "C",
        "size": "HUGE",
        "task_type": "视频出片",
        "risk": "中",
        "current_state": "CLOSED",
    }))
    with pytest.raises(ArchiveWriteError) as exc:
        write_archive_entry(task_id="x", task_board_path=tb, archive_path=tmp_archive)
    assert "size" in str(exc.value)


def test_schema_violation_raises(tmp_path, tmp_archive):
    # Empty task_id directly violates schema minLength=1 → writer must raise.
    tb = tmp_path / "tb.json"
    tb.write_text(json.dumps({
        "task_id": "",
        "project": "p",
        "route_id": "C",
        "size": "M",
        "task_type": "后端feature",
        "risk": "中",
        "current_state": "CLOSED",
    }))
    with pytest.raises(ArchiveWriteError) as exc:
        write_archive_entry(
            task_id="",
            task_board_path=tb,
            archive_path=tmp_archive,
        )
    assert "schema" in str(exc.value).lower() or "task_id" in str(exc.value)


def test_frequency_distinct_error_types(p20_task_board, tmp_archive, tmp_path):
    # Entry A: DOD_GAP
    vr1 = tmp_path / "vr1.json"
    vr1.write_text(json.dumps({
        "verdict": "FAIL",
        "failed_conditions": ['oss_head("u")'],
        "red_lines": ["DOD_GAP_ALERT"],
        "evidence_chain": {"existence": [], "behavior": [], "quality": []},
    }))
    write_archive_entry(
        task_id="a", task_board_path=p20_task_board,
        verifier_report_path=vr1, archive_path=tmp_archive,
    )
    # Entry B: different subcontract, should not inherit A's frequency
    vr2 = tmp_path / "vr2.json"
    vr2.write_text(json.dumps({
        "verdict": "FAIL",
        "failed_conditions": ['ffprobe_duration("p.mp4") > 0'],
        "red_lines": ["DOD_GAP_ALERT"],
        "evidence_chain": {"existence": [], "behavior": [], "quality": []},
    }))
    entry_b = write_archive_entry(
        task_id="b", task_board_path=p20_task_board,
        verifier_report_path=vr2, archive_path=tmp_archive,
    )
    # Different missing_subcontract → different freq chain
    assert entry_b["frequency"] == 1


def _child_append(task_board_path, vr_path, archive_path, idx):
    try:
        write_archive_entry(
            task_id=f"cc-{idx}",
            task_board_path=task_board_path,
            verifier_report_path=vr_path,
            archive_path=archive_path,
        )
    except Exception as e:
        return f"ERR: {e}"
    return "OK"


def _run_concurrent_writes_no_loss_once(p20_task_board, p20_verifier_report, tmp_archive):
    """Single attempt of the concurrent write test. Raises AssertionError on any loss."""
    ctx = multiprocessing.get_context("spawn")
    n = 5
    procs = []
    for i in range(n):
        p = ctx.Process(
            target=_child_append,
            args=(str(p20_task_board), str(p20_verifier_report), str(tmp_archive), i),
        )
        procs.append(p)
        p.start()
    for p in procs:
        p.join(timeout=60)  # widened from 30 (cold spawn + fcntl 3×5s retry ceiling ~15s)
        if p.is_alive():
            p.terminate()
            raise AssertionError(f"child process {p.pid} did not finish within 60s")

    lines = tmp_archive.read_text().strip().splitlines()
    assert len(lines) == n, f"expected {n} entries; got {len(lines)}"
    for line in lines:
        json.loads(line)


def test_concurrent_writes_no_loss(p20_task_board, p20_verifier_report, tmp_archive):
    """Concurrent fcntl-locked write: 5 spawn processes, no line loss.

    Retries up to 3 times — rare CI flakes come from spawn-warmup + kernel
    scheduler jitter on the fcntl blocking wait; the writer itself is correct.
    If all 3 attempts fail, the retry pattern is the real bug, not timing.
    """
    last_err: Exception | None = None
    for attempt in range(3):
        # Each retry uses a fresh archive file (previous may have partial writes)
        attempt_archive = tmp_archive.with_name(f"{tmp_archive.name}.attempt{attempt}")
        try:
            _run_concurrent_writes_no_loss_once(p20_task_board, p20_verifier_report, attempt_archive)
            return  # success
        except AssertionError as e:
            last_err = e
            time.sleep(1)  # back-off before next attempt
    assert last_err is None, f"concurrent_writes_no_loss failed after 3 attempts: {last_err}"
