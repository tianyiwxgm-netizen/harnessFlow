"""TC-L104-L206 · 边界 / 难测路径 TC · 补齐覆盖率 + 硬红线验证.

核心 TC：
- _classify_error · unknown 异常 → default fallback (ic_20_api_error)
- dispatch · dispatched=False 3 次连续失败 · retry_log 分类
- signature_checker · _to_set 边界（None / 单值 / set）
- signature_checker · _summary 非 dict 入参
- orchestrator · _parse_verifier_output 用 observed_blueprint 字段名替代
- orchestrator · _parse_verifier_output 用 test_report 字段名替代 s4_diff_analysis
- ic_20_dispatcher · verify_session_prefix 中 session_id != main 但 main-prefix 边界
"""
from __future__ import annotations

from typing import Any

import pytest

from app.quality_loop.verifier.ic_20_dispatcher import (
    DelegationFailureError,
    _classify_error,
    dispatch_with_retry,
    verify_session_prefix,
)
from app.quality_loop.verifier.orchestrator import (
    VerifierDeps,
    orchestrate_s5,
)
from app.quality_loop.verifier.schemas import (
    IC20Command,
    IC20DispatchResult,
    VerificationRequest,
    VerifierVerdict,
)
from app.quality_loop.verifier.signature_checker import (
    _summary,
    _to_set,
)
from app.quality_loop.verifier.trace_adapter import MockExecutionTrace


async def no_sleep(_: float) -> None:
    return None


def _mk_req(**o: Any) -> VerificationRequest:
    d: dict[str, Any] = {
        "project_id": "proj-X",
        "wp_id": "wp-1",
        "blueprint_slice": {"dod": "x"},
        "s4_snapshot": {"artifact_refs": [], "git_head": "abc"},
        "acceptance_criteria": {},
        "main_session_id": "main-xyz",
        "delegation_id": "ver-edge-1",
        "timeout_s": 600,
        "ts": "2026-04-23T10:00:00Z",
    }
    d.update(o)
    return VerificationRequest(**d)


def _mk_trace(**o: Any) -> MockExecutionTrace:
    d: dict[str, Any] = {
        "project_id": "proj-X",
        "wp_id": "wp-1",
        "git_head": "abc",
        "blueprint_slice": {"dod_expression": "x", "red_tests": []},
        "main_session_id": "main-xyz",
        "ts": "2026-04-23T10:00:00Z",
        "artifact_refs": (),
        "test_report": {},
        "acceptance_criteria": {},
    }
    d.update(o)
    return MockExecutionTrace(**d)


# ==============================================================================
# _classify_error 覆盖
# ==============================================================================


class TestClassifyError:
    """TC-L104-L206-600 · _classify_error 所有分支."""

    def test_timeout_name(self) -> None:
        assert _classify_error(TimeoutError()) == "timeout"

    def test_timeout_message(self) -> None:
        assert _classify_error(RuntimeError("operation timeout")) == "timeout"

    def test_rate_limit(self) -> None:
        assert _classify_error(RuntimeError("429 too many requests")) == "ic_20_api_rate_limit"

    def test_rate_word(self) -> None:
        assert _classify_error(RuntimeError("rate limiter activated")) == "ic_20_api_rate_limit"

    def test_limit_word(self) -> None:
        assert _classify_error(RuntimeError("hit API limit")) == "ic_20_api_rate_limit"

    def test_server_5xx(self) -> None:
        assert _classify_error(RuntimeError("500 internal server error")) == "ic_20_api_error"

    def test_server_word(self) -> None:
        assert _classify_error(RuntimeError("server unreachable")) == "ic_20_api_error"

    def test_spawn_word(self) -> None:
        assert _classify_error(RuntimeError("spawn subprocess failed")) == "subagent_spawn_failure"

    def test_start_word(self) -> None:
        assert _classify_error(RuntimeError("failed to start")) == "subagent_spawn_failure"

    def test_unknown_default(self) -> None:
        """未知错误 → default ic_20_api_error."""
        assert _classify_error(RuntimeError("some_obscure_issue")) == "ic_20_api_error"


# ==============================================================================
# signature_checker 内部辅助
# ==============================================================================


class TestSignatureCheckerAux:
    """TC-L104-L206-610 · _to_set + _summary 边界."""

    def test_to_set_from_none(self) -> None:
        assert _to_set(None) == frozenset()

    def test_to_set_from_list(self) -> None:
        assert _to_set(["a", "b", "a"]) == frozenset({"a", "b"})

    def test_to_set_from_tuple(self) -> None:
        assert _to_set(("a", "b")) == frozenset({"a", "b"})

    def test_to_set_from_set(self) -> None:
        assert _to_set({"a", "b"}) == frozenset({"a", "b"})

    def test_to_set_from_single_string(self) -> None:
        """单值非 list/tuple/set · 包成 set."""
        assert _to_set("single") == frozenset({"single"})

    def test_summary_on_dict(self) -> None:
        d = {"dod_expression": "foo", "red_tests": [1], "extra": "should_drop"}
        s = _summary(d)
        assert "dod_expression" in s
        assert "extra" not in s

    def test_summary_on_non_dict(self) -> None:
        """非 dict · 返 {'_type': TypeName}."""
        r = _summary([1, 2, 3])
        assert r == {"_type": "list"}


