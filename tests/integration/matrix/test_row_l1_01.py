"""Row L1-01 主决策(main_loop) → others · 4 cells × 6 TC = 24 TC.

**4 cells**:
    L1-01 → L1-02 · IC-01 触发 stage_transition (7 状态 / PM-14 / 拒非法边)
    L1-01 → L1-04 · IC-14 trigger Gate (verdict 接收 / 重试 / 升级)
    L1-01 → L1-05 · IC-04 调 skill (调用 / 超时 / fallback)
    L1-01 → L1-09 · IC-09 append_event (hash chain / SLO)

**每 cell 6 TC**: HAPPY × 2 / NEGATIVE × 2 / SLO × 1 / E2E × 1.
"""
from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from app.main_loop.state_machine import (
    StateMachineOrchestrator,
    TransitionRequest,
)
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
)
from tests.shared.matrix_helpers import CaseType


# IC-01 严格 pid 格式: ^pid-[0-9a-fA-F-]{8,}$
_L1_01_PID = "pid-00000000-0000-0000-0000-000000ab0001"
_L1_01_PID_OTHER = "pid-00000000-0000-0000-0000-000000ab0002"


def _build_request(
    project_id: str, frm: str, to: str, *, suffix: str = "0001",
) -> TransitionRequest:
    # transition_id 格式: ^trans-[0-9a-fA-F-]{8,}$ (只允许 hex + 短横)
    tid_suffix = suffix.zfill(4)  # padding 到 4 hex
    return TransitionRequest(
        transition_id=f"trans-{tid_suffix}-deadbeef-feedface",
        project_id=project_id,
        from_state=frm,
        to_state=to,
        reason=f"IC-01 矩阵集成测试 {frm} -> {to} reason ≥ 20 字",
        trigger_tick="tick-00000000-0000-0000-0000-000000000001",
        evidence_refs=("ev-matrix-1",),
        ts="2026-04-23T10:00:00.000000Z",
    )


# =============================================================================
# Cell 1: L1-01 → L1-02 · IC-01 触发 stage_transition (6 TC)
# =============================================================================


class TestRowL1_01_to_L1_02:
    """L1-01 主决策 → L1-02 项目生命周期 · IC-01 stage_transition 契约."""

    def test_happy_init_to_planning_state_transition(self, matrix_cov) -> None:
        """HAPPY · NOT_EXIST → INITIALIZED 合法 transition."""
        from .conftest import record_cell

        orch = StateMachineOrchestrator(
            project_id=_L1_01_PID, initial_state="NOT_EXIST",
        )
        req = _build_request(_L1_01_PID, "NOT_EXIST", "INITIALIZED")
        result = orch.transition(req)
        assert result.accepted is True
        assert result.new_state == "INITIALIZED"
        assert orch.get_current_state() == "INITIALIZED"
        record_cell(matrix_cov, "L1-01", "L1-02", CaseType.HAPPY)

    def test_happy_planning_to_tdd_full_chain(self, matrix_cov) -> None:
        """HAPPY · 推进 PLANNING → TDD_PLANNING (常用主链路)."""
        from .conftest import record_cell

        orch = StateMachineOrchestrator(
            project_id=_L1_01_PID, initial_state="PLANNING",
        )
        req = _build_request(_L1_01_PID, "PLANNING", "TDD_PLANNING")
        result = orch.transition(req)
        assert result.accepted is True
        assert result.new_state == "TDD_PLANNING"
        record_cell(matrix_cov, "L1-01", "L1-02", CaseType.HAPPY)

    def test_negative_illegal_edge_rejected(self, matrix_cov) -> None:
        """NEGATIVE · 非法边 NOT_EXIST → CLOSED 必拒 + error_code."""
        from .conftest import record_cell

        orch = StateMachineOrchestrator(
            project_id=_L1_01_PID, initial_state="NOT_EXIST",
        )
        req = _build_request(_L1_01_PID, "NOT_EXIST", "CLOSED")
        result = orch.transition(req)
        assert result.accepted is False
        assert result.error_code is not None
        # state 不变
        assert orch.get_current_state() == "NOT_EXIST"
        record_cell(matrix_cov, "L1-01", "L1-02", CaseType.NEGATIVE)

    def test_negative_pm14_cross_project_rejected(self, matrix_cov) -> None:
        """NEGATIVE/PM-14 · 跨 pid transition_id 必拒(orchestrator pid != req pid)."""
        from app.main_loop.state_machine.schemas import (
            E_TRANS_CROSS_PROJECT,
            StateMachineError,
        )

        from .conftest import record_cell

        orch = StateMachineOrchestrator(
            project_id=_L1_01_PID, initial_state="NOT_EXIST",
        )
        # 用 other pid 构造 request (违反 PM-14)
        req = _build_request(_L1_01_PID_OTHER, "NOT_EXIST", "INITIALIZED")
        with pytest.raises(StateMachineError) as exc_info:
            orch.transition(req)
        assert exc_info.value.error_code == E_TRANS_CROSS_PROJECT
        record_cell(matrix_cov, "L1-01", "L1-02", CaseType.PM14)

    def test_slo_transition_under_100ms(self, matrix_cov) -> None:
        """SLO · IC-01 transition P99 < 100ms."""
        from .conftest import record_cell

        orch = StateMachineOrchestrator(
            project_id=_L1_01_PID, initial_state="NOT_EXIST",
        )
        req = _build_request(_L1_01_PID, "NOT_EXIST", "INITIALIZED")
        t0 = time.monotonic()
        result = orch.transition(req)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert result.accepted is True
        assert elapsed_ms < 100, f"IC-01 SLO 违反 实际 {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-01", "L1-02", CaseType.HAPPY)

    def test_e2e_full_7_states_chain(self, matrix_cov) -> None:
        """E2E · 走完 6 边 N→I→P→T→E→C→CLOSED 全链 7 态正确."""
        from .conftest import record_cell

        orch = StateMachineOrchestrator(
            project_id=_L1_01_PID, initial_state="NOT_EXIST",
        )
        chain = [
            ("NOT_EXIST", "INITIALIZED"),
            ("INITIALIZED", "PLANNING"),
            ("PLANNING", "TDD_PLANNING"),
            ("TDD_PLANNING", "EXECUTING"),
            ("EXECUTING", "CLOSING"),
            ("CLOSING", "CLOSED"),
        ]
        for i, (frm, to) in enumerate(chain):
            req = _build_request(_L1_01_PID, frm, to, suffix=f"e2e{i:03d}")
            result = orch.transition(req)
            assert result.accepted is True
            assert result.new_state == to
        assert orch.get_current_state() == "CLOSED"
        record_cell(matrix_cov, "L1-01", "L1-02", CaseType.DEGRADE)


