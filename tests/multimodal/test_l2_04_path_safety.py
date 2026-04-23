"""WP-η-01 · L2-04 Path Safety tests."""

from __future__ import annotations

import pytest

from app.multimodal.common.errors import (
    IC_11_ERROR_CODES,
    L2_04_ERROR_CODES,
    L108Error,
)


# --- Task 01.1 error codes tests ---


def test_l2_04_error_codes_complete() -> None:
    """L2-04 源 doc §3.7 列出的 15 错误码必须全在 frozenset 里。"""
    expected = {
        "path_forbidden", "path_escape", "cross_project", "not_found",
        "permission_denied", "not_a_file", "binary_unsupported",
        "type_mismatch", "size_exceeded", "format_unsupported",
        "invalid_path", "invalid_project_id", "external_endpoint_blocked",
        "concurrency_lock_timeout", "halted_denied",
    }
    assert expected == set(L2_04_ERROR_CODES)
    assert len(L2_04_ERROR_CODES) == 15


def test_ic_11_error_codes_complete() -> None:
    """IC-11 contract §3.11.4 列出的 6 错误码必须全在 frozenset 里。"""
    expected = {
        "E_PC_NO_PROJECT_ID", "E_PC_PATH_OUT_OF_PROJECT", "E_PC_PATH_NOT_FOUND",
        "E_PC_TYPE_TASK_MISMATCH", "E_PC_LARGE_CODE_BASE", "E_PC_VISION_API_FAIL",
    }
    assert expected == set(IC_11_ERROR_CODES)
    assert len(IC_11_ERROR_CODES) == 6


def test_l108_error_carries_code_and_detail() -> None:
    e = L108Error("path_escape", "../../etc/passwd")
    assert e.code == "path_escape"
    assert e.detail == "../../etc/passwd"
    assert "path_escape" in str(e)
    assert "../../etc/passwd" in str(e)


def test_l108_error_accepts_ic_11_codes() -> None:
    e = L108Error("E_PC_NO_PROJECT_ID")
    assert e.code == "E_PC_NO_PROJECT_ID"


def test_l108_error_rejects_unknown_code() -> None:
    with pytest.raises(ValueError, match="unknown L1-08 error code"):
        L108Error("not_a_real_code")


# --- Task 01.2 schemas tests ---


def _valid_cmd_kwargs() -> dict:
    return dict(
        command_id="pc-01HYA1ABCDEF",
        project_id="p-001",
        content_type="md",
        target_path="docs/intro.md",
        task="summarize",
        caller_l1="L1-01",
        ts="2026-04-23T10:00:00Z",
    )


def test_process_content_command_defaults() -> None:
    from app.multimodal.path_safety.schemas import ProcessContentCommand
    cmd = ProcessContentCommand(**_valid_cmd_kwargs())
    assert cmd.sync_mode is True
    assert cmd.context is None


def test_process_content_command_rejects_invalid_content_type() -> None:
    from app.multimodal.path_safety.schemas import ProcessContentCommand
    with pytest.raises(Exception):
        ProcessContentCommand(**{**_valid_cmd_kwargs(), "content_type": "invalid"})


def test_process_content_command_rejects_invalid_task() -> None:
    from app.multimodal.path_safety.schemas import ProcessContentCommand
    with pytest.raises(Exception):
        ProcessContentCommand(**{**_valid_cmd_kwargs(), "task": "nope"})


def test_process_content_command_rejects_bad_command_id() -> None:
    from app.multimodal.path_safety.schemas import ProcessContentCommand
    with pytest.raises(Exception):
        ProcessContentCommand(**{**_valid_cmd_kwargs(), "command_id": "bad_id"})


def test_process_content_command_rejects_extra_fields() -> None:
    from app.multimodal.path_safety.schemas import ProcessContentCommand
    with pytest.raises(Exception):
        ProcessContentCommand(**{**_valid_cmd_kwargs(), "unknown_field": 1})


def test_process_content_result_ok() -> None:
    from app.multimodal.path_safety.schemas import ProcessContentResult
    r = ProcessContentResult(
        command_id="pc-01HYA1",
        success=True,
        structured_output={"summary": "hi"},
        duration_ms=42,
    )
    assert r.success is True
    assert r.error is None


def test_process_content_result_error() -> None:
    from app.multimodal.path_safety.schemas import ProcessContentResult, ErrorBody
    r = ProcessContentResult(
        command_id="pc-01HYA1",
        success=False,
        error=ErrorBody(code="E_PC_NO_PROJECT_ID", message="missing"),
        duration_ms=3,
    )
    assert r.error is not None
    assert r.error.code == "E_PC_NO_PROJECT_ID"


def test_process_content_result_async_task_id_format() -> None:
    from app.multimodal.path_safety.schemas import ProcessContentResult
    r = ProcessContentResult(
        command_id="pc-01HYA1", success=True,
        async_task_id="async-01HYA1XYZ", duration_ms=5,
    )
    assert r.async_task_id.startswith("async-")


