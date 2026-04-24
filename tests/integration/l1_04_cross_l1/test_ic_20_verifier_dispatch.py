"""WP09-03 · IC-20 生产端 · L1-04 Verifier → L1-05 delegate_verifier.

**契约链**:
1. L1-04 orchestrate_s5 · trace_adapter → `VerificationRequest`
2. `build_ic_20_command(request)` → `IC20Command` payload (§3.20.2)
3. 通过 `DelegateVerifierProtocol` → L1-05 真实 IC-20 delegator (Dev-γ merged)
4. L1-05 分配 `sub-{uuid}` 独立 session id · 校验硬红线 PM-03
5. verifier 独立 session 跑完 → 通过 callback_waiter 回三段证据
6. orchestrator 组装 `VerifiedResult` · 同时 emit IC-09 审计

**硬校验**:
- IC20Command 所有必填字段对齐 `ic-contracts.md §3.20.2`
- `verifier_session_id` 必 sub- 前缀（PM-03 硬红线）
- session_id 不等于 main_session_id (L2-06 §6.7)
- 3 次重试耗尽 · 触发 DelegationFailureError (L2-06 §6.4)
"""
from __future__ import annotations

import pytest

from app.quality_loop.verifier.ic_20_dispatcher import (
    DelegationFailureError,
    SessionPrefixViolationError,
    build_ic_20_command,
)
from app.quality_loop.verifier.orchestrator import VerifierDeps, orchestrate_s5
from app.quality_loop.verifier.schemas import (
    IC20Command,
    IC20DispatchResult,
    VerifierVerdict,
)
from app.quality_loop.verifier.trace_adapter import adapt_from_s4


# ==============================================================================
# TC-1 · IC-20 command payload 字段级对齐
# ==============================================================================


class TestIC20CommandBuild:
    """build_ic_20_command 纯函数 · 字段对齐 §3.20.2."""

    def test_command_schema_complete_fields(self, make_trace) -> None:
        """所有 IC-20 必填字段齐 + allowed_tools 白名单."""
        trace = make_trace()
        request = adapt_from_s4(trace)
        cmd = build_ic_20_command(request)

        assert isinstance(cmd, IC20Command)
        # PM-14
        assert cmd.project_id == trace.project_id
        # 必填 IC-20 §3.20.2
        assert cmd.delegation_id.startswith("ver-")
        assert cmd.wp_id == trace.wp_id
        assert "dod_expression" in cmd.blueprint_slice
        assert cmd.s4_snapshot["git_head"] == trace.git_head
        assert list(cmd.s4_snapshot["artifact_refs"]) == list(trace.artifact_refs)
        assert cmd.acceptance_criteria == dict(trace.acceptance_criteria)
        # allowed_tools 默认白名单（read-only · verifier session 不改代码）
        assert set(cmd.allowed_tools) == {"Read", "Glob", "Grep", "Bash"}
        assert cmd.timeout_s == 1200


# ==============================================================================
# TC-2 · 正向 · delegate_verifier 返 sub- 合法 session → 3 段证据组装
# ==============================================================================


class TestIC20DispatchHappy:
    async def test_dispatch_pass_verdict(
        self,
        make_trace,
        delegate_stub,
        pass_verifier_output,
        no_sleep,
    ) -> None:
        """IC-20 派发成功 · verifier 回 PASS · 三段证据齐."""
        from tests.integration.l1_04_cross_l1.conftest import CallbackWaiterStub

        waiter = CallbackWaiterStub(output=pass_verifier_output)
        deps = VerifierDeps(
            delegator=delegate_stub,
            callback_waiter=waiter,
            audit_emitter=None,
            sleep=no_sleep,
        )
        result = await orchestrate_s5(make_trace(), deps)

        # delegator 被调用 1 次 · command 字段齐
        assert len(delegate_stub.calls) == 1
        cmd = delegate_stub.calls[0]
        assert cmd.project_id == "proj-wp09"
        assert cmd.wp_id == "wp-int-1"
        # session_id 合法 sub- 前缀
        assert result.verifier_session_id is not None
        assert result.verifier_session_id.startswith("sub-")
        # 三段证据齐
        assert set(result.three_segment_evidence.keys()) == {
            "blueprint_alignment",
            "s4_diff_analysis",
            "dod_evaluation",
        }
        assert result.verdict == VerifierVerdict.PASS


