"""TC-WP04-S01..S05 · schemas.py 数据契约 · 不变量。"""
from __future__ import annotations

import pytest

from app.main_loop.tick_scheduler.schemas import (
    HARD_HALT_SLO_MS,
    PANIC_SLO_MS,
    TERMINAL_STATES,
    TICK_DRIFT_SLO_MS,
    TICK_INTERVAL_MS_DEFAULT,
    DriftViolationRecord,
    TickBudget,
    TickError,
    TickEvent,
    TickEventType,
    TickResult,
    TickState,
)


class TestSchemas:
    """schemas · 数据契约 + SLO 常量 + 不变量。"""

    def test_TC_WP04_S01_tick_state_has_4_values(self) -> None:
        """TC-WP04-S01 · TickState 4 态(IDLE/RUNNING/PAUSED/HALTED)。"""
        names = {s.name for s in TickState}
        assert names == {"IDLE", "RUNNING", "PAUSED", "HALTED"}
        # value 对齐 HardHaltState 字符串(RUNNING/PAUSED/HALTED · 3 态对齐)
        assert TickState.RUNNING.value == "RUNNING"
        assert TickState.PAUSED.value == "PAUSED"
        assert TickState.HALTED.value == "HALTED"

    def test_TC_WP04_S02_slo_constants_are_100ms_hard(self) -> None:
        """TC-WP04-S02 · 3 硬约束 SLO 常量 = 100ms (release blocker)。"""
        assert TICK_INTERVAL_MS_DEFAULT == 100
        assert TICK_DRIFT_SLO_MS == 100
        assert HARD_HALT_SLO_MS == 100
        assert PANIC_SLO_MS == 100

    def test_TC_WP04_S03_tick_budget_requires_positive_interval(self) -> None:
        """TC-WP04-S03 · TickBudget 非法 interval 直接拒。"""
        with pytest.raises(ValueError, match="interval_ms"):
            TickBudget(
                tick_id="tick-1",
                interval_ms=0,
                started_at_ns=1_000,
                deadline_ns=2_000,
            )
        with pytest.raises(ValueError, match="interval_ms"):
            TickBudget(
                tick_id="tick-1",
                interval_ms=-10,
                started_at_ns=1_000,
                deadline_ns=2_000,
            )

    def test_TC_WP04_S04_tick_budget_deadline_after_start(self) -> None:
        """TC-WP04-S04 · deadline_ns 必须 > started_at_ns。"""
        with pytest.raises(ValueError, match="deadline_ns"):
            TickBudget(
                tick_id="tick-1",
                interval_ms=100,
                started_at_ns=2_000,
                deadline_ns=1_000,
            )

    def test_TC_WP04_S05_tick_budget_happy_path(self) -> None:
        """TC-WP04-S05 · 正常 TickBudget · budget_ms 正确计算。"""
        b = TickBudget(
            tick_id="tick-1",
            interval_ms=100,
            started_at_ns=1_000_000,  # 1ms
            deadline_ns=101_000_000,  # 101ms
        )
        assert b.budget_ms == 100
        assert b.drift_slo_ms == TICK_DRIFT_SLO_MS

    def test_TC_WP04_S06_terminal_states_set(self) -> None:
        """TC-WP04-S06 · HALTED 在 TERMINAL_STATES · 一旦进入不再迁出。"""
        assert TickState.HALTED in TERMINAL_STATES
        assert TickState.RUNNING not in TERMINAL_STATES
        assert TickState.PAUSED not in TERMINAL_STATES

    def test_TC_WP04_S07_tick_event_enum_coverage(self) -> None:
        """TC-WP04-S07 · TickEventType 覆盖 8 类审计点。"""
        expected = {
            "tick_scheduled",
            "tick_dispatched",
            "tick_completed",
            "tick_drift_violated",
            "halt_received",
            "panic_received",
            "state_changed",
            "action_rejected",
        }
        assert {e.value for e in TickEventType} == expected

    def test_TC_WP04_S08_tick_error_carries_error_code(self) -> None:
        """TC-WP04-S08 · TickError 必带 error_code + project_id + context。"""
        err = TickError(
            error_code="E_TICK_HALTED_REJECT",
            message="halted",
            project_id="pid-001",
            context={"halt_id": "halt-xxx"},
        )
        assert err.error_code == "E_TICK_HALTED_REJECT"
        assert err.project_id == "pid-001"
        assert err.context == {"halt_id": "halt-xxx"}
        assert str(err) == "halted"

    def test_TC_WP04_S09_tick_result_fields(self) -> None:
        """TC-WP04-S09 · TickResult frozen + 必填字段到位。"""
        r = TickResult(
            tick_id="tick-5",
            dispatched=True,
            action_kind="invoke_skill",
            latency_ms=8,
            drift_ms=3,
            drift_violated=False,
            state=TickState.RUNNING,
            reject_reason=None,
        )
        assert r.tick_id == "tick-5"
        assert r.dispatched is True
        assert r.drift_violated is False
        # frozen = 不可变
        with pytest.raises((AttributeError, TypeError)):
            r.dispatched = False  # type: ignore[misc]

    def test_TC_WP04_S10_drift_violation_record_fields(self) -> None:
        """TC-WP04-S10 · DriftViolationRecord 字段完整(HRL-04 审计证据)。"""
        v = DriftViolationRecord(
            tick_id="tick-9",
            project_id="pid-xxx",
            expected_interval_ms=100,
            actual_interval_ms=250,
            drift_ms=150,
            ts_ns=1_000_000_000,
            context={"cause": "gc_pause"},
        )
        assert v.drift_ms == 150
        assert v.expected_interval_ms == 100
        # frozen
        with pytest.raises((AttributeError, TypeError)):
            v.drift_ms = 0  # type: ignore[misc]

    def test_TC_WP04_S11_tick_event_defaults(self) -> None:
        """TC-WP04-S11 · TickEvent 可选字段默认 None · extra 默认 empty dict。"""
        e = TickEvent(
            event_type=TickEventType.TICK_SCHEDULED,
            tick_id="tick-1",
            project_id="pid-xxx",
            ts_ns=1_000,
        )
        assert e.latency_ms is None
        assert e.drift_ms is None
        assert e.extra == {}
