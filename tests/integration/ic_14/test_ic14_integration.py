"""IC-14 · stage_gate_verdict (verifier orchestrate) 集成测试 · 5 TC.

(WP04 任务表 IC-14 重映射 = main-1 L1-04 quality_loop verifier orchestrator)

覆盖:
    TC-1 PASS · 端到端 trace → orchestrate → verdict=PASS
    TC-2 BLOCK (FAIL_L4) · waiter timeout → verdict=FAIL_L4
    TC-3 INCONCLUSIVE (FAIL_L3) · DoD gate 不过 → verdict=FAIL_L3
    TC-4 重试 · IC-20 dispatch 1 次失败 + 第 2 次成功 → 最终 PASS
    TC-5 SLO · orchestrate 整体 ≤ 1000ms (mock 路径远低)
"""
from __future__ import annotations

import asyncio
import time

import pytest

from app.quality_loop.verifier.orchestrator import VerifierDeps, orchestrate_s5
from app.quality_loop.verifier.schemas import (
    IC20DispatchResult,
    VerifierVerdict,
)

from .conftest import (
    ControlledDelegator,
    ControlledWaiter,
    InMemoryAuditEmitter,
    no_sleep,
    out_fail_l3_dod_unmet,
    out_pass,
)


def run_async(coro):
    return asyncio.run(coro)


class TestIC14Integration:
    """IC-14 集成 · L1-04 verifier orchestrate_s5."""

    # ---- TC-1 · PASS · 端到端 ----
    def test_end_to_end_pass(
        self, make_trace, delegator: ControlledDelegator, audit_emitter,
    ) -> None:
        trace = make_trace()
        waiter = ControlledWaiter(output=out_pass())
        deps = VerifierDeps(
            delegator=delegator,
            callback_waiter=waiter,
            audit_emitter=audit_emitter,
            sleep=no_sleep,
        )

        result = run_async(orchestrate_s5(trace, deps))

        assert result.verdict == VerifierVerdict.PASS
        # IC-14 §3.14 三段证据全 (blueprint + s4_diff + dod)
        assert "blueprint_alignment" in result.three_segment_evidence
        assert "s4_diff_analysis" in result.three_segment_evidence
        assert "dod_evaluation" in result.three_segment_evidence
        # IC-20 被调 1 次
        assert len(delegator.calls) == 1
        # waiter 1 次
        assert len(waiter.calls) == 1

    # ---- TC-2 · BLOCK (timeout → FAIL_L4) ----
    def test_callback_timeout_returns_fail_l4(
        self, make_trace, delegator: ControlledDelegator, audit_emitter,
    ) -> None:
        trace = make_trace()
        waiter = ControlledWaiter(exc=TimeoutError("verifier timeout"))
        deps = VerifierDeps(
            delegator=delegator,
            callback_waiter=waiter,
            audit_emitter=audit_emitter,
            sleep=no_sleep,
        )

        result = run_async(orchestrate_s5(trace, deps))

        # IC-14 §3.14 timeout 降级 verdict=FAIL_L4 (BLOCK 级)
        assert result.verdict == VerifierVerdict.FAIL_L4
        # 至少 1 次 dispatch (waiter 才会被调用)
        assert len(delegator.calls) >= 1

    # ---- TC-3 · INCONCLUSIVE (FAIL_L3 · DoD gate 不过) ----
    def test_dod_unmet_returns_fail_l3(
        self, make_trace, delegator: ControlledDelegator, audit_emitter,
    ) -> None:
        trace = make_trace(coverage=0.65, coverage_gate=0.8)
        waiter = ControlledWaiter(output=out_fail_l3_dod_unmet())
        deps = VerifierDeps(
            delegator=delegator,
            callback_waiter=waiter,
            audit_emitter=audit_emitter,
            sleep=no_sleep,
        )

        result = run_async(orchestrate_s5(trace, deps))

        # 调用方 DoD 评估 verdict 是 FAIL_L3 → 最终 verdict 也是 FAIL_L3 (no downgrade upgrade)
        assert result.verdict == VerifierVerdict.FAIL_L3
        assert "dod_evaluation" in result.three_segment_evidence

    # ---- TC-4 · 重试: IC-20 dispatch 1 次失败 → 第 2 次成功 ----
    def test_retry_succeeds_on_second_dispatch(
        self, make_trace, audit_emitter,
    ) -> None:
        # 第 1 次返 dispatched=False (触发 retry) · 第 2 次成功
        delegator = ControlledDelegator(queue=[
            IC20DispatchResult(
                delegation_id="ver-retry",
                dispatched=False,
                verifier_session_id=None,
            ),
            IC20DispatchResult(
                delegation_id="ver-retry",
                dispatched=True,
                verifier_session_id="sub-retry-002",
            ),
        ])
        waiter = ControlledWaiter(output=out_pass())
        deps = VerifierDeps(
            delegator=delegator,
            callback_waiter=waiter,
            audit_emitter=audit_emitter,
            sleep=no_sleep,
        )

        result = run_async(orchestrate_s5(trace=make_trace(), deps=deps))

        # 重试后成功 · verdict=PASS
        assert result.verdict == VerifierVerdict.PASS
        # delegator 至少调用 2 次
        assert len(delegator.calls) >= 2

    # ---- TC-5 · SLO orchestrate ≤ 1000ms (mock 路径) ----
    def test_slo_orchestrate_under_1s(
        self, make_trace, delegator: ControlledDelegator, audit_emitter,
    ) -> None:
        trace = make_trace()
        waiter = ControlledWaiter(output=out_pass())
        deps = VerifierDeps(
            delegator=delegator,
            callback_waiter=waiter,
            audit_emitter=audit_emitter,
            sleep=no_sleep,
        )

        t0 = time.perf_counter()
        result = run_async(orchestrate_s5(trace, deps))
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert result.verdict == VerifierVerdict.PASS
        # IC-14 mock 路径 SLO · 不应超 1s
        assert elapsed_ms < 1000.0, f"IC-14 orchestrate 超时 {elapsed_ms:.1f}ms"
