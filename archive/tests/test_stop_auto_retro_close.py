"""
Tests for hooks/Stop-final-gate.sh v1.4 AUTO-RETRO-CLOSE 路径（defects #4）.

设计:
  - 用 tmp_path 建一个 mini harness（boards_dir + retros_dir + archive_path）
  - subprocess 调 hook script，用 HARNESSFLOW_DIR env 重定向
  - 断言 stdout JSON / exit code

行为契约:
  1. COMMIT + verifier PASS + 缺 retro → JSON `decision:block` + reason 含 task_id + missing_retro
  2. COMMIT + verifier PASS + 缺 archive → JSON `decision:block` + reason 含 missing_archive
  3. COMMIT + verifier PASS + retro/archive 都齐但没 transition → JSON missing_transition
  4. COMMIT + verifier FAIL → 老硬阻塞路径，exit 2 + stderr
  5. 多个 task 同时命中 → 单一 JSON，items 数组
  6. CLOSED + 全合规 → exit 0 silent
  7. ABORTED + archive 齐 → exit 0 silent
  8. 空 boards_dir → exit 0 silent
  9. INIT + clarify_rounds==0 → exit 0 silent（空任务豁免）
  10. PAUSED_ESCALATED → exit 0 silent
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

HOOK_SCRIPT = (
    Path(__file__).resolve().parent.parent.parent
    / "hooks"
    / "Stop-final-gate.sh"
)


def _run_hook(harness_dir: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["HARNESSFLOW_DIR"] = str(harness_dir)
    return subprocess.run(
        ["bash", str(HOOK_SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def _make_mini_harness(tmp_path: Path) -> dict:
    boards = tmp_path / "task-boards"
    retros = tmp_path / "retros"
    boards.mkdir()
    retros.mkdir()
    (tmp_path / "schemas").mkdir(exist_ok=True)
    return {"root": tmp_path, "boards": boards, "retros": retros}


def _write_board(boards: Path, task_id: str, **fields) -> Path:
    base = {
        "task_id": task_id,
        "current_state": "INIT",
        "route": "C",
    }
    base.update(fields)
    p = boards / f"{task_id}.json"
    p.write_text(json.dumps(base), encoding="utf-8")
    return p


def test_empty_boards_dir_exits_zero(tmp_path):
    h = _make_mini_harness(tmp_path)
    r = _run_hook(h["root"])
    assert r.returncode == 0
    assert r.stdout == ""


def test_init_with_zero_clarify_rounds_exits_zero(tmp_path):
    h = _make_mini_harness(tmp_path)
    _write_board(h["boards"], "t-init-empty", current_state="INIT", clarify_rounds=0)
    r = _run_hook(h["root"])
    assert r.returncode == 0
    assert r.stdout == ""


def test_paused_escalated_exits_zero(tmp_path):
    h = _make_mini_harness(tmp_path)
    _write_board(h["boards"], "t-paused", current_state="PAUSED_ESCALATED")
    r = _run_hook(h["root"])
    assert r.returncode == 0


def test_commit_pass_missing_retro_emits_auto_retro_json(tmp_path):
    h = _make_mini_harness(tmp_path)
    _write_board(
        h["boards"],
        "t-commit-no-retro",
        current_state="COMMIT",
        route="C",
        verifier_report={"overall": "PASS"},
    )
    r = _run_hook(h["root"])
    assert r.returncode == 0, f"stderr={r.stderr}"
    out = json.loads(r.stdout)
    assert out["decision"] == "block"
    assert "t-commit-no-retro" in out["reason"]
    assert "missing_retro" in out["reason"]
    assert "retro-generator" in out["reason"]
    assert "failure-archive-writer" in out["reason"]
    assert "AUTO-RETRO-CLOSE" in out["reason"]
    assert "systemMessage" in out


def test_commit_pass_missing_archive_emits_auto_retro_json(tmp_path):
    h = _make_mini_harness(tmp_path)
    task_id = "t-commit-no-archive"
    # retro 文件存在但缺 archive_entry_link
    retro_md = h["retros"] / f"{task_id}.md"
    retro_md.write_text("# retro\n## 1. \n", encoding="utf-8")
    _write_board(
        h["boards"],
        task_id,
        current_state="COMMIT",
        route="C",
        verifier_report={"overall": "PASS"},
        retro_link=str(retro_md),
    )
    r = _run_hook(h["root"])
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["decision"] == "block"
    assert task_id in out["reason"]
    assert "missing_archive" in out["reason"]


def test_commit_pass_all_present_but_not_transitioned_emits_auto_retro_json(tmp_path):
    h = _make_mini_harness(tmp_path)
    task_id = "t-commit-no-transition"
    retro_md = h["retros"] / f"{task_id}.md"
    retro_md.write_text("# retro\n## 1. \n", encoding="utf-8")
    _write_board(
        h["boards"],
        task_id,
        current_state="COMMIT",
        route="C",
        verifier_report={"overall": "PASS"},
        retro_link=str(retro_md),
        archive_entry_link="failure-archive.jsonl#L99",
    )
    r = _run_hook(h["root"])
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["decision"] == "block"
    assert "missing_transition" in out["reason"]


def test_commit_verifier_fail_falls_through_to_hard_block(tmp_path):
    h = _make_mini_harness(tmp_path)
    _write_board(
        h["boards"],
        "t-commit-fail",
        current_state="COMMIT",
        route="C",
        verifier_report={"overall": "FAIL", "red_lines_detected": []},
    )
    r = _run_hook(h["root"])
    assert r.returncode == 2
    assert "not terminal" in r.stderr
    assert r.stdout == ""


def test_commit_pass_route_a_falls_through(tmp_path):
    """A 路线豁免：不走 auto-retro，落到老的 not-terminal 报错（A 应该直接 CLOSED）。"""
    h = _make_mini_harness(tmp_path)
    _write_board(
        h["boards"],
        "t-commit-a-route",
        current_state="COMMIT",
        route="A",
        verifier_report={"overall": "PASS"},
    )
    r = _run_hook(h["root"])
    assert r.returncode == 2
    assert "not terminal" in r.stderr


def test_multiple_commits_aggregate_in_one_json(tmp_path):
    h = _make_mini_harness(tmp_path)
    _write_board(
        h["boards"], "t-multi-1",
        current_state="COMMIT", route="C",
        verifier_report={"overall": "PASS"},
    )
    _write_board(
        h["boards"], "t-multi-2",
        current_state="COMMIT", route="B",
        verifier_report={"overall": "PASS"},
    )
    r = _run_hook(h["root"])
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert "t-multi-1" in out["reason"]
    assert "t-multi-2" in out["reason"]
    assert "2 task(s)" in out["reason"]


def test_closed_with_full_chain_exits_zero(tmp_path):
    h = _make_mini_harness(tmp_path)
    task_id = "t-closed-ok"
    retro_md = h["retros"] / f"{task_id}.md"
    # 11 section titles required
    sections = "\n".join(f"## {i}. heading" for i in range(1, 12))
    retro_md.write_text(f"# retro\n{sections}\n", encoding="utf-8")
    archive_path = h["root"] / "failure-archive.jsonl"
    archive_path.write_text("{}\n", encoding="utf-8")  # placeholder line 1
    _write_board(
        h["boards"], task_id,
        current_state="CLOSED",
        route="C",
        verifier_report={"overall": "PASS", "red_lines_detected": []},
        red_lines=[],
        artifacts=[{"path": "x.py"}],
        final_outcome="success",
        retro_link=str(retro_md),
        archive_entry_link="failure-archive.jsonl#L1",
        closed_at="2099-01-01T00:00:00Z",
    )
    r = _run_hook(h["root"])
    assert r.returncode == 0, f"stderr={r.stderr}"
    assert r.stdout == ""


def test_aborted_with_archive_exits_zero(tmp_path):
    h = _make_mini_harness(tmp_path)
    _write_board(
        h["boards"], "t-aborted",
        current_state="ABORTED",
        route="C",
        archive_entry_link="failure-archive.jsonl#L5",
    )
    r = _run_hook(h["root"])
    assert r.returncode == 0


def test_aborted_without_archive_blocks(tmp_path):
    h = _make_mini_harness(tmp_path)
    _write_board(
        h["boards"], "t-aborted-noarc",
        current_state="ABORTED",
        route="C",
    )
    r = _run_hook(h["root"])
    assert r.returncode == 2
    assert "archive_entry_link missing" in r.stderr


def test_corrupt_taskboard_blocks(tmp_path):
    h = _make_mini_harness(tmp_path)
    p = h["boards"] / "t-bad.json"
    p.write_text("{not json", encoding="utf-8")
    r = _run_hook(h["root"])
    assert r.returncode == 2
    assert "JSON invalid" in r.stderr


def test_auto_retro_takes_priority_over_other_failures(tmp_path):
    """AUTO-RETRO-CLOSE 的 task 与 hard-fail 的 task 同时存在 → 仍输出 JSON exit 0。"""
    h = _make_mini_harness(tmp_path)
    _write_board(
        h["boards"], "t-auto",
        current_state="COMMIT", route="C",
        verifier_report={"overall": "PASS"},
    )
    _write_board(
        h["boards"], "t-bad",
        current_state="ABORTED", route="C",  # 缺 archive_entry_link
    )
    r = _run_hook(h["root"])
    # 即使有 bad task，auto-retro 优先输出 JSON 让主 skill 接管
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert "t-auto" in out["reason"]
