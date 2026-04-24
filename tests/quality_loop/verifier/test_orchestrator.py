"""TC-L104-L206 · orchestrator · orchestrate_s5 主入口 · 7 步编排.

核心 TC：
- happy · 全绿 → PASS · 双签 OK · dod_evaluation.verdict=PASS
- 双签失败降级: blueprint 不一致 → FAIL_L2 · s4 diff 不一致 → FAIL_L1
- DoD fail → FAIL_L3（两签 OK · dod.all_pass=False）
- IC-20 3 次失败 → DelegationFailureError 传 up（caller 走 BLOCK）
- verifier 回调超时 → verdict=FAIL_L4（内部 catch TimeoutError · 不 raise）
- session prefix 硬红线 → SessionPrefixViolationError 直接 up
- callback schema 违反 → CallbackSchemaError
- PM-14 pid 透传 · 全链路 project_id 一致
- audit 事件 · orchestrate_started + report_issued / timeout
- three_segment_evidence 结构完整（含两签 + dod_evaluation）
"""
from __future__ import annotations

from typing import Any

import pytest

from app.quality_loop.verifier.ic_20_dispatcher import (
    DelegationFailureError,
    SessionPrefixViolationError,
)
from app.quality_loop.verifier.orchestrator import (
    CallbackSchemaError,
    VerifierDeps,
    orchestrate_s5,
)
from app.quality_loop.verifier.schemas import (
    IC20Command,
    IC20DispatchResult,
    VerifierVerdict,
)
from app.quality_loop.verifier.trace_adapter import MockExecutionTrace

# ==============================================================================
# Fixtures / Fakes
# ==============================================================================


def _mk_trace(**o: Any) -> MockExecutionTrace:
    defaults: dict[str, Any] = {
        "project_id": "proj-A",
        "wp_id": "wp-1",
        "git_head": "abc1234567890",
        "blueprint_slice": {"dod_expression": "tests_pass AND coverage_ge_80", "red_tests": ["t1", "t2"]},
        "main_session_id": "main-xyz-888",
        "ts": "2026-04-23T10:00:00Z",
        "artifact_refs": ("a.py",),
        "test_report": {"passed": 10, "failed": 0, "coverage": 0.85},
        "acceptance_criteria": {"coverage_gate": 0.8},
    }
    defaults.update(o)
    return MockExecutionTrace(**defaults)


class FakeDelegator:
    def __init__(self, *, session_id: str = "sub-test-001", raise_exc: Exception | None = None) -> None:
        self.session_id = session_id
        self.raise_exc = raise_exc
        self.calls: list[IC20Command] = []

    async def delegate_verifier(self, command: IC20Command) -> IC20DispatchResult:
        self.calls.append(command)
        if self.raise_exc is not None:
            raise self.raise_exc
        return IC20DispatchResult(
            delegation_id=command.delegation_id,
            dispatched=True,
            verifier_session_id=self.session_id,
        )


class FakeCallbackWaiter:
    """可控 callback · 用于测试 verifier 回调的各种情形."""

    def __init__(
        self,
        *,
        output: dict[str, Any] | None = None,
        raise_exc: Exception | None = None,
    ) -> None:
        self.output = output
        self.raise_exc = raise_exc
        self.calls: list[dict[str, Any]] = []

    async def wait(
        self,
        *,
        delegation_id: str,
        verifier_session_id: str,
        timeout_s: int,
    ) -> dict[str, Any]:
        self.calls.append({
            "delegation_id": delegation_id,
            "verifier_session_id": verifier_session_id,
            "timeout_s": timeout_s,
        })
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.output or {}


class AuditCollector:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append((event_type, payload))


async def no_sleep(_: float) -> None:
    return None