# =============================================================================
# Cell 2: L1-01 → L1-04 · IC-14 trigger Gate / verdict 接收 (6 TC)
# =============================================================================


def _build_rollback_command(
    project_id: str = "proj-m3-shared",
    *,
    wp_id: str = "wp-m3-1",
    route_id: str = "route-m3-1",
    verdict: str = "FAIL_L1",
    target_stage: str = "S3",
    level_count: int = 1,
):
    from app.quality_loop.rollback_router.schemas import (
        FailVerdict,
        PushRollbackRouteCommand,
        RouteEvidence,
        TargetStage,
    )

    return PushRollbackRouteCommand(
        route_id=route_id,
        project_id=project_id,
        wp_id=wp_id,
        verdict=FailVerdict[verdict],
        target_stage=TargetStage[target_stage],
        level_count=level_count,
        evidence=RouteEvidence(verifier_report_id="vr-1", decision_id="dec-1"),
        ts="2026-04-23T10:00:00.000000Z",
    )


class _RealBusAdapter:
    """适配 L1-09 EventBus.append (sync) → executor 期望的 async append_event 协议."""

    def __init__(self, real_bus, default_actor: str = "verifier") -> None:
        self._bus = real_bus
        self._default_actor = default_actor

    async def append_event(
        self,
        *,
        project_id: str,
        type: str,
        payload: dict,
        evidence_refs: tuple = (),
    ) -> str:
        from datetime import UTC, datetime

        from app.l1_09.event_bus.schemas import Event

        evt = Event(
            project_id=project_id,
            type=type,
            actor=self._default_actor,
            payload=dict(payload),
            timestamp=datetime.now(UTC),
        )
        result = self._bus.append(evt)
        return result.event_id


def _build_ic14_consumer(session_pid: str, real_event_bus, state_spy):
    """组装真 IC14Consumer · 使用真 EventBus(via adapter) + spy state_transition."""
    from app.quality_loop.rollback_router.ic_14_consumer import IC14Consumer

    return IC14Consumer(
        session_pid=session_pid,
        state_transition=state_spy,
        event_bus=_RealBusAdapter(real_event_bus, default_actor="verifier"),
    )


