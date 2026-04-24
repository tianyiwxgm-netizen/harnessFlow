"""WP08 · e2e · 场景 3 · S4Driver Trace → Verifier.orchestrate_s5 → IC-20 command 全链.

覆盖 WP05 (L2-05 S4Driver) → WP06 (L2-06 Verifier) · 含 IC-20 delegate_verifier 生产端。

**验证点**:
- WP05 drive_s4 产 ExecutionTrace(真实 state/attempts/metric)
- 把 S4 ExecutionTrace 转 WP06 verifier 所需的 ExecutionTraceLike
- WP06 orchestrate_s5 → IC-20 dispatch + 双签 + VerifiedResult
- verdict 5 档枚举(PASS / FAIL_L1 / FAIL_L2 / FAIL_L3 / FAIL_L4)全链对齐
- IC-20 session_id 前缀硬锁(PM-03)

**铁律**:
- WP05 真实 S4Driver(stub runner + mock skill bridge 降级)
- WP06 真实 orchestrate_s5(mock L1-05 delegator + callback waiter)
- 三个 L2 边界无 mock(trace 适配 · 签名校验 · verdict 降级)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.quality_loop.s4_driver.driver import Clock, DriverConfig, S4Driver
from app.quality_loop.s4_driver.metric_collector import MetricCollector
from app.quality_loop.s4_driver.schemas import (
    DriverState,
    ExecutionTrace,
    WPExecutionInput,
)
from app.quality_loop.s4_driver.subagent_dispatcher import (
    MockSkillBridge,
    SubagentDispatcher,
)
from app.quality_loop.s4_driver.test_runner import StubTestExecutor, TestRunner
from app.quality_loop.verifier.orchestrator import VerifierDeps, orchestrate_s5
from app.quality_loop.verifier.schemas import (
    IC20Command,
    IC20DispatchResult,
    VerifierVerdict,
)
from app.quality_loop.verifier.trace_adapter import MockExecutionTrace


# =============================================================================
# 桥接 S4 ExecutionTrace → verifier.trace_adapter.ExecutionTraceLike
# =============================================================================


def _bridge_s4_trace(
    s4_trace: ExecutionTrace,
    *,
    git_head: str,
    blueprint_slice: dict[str, Any],
    main_session_id: str,
    acceptance_criteria: dict[str, Any] | None = None,
) -> MockExecutionTrace:
    """把 WP05 S4 ExecutionTrace → WP06 ExecutionTraceLike(兼容鸭子类型).

    这是本集成测试的核心桥接点 · 确保 WP05/WP06 两侧 VO 字段级对齐。
    WP05 的 metric 字段含 test_pass_ratio → WP06 test_report。
    """
    if s4_trace.metric is not None:
        total = len(s4_trace.attempts[-1].cases) if s4_trace.attempts else 0
        passed = int(s4_trace.metric.test_pass_ratio * total) if total else 0
        failed = total - passed
        test_report = {
            "passed": passed,
            "failed": failed,
            "coverage": s4_trace.metric.coverage_pct,
        }
    else:
        test_report = {"passed": 0, "failed": 0, "coverage": 0.0}

    return MockExecutionTrace(
        project_id=s4_trace.project_id,
        wp_id=s4_trace.wp_id,
        git_head=git_head,
        blueprint_slice=blueprint_slice,
        main_session_id=main_session_id,
        ts=s4_trace.ended_at or s4_trace.started_at or "2026-04-23T10:00:00Z",
        artifact_refs=tuple(f"projects/{s4_trace.project_id}/workspaces/{s4_trace.wp_id}/output.py"
                            for _ in range(1)),
        test_report=test_report,
        acceptance_criteria=dict(acceptance_criteria or {}),
    )


# =============================================================================
# Mock L1-05 delegator / waiter (WP06 外部依赖 · 被允许 mock)
# =============================================================================


class QueueDelegator:
    """可配置的 delegate_verifier · 按队列返结果/异常."""

    def __init__(self, *, queue: list[Any]) -> None:
        self.queue = queue
        self.calls: list[IC20Command] = []

    async def delegate_verifier(self, command: IC20Command) -> IC20DispatchResult:
        self.calls.append(command)
        idx = len(self.calls) - 1
        if idx < len(self.queue):
            item = self.queue[idx]
            if isinstance(item, Exception):
                raise item
            return item
        return IC20DispatchResult(
            delegation_id=command.delegation_id,
            dispatched=True,
            verifier_session_id=f"sub-default-{idx}",
        )


class FixedOutputWaiter:
    """固定输出 waiter · 支持抛异常."""

    def __init__(self, *, output: dict[str, Any] | None = None,
                 exc: Exception | None = None) -> None:
        self.output = output or {}
        self.exc = exc

    async def wait(
        self, *, delegation_id: str, verifier_session_id: str, timeout_s: int,
    ) -> dict[str, Any]:
        if self.exc is not None:
            raise self.exc
        return dict(self.output)


async def _no_sleep(_: float) -> None:
    """免 retry 等待 · 测试提速。"""
    return None


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def pid() -> str:
    return "proj-wp08-s4-verifier"


class FrozenClock(Clock):
    def now_iso(self) -> str:
        return "2026-04-23T10:00:00.000000Z"

    def monotonic_ms(self) -> int:
        return 0


@pytest.fixture
def s4_driver() -> S4Driver:
    """WP05 happy S4Driver · 默认 stub executor 全绿。"""
    return S4Driver(
        dispatcher=SubagentDispatcher(bridge=MockSkillBridge()),
        runner=TestRunner(executor=StubTestExecutor(default_all_green=True)),
        collector=MetricCollector(),
        clock=FrozenClock(),
        config=DriverConfig(coverage_pct_override=0.92),
    )


# =============================================================================
# 场景 3.1 · happy · S4 green → Verifier PASS
# =============================================================================


class TestS4ToVerifierPass:
    """WP05 COMPLETED + is_success → WP06 → VerifierVerdict.PASS。"""

    @pytest.mark.asyncio
    async def test_TC_E2E_S4_VER_01_s4_green_then_verifier_pass(
        self, s4_driver: S4Driver, pid: str,
    ) -> None:
        """TC-E2E-S4-VER-01 · S4 全绿 · 主声称与 verifier 一致 · verdict=PASS.

        链路:
          WP05 drive_s4 → trace(green · metric) →
          bridge → ExecutionTraceLike →
          WP06 orchestrate_s5 → IC-20 dispatch → 双签 OK + DoD PASS → PASS
        """
        # 1. WP05 · drive_s4
        wp_in = WPExecutionInput(
            project_id=pid, wp_id="wp-vf-01", suite_id="suite-vf-01",
        )
        s4_trace = s4_driver.drive_s4(wp_in, suite_test_ids=["t-1", "t-2", "t-3"])
        assert s4_trace.state == DriverState.COMPLETED
        assert s4_trace.is_success is True
        assert s4_trace.metric is not None

        # 2. bridge · S4 trace → verifier trace
        blueprint_slice = {
            "dod_expression": "tests_pass",
            "red_tests": ["t-1", "t-2", "t-3"],
        }
        verifier_trace = _bridge_s4_trace(
            s4_trace,
            git_head="deadbeef01",
            blueprint_slice=blueprint_slice,
            main_session_id="main-wp08-01",
            acceptance_criteria={"coverage_gate": 0.8},
        )
        assert verifier_trace.project_id == pid
        assert verifier_trace.test_report["passed"] == 3
        assert verifier_trace.test_report["coverage"] == 0.92

        # 3. WP06 · orchestrate_s5
        delegator = QueueDelegator(queue=[
            IC20DispatchResult(
                delegation_id="ver-s4-01",
                dispatched=True,
                verifier_session_id="sub-s4-01",
            ),
        ])
        waiter = FixedOutputWaiter(output={
            "blueprint_alignment": blueprint_slice,  # verifier 看到与主声称一致
            "s4_diff_analysis": verifier_trace.test_report,
            "dod_evaluation": {"verdict": "PASS", "all_pass": True},
            "verifier_report_id": "vr-s4-01",
        })
        deps = VerifierDeps(delegator=delegator, callback_waiter=waiter, sleep=_no_sleep)
        result = await orchestrate_s5(verifier_trace, deps, delegation_id="ver-s4-01")

        # 4. 断言全链
        assert result.verdict == VerifierVerdict.PASS
        assert result.project_id == pid
        assert result.wp_id == "wp-vf-01"
        assert result.verifier_session_id == "sub-s4-01"
        assert result.signatures.both_ok is True
        # IC-20 被调 1 次(happy · 无 retry)
        assert len(delegator.calls) == 1
        ic20_cmd = delegator.calls[0]
        assert ic20_cmd.project_id == pid
        assert ic20_cmd.wp_id == "wp-vf-01"
        assert ic20_cmd.blueprint_slice == blueprint_slice


# =============================================================================
# 场景 3.2 · S4 green · 但 verifier 独跑 diff → FAIL_L1(信任坍塌)
# =============================================================================


class TestS4ToVerifierTrustCollapse:
    """主 session 声称 3 pass · verifier 独跑实测 1 pass → FAIL_L1。"""

    @pytest.mark.asyncio
    async def test_TC_E2E_S4_VER_02_trust_collapse_fail_l1(
        self, s4_driver: S4Driver, pid: str,
    ) -> None:
        """TC-E2E-S4-VER-02 · S4 声 3 pass · verifier 独跑 1 pass → FAIL_L1."""
        wp_in = WPExecutionInput(
            project_id=pid, wp_id="wp-vf-02", suite_id="suite-vf-02",
        )
        s4_trace = s4_driver.drive_s4(wp_in, suite_test_ids=["t-a", "t-b", "t-c"])
        assert s4_trace.is_success is True

        blueprint_slice = {"dod_expression": "tests_pass", "red_tests": ["t-a"]}
        verifier_trace = _bridge_s4_trace(
            s4_trace,
            git_head="deadbeef02",
            blueprint_slice=blueprint_slice,
            main_session_id="main-wp08-02",
        )
        # 主声称 3 pass(来自 S4 trace.metric)
        assert verifier_trace.test_report["passed"] == 3

        # verifier 独跑实测 1 pass → signatures.s4_diff fail
        delegator = QueueDelegator(queue=[
            IC20DispatchResult(
                delegation_id="ver-s4-02", dispatched=True,
                verifier_session_id="sub-s4-02",
            ),
        ])
        waiter = FixedOutputWaiter(output={
            "blueprint_alignment": blueprint_slice,
            "s4_diff_analysis": {"passed": 1, "failed": 2, "coverage": 0.92},
            "dod_evaluation": {"verdict": "PASS"},
            "verifier_report_id": "vr-s4-02",
        })
        deps = VerifierDeps(delegator=delegator, callback_waiter=waiter, sleep=_no_sleep)
        result = await orchestrate_s5(verifier_trace, deps)

        assert result.verdict == VerifierVerdict.FAIL_L1
        assert result.signatures.s4_diff_analysis_ok is False
        # three_segment_evidence 含 diff 细节
        diff_evidence = result.three_segment_evidence["s4_diff_analysis"]
        assert any(
            d["field"] == "passed" and d["main_claimed"] == 3 and d["verifier_actual"] == 1
            for d in diff_evidence["diff"]
        )


# =============================================================================
# 场景 3.3 · S4 exhausted → Verifier FAIL_L3(DoD 未过)
# =============================================================================


class TestS4ExhaustedToVerifierFailL3:
    """S4 self-repair 耗尽 · verifier dod_evaluation 失败 → FAIL_L3。"""

    @pytest.mark.asyncio
    async def test_TC_E2E_S4_VER_03_s4_exhausted_dod_breach_fail_l3(
        self, pid: str,
    ) -> None:
        """TC-E2E-S4-VER-03 · S4 全红耗尽 · 双签 ok · DoD fail → verdict=FAIL_L3."""
        # 1. 构造 S4 全红 driver
        from app.quality_loop.s4_driver.schemas import (
            TestCaseOutcome,
            TestOutcomeStatus,
            TestRunResult,
        )
        red_result = TestRunResult(
            cases=tuple(
                TestCaseOutcome(test_id=f"t-{i}", status=TestOutcomeStatus.RED,
                                failure_message="stub red") for i in range(3)
            ),
            red_count=3, green_count=0, error_count=0, total_duration_ms=100,
        )
        red_runner = TestRunner(
            executor=StubTestExecutor(plan=[red_result] * 10, default_all_green=False)
        )
        driver = S4Driver(
            dispatcher=SubagentDispatcher(bridge=MockSkillBridge()),
            runner=red_runner,
            collector=MetricCollector(),
            clock=FrozenClock(),
        )
        s4_trace = driver.drive_s4(
            WPExecutionInput(
                project_id=pid, wp_id="wp-vf-03", suite_id="suite-vf-03",
                attempt_budget=1,
            ),
            suite_test_ids=["t-0", "t-1", "t-2"],
        )
        assert s4_trace.is_exhausted is True
        # exhausted 属于 COMPLETED · S4 仍 collect metric · 但 test_pass_ratio=0
        assert s4_trace.metric is not None
        assert s4_trace.metric.test_pass_ratio == 0.0

        # 2. bridge 用 fallback test_report(passed=0 · coverage=0)
        blueprint_slice = {"dod_expression": "cov>=0.8", "red_tests": []}
        verifier_trace = _bridge_s4_trace(
            s4_trace,
            git_head="deadbeef03",
            blueprint_slice=blueprint_slice,
            main_session_id="main-wp08-03",
        )

        # 3. verifier · 双签 OK(主声称 0 pass · verifier 实测 0 pass · 对齐)
        # 但 DoD 评估 fail → FAIL_L3
        delegator = QueueDelegator(queue=[
            IC20DispatchResult(
                delegation_id="ver-s4-03", dispatched=True,
                verifier_session_id="sub-s4-03",
            ),
        ])
        # 双签对齐: verifier 实测与主声称一致(passed=0 · failed 匹配 bridge 算出)
        main_claim = verifier_trace.test_report
        waiter = FixedOutputWaiter(output={
            "blueprint_alignment": blueprint_slice,
            "s4_diff_analysis": dict(main_claim),  # 完全对齐 · s4_diff_analysis_ok=True
            "dod_evaluation": {
                "verdict": "FAIL_L3",
                "all_pass": False,
                "failed_gates": ["cov>=0.8"],
            },
            "verifier_report_id": "vr-s4-03",
        })
        deps = VerifierDeps(delegator=delegator, callback_waiter=waiter, sleep=_no_sleep)
        result = await orchestrate_s5(verifier_trace, deps)

        assert result.verdict == VerifierVerdict.FAIL_L3
        assert result.signatures.both_ok is True
        assert result.dod_evaluation["failed_gates"] == ["cov>=0.8"]


# =============================================================================
# 场景 3.4 · IC-20 session_id 硬红线
# =============================================================================


class TestS4ToVerifierSessionPrefixViolation:
    """IC-20 返 main. 前缀 session_id → SessionPrefixViolationError · 不重试。"""

    @pytest.mark.asyncio
    async def test_TC_E2E_S4_VER_04_main_prefix_session_id_violation(
        self, s4_driver: S4Driver, pid: str,
    ) -> None:
        """TC-E2E-S4-VER-04 · IC-20 返 main. 前缀 · PM-03 硬红线 · 直接传 up."""
        from app.quality_loop.verifier.ic_20_dispatcher import (
            SessionPrefixViolationError,
        )

        wp_in = WPExecutionInput(
            project_id=pid, wp_id="wp-vf-04", suite_id="suite-vf-04",
        )
        s4_trace = s4_driver.drive_s4(wp_in, suite_test_ids=["t-x"])
        blueprint_slice = {"dod_expression": "x", "red_tests": []}
        verifier_trace = _bridge_s4_trace(
            s4_trace,
            git_head="cafe04",
            blueprint_slice=blueprint_slice,
            main_session_id="main-wp08-04",
        )

        # L1-05 返错前缀(硬红线)· 不重试 · 直接 up
        delegator = QueueDelegator(queue=[
            IC20DispatchResult(
                delegation_id="ver-s4-04", dispatched=True,
                verifier_session_id="main.hacked-01",  # 非法 · main. 前缀
            ),
        ])
        waiter = FixedOutputWaiter(output={})
        deps = VerifierDeps(delegator=delegator, callback_waiter=waiter, sleep=_no_sleep)

        with pytest.raises(SessionPrefixViolationError):
            await orchestrate_s5(verifier_trace, deps)