def _verifier_output_pass() -> dict[str, Any]:
    """构造"全绿"的 verifier 回调."""
    return {
        "blueprint_alignment": {
            "dod_expression": "tests_pass AND coverage_ge_80",
            "red_tests": ["t1", "t2"],
        },
        "s4_diff_analysis": {
            "passed": 10, "failed": 0, "coverage": 0.85,
        },
        "dod_evaluation": {
            "verdict": "PASS",
            "all_pass": True,
            "gates": [{"name": "coverage", "pass": True}],
        },
        "verifier_report_id": "vr-abc123",
    }


def _make_deps(delegator: FakeDelegator, waiter: FakeCallbackWaiter, audit: AuditCollector | None = None) -> VerifierDeps:
    return VerifierDeps(
        delegator=delegator,
        callback_waiter=waiter,
        audit_emitter=audit.emit if audit else None,
        sleep=no_sleep,
    )


# ==============================================================================
# Happy path
# ==============================================================================


class TestOrchestrateS5Happy:
    """TC-L104-L206-400 · happy path PASS."""

    @pytest.mark.asyncio
    async def test_happy_returns_pass(self) -> None:
        """全绿 · 双签 OK + dod PASS → verdict=PASS."""
        trace = _mk_trace()
        delegator = FakeDelegator(session_id="sub-happy-001")
        waiter = FakeCallbackWaiter(output=_verifier_output_pass())
        deps = _make_deps(delegator, waiter)

        result = await orchestrate_s5(trace, deps)

        assert result.is_pass is True
        assert result.verdict == VerifierVerdict.PASS
        assert result.verifier_session_id == "sub-happy-001"
        assert result.project_id == "proj-A"
        assert result.delegation_id.startswith("ver-")
        assert result.verifier_report_id == "vr-abc123"
        # 双签都 OK
        assert result.signatures.both_ok is True

    @pytest.mark.asyncio
    async def test_three_segment_evidence_complete(self) -> None:
        """three_segment_evidence 含三段."""
        trace = _mk_trace()
        deps = _make_deps(FakeDelegator(), FakeCallbackWaiter(output=_verifier_output_pass()))
        result = await orchestrate_s5(trace, deps)
        ev = result.three_segment_evidence
        assert set(ev.keys()) == {"blueprint_alignment", "s4_diff_analysis", "dod_evaluation"}
        assert ev["blueprint_alignment"]["ok"] is True
        assert ev["s4_diff_analysis"]["ok"] is True
        assert ev["dod_evaluation"]["verdict"] == "PASS"

    @pytest.mark.asyncio
    async def test_audit_events_emitted(self) -> None:
        """audit 收到 orchestrate_started + report_issued."""
        trace = _mk_trace()
        audit = AuditCollector()
        deps = _make_deps(FakeDelegator(), FakeCallbackWaiter(output=_verifier_output_pass()), audit)
        await orchestrate_s5(trace, deps)
        types = [e[0] for e in audit.events]
        assert "L1-04:verifier_orchestrate_started" in types
        assert "L1-04:verifier_report_issued" in types

    @pytest.mark.asyncio
    async def test_dod_evaluation_passed_through(self) -> None:
        """dod_evaluation 原样透传到 VerifiedResult."""
        trace = _mk_trace()
        output = _verifier_output_pass()
        output["dod_evaluation"]["extra_metric"] = 42
        deps = _make_deps(FakeDelegator(), FakeCallbackWaiter(output=output))
        result = await orchestrate_s5(trace, deps)
        assert result.dod_evaluation["extra_metric"] == 42


# ==============================================================================
# 双签降级
# ==============================================================================


