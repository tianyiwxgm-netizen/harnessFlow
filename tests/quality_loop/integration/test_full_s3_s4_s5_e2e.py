"""WP08 · e2e · 场景 5 · Quality Loop 完整 S3→S4→S5 全链(所有 L2 串联).

**链路**(brief §3 WP08 场景 5):
    WP02 TDDBlueprint (S3 蓝图)
         → WP03 TestCaseGenerator (S3 用例)
         → WP01 DoDExpressionCompiler (S3 DoD YAML → CompiledDoD)
         → WP05 S4Driver (S4 执行)
         → WP06 Verifier (S5 验证 · IC-20)
         → WP04 GateCompiler (S5 Gate 判定)
         → [FAIL 分支] WP07 IC14Consumer (回退)

所有 7 个 L2 真实 import · 不用 mock · 仅 mock L1 外部依赖(L1-05/09)。

**铁律**:
- 同一 project_id 全链贯穿(PM-14)
- 同一 wp_id 从 blueprint 传到 rollback
- verdict 5 档 + baseline 5 档全覆盖
"""
from __future__ import annotations

from typing import Any

import pytest

from app.quality_loop.dod_compiler import (
    DoDEvaluator,
    DoDExpressionCompiler,
)
from app.quality_loop.dod_compiler.predicate_eval import WhitelistRegistry
from app.quality_loop.gate_compiler.baseline_evaluator import BaselineEvaluator
from app.quality_loop.gate_compiler.checklist_compiler import ChecklistCompiler
from app.quality_loop.gate_compiler.dod_adapter import DoDAdapter
from app.quality_loop.gate_compiler.gate import (
    EvaluateGateCommand,
    GateCompiler,
    RewordCounter,
)
from app.quality_loop.gate_compiler.metric_sampler import MetricSampler
from app.quality_loop.gate_compiler.schemas import Baseline
from app.quality_loop.rollback_router.ic_14_consumer import IC14Consumer
from app.quality_loop.rollback_router.schemas import (
    FailVerdict,
    PushRollbackRouteCommand,
    RouteEvidence,
    TargetStage,
)
from app.quality_loop.s4_driver.driver import Clock, DriverConfig, S4Driver
from app.quality_loop.s4_driver.metric_collector import MetricCollector
from app.quality_loop.s4_driver.schemas import (
    DriverState,
    TestCaseOutcome,
    TestOutcomeStatus,
    TestRunResult,
    WPExecutionInput,
)
from app.quality_loop.s4_driver.subagent_dispatcher import (
    MockSkillBridge,
    SubagentDispatcher,
)
from app.quality_loop.s4_driver.test_runner import StubTestExecutor, TestRunner
from app.quality_loop.tdd_blueprint import TDDBlueprintGenerator
from app.quality_loop.tdd_blueprint.schemas import GenerateBlueprintRequest
from app.quality_loop.test_case_generator import RenderOptions
from app.quality_loop.test_case_generator.generator import TestCaseGenerator
from app.quality_loop.verifier.orchestrator import VerifierDeps, orchestrate_s5
from app.quality_loop.verifier.schemas import (
    IC20Command,
    IC20DispatchResult,
    VerifiedResult,
    VerifierVerdict,
)
from app.quality_loop.verifier.trace_adapter import MockExecutionTrace


# =============================================================================
# Shared Mocks & Helpers
# =============================================================================


class FrozenClock(Clock):
    def now_iso(self) -> str:
        return "2026-04-23T10:00:00.000000Z"

    def monotonic_ms(self) -> int:
        return 0


class FixedDelegator:
    def __init__(self, *, session_id: str = "sub-fullloop") -> None:
        self.session_id = session_id
        self.calls: list[IC20Command] = []

    async def delegate_verifier(self, command: IC20Command) -> IC20DispatchResult:
        self.calls.append(command)
        return IC20DispatchResult(
            delegation_id=command.delegation_id,
            dispatched=True,
            verifier_session_id=self.session_id,
        )


