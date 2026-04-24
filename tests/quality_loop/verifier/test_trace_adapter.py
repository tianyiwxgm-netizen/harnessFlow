"""TC-L104-L206 · trace_adapter · S4 ExecutionTrace → VerificationRequest.

核心 TC：
- happy · 完整 trace 适配成功
- 幂等 · 同 (wp_id, git_head) 外部指定 delegation_id 可复用
- PM-14 · project_id 空拒绝
- E06 · blueprint_slice 空拒绝（missing_blueprint_artifact）
- E10 · git_head 空 / wp_id 空拒绝（s4_snapshot_invalid）
- E07 · main_session_id 缺失拒绝
- test_report 可选 · None 时不进入 s4_snapshot
- Protocol 鸭子类型 · 任意对象只要字段全就接受
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.quality_loop.verifier.schemas import VerificationRequest
from app.quality_loop.verifier.trace_adapter import (
    MockExecutionTrace,
    TraceAdapterError,
    adapt_from_s4,
)


def _mk_trace(**overrides: Any) -> MockExecutionTrace:
    defaults: dict[str, Any] = {
        "project_id": "proj-A",
        "wp_id": "wp-1",
        "git_head": "abcdef1234567890",
        "blueprint_slice": {"dod": "tests_pass", "red_tests": ["t1"]},
        "main_session_id": "main-session-xyz",
        "ts": "2026-04-23T10:00:00Z",
        "artifact_refs": ("app/x.py", "app/y.py"),
        "test_report": {"passed": 5, "failed": 0},
        "acceptance_criteria": {"coverage": 0.8},
    }
    defaults.update(overrides)
    return MockExecutionTrace(**defaults)


class TestAdaptFromS4Happy:
    """TC-L104-L206-100 · adapt happy · 完整 trace → VerificationRequest."""

    def test_full_trace_adapts(self) -> None:
        """所有字段齐 · 返回合法 VerificationRequest."""
        trace = _mk_trace()
        req = adapt_from_s4(trace)
        assert isinstance(req, VerificationRequest)
        assert req.project_id == "proj-A"
        assert req.wp_id == "wp-1"
        assert req.blueprint_slice == {"dod": "tests_pass", "red_tests": ["t1"]}
        # s4_snapshot 应含 artifact_refs + git_head + test_report
        assert req.s4_snapshot["git_head"] == "abcdef1234567890"
        assert req.s4_snapshot["artifact_refs"] == ["app/x.py", "app/y.py"]
        assert req.s4_snapshot["test_report"] == {"passed": 5, "failed": 0}
        assert req.acceptance_criteria == {"coverage": 0.8}
        assert req.main_session_id == "main-session-xyz"
        assert req.timeout_s == 1200  # default
        assert req.delegation_id.startswith("ver-")

    def test_trace_without_test_report(self) -> None:
        """test_report=None · s4_snapshot 不含该字段（可选）."""
        trace = _mk_trace(test_report=None)
        req = adapt_from_s4(trace)
        assert "test_report" not in req.s4_snapshot

    def test_trace_without_acceptance_criteria(self) -> None:
        """acceptance_criteria 空 dict · req 也传空 dict."""
        trace = _mk_trace(acceptance_criteria={})
        req = adapt_from_s4(trace)
        assert req.acceptance_criteria == {}

    def test_empty_artifact_refs_ok(self) -> None:
        """artifact_refs 空元组 → s4_snapshot.artifact_refs 为空 list · 仍然合法."""
        trace = _mk_trace(artifact_refs=())
        req = adapt_from_s4(trace)
        assert req.s4_snapshot["artifact_refs"] == []


class TestAdaptFromS4Idempotency:
    """TC-L104-L206-110 · delegation_id 幂等 · 外部指定复用."""

    def test_delegation_id_override(self) -> None:
        """外部传 delegation_id · 适配器复用不覆盖."""
        trace = _mk_trace()
        req = adapt_from_s4(trace, delegation_id="ver-fixed-123")
        assert req.delegation_id == "ver-fixed-123"

    def test_delegation_id_auto_generated_unique(self) -> None:
        """不传 · 自动生成 · 每次 uuid 不同."""
        trace = _mk_trace()
        r1 = adapt_from_s4(trace)
        r2 = adapt_from_s4(trace)
        assert r1.delegation_id != r2.delegation_id
        assert r1.delegation_id.startswith("ver-")
        assert r2.delegation_id.startswith("ver-")

    def test_custom_timeout(self) -> None:
        """外部指定 timeout_s 覆盖 default."""
        trace = _mk_trace()
        req = adapt_from_s4(trace, timeout_s=600)
        assert req.timeout_s == 600


class TestAdaptFromS4Errors:
    """TC-L104-L206-120 · 负向 · 缺字段 / schema 违反抛 TraceAdapterError."""

    def test_empty_project_id_rejects(self) -> None:
        """PM-14 · project_id 空 → E_VER_NO_PROJECT_ID."""
        trace = _mk_trace(project_id=" ")
        with pytest.raises(TraceAdapterError) as exc:
            adapt_from_s4(trace)
        assert "E_VER_NO_PROJECT_ID" in str(exc.value)

    def test_empty_wp_id_rejects(self) -> None:
        """wp_id 空 → E10_s4_snapshot_invalid."""
        trace = _mk_trace(wp_id="")
        with pytest.raises(TraceAdapterError) as exc:
            adapt_from_s4(trace)
        assert "E10_s4_snapshot_invalid" in str(exc.value)

    def test_empty_git_head_rejects(self) -> None:
        """git_head 空 → E10_s4_snapshot_invalid."""
        trace = _mk_trace(git_head="")
        with pytest.raises(TraceAdapterError) as exc:
            adapt_from_s4(trace)
        assert "E10_s4_snapshot_invalid" in str(exc.value)

    def test_missing_main_session_id(self) -> None:
        """main_session_id 空 → E07_main_session_id_collision."""
        trace = _mk_trace(main_session_id="")
        with pytest.raises(TraceAdapterError) as exc:
            adapt_from_s4(trace)
        assert "E07_main_session_id_collision" in str(exc.value)

    def test_empty_blueprint_slice_rejects(self) -> None:
        """blueprint_slice 空 dict → E06_missing_blueprint_artifact."""
        trace = _mk_trace(blueprint_slice={})
        with pytest.raises(TraceAdapterError) as exc:
            adapt_from_s4(trace)
        assert "E06_missing_blueprint_artifact" in str(exc.value)


class TestAdaptFromS4DuckType:
    """TC-L104-L206-130 · Protocol 鸭子类型 · 任意 trace-like 对象都接受."""

    def test_custom_trace_like_object(self) -> None:
        """任意 dataclass / 对象只要字段全 · 就能适配."""

        @dataclass(frozen=True)
        class CustomTrace:
            project_id: str
            wp_id: str
            git_head: str
            blueprint_slice: dict[str, Any]
            main_session_id: str
            ts: str
            artifact_refs: tuple[str, ...]
            test_report: dict[str, Any] | None
            acceptance_criteria: dict[str, Any]

        ctrace = CustomTrace(
            project_id="proj-Z",
            wp_id="wp-custom",
            git_head="deadbeef",
            blueprint_slice={"d": 1},
            main_session_id="main-123",
            ts="2026-04-23T00:00:00Z",
            artifact_refs=("a.py",),
            test_report=None,
            acceptance_criteria={},
        )
        req = adapt_from_s4(ctrace)
        assert req.project_id == "proj-Z"
        assert req.wp_id == "wp-custom"