class TestOrchestrateSignatureDowngrade:
    """TC-L104-L206-410 · 双签失败触发 verdict 降级."""

    @pytest.mark.asyncio
    async def test_blueprint_mismatch_fail_l2(self) -> None:
        """verifier 看到的 dod_expression 与 request 不符 → FAIL_L2."""
        trace = _mk_trace()
        output = _verifier_output_pass()
        output["blueprint_alignment"]["dod_expression"] = "CHANGED_DOD"  # 污染
        deps = _make_deps(FakeDelegator(), FakeCallbackWaiter(output=output))
        result = await orchestrate_s5(trace, deps)
        assert result.verdict == VerifierVerdict.FAIL_L2
        assert result.signatures.blueprint_alignment_ok is False

    @pytest.mark.asyncio
    async def test_s4_diff_fail_l1(self) -> None:
        """verifier 跑出来的 passed 数与主声称不符 → FAIL_L1（信任坍塌）."""
        trace = _mk_trace()
        output = _verifier_output_pass()
        output["s4_diff_analysis"]["passed"] = 5  # 主声称 10 · 实测 5
        output["s4_diff_analysis"]["failed"] = 5
        deps = _make_deps(FakeDelegator(), FakeCallbackWaiter(output=output))
        result = await orchestrate_s5(trace, deps)
        assert result.verdict == VerifierVerdict.FAIL_L1
        assert result.signatures.s4_diff_analysis_ok is False

    @pytest.mark.asyncio
    async def test_s4_fail_priority_over_blueprint(self) -> None:
        """两签均失败 · s4 优先 → FAIL_L1."""
        trace = _mk_trace()
        output = _verifier_output_pass()
        output["blueprint_alignment"]["dod_expression"] = "CHANGED"
        output["s4_diff_analysis"]["passed"] = 0
        deps = _make_deps(FakeDelegator(), FakeCallbackWaiter(output=output))
        result = await orchestrate_s5(trace, deps)
        assert result.verdict == VerifierVerdict.FAIL_L1


# ==============================================================================
# DoD failure
# ==============================================================================


class TestOrchestrateDodFailure:
    """TC-L104-L206-420 · 双签 OK · DoD gate 未过阈值 → FAIL_L3."""

    @pytest.mark.asyncio
    async def test_dod_all_pass_false_fail_l3(self) -> None:
        """dod_evaluation.all_pass=False → FAIL_L3."""
        trace = _mk_trace()
        output = _verifier_output_pass()
        output["dod_evaluation"] = {
            "verdict": "FAIL_L3",
            "all_pass": False,
            "failed_gates": ["coverage"],
        }
        deps = _make_deps(FakeDelegator(), FakeCallbackWaiter(output=output))
        result = await orchestrate_s5(trace, deps)
        assert result.verdict == VerifierVerdict.FAIL_L3
        # 双签应仍为 OK
        assert result.signatures.both_ok is True

    @pytest.mark.asyncio
    async def test_dod_missing_verdict_default_fail_l3(self) -> None:
        """dod 无 verdict 且 all_pass 不是 True → default FAIL_L3."""
        trace = _mk_trace()
        output = _verifier_output_pass()
        output["dod_evaluation"] = {"gates": [{"name": "x", "pass": False}]}
        deps = _make_deps(FakeDelegator(), FakeCallbackWaiter(output=output))
        result = await orchestrate_s5(trace, deps)
        assert result.verdict == VerifierVerdict.FAIL_L3


# ==============================================================================
# IC-20 failure propagation
# ==============================================================================


class TestOrchestrateIC20Failures:
    """TC-L104-L206-430 · IC-20 失败传导（3 次失败 · 硬红线）."""

    @pytest.mark.asyncio
    async def test_three_failures_raises_delegation_error(self) -> None:
        """delegator 每次抛 500 · 3 次后 DelegationFailureError 传 up."""
        trace = _mk_trace()

        class AlwaysFailsDelegator:
            calls = 0
            async def delegate_verifier(self, command: IC20Command) -> IC20DispatchResult:
                AlwaysFailsDelegator.calls += 1
                raise RuntimeError("500 server error")

        deps = VerifierDeps(
            delegator=AlwaysFailsDelegator(),
            callback_waiter=FakeCallbackWaiter(),
            sleep=no_sleep,
        )
        with pytest.raises(DelegationFailureError) as exc:
            await orchestrate_s5(trace, deps)
        assert len(exc.value.retry_log) == 3

    @pytest.mark.asyncio
    async def test_session_prefix_hard_red_line_propagates(self) -> None:
        """delegator 返回 main.xxx · 硬红线 · SessionPrefixViolationError 直接 up."""
        trace = _mk_trace()
        delegator = FakeDelegator(session_id="main.bad-id")
        deps = _make_deps(delegator, FakeCallbackWaiter())
        with pytest.raises(SessionPrefixViolationError):
            await orchestrate_s5(trace, deps)