# ==============================================================================
# ic_20_dispatcher · dispatched=False 3 连失败路径
# ==============================================================================


class FakeDispatchedFalse:
    """永远返回 dispatched=False."""

    def __init__(self, delegation_id: str) -> None:
        self.delegation_id = delegation_id
        self.calls: list[IC20Command] = []

    async def delegate_verifier(self, command: IC20Command) -> IC20DispatchResult:
        self.calls.append(command)
        return IC20DispatchResult(
            delegation_id=command.delegation_id,
            dispatched=False,
        )


class TestDispatchedFalseThreeFailures:
    """TC-L104-L206-620 · dispatched=False 3 次全失败 · 分支 branch 290."""

    @pytest.mark.asyncio
    async def test_three_dispatched_false_raises(self) -> None:
        req = _mk_req()
        fake = FakeDispatchedFalse(req.delegation_id)
        with pytest.raises(DelegationFailureError) as exc:
            await dispatch_with_retry(req, fake, sleep=no_sleep)
        assert len(exc.value.retry_log) == 3
        outcomes = [log["outcome"] for log in exc.value.retry_log]
        assert all(o == "subagent_spawn_failure" for o in outcomes)
        assert len(fake.calls) == 3


# ==============================================================================
# orchestrator · 替代字段名
# ==============================================================================


class FakeDeleg:
    def __init__(self, sid: str = "sub-alt-001") -> None:
        self.sid = sid
        self.calls: list[IC20Command] = []

    async def delegate_verifier(self, command: IC20Command) -> IC20DispatchResult:
        self.calls.append(command)
        return IC20DispatchResult(
            delegation_id=command.delegation_id,
            dispatched=True,
            verifier_session_id=self.sid,
        )


class FakeWaiter:
    def __init__(self, output: dict[str, Any]) -> None:
        self.output = output

    async def wait(self, **_: Any) -> dict[str, Any]:
        return self.output


class TestOrchestratorAlternativeFieldNames:
    """TC-L104-L206-630 · verifier 用 observed_blueprint/test_report 替代字段名."""

    @pytest.mark.asyncio
    async def test_observed_blueprint_field_name(self) -> None:
        """verifier 用 `observed_blueprint` 替代 `blueprint_alignment` · 应接受."""
        trace = _mk_trace(blueprint_slice={"dod_expression": "foo", "red_tests": []})
        output = {
            "observed_blueprint": {"dod_expression": "foo", "red_tests": []},  # 替代名
            "s4_diff_analysis": {},
            "dod_evaluation": {"verdict": "PASS", "all_pass": True},
        }
        deps = VerifierDeps(
            delegator=FakeDeleg(),
            callback_waiter=FakeWaiter(output),
            sleep=no_sleep,
        )
        result = await orchestrate_s5(trace, deps)
        assert result.verdict == VerifierVerdict.PASS

    @pytest.mark.asyncio
    async def test_test_report_field_name(self) -> None:
        """verifier 用 `test_report` 替代 `s4_diff_analysis`."""
        trace = _mk_trace(test_report={"passed": 5, "failed": 0, "coverage": 0.9})
        output = {
            "blueprint_alignment": {"dod_expression": "x", "red_tests": []},
            "test_report": {"passed": 5, "failed": 0, "coverage": 0.9},  # 替代名
            "dod_evaluation": {"verdict": "PASS", "all_pass": True},
        }
        deps = VerifierDeps(
            delegator=FakeDeleg(),
            callback_waiter=FakeWaiter(output),
            sleep=no_sleep,
        )
        result = await orchestrate_s5(trace, deps)
        assert result.verdict == VerifierVerdict.PASS


# ==============================================================================
# verify_session_prefix 额外边界
# ==============================================================================


class TestVerifySessionPrefixExtras:
    """TC-L104-L206-640 · 边界 · main_session_id 以 sub- 开头的异常情形."""

    def test_main_session_with_sub_prefix_and_equal_id(self) -> None:
        """罕见场景 · main_session_id 本身就是 sub- 开头且等于 verifier_session_id → E20."""
        # 此情景模拟 L1-05 bug · 返了 main_session_id 本身
        from app.quality_loop.verifier.ic_20_dispatcher import (
            SessionPrefixViolationError,
        )

        with pytest.raises(SessionPrefixViolationError):
            verify_session_prefix("sub-main-shared", "sub-main-shared")

    def test_sub_prefix_with_hyphen_ok(self) -> None:
        """sub-xxx-yyy 合法."""
        verify_session_prefix("sub-project-a-deadbeef", "main-session-x")