def test_route_decision_enum_values() -> None:
    from app.multimodal.path_safety.schemas import RouteDecision
    assert {d.value for d in RouteDecision} == {"DIRECT", "PAGED", "DELEGATE", "REJECT"}


def test_validation_result_ok_shape() -> None:
    from app.multimodal.path_safety.schemas import ValidationResult
    v = ValidationResult(ok=True, realpath="/tmp/p/docs/a.md", allowlist_match="docs/")
    assert v.ok is True
    assert v.error_code is None


def test_validation_result_error_shape() -> None:
    from app.multimodal.path_safety.schemas import ValidationResult
    v = ValidationResult(ok=False, error_code="path_escape")
    assert v.ok is False
    assert v.error_code == "path_escape"


# --- Task 01.3 whitelist tests ---

from pathlib import Path

from app.multimodal.path_safety.whitelist import PathWhitelistValidator


@pytest.mark.parametrize("bad_path,expected_code", [
    ("../../etc/passwd", "path_escape"),
    ("/etc/passwd", "path_escape"),
    ("docs/normal.md\x00", "invalid_path"),
    ("", "invalid_path"),
    ("../p-other-project/secret.md", "cross_project"),
    ("node_modules/foo.js", "path_forbidden"),
])
def test_whitelist_rejects(tmp_project_root: Path, bad_path: str, expected_code: str) -> None:
    v = PathWhitelistValidator(
        project_root=tmp_project_root,
        project_id="p-001",
        allowlist=["docs/", "tests/", "harnessFlow/"],
    )
    with pytest.raises(L108Error) as ei:
        v.validate(bad_path, action="read")
    assert ei.value.code == expected_code


def test_whitelist_allows_valid(tmp_project_root: Path) -> None:
    (tmp_project_root / "docs").mkdir()
    (tmp_project_root / "docs" / "intro.md").write_text("# hi")
    v = PathWhitelistValidator(
        project_root=tmp_project_root,
        project_id="p-001",
        allowlist=["docs/", "tests/"],
    )
    result = v.validate("docs/intro.md", action="read")
    assert result.ok is True
    assert result.realpath is not None
    assert result.realpath.endswith("docs/intro.md")
    assert result.allowlist_match == "docs/"


def test_whitelist_rejects_none_path(tmp_project_root: Path) -> None:
    v = PathWhitelistValidator(tmp_project_root, "p-001", ["docs/"])
    with pytest.raises(L108Error) as ei:
        v.validate(None, action="read")  # type: ignore[arg-type]
    assert ei.value.code == "invalid_path"


# --- Task 01.4 symlink cycle detection tests ---

import os

from app.multimodal.path_safety.symlink_detector import SymlinkCycleDetector


def test_symlink_no_cycle_passes(tmp_project_root: Path) -> None:
    """Plain file · no symlinks · no cycle detected."""
    (tmp_project_root / "docs").mkdir()
    target = tmp_project_root / "docs" / "a.md"
    target.write_text("hi")
    SymlinkCycleDetector().check(target)  # should not raise


def test_symlink_detects_cycle_a_b_c_a(tmp_project_root: Path) -> None:
    """Cycle a → b → c → a must be detected as path_escape/symlink_loop."""
    docs = tmp_project_root / "docs"
    docs.mkdir()
    a, b, c = docs / "a", docs / "b", docs / "c"
    os.symlink(b, a)
    os.symlink(c, b)
    os.symlink(a, c)
    with pytest.raises(L108Error) as ei:
        SymlinkCycleDetector().check(a)
    assert ei.value.code == "path_escape"
    assert "symlink_loop" in ei.value.detail


def test_symlink_depth_exceeded(tmp_project_root: Path) -> None:
    """Chain a → b → c → d → … (10 hops) · exceeds MAX_DEPTH=8."""
    docs = tmp_project_root / "docs"
    docs.mkdir()
    # Build a chain of 10 symlinks pointing forward, last one points to a real file.
    final = docs / "final.md"
    final.write_text("end")
    prev = final
    for i in range(10):
        link = docs / f"s{i}"
        os.symlink(prev, link)
        prev = link
    with pytest.raises(L108Error) as ei:
        SymlinkCycleDetector().check(prev)
    assert ei.value.code == "path_escape"
    assert "symlink_depth_exceeded" in ei.value.detail


def test_symlink_depth_within_limit(tmp_project_root: Path) -> None:
    """Chain of 5 symlinks → under MAX_DEPTH=8 → passes."""
    docs = tmp_project_root / "docs"
    docs.mkdir()
    final = docs / "final.md"
    final.write_text("end")
    prev = final
    for i in range(5):
        link = docs / f"s{i}"
        os.symlink(prev, link)
        prev = link
    SymlinkCycleDetector().check(prev)  # should not raise
