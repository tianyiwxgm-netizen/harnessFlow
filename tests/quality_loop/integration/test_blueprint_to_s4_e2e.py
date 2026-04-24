"""WP08 · e2e · 场景 2 · TDDBlueprint → test_case_generator → S4Driver 全链.

覆盖 WP02 (L2-01 TDD 蓝图) → WP03 (L2-03 测试用例生成) → WP05 (L2-05 S4 驱动器) 全链。

**验证点**:
- WP02 generate_blueprint → 真实 TDDBlueprint(含 ACMatrix + slot_ids)
- WP03 TestCaseGenerator.generate → 真实 TestSuite(从 blueprint 展开 slot)
- WP05 S4Driver.drive_s4 消费 TestSuite 的 case_ids 作为 suite_test_ids
- trace.state == COMPLETED · is_success=True · metric 非空

**铁律**:
- blueprint / suite / trace 三者 project_id 一致(PM-14)
- WP03 的 case_id → WP05 suite_test_ids 合约传递
- StubTestExecutor 默认全绿 · 不真跑 pytest
"""
from __future__ import annotations

from typing import Any

import pytest

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
from app.quality_loop.tdd_blueprint.schemas import (
    BlueprintState,
    GenerateBlueprintRequest,
)
from app.quality_loop.test_case_generator import RenderOptions, SuiteState
from app.quality_loop.test_case_generator.generator import TestCaseGenerator


# =============================================================================
# Helpers
# =============================================================================


def _make_generate_request(
    *, project_id: str, clause_count: int = 6, nonce: str = "wp08-e2e",
) -> GenerateBlueprintRequest:
    """最小 GenerateBlueprintRequest · 只填必需字段。

    entry_phase='S3' 固定(§3.1 _VALID_PHASES)· clause_count 决定 AC 条目数。
    """
    return GenerateBlueprintRequest(
        command_id=f"cmd-{project_id}-{nonce}",
        project_id=project_id,
        entry_phase="S3",
        four_pieces_refs={"four_pieces_hash": "sha256:" + "a" * 64},
        wbs_refs={"wbs_version": 1, "topology_path": f"projects/{project_id}/wbs.yaml"},
        ac_clauses_refs={
            "clause_count": clause_count,
            "ac_manifest_path": f"projects/{project_id}/ac.yaml",
        },
        nonce=nonce,
    )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def pid() -> str:
    return "proj-wp08-blueprint-s4"


@pytest.fixture
def bp_generator() -> TDDBlueprintGenerator:
    """WP02 真实 Blueprint Generator(in-memory repo · 无事件总线注入)。"""
    return TDDBlueprintGenerator()


@pytest.fixture
def tc_generator() -> TestCaseGenerator:
    """WP03 真实 TestCaseGenerator(无参 · 内置 BlueprintReader + PytestRenderer)。"""
    return TestCaseGenerator()


class FrozenClock(Clock):
    """可注入时钟 · 手动递增 monotonic_ms。"""

    def __init__(self) -> None:
        self._ms = 0

    def now_iso(self) -> str:
        return "2026-04-23T10:00:00.000000Z"

    def monotonic_ms(self) -> int:
        return self._ms


@pytest.fixture
def s4_driver() -> S4Driver:
    """WP05 S4Driver · 默认 happy path(stub executor 全绿 · mock skill bridge 全 success)。"""
    return S4Driver(
        dispatcher=SubagentDispatcher(bridge=MockSkillBridge()),
        runner=TestRunner(executor=StubTestExecutor(default_all_green=True)),
        collector=MetricCollector(),
        clock=FrozenClock(),
        config=DriverConfig(),
    )


# =============================================================================
# 场景 2.1 · happy · Blueprint → TestSuite → S4 全链
# =============================================================================


