"""ε-WP05 · L2-05 失败回退协调器单元测试（≥ 38 TC）。

覆盖：
- §1 FailureCounter 5 态机（NORMAL → RETRY_1 → RETRY_2 → RETRY_3 → ESCALATED）
- §2 FailureCounter 幂等 / 隔离（每 wp_id 独立）
- §3 Escalator IC-14 / IC-15 出口
- §4 RollbackAdvice schema + AdviceOption enum
- §5 RollbackCoordinator · on_wp_failed 首次 / 连续 2 / 连续 3+
- §6 RollbackCoordinator · on_wp_done_reset 幂等
- §7 RollbackCoordinator · 独立 WP counter 隔离
- §8 RollbackCoordinator · on_deadlock_notified → IC-15 halt
- §9 Manager 集成（mark_stuck 在升级时联动）
- §10 事件 emit
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.l1_03.common.event_bus_stub import EventBusStub
from app.l1_03.rollback import (
    AdviceOption,
    Escalator,
    FailureCounter,
    FailureCounterSnapshot,
    FailureCounterState,
    RollbackAdvice,
    RollbackCoordinator,
    RollbackRoute,
)
from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.state_machine import State

# =====================================================================
# §1 FailureCounter 5 态机转换
# =====================================================================

class TestFailureCounterTransitions:
    def test_initial_state_normal(self) -> None:
        c = FailureCounter()
        assert c.state_of("wp-a") == FailureCounterState.NORMAL
        assert c.count_of("wp-a") == 0

    def test_TC_L103_L205_101_normal_to_retry1(self) -> None:
        c = FailureCounter()
        nxt = c.on_failed("wp-a")
        assert nxt == FailureCounterState.RETRY_1
        assert c.count_of("wp-a") == 1

    def test_retry1_to_retry2(self) -> None:
        c = FailureCounter()
        c.on_failed("wp-a")
        nxt = c.on_failed("wp-a")
        assert nxt == FailureCounterState.RETRY_2
        assert c.count_of("wp-a") == 2

    def test_TC_L103_L205_103_retry2_to_retry3_escalates(self) -> None:
        c = FailureCounter()
        for _ in range(3):
            nxt = c.on_failed("wp-a")
        assert nxt == FailureCounterState.RETRY_3
        assert c.is_escalated("wp-a") is True

    def test_retry3_to_escalated_sticky(self) -> None:
        c = FailureCounter()
        for _ in range(4):
            nxt = c.on_failed("wp-a")
        assert nxt == FailureCounterState.ESCALATED
        # 再失败仍 ESCALATED
        c.on_failed("wp-a")
        assert c.state_of("wp-a") == FailureCounterState.ESCALATED

    def test_is_escalated_covers_retry3_and_escalated(self) -> None:
        c = FailureCounter()
        for _ in range(3):
            c.on_failed("wp-a")
        assert c.state_of("wp-a") == FailureCounterState.RETRY_3
        assert c.is_escalated("wp-a") is True
        c.on_failed("wp-a")  # 进入 ESCALATED
        assert c.is_escalated("wp-a") is True


# =====================================================================
# §2 FailureCounter 幂等 / 隔离
# =====================================================================

class TestFailureCounterResetAndIsolation:
    def test_TC_L103_L205_105_done_reset_idempotent(self) -> None:
        c = FailureCounter()
        c.on_failed("wp-a")
        c.on_done_reset("wp-a")
        assert c.state_of("wp-a") == FailureCounterState.NORMAL
        # 再 reset 不 raise
        c.on_done_reset("wp-a")
        c.on_done_reset("wp-a")
        assert c.state_of("wp-a") == FailureCounterState.NORMAL

    def test_reset_unknown_wp_no_raise(self) -> None:
        c = FailureCounter()
        c.on_done_reset("wp-never-seen")  # 不 raise
        assert c.state_of("wp-never-seen") == FailureCounterState.NORMAL

    def test_TC_L103_L205_107_wp_isolation(self) -> None:
        c = FailureCounter()
        c.on_failed("wp-a")
        c.on_failed("wp-a")
        c.on_failed("wp-b")
        assert c.state_of("wp-a") == FailureCounterState.RETRY_2
        assert c.state_of("wp-b") == FailureCounterState.RETRY_1
        # reset wp-a 不影响 wp-b
        c.on_done_reset("wp-a")
        assert c.state_of("wp-a") == FailureCounterState.NORMAL
        assert c.state_of("wp-b") == FailureCounterState.RETRY_1

    def test_reset_all_clears_everything(self) -> None:
        c = FailureCounter()
        c.on_failed("wp-a")
        c.on_failed("wp-b")
        c.reset_all()
        assert c.state_of("wp-a") == FailureCounterState.NORMAL
        assert c.count_of("wp-a") == 0
        assert c.state_of("wp-b") == FailureCounterState.NORMAL


# =====================================================================
# §3 Escalator
# =====================================================================

class TestEscalator:
    def test_push_rollback_route_captured(self, project_id: str) -> None:
        e = Escalator()
        advice = RollbackAdvice(
            wp_id="wp-a", project_id=project_id, failure_count=3,
            options=[AdviceOption.SPLIT_WP], evidence_refs=[],
        )
        route = RollbackRoute(route_id="r1", project_id=project_id, advice=advice)
        e.push_rollback_route(route)
        assert len(e.captured_routes) == 1
        assert e.captured_routes[0].route_id == "r1"

    def test_push_rollback_route_forwards_to_emitter(self, project_id: str) -> None:
        delivered: list[RollbackRoute] = []
        e = Escalator(on_push_rollback=lambda r: delivered.append(r))
        advice = RollbackAdvice(
            wp_id="wp-a", project_id=project_id, failure_count=3,
            options=[AdviceOption.SPLIT_WP],
        )
        e.push_rollback_route(RollbackRoute(route_id="r1", project_id=project_id, advice=advice))
        assert len(delivered) == 1

    def test_request_hard_halt_captured(self) -> None:
        e = Escalator()
        e.request_hard_halt("pid-a", "deadlock")
        assert e.captured_halts == [("pid-a", "deadlock")]

    def test_request_hard_halt_forwards(self) -> None:
        delivered: list[tuple[str, str]] = []
        e = Escalator(on_request_halt=lambda p, r: delivered.append((p, r)))
        e.request_hard_halt("pid-a", "x")
        assert delivered == [("pid-a", "x")]


# =====================================================================
# §4 Schemas
# =====================================================================

class TestSchemas:
    def test_advice_option_enum(self) -> None:
        assert str(AdviceOption.SPLIT_WP) == "split_wp"
        assert str(AdviceOption.MODIFY_WBS) == "modify_wbs"
        assert str(AdviceOption.MODIFY_AC) == "modify_ac"

    def test_rollback_advice_frozen(self, project_id: str) -> None:
        a = RollbackAdvice(
            wp_id="wp-a", project_id=project_id, failure_count=3,
            options=[AdviceOption.SPLIT_WP],
        )
        with pytest.raises(ValidationError):
            a.wp_id = "wp-hack"  # type: ignore[misc]

    def test_rollback_advice_failure_count_min(self, project_id: str) -> None:
        with pytest.raises(ValidationError):
            RollbackAdvice(
                wp_id="wp-a", project_id=project_id, failure_count=0,  # 至少 1
            )

    def test_failure_counter_snapshot(self) -> None:
        s = FailureCounterSnapshot(
            wp_id="wp-a", state="RETRY_2", consecutive_failures=2,
        )
        assert s.state == "RETRY_2"
        assert s.consecutive_failures == 2


# =====================================================================
# §5 Coordinator on_wp_failed
# =====================================================================

class TestCoordinatorFailedPath:
    def test_TC_L103_L205_201_first_failure_no_escalation(
        self, project_id: str, event_bus: EventBusStub,
    ) -> None:
        c = RollbackCoordinator(project_id=project_id, event_bus=event_bus)
        c.on_wp_failed("wp-a", reason="first try")
        assert c.counter.state_of("wp-a") == FailureCounterState.RETRY_1
        assert c.escalator.captured_routes == []

    def test_second_failure_no_escalation(
        self, project_id: str, event_bus: EventBusStub,
    ) -> None:
        c = RollbackCoordinator(project_id=project_id, event_bus=event_bus)
        c.on_wp_failed("wp-a")
        c.on_wp_failed("wp-a")
        assert c.counter.state_of("wp-a") == FailureCounterState.RETRY_2
        assert c.escalator.captured_routes == []

    def test_TC_L103_L205_202_third_failure_escalates(
        self, project_id: str, event_bus: EventBusStub,
    ) -> None:
        """连续 3 次失败 → RETRY_3 + IC-14 push_rollback_route。"""
        c = RollbackCoordinator(project_id=project_id, event_bus=event_bus)
        c.on_wp_failed("wp-a", reason="r1")
        c.on_wp_failed("wp-a", reason="r2")
        c.on_wp_failed("wp-a", reason="r3")
        assert c.counter.state_of("wp-a") == FailureCounterState.RETRY_3
        assert len(c.escalator.captured_routes) == 1
        route = c.escalator.captured_routes[0]
        assert route.advice.wp_id == "wp-a"
        assert route.advice.failure_count == 3
        assert len(route.advice.options) == 3
        assert AdviceOption.SPLIT_WP in route.advice.options

    def test_advice_options_are_three_by_default(
        self, project_id: str,
    ) -> None:
        c = RollbackCoordinator(project_id=project_id)
        for _ in range(3):
            c.on_wp_failed("wp-a")
        advice = c.escalator.captured_routes[0].advice
        assert advice.options == [
            AdviceOption.SPLIT_WP,
            AdviceOption.MODIFY_WBS,
            AdviceOption.MODIFY_AC,
        ]

    def test_evidence_ref_propagated(self, project_id: str) -> None:
        c = RollbackCoordinator(project_id=project_id)
        for _ in range(2):
            c.on_wp_failed("wp-a")
        c.on_wp_failed("wp-a", evidence_ref="artifacts/wp-a-fail.tar.gz")
        advice = c.escalator.captured_routes[0].advice
        assert advice.evidence_refs == ["artifacts/wp-a-fail.tar.gz"]

    def test_fourth_failure_keeps_escalated(self, project_id: str) -> None:
        """第 4 次失败仍在 ESCALATED 状态 · 再触发一次 IC-14（粘性 · 每次都报）。"""
        c = RollbackCoordinator(project_id=project_id)
        for i in range(4):
            c.on_wp_failed("wp-a")
        # RETRY_3 (第3次) → ESCALATED (第4次) · 每次都 emit 一个 route
        assert len(c.escalator.captured_routes) == 2


# =====================================================================
# §6 Coordinator on_wp_done_reset
# =====================================================================

class TestCoordinatorDoneReset:
    def test_reset_clears_counter(self, project_id: str) -> None:
        c = RollbackCoordinator(project_id=project_id)
        c.on_wp_failed("wp-a")
        c.on_wp_failed("wp-a")
        assert c.counter.state_of("wp-a") == FailureCounterState.RETRY_2
        c.on_wp_done_reset("wp-a")
        assert c.counter.state_of("wp-a") == FailureCounterState.NORMAL
        # 下次失败从 NORMAL 起（不是 RETRY_2 接续）
        c.on_wp_failed("wp-a")
        assert c.counter.state_of("wp-a") == FailureCounterState.RETRY_1

    def test_reset_unknown_wp_idempotent(self, project_id: str) -> None:
        c = RollbackCoordinator(project_id=project_id)
        c.on_wp_done_reset("wp-unknown")  # 不 raise
        c.on_wp_done_reset("wp-unknown")

    def test_reset_idempotent_for_normal_state(self, project_id: str) -> None:
        c = RollbackCoordinator(project_id=project_id)
        c.on_wp_done_reset("wp-a")
        c.on_wp_done_reset("wp-a")
        assert c.counter.state_of("wp-a") == FailureCounterState.NORMAL


# =====================================================================
# §7 WP 隔离
# =====================================================================

class TestCoordinatorWPIsolation:
    def test_wp_a_failure_doesnt_affect_wp_b(self, project_id: str) -> None:
        c = RollbackCoordinator(project_id=project_id)
        c.on_wp_failed("wp-a")
        c.on_wp_failed("wp-a")
        c.on_wp_failed("wp-a")  # wp-a RETRY_3
        # wp-b 首次失败 · 应仍 RETRY_1
        c.on_wp_failed("wp-b")
        assert c.counter.state_of("wp-a") == FailureCounterState.RETRY_3
        assert c.counter.state_of("wp-b") == FailureCounterState.RETRY_1
        # wp-b 的 advice 不应被发（未升级）
        # 只 wp-a 一个升级
        assert len(c.escalator.captured_routes) == 1
        assert c.escalator.captured_routes[0].advice.wp_id == "wp-a"


# =====================================================================
# §8 on_deadlock_notified
# =====================================================================

class TestDeadlockNotification:
    def test_TC_L103_L205_301_deadlock_triggers_hard_halt(
        self, project_id: str, event_bus: EventBusStub,
    ) -> None:
        c = RollbackCoordinator(project_id=project_id, event_bus=event_bus)
        c.on_deadlock_notified(project_id, reason="all paths stuck")
        assert len(c.escalator.captured_halts) == 1
        pid, reason = c.escalator.captured_halts[0]
        assert pid == project_id
        assert "deadlock" in reason.lower()

    def test_deadlock_pm14_cross_pid_ignored(self, project_id: str) -> None:
        c = RollbackCoordinator(project_id=project_id)
        c.on_deadlock_notified("pid-OTHER")
        assert c.escalator.captured_halts == []

    def test_deadlock_emits_event(
        self, project_id: str, event_bus: EventBusStub,
    ) -> None:
        c = RollbackCoordinator(project_id=project_id, event_bus=event_bus)
        event_bus.reset()
        c.on_deadlock_notified(project_id, reason="dead")
        ev = event_bus.filter(event_type="L1-03:request_hard_halt")
        assert len(ev) == 1


# =====================================================================
# §9 Manager 集成
# =====================================================================

class TestManagerIntegration:
    def test_escalation_calls_mark_stuck(
        self, project_id: str, event_bus: EventBusStub, make_wp,
    ) -> None:
        """RETRY_3 升级时 · 如果有 manager，调 mark_stuck（FAILED→STUCK）。"""
        mgr = WBSTopologyManager(project_id=project_id, event_bus=event_bus)
        mgr.load_topology([make_wp("wp-a")], [])
        # 先把 wp-a 走到 FAILED（这样 mark_stuck 才合法）
        mgr.transition_state("wp-a", State.READY, State.RUNNING)
        mgr.transition_state("wp-a", State.RUNNING, State.FAILED)
        c = RollbackCoordinator(
            project_id=project_id, manager=mgr, event_bus=event_bus,
        )
        for _ in range(3):
            c.on_wp_failed("wp-a")
        wp = mgr.find_wp("wp-a")
        assert wp is not None and wp.state == State.STUCK

    def test_escalation_without_manager_works(self, project_id: str) -> None:
        """无 manager · 也能走升级（advice 发 · mark_stuck 跳过）。"""
        c = RollbackCoordinator(project_id=project_id, manager=None)
        for _ in range(3):
            c.on_wp_failed("wp-a")
        assert len(c.escalator.captured_routes) == 1

    def test_mark_stuck_failure_silent(self, project_id: str, make_wp) -> None:
        """如果 mark_stuck 失败（如 wp 不在 FAILED 态）· 升级仍发出。"""
        c = RollbackCoordinator(project_id=project_id)
        # 注入坏 manager
        class _BadMgr:
            def mark_stuck(self, _wp_id: str) -> None:
                raise RuntimeError("wp 不在 FAILED 态")
        c._manager = _BadMgr()  # noqa: SLF001
        for _ in range(3):
            c.on_wp_failed("wp-a")
        # 升级仍成功（advice 发了）
        assert len(c.escalator.captured_routes) == 1


# =====================================================================
# §10 事件 emit
# =====================================================================

class TestEventEmit:
    def test_advice_issued_event_emitted(
        self, project_id: str, event_bus: EventBusStub,
    ) -> None:
        c = RollbackCoordinator(project_id=project_id, event_bus=event_bus)
        for _ in range(3):
            c.on_wp_failed("wp-a", reason="explosion")
        ev = event_bus.filter(event_type="L1-03:rollback_advice_issued")
        assert len(ev) == 1
        assert ev[0].content["failure_count"] == 3
        assert ev[0].content["options"] == ["split_wp", "modify_wbs", "modify_ac"]
        assert "explosion" in ev[0].content["reason"]
        assert ev[0].project_id == project_id

    def test_no_event_before_escalation(
        self, project_id: str, event_bus: EventBusStub,
    ) -> None:
        c = RollbackCoordinator(project_id=project_id, event_bus=event_bus)
        c.on_wp_failed("wp-a")
        c.on_wp_failed("wp-a")
        ev = event_bus.filter(event_type="L1-03:rollback_advice_issued")
        assert len(ev) == 0


# =====================================================================
# §11 snapshot + PM-14
# =====================================================================

class TestSnapshotAndPM14:
    def test_snapshot_of_wp(self, project_id: str) -> None:
        c = RollbackCoordinator(project_id=project_id)
        c.on_wp_failed("wp-a")
        snap = c.snapshot("wp-a")
        assert snap.wp_id == "wp-a"
        assert snap.state == "RETRY_1"
        assert snap.consecutive_failures == 1

    def test_coordinator_requires_project_id(self) -> None:
        with pytest.raises(ValueError, match="PM-14"):
            RollbackCoordinator(project_id="")