class FixedWaiter:
    def __init__(self, *, output: dict[str, Any]) -> None:
        self.output = output

    async def wait(
        self, *, delegation_id: str, verifier_session_id: str, timeout_s: int,
    ) -> dict[str, Any]:
        return dict(self.output)


async def _no_sleep(_: float) -> None:
    return None


class RecordingStateTransition:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def state_transition(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {"transitioned": True}


class RecordingEventBus:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def append_event(
        self, *, project_id: str, type: str, payload: dict[str, Any],
        evidence_refs: tuple[str, ...] = (),
    ) -> str:
        self.events.append({"project_id": project_id, "type": type, "payload": payload})
        return f"ev-{len(self.events)}"


# DoD YAML · full Quality Loop 使用
_FULL_DOD_YAML = """
dod:
  hard:
    - clause_id: h-cov
      text: "line_coverage() >= 0.8"
      source_ac_ids: [ac-0001]
    - clause_id: h-lint
      text: "lint_errors() == 0"
      source_ac_ids: [ac-0002]
  soft: []
  metric: []
"""


def _make_blueprint_request(
    *, project_id: str, wp_id: str, nonce: str,
    clause_count: int = 4,
) -> GenerateBlueprintRequest:
    return GenerateBlueprintRequest(
        command_id=f"cmd-{project_id}-{wp_id}-{nonce}",
        project_id=project_id,
        entry_phase="S3",
        four_pieces_refs={"four_pieces_hash": "sha256:" + "b" * 64},
        wbs_refs={"wbs_version": 1},
        ac_clauses_refs={"clause_count": clause_count, "ac_manifest_path": "acs.yaml"},
        nonce=nonce,
    )


# =============================================================================
# 场景 5.1 · Quality Loop happy 全链 · 5 L2 串联 · verdict=PASS + Gate HARD_PASS
# =============================================================================


class TestFullQualityLoopHappy:
    """完整 S3 → S4 → S5 · 全链绿 · 无 rollback 触发。"""

    @pytest.mark.asyncio
    async def test_TC_E2E_FULL_01_full_quality_loop_happy_to_pass(self) -> None:
        """TC-E2E-FULL-01 · S3 → S4 → S5 全链 happy · 7 L2 真实 import.

        验证:
          1. WP02 + WP03 + WP01 · S3 产出(blueprint + suite + compiled_dod)
          2. WP05 · S4 跑绿
          3. WP06 · S5 verifier PASS
          4. WP04 · Gate HARD_PASS
          5. PM-14 · 全链同 project_id/wp_id
        """
        pid = "proj-wp08-full-happy"
        wp_id = "wp-full-01"

        # ============ S3 ============

        # S3.1 · WP02 生成蓝图
        bp_gen = TDDBlueprintGenerator()
        bp_resp = bp_gen.generate_blueprint(
            _make_blueprint_request(project_id=pid, wp_id=wp_id, nonce="full-01")
        )
        bp = bp_gen.repo.get(bp_resp.blueprint_id)
        assert bp is not None and bp.project_id == pid

        # S3.2 · WP03 TestSuite
        tc_gen = TestCaseGenerator()
        suite = tc_gen.generate(bp, options=RenderOptions(project_id=pid, wp_id=wp_id))
        assert suite.project_id == pid
        case_ids = [c.case_id for c in suite.cases]
        assert len(case_ids) >= 1

        # S3.3 · WP01 DoD YAML → CompiledDoD
        compiler = DoDExpressionCompiler(whitelist_registry=WhitelistRegistry())
        compile_res = compiler.compile_from_yaml(
            _FULL_DOD_YAML, project_id=pid, wp_id=wp_id,
        )
        assert compile_res.accepted
        compiled_dod = compile_res.compiled

        # ============ S4 ============

        # WP05 · drive_s4 · stub 全绿
        driver = S4Driver(
            dispatcher=SubagentDispatcher(bridge=MockSkillBridge()),
            runner=TestRunner(executor=StubTestExecutor(default_all_green=True)),
            collector=MetricCollector(),
            clock=FrozenClock(),
            config=DriverConfig(coverage_pct_override=0.92),
        )
        s4_trace = driver.drive_s4(
            WPExecutionInput(
                project_id=pid, wp_id=wp_id, suite_id=suite.suite_id,
            ),
            suite_test_ids=case_ids,
        )
        assert s4_trace.is_success is True
        assert s4_trace.state == DriverState.COMPLETED
        assert s4_trace.metric is not None
        total = len(s4_trace.attempts[-1].cases)

        # ============ S5 ============

        # WP06 · verifier orchestrate_s5
        blueprint_slice = {
            "dod_expression": "line_coverage() >= 0.8 and lint_errors() == 0",
            "red_tests": case_ids,
        }
        verifier_trace = MockExecutionTrace(
            project_id=pid, wp_id=wp_id, git_head="happy01",
            blueprint_slice=blueprint_slice,
            main_session_id="main-wp08-full-01",
            ts="2026-04-23T10:00:00Z",
            artifact_refs=(f"projects/{pid}/output.py",),
            test_report={
                "passed": total, "failed": 0,
                "coverage": s4_trace.metric.coverage_pct,
            },
            acceptance_criteria={"coverage_gate": 0.8},
        )
        delegator = FixedDelegator(session_id="sub-full-01")
        waiter = FixedWaiter(output={
            "blueprint_alignment": blueprint_slice,
            "s4_diff_analysis": verifier_trace.test_report,
            "dod_evaluation": {"verdict": "PASS", "all_pass": True},
            "verifier_report_id": "vr-full-01",
        })
        deps = VerifierDeps(delegator=delegator, callback_waiter=waiter, sleep=_no_sleep)
        verified: VerifiedResult = await orchestrate_s5(
            verifier_trace, deps, delegation_id="ver-full-01",
        )
        assert verified.verdict == VerifierVerdict.PASS

        # WP04 · Gate · evaluate_gate(CompiledDoD, metric)
        evaluator = DoDEvaluator(compiler, whitelist_registry=compiler.registry)
        gate = GateCompiler(
            dod_adapter=DoDAdapter(evaluator=evaluator),
            metric_sampler=MetricSampler(),
            rework_counter=RewordCounter(),
            baseline_evaluator=BaselineEvaluator(),
            checklist_compiler=ChecklistCompiler(),
        )
        gate_result = gate.evaluate_gate(EvaluateGateCommand(
            project_id=pid,
            compiled=compiled_dod,
            metrics={
                "coverage": {"line_rate": s4_trace.metric.coverage_pct},
                "lint": {"error_count": 0},
            },
            wp_id=wp_id,
        ))
        assert gate_result.verdict.baseline == Baseline.HARD_PASS

        # ============ 终局断言 · 全链 PM-14 一致 ============
        assert bp.project_id == suite.project_id == compiled_dod.project_id == pid
        assert s4_trace.project_id == verified.project_id == pid
        assert gate_result.verdict.project_id == pid
        assert s4_trace.wp_id == wp_id
        assert verified.wp_id == wp_id
        assert gate_result.verdict.wp_id == wp_id


# =============================================================================
# 场景 5.2 · FAIL 分支 · S5 FAIL_L3 → WP04 Gate REWORK → WP07 rollback
# =============================================================================


class TestFullQualityLoopFailBranch:
    """S4 绿 + S5 DoD 未过 FAIL_L3 + WP04 Gate REWORK → WP07 retry_s5."""

    @pytest.mark.asyncio
    async def test_TC_E2E_FULL_02_full_loop_fail_l3_then_rollback_retry_s5(self) -> None:
        """TC-E2E-FULL-02 · 完整 fail 链路 · verifier FAIL_L3 → rollback retry_s5.

        关键:
          - S4 产绿 metric(coverage=0.65 低于 DoD 要求的 0.8)
          - S5 verifier 双签 OK · DoD 评估 FAIL_L3
          - WP04 Gate 也 REWORK(因为 DoD 未达标)
          - 模拟 L1-07 supervisor 把 VerifierVerdict.FAIL_L3 → IC-14 push → 消费
        """
        pid = "proj-wp08-full-fail"
        wp_id = "wp-full-02"

        # S3
        bp_gen = TDDBlueprintGenerator()
        bp_resp = bp_gen.generate_blueprint(
            _make_blueprint_request(project_id=pid, wp_id=wp_id, nonce="full-02")
        )
        bp = bp_gen.repo.get(bp_resp.blueprint_id)
        suite = TestCaseGenerator().generate(
            bp, options=RenderOptions(project_id=pid, wp_id=wp_id),
        )
        compiler = DoDExpressionCompiler(whitelist_registry=WhitelistRegistry())
        compile_res = compiler.compile_from_yaml(
            _FULL_DOD_YAML, project_id=pid, wp_id=wp_id,
        )
        compiled_dod = compile_res.compiled

        # S4 · 低 coverage(0.65)· test 仍绿(stub)
        driver = S4Driver(
            dispatcher=SubagentDispatcher(bridge=MockSkillBridge()),
            runner=TestRunner(executor=StubTestExecutor(default_all_green=True)),
            collector=MetricCollector(),
            clock=FrozenClock(),
            config=DriverConfig(coverage_pct_override=0.65),
        )
        s4_trace = driver.drive_s4(
            WPExecutionInput(
                project_id=pid, wp_id=wp_id, suite_id=suite.suite_id,
            ),
            suite_test_ids=[c.case_id for c in suite.cases],
        )
        assert s4_trace.is_success is True
        assert s4_trace.metric.coverage_pct == 0.65

        # S5 · verifier FAIL_L3
        total = len(s4_trace.attempts[-1].cases)
        blueprint_slice = {"dod_expression": "line_coverage>=0.8", "red_tests": []}
        verifier_trace = MockExecutionTrace(
            project_id=pid, wp_id=wp_id, git_head="fail02",
            blueprint_slice=blueprint_slice,
            main_session_id="main-wp08-full-02",
            ts="2026-04-23T10:00:00Z",
            test_report={"passed": total, "failed": 0, "coverage": 0.65},
        )
        verified = await orchestrate_s5(
            verifier_trace,
            VerifierDeps(
                delegator=FixedDelegator(session_id="sub-full-02"),
                callback_waiter=FixedWaiter(output={
                    "blueprint_alignment": blueprint_slice,
                    "s4_diff_analysis": verifier_trace.test_report,
                    "dod_evaluation": {
                        "verdict": "FAIL_L3",
                        "all_pass": False,
                        "failed_gates": ["line_coverage>=0.8"],
                    },
                    "verifier_report_id": "vr-full-02",
                }),
                sleep=_no_sleep,
            ),
            delegation_id="ver-full-02",
        )
        assert verified.verdict == VerifierVerdict.FAIL_L3

        # WP04 Gate · REWORK(coverage 0.65 < 0.8 · hard fail)
        evaluator = DoDEvaluator(compiler, whitelist_registry=compiler.registry)
        gate = GateCompiler(
            dod_adapter=DoDAdapter(evaluator=evaluator),
            metric_sampler=MetricSampler(),
            rework_counter=RewordCounter(),
        )
        gate_result = gate.evaluate_gate(EvaluateGateCommand(
            project_id=pid, compiled=compiled_dod,
            metrics={
                "coverage": {"line_rate": 0.65},
                "lint": {"error_count": 0},
            },
            wp_id=wp_id,
        ))
        assert gate_result.verdict.baseline == Baseline.REWORK

        # WP07 · 模拟 L1-07 supervisor 把 verdict → PushRollbackRouteCommand
        # FAIL_L3 → retry_s5
        rollback_cmd = PushRollbackRouteCommand(
            route_id=f"route-{verified.delegation_id}",
            project_id=pid,
            wp_id=wp_id,
            verdict=FailVerdict.FAIL_L3,
            target_stage=TargetStage.S5,
            level_count=1,
            evidence=RouteEvidence(verifier_report_id=verified.verifier_report_id or "vr-full-02"),
            ts="2026-04-23T10:00:00Z",
        )
        st = RecordingStateTransition()
        bus = RecordingEventBus()
        consumer = IC14Consumer(session_pid=pid, state_transition=st, event_bus=bus)
        ack = await consumer.consume(rollback_cmd)
        assert ack.applied is True
        assert ack.new_wp_state.value == "retry_s5"
        assert ack.escalated is False

        # 终局 · 全链 PM-14
        assert verified.project_id == pid
        assert gate_result.verdict.project_id == pid
        assert st.calls[0]["project_id"] == pid
        # event_bus 只收到本 L2 的事件 · 全 pid 一致
        for ev in bus.events:
            assert ev["project_id"] == pid


# =============================================================================
# 场景 5.3 · Full loop · WP04 Gate REWORK × 3 → ABORT · 系统自举 UPGRADE
# =============================================================================


class TestFullQualityLoopGateAbortPath:
    """WP04 Gate 连续 rework → ABORT · 仍由 WP07 消费对应的 IC-14 upgrade."""

    @pytest.mark.asyncio
    async def test_TC_E2E_FULL_03_gate_abort_with_rollback_upgrade(self) -> None:
        """TC-E2E-FULL-03 · WP04 Gate 连 3 REWORK 转 ABORT · WP07 消费 UPGRADE.

        验证:
          - WP04 内置 RewordCounter · 连续 3 次 REWORK 自动升级
          - 这种场景由 L1-07 supervisor 包装成 IC-14(FAIL_L4/UPGRADE)消费
          - WP07 FAIL_L4 + level_count=3 → 强 escalated UPGRADE
        """
        pid = "proj-wp08-full-abort"
        wp_id = "wp-full-03"

        compiler = DoDExpressionCompiler(whitelist_registry=WhitelistRegistry())
        compiled = compiler.compile_from_yaml(
            _FULL_DOD_YAML, project_id=pid, wp_id=wp_id,
        ).compiled
        evaluator = DoDEvaluator(compiler, whitelist_registry=compiler.registry)
        gate = GateCompiler(
            dod_adapter=DoDAdapter(evaluator=evaluator),
            metric_sampler=MetricSampler(),
            rework_counter=RewordCounter(),
        )

        # 连续 3 轮 REWORK · 第 4 轮 ABORT
        bad_metrics = {
            "coverage": {"line_rate": 0.40},
            "lint": {"error_count": 0},
        }
        baselines: list[Baseline] = []
        for _ in range(4):
            r = gate.evaluate_gate(EvaluateGateCommand(
                project_id=pid, compiled=compiled, metrics=bad_metrics, wp_id=wp_id,
            ))
            baselines.append(r.verdict.baseline)
        assert baselines == [Baseline.REWORK] * 3 + [Baseline.ABORT]

        # L1-07 supervisor 把 ABORT 映射到 IC-14 · 用 level_count=3 触发 escalated
        # (ABORT · verdict=FAIL_L4 · target_stage=UPGRADE · level_count=3)
        rollback_cmd = PushRollbackRouteCommand(
            route_id=f"route-abort-{pid}-{wp_id}",
            project_id=pid,
            wp_id=wp_id,
            verdict=FailVerdict.FAIL_L4,
            target_stage=TargetStage.UPGRADE_TO_L1_01,
            level_count=3,
            evidence=RouteEvidence(verifier_report_id="vr-abort-03"),
            ts="2026-04-23T10:00:00Z",
        )
        st = RecordingStateTransition()
        bus = RecordingEventBus()
        consumer = IC14Consumer(session_pid=pid, state_transition=st, event_bus=bus)
        ack = await consumer.consume(rollback_cmd)
        assert ack.new_wp_state.value == "upgraded_to_l1_01"
        assert ack.escalated is True
        # 审计含 rollback_escalated(level_count=3 触发)
        escalated_events = [e for e in bus.events if e["type"] == "L1-04:rollback_escalated"]
        assert len(escalated_events) == 1
        assert escalated_events[0]["payload"]["level_count"] == 3