class TestBlueprintToS4HappyPath:
    """WP02 → WP03 → WP05 · 全绿路径。"""

    def test_TC_E2E_BP_S4_01_blueprint_to_suite_to_s4_happy(
        self,
        bp_generator: TDDBlueprintGenerator,
        tc_generator: TestCaseGenerator,
        s4_driver: S4Driver,
        pid: str,
    ) -> None:
        """TC-E2E-BP-S4-01 · 生蓝图 → 生 TestSuite → 跑 S4 → COMPLETED.

        验证 3 件套在真实实例间字段级对齐:
        - blueprint_id / version 从 WP02 → WP03 传透
        - suite.cases 的 case_id 用作 WP05 suite_test_ids
        - trace.is_success=True · attempt_count=1 · 首跑全绿
        """
        # 1. WP02 · 生成蓝图
        req = _make_generate_request(project_id=pid, clause_count=6, nonce="bp-s4-01")
        bp_resp = bp_generator.generate_blueprint(req)
        assert bp_resp.status in ("ACCEPTED", "CACHED")
        assert bp_resp.project_id == pid
        bp = bp_generator.repo.get(bp_resp.blueprint_id)
        assert bp is not None
        # blueprint 会因 _auto_broadcast 转 PUBLISHED · 非 DRAFT
        assert bp.state in (BlueprintState.READY, BlueprintState.PUBLISHED)
        assert len(bp.ac_matrix.rows) >= 1

        # 2. WP03 · 蓝图 → TestSuite
        options = RenderOptions(project_id=pid, wp_id="wp-bp-s4-01")
        suite = tc_generator.generate(bp, options=options)
        assert suite.state == SuiteState.READY
        assert suite.project_id == pid
        assert suite.blueprint_id == bp.blueprint_id
        assert suite.blueprint_version == bp.version
        assert suite.total_count >= 1
        # 生成即红灯(WP03 §10.5)
        assert suite.red_count == suite.total_count

        # 3. WP05 · S4Driver.drive_s4 消费 suite 的 case_ids 作 test_ids
        suite_test_ids = [c.case_id for c in suite.cases]
        wp_input = WPExecutionInput(
            project_id=pid,
            wp_id="wp-bp-s4-01",
            suite_id=suite.suite_id,
            attempt_budget=3,
            timeout_ms=180_000,
        )
        trace = s4_driver.drive_s4(wp_input, suite_test_ids=suite_test_ids)

        # 4. trace 断言全链对齐
        assert trace.state == DriverState.COMPLETED
        assert trace.is_success is True
        assert trace.project_id == pid
        assert trace.wp_id == "wp-bp-s4-01"
        assert trace.suite_id == suite.suite_id
        # stub 默认全绿 · 首跑 attempt=0 即 return · attempt_count=1
        assert trace.attempt_count == 1
        # metric 已收集(绿灯才有 metric)
        assert trace.metric is not None
        assert trace.metric.test_pass_ratio == 1.0

    def test_TC_E2E_BP_S4_02_suite_case_ids_feed_s4_test_ids(
        self,
        bp_generator: TDDBlueprintGenerator,
        tc_generator: TestCaseGenerator,
        s4_driver: S4Driver,
        pid: str,
    ) -> None:
        """TC-E2E-BP-S4-02 · WP03 suite.cases[].case_id 可作 WP05 test_ids · 字段级合约。

        关键合约: WP03 输出的 case_id 必须是 WP05 可接受的 str · 非空 · 稳定。
        """
        req = _make_generate_request(project_id=pid, clause_count=4, nonce="bp-s4-02")
        bp_resp = bp_generator.generate_blueprint(req)
        bp = bp_generator.repo.get(bp_resp.blueprint_id)
        suite = tc_generator.generate(bp, options=RenderOptions(project_id=pid))
        case_ids = [c.case_id for c in suite.cases]
        # 合约 1: 每个 case_id 非空字符串
        for cid in case_ids:
            assert isinstance(cid, str) and cid
        # 合约 2: case_id 全域唯一(WP03 slot_id 稳定唯一)
        assert len(set(case_ids)) == len(case_ids)
        # 合约 3: 喂 S4 成功(不抛 · 跑通)
        trace = s4_driver.drive_s4(
            WPExecutionInput(project_id=pid, wp_id="wp-feeds-02", suite_id=suite.suite_id),
            suite_test_ids=case_ids,
        )
        assert trace.state == DriverState.COMPLETED


# =============================================================================
# 场景 2.2 · 负向 · S4 全红 · self-repair 耗尽
# =============================================================================


class TestBlueprintToS4SelfRepairExhausted:
    """WP05 self-repair 硬锁耗尽 · trace 标 exhausted。"""

    def test_TC_E2E_BP_S4_03_stub_all_red_then_self_repair_exhausted(
        self,
        bp_generator: TDDBlueprintGenerator,
        tc_generator: TestCaseGenerator,
        pid: str,
    ) -> None:
        """TC-E2E-BP-S4-03 · StubExecutor 全红 · attempt_budget=2 耗尽 → is_exhausted.

        构造红色 runner · 验证 WP05 硬锁机制在 WP02/03 真实 blueprint/suite 下依然生效。
        """
        # 1. WP02 生蓝图
        req = _make_generate_request(project_id=pid, clause_count=3, nonce="bp-s4-03")
        bp_resp = bp_generator.generate_blueprint(req)
        bp = bp_generator.repo.get(bp_resp.blueprint_id)

        # 2. WP03 生 Suite
        suite = TestCaseGenerator().generate(bp, options=RenderOptions(project_id=pid))
        case_ids = [c.case_id for c in suite.cases]

        # 3. 构造全红 executor · attempt_budget=2 → 一共跑 3 轮(0+repair*2) 然后 exhausted
        red_result = TestRunResult(
            cases=tuple(
                TestCaseOutcome(test_id=cid, status=TestOutcomeStatus.RED,
                                failure_message="stub red") for cid in case_ids
            ),
            red_count=len(case_ids),
            green_count=0,
            error_count=0,
            total_duration_ms=100,
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

        wp_input = WPExecutionInput(
            project_id=pid, wp_id="wp-red-03", suite_id=suite.suite_id,
            attempt_budget=2,
        )
        trace = driver.drive_s4(wp_input, suite_test_ids=case_ids)

        assert trace.state == DriverState.COMPLETED
        assert trace.is_success is False
        assert trace.is_exhausted is True
        # attempt_budget=2 → 最多 3 次 attempt(0, 1, 2)
        assert trace.attempt_count == 3