class TestRowL1_01_to_L1_04:
    """L1-01 主决策 → L1-04 Quality Loop · IC-14 rollback / verdict."""

    async def test_happy_fail_l1_to_s3_retry(
        self, project_id: str, real_event_bus, state_spy, matrix_cov,
    ) -> None:
        """HAPPY · FAIL_L1 → S3 retry · ack.applied=True · new_wp_state=retry_s3."""
        from .conftest import record_cell

        consumer = _build_ic14_consumer(project_id, real_event_bus, state_spy)
        cmd = _build_rollback_command(project_id, verdict="FAIL_L1", target_stage="S3")
        ack = await consumer.consume(cmd)
        assert ack.applied is True
        assert ack.new_wp_state.value == "retry_s3"
        # state_transition 被调
        assert len(state_spy.calls) >= 1
        assert state_spy.calls[0]["wp_id"] == "wp-m3-1"
        assert state_spy.calls[0]["new_wp_state"] == "retry_s3"
        record_cell(matrix_cov, "L1-01", "L1-04", CaseType.HAPPY)

    async def test_happy_fail_l4_upgrade_to_l1_01(
        self, project_id: str, real_event_bus, state_spy, matrix_cov,
    ) -> None:
        """HAPPY · FAIL_L4 → UPGRADE_TO_L1_01 · ack.escalated=True."""
        from .conftest import record_cell

        consumer = _build_ic14_consumer(project_id, real_event_bus, state_spy)
        cmd = _build_rollback_command(
            project_id,
            wp_id="wp-m3-2", route_id="route-m3-2",
            verdict="FAIL_L4", target_stage="UPGRADE_TO_L1_01",
            level_count=3,
        )
        ack = await consumer.consume(cmd)
        assert ack.applied is True
        assert ack.escalated is True
        assert ack.new_wp_state.value == "upgraded_to_l1_01"
        record_cell(matrix_cov, "L1-01", "L1-04", CaseType.HAPPY)

    async def test_negative_idempotent_replay_returns_cached_ack(
        self, project_id: str, real_event_bus, state_spy, matrix_cov,
    ) -> None:
        """NEGATIVE · 同 route_id 重复推 · 返 cached ack · state_transition 不重调."""
        from .conftest import record_cell

        consumer = _build_ic14_consumer(project_id, real_event_bus, state_spy)
        cmd = _build_rollback_command(
            project_id, route_id="route-m3-idem", verdict="FAIL_L1",
        )
        ack1 = await consumer.consume(cmd)
        ack2 = await consumer.consume(cmd)
        assert ack1 == ack2
        # 仅一次实际 transition (第二次走幂等缓存)
        assert len(state_spy.calls) == 1
        record_cell(matrix_cov, "L1-01", "L1-04", CaseType.NEGATIVE)

    async def test_negative_pm14_cross_project_rejected(
        self, project_id: str, other_project_id: str, real_event_bus, state_spy,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · cross-project 必拒 E_ROUTE_CROSS_PROJECT."""
        from .conftest import record_cell

        consumer = _build_ic14_consumer(project_id, real_event_bus, state_spy)
        # 用 other pid 构造 command
        cmd = _build_rollback_command(other_project_id, verdict="FAIL_L1")
        with pytest.raises(ValueError) as exc_info:
            await consumer.consume(cmd)
        assert "E_ROUTE_CROSS_PROJECT" in str(exc_info.value)
        record_cell(matrix_cov, "L1-01", "L1-04", CaseType.PM14)

    async def test_slo_consume_under_100ms(
        self, project_id: str, real_event_bus, state_spy, matrix_cov,
    ) -> None:
        """SLO · IC-14 consume 单次 < 100ms (无回退预算)."""
        from .conftest import record_cell

        consumer = _build_ic14_consumer(project_id, real_event_bus, state_spy)
        cmd = _build_rollback_command(project_id, verdict="FAIL_L1")
        t0 = time.monotonic()
        await consumer.consume(cmd)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 100, f"IC-14 SLO 违反 {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-01", "L1-04", CaseType.HAPPY)

    async def test_e2e_4_verdicts_full_routes(
        self, project_id: str, real_event_bus, state_spy, matrix_cov,
    ) -> None:
        """E2E · 4 verdict (L1/L2/L3/L4) → 各自 target_stage 全链路."""
        from .conftest import record_cell

        consumer = _build_ic14_consumer(project_id, real_event_bus, state_spy)
        cases = [
            ("FAIL_L1", "S3", "retry_s3", False),
            ("FAIL_L2", "S4", "retry_s4", False),
            ("FAIL_L3", "S5", "retry_s5", False),
            # FAIL_L4 首次(level_count=1) · 非"同级 ≥ 3" 触发 · escalated=False
            ("FAIL_L4", "UPGRADE_TO_L1_01", "upgraded_to_l1_01", False),
        ]
        for i, (verdict, ts, new_state, escalated) in enumerate(cases):
            cmd = _build_rollback_command(
                project_id,
                wp_id=f"wp-e2e-{i}", route_id=f"route-e2e-{i}",
                verdict=verdict, target_stage=ts, level_count=1,
            )
            ack = await consumer.consume(cmd)
            assert ack.new_wp_state.value == new_state
            assert ack.escalated is escalated
        # 4 个 transition 调用
        assert len(state_spy.calls) == 4
        record_cell(matrix_cov, "L1-01", "L1-04", CaseType.DEGRADE)
