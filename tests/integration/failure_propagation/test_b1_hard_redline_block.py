"""B1 · L1-07 → L1-01 硬红线 BLOCK 链(IC-15) ≤ 100ms · 5 TC.

链路:
    硬红线触发 → IC-15 request_hard_halt → L1-01 halt(state=HALTED)
    SLO: halt_latency_ms ≤ 100ms (HRL-05 release blocker)
"""
from __future__ import annotations

import time

import pytest

from app.supervisor.event_sender.halt_requester import HaltRequester, MockHardHaltTarget
from app.supervisor.event_sender.schemas import HardHaltState
from tests.shared.ic_assertions import assert_panic_within_100ms


class TestB1HardRedlineBlock:
    """B1 · IC-15 硬红线 BLOCK 链 · 5 TC."""

    async def test_b1_01_redline_triggers_halt_within_100ms(
        self,
        halt_requester: HaltRequester,
        halt_target: MockHardHaltTarget,
        make_halt_command,
        project_id: str,
    ) -> None:
        """B1.1: 命中硬红线 HRL-01 · halt 在 100ms 内 · L1-01 state=HALTED."""
        cmd = make_halt_command(project_id=project_id, red_line_id="HRL-01")
        start = time.monotonic()
        ack = await halt_requester.request_hard_halt(cmd)
        end = time.monotonic()
        # SLO 校验
        assert_panic_within_100ms(start, end, budget_ms=100.0)
        # 状态机
        assert ack.halted is True
        assert ack.state_after == HardHaltState.HALTED
        assert ack.state_before == HardHaltState.RUNNING
        # halt_latency_ms 字段
        assert ack.halt_latency_ms <= 100, f"latency={ack.halt_latency_ms}ms"
        # target.halt_log 记录
        assert halt_target.halt_call_count == 1
        assert halt_target.halt_log[0] == ("halt-001", "HRL-01")

    async def test_b1_02_l1_01_state_halted_after_redline(
        self,
        halt_requester: HaltRequester,
        halt_target: MockHardHaltTarget,
        make_halt_command,
        project_id: str,
    ) -> None:
        """B1.2: halt 后 L1-01 current_state=HALTED · 不再接受 tick."""
        cmd = make_halt_command(project_id=project_id, red_line_id="HRL-02")
        await halt_requester.request_hard_halt(cmd)
        # halt_target 已转 HALTED
        assert halt_target.current_state == HardHaltState.HALTED

    async def test_b1_03_idempotent_halt_same_red_line_id(
        self,
        halt_requester: HaltRequester,
        halt_target: MockHardHaltTarget,
        make_halt_command,
        project_id: str,
    ) -> None:
        """B1.3: 同 red_line_id 重复触发 · idem cache 直返首次 ack · halt_target 只调 1 次.

        IC-15 §3.15.5 幂等 by red_line_id.
        """
        cmd1 = make_halt_command(
            project_id=project_id, red_line_id="HRL-03", halt_id="halt-aaa1"
        )
        cmd2 = make_halt_command(
            project_id=project_id, red_line_id="HRL-03", halt_id="halt-aaa2"
        )
        ack1 = await halt_requester.request_hard_halt(cmd1)
        ack2 = await halt_requester.request_hard_halt(cmd2)
        # 二次返首次 cached ack
        assert ack1.halt_id == ack2.halt_id == "halt-aaa1"
        # halt_target 只调一次
        assert halt_target.halt_call_count == 1

    async def test_b1_04_cross_pid_halt_rejected(
        self,
        halt_requester: HaltRequester,
        make_halt_command,
        project_id: str,
        other_project_id: str,
    ) -> None:
        """B1.4: 跨 pid halt request 被拒 · raise ValueError E_HALT_NO_PROJECT_ID.

        IC-15 §3.15.4: HaltRequester.session_pid 锁死 · 跨 pid 直接拒.
        """
        cmd = make_halt_command(
            project_id=other_project_id,  # 跨 pid
            red_line_id="HRL-04",
        )
        with pytest.raises(ValueError, match="E_HALT_NO_PROJECT_ID"):
            await halt_requester.request_hard_halt(cmd)

    async def test_b1_05_slo_violation_emits_alert(
        self,
        project_id: str,
        sup_event_bus,
        make_halt_command,
    ) -> None:
        """B1.5: halt 慢路径(slow_halt_ms=150) · halt_latency 超 100ms · 触发 SLO 告警.

        IC-15 §3.15.6: latency > 100ms emit L1-07:halt_slo_violated 事件.
        """
        slow_target = MockHardHaltTarget(
            initial_state=HardHaltState.RUNNING,
            slow_halt_ms=150,  # 强制慢
        )
        slow_requester = HaltRequester(
            session_pid=project_id,
            target=slow_target,
            event_bus=sup_event_bus,
        )
        cmd = make_halt_command(project_id=project_id, red_line_id="HRL-05")
        ack = await slow_requester.request_hard_halt(cmd)
        # ack.halted=true 但 latency 超
        assert ack.halted is True
        assert ack.halt_latency_ms >= 100
        # SLO 违反事件应在 sup_event_bus 中
        events = sup_event_bus._events  # 内部 list
        slo_events = [e for e in events if e.type == "L1-07:halt_slo_violated"]
        assert len(slo_events) == 1
        assert slo_events[0].payload["error_code"] == "E_HALT_SLO_VIOLATION"
