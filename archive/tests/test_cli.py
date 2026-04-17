"""Tests for archive CLI entry point (Phase 8.2).

All 3 subcommands must be invocable via `python3 -m archive <cmd>`.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
HARNESS_ROOT = HERE.parent.parent


def _run(args, cwd=None, extra_env=None):
    """Invoke CLI as subprocess, return (returncode, stdout, stderr)."""
    env = {"PYTHONPATH": str(HARNESS_ROOT)}
    if extra_env:
        env.update(extra_env)
    import os
    env = {**os.environ, **env}
    result = subprocess.run(
        [sys.executable, "-m", "archive", *args],
        cwd=cwd or HARNESS_ROOT,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


@pytest.fixture
def tmp_archive(tmp_path):
    """Minimal 2-entry archive for CLI tests."""
    p = tmp_path / "test-archive.jsonl"
    entries = [
        {
            "task_id": "cli-t1", "project": "harnessFlow", "date": "2026-04-17",
            "ts": "2026-04-17T08:00:00Z", "task_type": "元技能验证",
            "size": "M", "risk": "低", "route": "B", "node": "verifier",
            "error_type": "OTHER", "missing_subcontract": [],
            "retry_count": 0, "retry_levels_used": [],
            "final_outcome": "success", "frequency": 1,
            "root_cause": "cli-test", "fix": "cli-test", "prevention": "cli-test",
            "supervisor_events_count": 0, "user_interrupts_count": 0,
        },
        {
            "task_id": "cli-t2", "project": "harnessFlow", "date": "2026-04-17",
            "ts": "2026-04-17T08:05:00Z", "task_type": "后端feature",
            "size": "M", "risk": "中", "route": "B", "node": "verifier",
            "error_type": "DOD_GAP", "missing_subcontract": ["oss_head"],
            "retry_count": 1, "retry_levels_used": ["L0"],
            "final_outcome": "failed", "frequency": 1,
            "root_cause": "cli-test", "fix": "cli-test", "prevention": "cli-test",
            "supervisor_events_count": 1, "user_interrupts_count": 0,
        },
    ]
    with p.open("w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    return p


def test_cli_list_recent(tmp_archive):
    rc, out, err = _run(["list", "--recent", "5", "--archive", str(tmp_archive)])
    assert rc == 0, f"stderr={err}"
    assert "cli-t1" in out
    assert "cli-t2" in out
    assert "success" in out
    assert "failed" in out


def test_cli_audit_dry_run(tmp_archive):
    rc, out, err = _run([
        "audit", "--dry-run", "--interval", "2", "--min-samples", "1",
        "--archive", str(tmp_archive),
    ])
    assert rc == 0, f"stderr={err}"
    assert "dry-run" in out or "not written" in out
    assert "suggestions:" in out
    # 确保 audit-reports/ 未被写入（dry-run 硬约束）
    assert not (HARNESS_ROOT / "audit-reports" / "audit-20260417T*.json").parent.joinpath().is_file()


def test_cli_stats(tmp_archive):
    rc, out, err = _run(["stats", "--archive", str(tmp_archive)])
    assert rc == 0, f"stderr={err}"
    assert "total entries: 2" in out
    assert "by final_outcome" in out
    assert "success" in out
    assert "failed" in out
    assert "by route" in out


def test_cli_list_empty(tmp_path):
    missing = tmp_path / "nope.jsonl"
    rc, out, err = _run(["list", "--archive", str(missing)])
    assert rc == 0
    assert "empty or missing" in out


def test_cli_bad_subcommand():
    rc, out, err = _run(["nonsense"])
    assert rc != 0
    assert "invalid choice" in err or "usage" in err.lower()
