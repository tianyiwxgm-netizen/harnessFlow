"""TC-L104-L206 · 集成场景 · trace → orchestrator → VerifiedResult 端到端.

核心 TC：
- 集成 · WP05 mock trace → orchestrate → PASS
- 集成 · 主声称 10 pass 但 verifier 实测 8 pass → FAIL_L1
- 集成 · verifier 被污染用错蓝图 → FAIL_L2
- 集成 · DoD coverage gate 未过 → FAIL_L3
- 集成 · IC-20 限流 429 3 次 → DelegationFailureError
- 集成 · verifier 跑超时（waiter 抛 TimeoutError）→ FAIL_L4
- 集成 · audit emitter 收所有事件（started + dispatched + report_issued）
- 边界 · audit emitter 抛异常 · 不阻塞主路径
- 边界 · delegator 抛 spawn 错误 · 错误分类归 subagent_spawn_failure
"""
from __future__ import annotations

from typing import Any

import pytest

from app.quality_loop.verifier.ic_20_dispatcher import DelegationFailureError
from app.quality_loop.verifier.orchestrator import (
    VerifierDeps,
    orchestrate_s5,
)
from app.quality_loop.verifier.schemas import (
    IC20Command,
    IC20DispatchResult,
    VerifierVerdict,
)
from app.quality_loop.verifier.trace_adapter import MockExecutionTrace


def _mk_trace(**o: Any) -> MockExecutionTrace:
    defaults: dict[str, Any] = {
        "project_id": "proj-int",
        "wp_id": "wp-int-1",
        "git_head": "int1234567",
        "blueprint_slice": {"dod_expression": "tests_pass", "red_tests": ["r1"]},
        "main_session_id": "main-int",
        "ts": "2026-04-23T10:00:00Z",
        "artifact_refs": ("app/feature.py",),
        "test_report": {"passed": 10, "failed": 0, "coverage": 0.85},
        "acceptance_criteria": {"coverage_gate": 0.8},
    }
    defaults.update(o)
    return MockExecutionTrace(**defaults)


class NoSleep:
    async def __call__(self, _: float) -> None:
        return None


async def no_sleep(_: float) -> None:
    return None


class InMemoryAuditEmitter:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append((event_type, dict(payload)))


class ControlledDelegator:
    """可配置的 delegator · 支持多次调用不同行为."""

    def __init__(self, *, queue: list[Any]) -> None:
        self.queue = queue  # list of (IC20DispatchResult | Exception)
        self.calls: list[IC20Command] = []

    async def delegate_verifier(self, command: IC20Command) -> IC20DispatchResult:
        self.calls.append(command)
        idx = len(self.calls) - 1
        if idx < len(self.queue):
            b = self.queue[idx]
            if isinstance(b, Exception):
                raise b
            return b
        # 超出 · 给默认 dispatched=True
        return IC20DispatchResult(
            delegation_id=command.delegation_id,
            dispatched=True,
            verifier_session_id="sub-default",
        )


class ControlledWaiter:
    def __init__(self, *, output: dict[str, Any] | None = None, exc: Exception | None = None) -> None:
        self.output = output
        self.exc = exc
        self.calls: list[dict[str, Any]] = []

    async def wait(self, *, delegation_id: str, verifier_session_id: str, timeout_s: int) -> dict[str, Any]:
        self.calls.append({
            "delegation_id": delegation_id,
            "verifier_session_id": verifier_session_id,
            "timeout_s": timeout_s,
        })
        if self.exc is not None:
            raise self.exc
        return self.output or {}


def _out_pass() -> dict[str, Any]:
    return {
        "blueprint_alignment": {"dod_expression": "tests_pass", "red_tests": ["r1"]},
        "s4_diff_analysis": {"passed": 10, "failed": 0, "coverage": 0.85},
        "dod_evaluation": {"verdict": "PASS", "all_pass": True},
        "verifier_report_id": "vr-int-001",
    }


# ==============================================================================
# 集成
# ==============================================================================


class TestIntegrationHappy:
    """TC-L104-L206-500 · 集成 happy · WP05 mock → orchestrate → PASS."""

    @pytest.mark.asyncio
    async def test_end_to_end_pass(self) -> None:
        trace = _mk_trace()
        delegator = ControlledDelegator(queue=[
            IC20DispatchResult(delegation_id="ver-e2e", dispatched=True, verifier_session_id="sub-e2e-001"),
        ])
        waiter = ControlledWaiter(output=_out_pass())
        audit = InMemoryAuditEmitter()
        deps = VerifierDeps(
            delegator=delegator,
            callback_waiter=waiter,
            audit_emitter=audit.emit,
            sleep=no_sleep,
        )
        result = await orchestrate_s5(trace, deps, delegation_id="ver-e2e")
        assert result.verdict == VerifierVerdict.PASS
        assert result.verifier_session_id == "sub-e2e-001"
        assert result.verifier_report_id == "vr-int-001"
        # audit 事件齐
        types = [e[0] for e in audit.events]
        assert "L1-04:verifier_orchestrate_started" in types
        assert "L1-04:verifier_delegation_dispatched" in types
        assert "L1-04:verifier_report_issued" in types

    @pytest.mark.asyncio
    async def test_audit_all_have_project_id(self) -> None:
        """所有 audit payload 根 project_id 统一."""
        trace = _mk_trace(project_id="proj-strict-pm14")
        audit = InMemoryAuditEmitter()
        deps = VerifierDeps(
            delegator=ControlledDelegator(queue=[
                IC20DispatchResult(delegation_id="ver-pm14", dispatched=True, verifier_session_id="sub-1"),
            ]),
            callback_waiter=ControlledWaiter(output=_out_pass()),
            audit_emitter=audit.emit,
            sleep=no_sleep,
        )
        await orchestrate_s5(trace, deps, delegation_id="ver-pm14")
        for ev_type, payload in audit.events:
            assert payload.get("project_id") == "proj-strict-pm14", (ev_type, payload)