# ==============================================================================
# TC-3 · session_id 前缀硬红线（PM-03）
# ==============================================================================


class TestIC20SessionPrefixRedLine:
    """PM-03 硬红线: verifier_session_id 必须 sub- 前缀 · 不得等 main_session_id."""

    async def test_main_prefix_rejected_as_red_line(
        self,
        make_trace,
        no_sleep,
    ) -> None:
        """delegator 返 main. 前缀 session_id → SessionPrefixViolationError."""
        from tests.integration.l1_04_cross_l1.conftest import CallbackWaiterStub

        # 创建一个故意返 main. 前缀的 delegator
        class _BadPrefixDelegator:
            def __init__(self) -> None:
                self.calls = []

            async def delegate_verifier(self, command: IC20Command) -> IC20DispatchResult:
                self.calls.append(command)
                return IC20DispatchResult(
                    delegation_id=command.delegation_id,
                    dispatched=True,
                    verifier_session_id="main.bad-prefix",  # ← 硬红线违反
                )

        waiter = CallbackWaiterStub(output={})
        deps = VerifierDeps(
            delegator=_BadPrefixDelegator(),
            callback_waiter=waiter,
            audit_emitter=None,
            sleep=no_sleep,
        )
        with pytest.raises(SessionPrefixViolationError):
            await orchestrate_s5(make_trace(), deps)


# ==============================================================================
# TC-4 · 3 次重试耗尽 · DelegationFailureError
# ==============================================================================


class TestIC20RetryExhaustion:
    """L2-06 §6.4 · max_retries 硬锁 3 · 3 次失败后抛 DelegationFailureError."""

    async def test_three_api_errors_exhaust_retries(
        self,
        make_trace,
        delegate_stub,
        no_sleep,
    ) -> None:
        """3 次 API 5xx 后 · DelegationFailureError 带 retry_log."""
        from tests.integration.l1_04_cross_l1.conftest import CallbackWaiterStub

        # 配 3 次异常 · 每次模拟 5xx API 错误
        delegate_stub.error_queue = [
            RuntimeError("500 server error"),
            RuntimeError("500 server error"),
            RuntimeError("500 server error"),
        ]
        waiter = CallbackWaiterStub(output={})
        deps = VerifierDeps(
            delegator=delegate_stub,
            callback_waiter=waiter,
            audit_emitter=None,
            sleep=no_sleep,
        )
        with pytest.raises(DelegationFailureError) as exc_info:
            await orchestrate_s5(make_trace(), deps)
        assert len(exc_info.value.retry_log) == 3
        # 每次都归 ic_20_api_error
        outcomes = [log["outcome"] for log in exc_info.value.retry_log]
        assert all(o == "ic_20_api_error" for o in outcomes)


# ==============================================================================
# TC-5 · FAIL_L3 · 双签 OK · DoD gate 未过 → 质量回退
# ==============================================================================


class TestIC20FailL3Pipeline:
    """FAIL_L3 触发 L1-04 → L1-07 → L1-04 RollbackRouter 回路的上半段.

    本 TC 仅验证 Verifier 正确产 FAIL_L3 · RollbackRouter consume 已由
    test_ic_14_rollback_consume.py 覆盖.
    """

    async def test_coverage_breach_produces_fail_l3(
        self,
        make_trace,
        delegate_stub,
        fail_l3_verifier_output,
        no_sleep,
    ) -> None:
        from tests.integration.l1_04_cross_l1.conftest import CallbackWaiterStub

        trace = make_trace(test_report={"passed": 10, "failed": 0, "coverage": 0.60})
        waiter = CallbackWaiterStub(output=fail_l3_verifier_output)
        deps = VerifierDeps(
            delegator=delegate_stub,
            callback_waiter=waiter,
            audit_emitter=None,
            sleep=no_sleep,
        )
        result = await orchestrate_s5(trace, deps)
        assert result.verdict == VerifierVerdict.FAIL_L3
        # 双签都 OK · 仅 DoD 层 fail
        assert result.signatures.both_ok is True
        # dod_evaluation 说明失败 gate
        assert result.dod_evaluation.get("failed_gates") == ["coverage_ge_80"]