# ==============================================================================
# Callback timeout → FAIL_L4
# ==============================================================================


class TestOrchestrateTimeout:
    """TC-L104-L206-440 · verifier 回调超时 → FAIL_L4."""

    @pytest.mark.asyncio
    async def test_timeout_returns_fail_l4(self) -> None:
        """waiter 抛 TimeoutError · orchestrator 不 raise · 返 FAIL_L4."""
        trace = _mk_trace()
        waiter = FakeCallbackWaiter(raise_exc=TimeoutError("30 min over"))
        deps = _make_deps(FakeDelegator(), waiter)
        result = await orchestrate_s5(trace, deps)
        assert result.verdict == VerifierVerdict.FAIL_L4
        # 双签因无实际回调 · 标 false
        assert result.signatures.blueprint_alignment_ok is False
        assert result.signatures.s4_diff_analysis_ok is False

    @pytest.mark.asyncio
    async def test_timeout_three_segment_evidence_has_reason(self) -> None:
        """超时 · 三段 evidence 应含 reason=verifier_timeout."""
        trace = _mk_trace()
        waiter = FakeCallbackWaiter(raise_exc=TimeoutError())
        deps = _make_deps(FakeDelegator(), waiter)
        result = await orchestrate_s5(trace, deps)
        ev = result.three_segment_evidence
        assert ev["blueprint_alignment"]["reason"] == "verifier_timeout"
        assert ev["s4_diff_analysis"]["reason"] == "verifier_timeout"
        assert "timeout" in ev["dod_evaluation"]["status"].lower()

    @pytest.mark.asyncio
    async def test_timeout_audit_event_emitted(self) -> None:
        """超时 · audit 收到 verifier_timeout."""
        trace = _mk_trace()
        waiter = FakeCallbackWaiter(raise_exc=TimeoutError())
        audit = AuditCollector()
        deps = _make_deps(FakeDelegator(), waiter, audit)
        await orchestrate_s5(trace, deps)
        types = [e[0] for e in audit.events]
        assert "L1-04:verifier_timeout" in types


# ==============================================================================
# Schema error
# ==============================================================================


class TestOrchestrateCallbackSchema:
    """TC-L104-L206-450 · verifier 回调 schema 违反."""

    @pytest.mark.asyncio
    async def test_missing_dod_evaluation_raises(self) -> None:
        """缺 dod_evaluation · CallbackSchemaError."""
        trace = _mk_trace()
        output = _verifier_output_pass()
        del output["dod_evaluation"]
        deps = _make_deps(FakeDelegator(), FakeCallbackWaiter(output=output))
        with pytest.raises(CallbackSchemaError) as exc:
            await orchestrate_s5(trace, deps)
        assert "E19" in str(exc.value)

    @pytest.mark.asyncio
    async def test_missing_blueprint_alignment_raises(self) -> None:
        """缺 blueprint_alignment · CallbackSchemaError."""
        trace = _mk_trace()
        output = _verifier_output_pass()
        del output["blueprint_alignment"]
        deps = _make_deps(FakeDelegator(), FakeCallbackWaiter(output=output))
        with pytest.raises(CallbackSchemaError):
            await orchestrate_s5(trace, deps)

    @pytest.mark.asyncio
    async def test_non_dict_output_raises(self) -> None:
        """verifier 回调不是 dict · CallbackSchemaError."""
        trace = _mk_trace()

        class BadWaiter:
            async def wait(self, **_: Any) -> Any:
                return "not a dict"  # type: ignore[return-value]

        deps = VerifierDeps(
            delegator=FakeDelegator(),
            callback_waiter=BadWaiter(),
            sleep=no_sleep,
        )
        with pytest.raises(CallbackSchemaError):
            await orchestrate_s5(trace, deps)