class TestIntegrationFailL1TrustCollapse:
    """TC-L104-L206-510 · 信任坍塌：主声称 10 pass · 实测 8 pass → FAIL_L1."""

    @pytest.mark.asyncio
    async def test_main_claims_10_verifier_actual_8(self) -> None:
        trace = _mk_trace(test_report={"passed": 10, "failed": 0, "coverage": 0.85})
        output = _out_pass()
        output["s4_diff_analysis"] = {"passed": 8, "failed": 2, "coverage": 0.85}
        deps = VerifierDeps(
            delegator=ControlledDelegator(queue=[
                IC20DispatchResult(delegation_id="ver-f1", dispatched=True, verifier_session_id="sub-f1"),
            ]),
            callback_waiter=ControlledWaiter(output=output),
            sleep=no_sleep,
        )
        result = await orchestrate_s5(trace, deps)
        assert result.verdict == VerifierVerdict.FAIL_L1
        assert result.signatures.s4_diff_analysis_ok is False
        # evidence 含实际 diff
        diff = result.three_segment_evidence["s4_diff_analysis"]["diff"]
        assert any(d["field"] == "passed" for d in diff)


class TestIntegrationFailL2BlueprintPoisoned:
    """TC-L104-L206-520 · verifier 被污染用错蓝图 → FAIL_L2."""

    @pytest.mark.asyncio
    async def test_verifier_observes_wrong_blueprint(self) -> None:
        trace = _mk_trace()
        output = _out_pass()
        output["blueprint_alignment"]["dod_expression"] = "POISONED_DOD"  # 被注入
        deps = VerifierDeps(
            delegator=ControlledDelegator(queue=[
                IC20DispatchResult(delegation_id="ver-f2", dispatched=True, verifier_session_id="sub-f2"),
            ]),
            callback_waiter=ControlledWaiter(output=output),
            sleep=no_sleep,
        )
        result = await orchestrate_s5(trace, deps)
        assert result.verdict == VerifierVerdict.FAIL_L2
        assert result.signatures.blueprint_alignment_ok is False


class TestIntegrationFailL3DoDBreach:
    """TC-L104-L206-530 · DoD coverage gate 未过 → FAIL_L3."""

    @pytest.mark.asyncio
    async def test_dod_coverage_breach(self) -> None:
        trace = _mk_trace(test_report={"passed": 10, "failed": 0, "coverage": 0.70})
        output = _out_pass()
        output["s4_diff_analysis"] = {"passed": 10, "failed": 0, "coverage": 0.70}
        output["dod_evaluation"] = {
            "verdict": "FAIL_L3",
            "all_pass": False,
            "failed_gates": ["coverage_ge_80"],
        }
        deps = VerifierDeps(
            delegator=ControlledDelegator(queue=[
                IC20DispatchResult(delegation_id="ver-f3", dispatched=True, verifier_session_id="sub-f3"),
            ]),
            callback_waiter=ControlledWaiter(output=output),
            sleep=no_sleep,
        )
        result = await orchestrate_s5(trace, deps)
        assert result.verdict == VerifierVerdict.FAIL_L3
        assert result.signatures.both_ok is True  # 双签没问题
        assert result.dod_evaluation["failed_gates"] == ["coverage_ge_80"]


class TestIntegrationIC20RateLimit:
    """TC-L104-L206-540 · 限流 429 3 次 → DelegationFailureError."""

    @pytest.mark.asyncio
    async def test_three_429_raises_delegation_failure(self) -> None:
        trace = _mk_trace()
        delegator = ControlledDelegator(queue=[
            RuntimeError("429 rate limit"),
            RuntimeError("429 rate limit"),
            RuntimeError("429 rate limit"),
        ])
        deps = VerifierDeps(
            delegator=delegator,
            callback_waiter=ControlledWaiter(output=_out_pass()),
            sleep=no_sleep,
        )
        with pytest.raises(DelegationFailureError) as exc:
            await orchestrate_s5(trace, deps)
        # retry_log 含 3 次 rate_limit
        outcomes = [log["outcome"] for log in exc.value.retry_log]
        assert outcomes == ["ic_20_api_rate_limit", "ic_20_api_rate_limit", "ic_20_api_rate_limit"]


class TestIntegrationTimeoutFailL4:
    """TC-L104-L206-550 · verifier 30min 超时 → FAIL_L4."""

    @pytest.mark.asyncio
    async def test_timeout_propagates_to_fail_l4(self) -> None:
        trace = _mk_trace()
        deps = VerifierDeps(
            delegator=ControlledDelegator(queue=[
                IC20DispatchResult(delegation_id="ver-f4", dispatched=True, verifier_session_id="sub-f4"),
            ]),
            callback_waiter=ControlledWaiter(exc=TimeoutError("verifier 30min timeout")),
            sleep=no_sleep,
        )
        result = await orchestrate_s5(trace, deps)
        assert result.verdict == VerifierVerdict.FAIL_L4
        assert result.verifier_session_id == "sub-f4"


class TestIntegrationAuditResilient:
    """TC-L104-L206-560 · audit emitter 抛异常 · 不阻塞主路径."""

    @pytest.mark.asyncio
    async def test_audit_emitter_raises_does_not_break_flow(self) -> None:
        trace = _mk_trace()

        class BrokenAudit:
            async def emit(self, event_type: str, payload: dict[str, Any]) -> None:
                raise RuntimeError("audit broken")

        broken = BrokenAudit()
        deps = VerifierDeps(
            delegator=ControlledDelegator(queue=[
                IC20DispatchResult(delegation_id="ver-audit", dispatched=True, verifier_session_id="sub-audit-1"),
            ]),
            callback_waiter=ControlledWaiter(output=_out_pass()),
            audit_emitter=broken.emit,
            sleep=no_sleep,
        )
        # 应该正常完成 · 不 raise
        result = await orchestrate_s5(trace, deps)
        assert result.verdict == VerifierVerdict.PASS

    @pytest.mark.asyncio
    async def test_sync_audit_emitter_also_works(self) -> None:
        """audit emitter 非 async · 也应支持."""
        trace = _mk_trace()
        calls: list[str] = []

        def sync_emit(event_type: str, payload: dict[str, Any]) -> None:
            calls.append(event_type)

        deps = VerifierDeps(
            delegator=ControlledDelegator(queue=[
                IC20DispatchResult(delegation_id="ver-sync", dispatched=True, verifier_session_id="sub-sync-1"),
            ]),
            callback_waiter=ControlledWaiter(output=_out_pass()),
            audit_emitter=sync_emit,  # sync callable
            sleep=no_sleep,
        )
        result = await orchestrate_s5(trace, deps)
        assert result.verdict == VerifierVerdict.PASS
        assert "L1-04:verifier_report_issued" in calls


class TestIntegrationErrorClassification:
    """TC-L104-L206-570 · 错误分类边界."""

    @pytest.mark.asyncio
    async def test_spawn_error_classified(self) -> None:
        """L1-05 起 session 失败 · 归 subagent_spawn_failure."""
        trace = _mk_trace()
        delegator = ControlledDelegator(queue=[
            RuntimeError("failed to spawn subagent process"),
            RuntimeError("failed to spawn subagent process"),
            RuntimeError("failed to spawn subagent process"),
        ])
        deps = VerifierDeps(
            delegator=delegator,
            callback_waiter=ControlledWaiter(output=_out_pass()),
            sleep=no_sleep,
        )
        with pytest.raises(DelegationFailureError) as exc:
            await orchestrate_s5(trace, deps)
        outcomes = [log["outcome"] for log in exc.value.retry_log]
        assert all(o == "subagent_spawn_failure" for o in outcomes)

    @pytest.mark.asyncio
    async def test_timeout_error_classified(self) -> None:
        """delegator 抛 TimeoutError · 归 timeout · 仍重试."""
        trace = _mk_trace()
        delegator = ControlledDelegator(queue=[
            TimeoutError("ic_20 call timeout"),
            TimeoutError("ic_20 call timeout"),
            TimeoutError("ic_20 call timeout"),
        ])
        deps = VerifierDeps(
            delegator=delegator,
            callback_waiter=ControlledWaiter(output=_out_pass()),
            sleep=no_sleep,
        )
        with pytest.raises(DelegationFailureError) as exc:
            await orchestrate_s5(trace, deps)
        outcomes = [log["outcome"] for log in exc.value.retry_log]
        assert all(o == "timeout" for o in outcomes)


class TestIntegrationDuration:
    """TC-L104-L206-580 · duration_ms 合理范围（mock · 非 perf SLO）."""

    @pytest.mark.asyncio
    async def test_duration_ms_set(self) -> None:
        """result.duration_ms 应为正整数."""
        trace = _mk_trace()
        deps = VerifierDeps(
            delegator=ControlledDelegator(queue=[
                IC20DispatchResult(delegation_id="ver-dur", dispatched=True, verifier_session_id="sub-dur"),
            ]),
            callback_waiter=ControlledWaiter(output=_out_pass()),
            sleep=no_sleep,
        )
        result = await orchestrate_s5(trace, deps)
        assert result.duration_ms >= 0