# ==============================================================================
# PM-14 透传
# ==============================================================================


class TestOrchestratePM14:
    """TC-L104-L206-460 · PM-14 · project_id 全链路透传."""

    @pytest.mark.asyncio
    async def test_project_id_transparent(self) -> None:
        """trace.project_id=X · delegator 收到的 command.project_id=X · result.project_id=X."""
        trace = _mk_trace(project_id="proj-custom-pid")
        delegator = FakeDelegator()
        deps = _make_deps(delegator, FakeCallbackWaiter(output=_verifier_output_pass()))
        result = await orchestrate_s5(trace, deps)
        assert result.project_id == "proj-custom-pid"
        assert delegator.calls[0].project_id == "proj-custom-pid"

    @pytest.mark.asyncio
    async def test_project_id_in_audit_events(self) -> None:
        """audit payload.project_id 一致."""
        trace = _mk_trace(project_id="proj-audit")
        audit = AuditCollector()
        deps = _make_deps(FakeDelegator(), FakeCallbackWaiter(output=_verifier_output_pass()), audit)
        await orchestrate_s5(trace, deps)
        for ev_type, payload in audit.events:
            assert payload.get("project_id") == "proj-audit", (ev_type, payload)


# ==============================================================================
# Delegation ID 幂等
# ==============================================================================


class TestOrchestrateDelegationId:
    """TC-L104-L206-470 · delegation_id 幂等支持."""

    @pytest.mark.asyncio
    async def test_external_delegation_id_used(self) -> None:
        """外部指定 delegation_id · 全链路复用."""
        trace = _mk_trace()
        delegator = FakeDelegator()
        deps = _make_deps(delegator, FakeCallbackWaiter(output=_verifier_output_pass()))
        result = await orchestrate_s5(trace, deps, delegation_id="ver-idempotent-key-1")
        assert result.delegation_id == "ver-idempotent-key-1"
        assert delegator.calls[0].delegation_id == "ver-idempotent-key-1"

    @pytest.mark.asyncio
    async def test_auto_delegation_id_unique_per_run(self) -> None:
        """不指定 · 每次 uuid 生成 · 不同."""
        trace = _mk_trace()
        deps1 = _make_deps(FakeDelegator(), FakeCallbackWaiter(output=_verifier_output_pass()))
        deps2 = _make_deps(FakeDelegator(), FakeCallbackWaiter(output=_verifier_output_pass()))
        r1 = await orchestrate_s5(trace, deps1)
        r2 = await orchestrate_s5(trace, deps2)
        assert r1.delegation_id != r2.delegation_id


# ==============================================================================
# Callback waiter 参数透传
# ==============================================================================


class TestCallbackWaiterArgs:
    """TC-L104-L206-480 · waiter 收到正确的 delegation_id + session_id + timeout_s."""

    @pytest.mark.asyncio
    async def test_waiter_receives_correct_args(self) -> None:
        """waiter 收到 trace.timeout_s (from request.timeout_s default) + session_id."""
        trace = _mk_trace()
        waiter = FakeCallbackWaiter(output=_verifier_output_pass())
        deps = _make_deps(FakeDelegator(session_id="sub-correct-001"), waiter)
        await orchestrate_s5(trace, deps, delegation_id="ver-arg-test")
        assert len(waiter.calls) == 1
        call = waiter.calls[0]
        assert call["delegation_id"] == "ver-arg-test"
        assert call["verifier_session_id"] == "sub-correct-001"
        # default timeout_s=1200 from VerificationRequest
        assert call["timeout_s"] == 1200
