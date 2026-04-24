"""TC-WP04-HE01..HE12 · HaltEnforcer · HRL-05 halt 协议 + reject 语义。"""
from __future__ import annotations

import pytest

from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.schemas import (
    E_TICK_HALTED_REJECT,
    E_TICK_PAUSED_REJECT,
    TickError,
    TickState,
)
from app.supervisor.event_sender.schemas import HardHaltState


@pytest.fixture
def enforcer() -> HaltEnforcer:
    return HaltEnforcer(project_id="pid-test")


class TestHaltEnforcer:
    """HaltEnforcer · HRL-05 halt 协议 + 各态 reject。"""

    def test_TC_WP04_HE01_initial_state_running(
        self, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-HE01 · 初始 state=RUNNING · is_halted()=False。"""
        assert enforcer.current_state == HardHaltState.RUNNING
        assert enforcer.is_halted() is False
        assert enforcer.as_tick_state() == TickState.RUNNING
        assert enforcer.reject_count == 0
        assert enforcer.active_halt_id is None

    async def test_TC_WP04_HE02_halt_flips_state_and_returns_before(
        self, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-HE02 · halt() 返回 state_before=RUNNING · 翻转到 HALTED。"""
        before = await enforcer.halt(halt_id="halt-1", red_line_id="IRREVERSIBLE_HALT")
        assert before == HardHaltState.RUNNING
        assert enforcer.current_state == HardHaltState.HALTED
        assert enforcer.is_halted() is True
        assert enforcer.as_tick_state() == TickState.HALTED
        assert enforcer.active_halt_id == "halt-1"

    async def test_TC_WP04_HE03_halt_records_history(
        self, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-HE03 · halt history 挂到 halt_history (供 L2-05 审计)。"""
        await enforcer.halt(halt_id="halt-9", red_line_id="AUDIT_MISS")
        h = enforcer.halt_history
        assert len(h) == 1
        assert h[0]["halt_id"] == "halt-9"
        assert h[0]["red_line_id"] == "AUDIT_MISS"
        assert h[0]["state_before"] == "RUNNING"
        assert h[0]["state_after"] == "HALTED"
        assert "latency_ms" in h[0]
        assert "slo_violated" in h[0]

    async def test_TC_WP04_HE04_halt_idempotent(
        self, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-HE04 · 重复 halt · 第 2 次 state_before=HALTED (幂等)。"""
        b1 = await enforcer.halt(halt_id="halt-1", red_line_id="DATA_LOSS")
        b2 = await enforcer.halt(halt_id="halt-2", red_line_id="DATA_LOSS")
        assert b1 == HardHaltState.RUNNING
        assert b2 == HardHaltState.HALTED, "第二次已经 HALTED"
        # history 两条
        assert len(enforcer.halt_history) == 2
        # active_halt_id 保留首次(不被第 2 次覆盖)
        assert enforcer.active_halt_id == "halt-1"

    def test_TC_WP04_HE05_assert_not_halted_passes_when_running(
        self, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-HE05 · 初态调 assert_not_halted · 不抛。"""
        enforcer.assert_not_halted()  # 不抛 = 通过
        assert enforcer.reject_count == 0

    async def test_TC_WP04_HE06_assert_not_halted_raises_after_halt(
        self, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-HE06 · halt 后 assert_not_halted → TickError(E_TICK_HALTED_REJECT)。"""
        await enforcer.halt(halt_id="halt-1", red_line_id="CROSS_PROJECT")
        with pytest.raises(TickError) as exc:
            enforcer.assert_not_halted()
        assert exc.value.error_code == E_TICK_HALTED_REJECT
        assert exc.value.project_id == "pid-test"
        assert exc.value.context["halt_id"] == "halt-1"
        assert enforcer.reject_count == 1

    async def test_TC_WP04_HE07_reject_count_increments(
        self, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-HE07 · 多次 reject · count 递增 (审计可观测)。"""
        await enforcer.halt(halt_id="h1", red_line_id="BUDGET_EXCEED")
        for _ in range(5):
            with pytest.raises(TickError):
                enforcer.assert_not_halted()
        assert enforcer.reject_count == 5

    def test_TC_WP04_HE08_mark_panic_moves_to_paused(
        self, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-HE08 · mark_panic · RUNNING → PAUSED (可逆)。"""
        enforcer.mark_panic()
        assert enforcer.current_state == HardHaltState.PAUSED
        assert enforcer.as_tick_state() == TickState.PAUSED

    def test_TC_WP04_HE09_clear_panic_returns_to_running(
        self, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-HE09 · PAUSED → RUNNING (user resume)。"""
        enforcer.mark_panic()
        enforcer.clear_panic()
        assert enforcer.current_state == HardHaltState.RUNNING

    async def test_TC_WP04_HE10_halted_blocks_mark_panic(
        self, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-HE10 · 已 HALTED · mark_panic 无效 (HALTED 优先级高于 PAUSED)。"""
        await enforcer.halt(halt_id="halt-1", red_line_id="DATA_LOSS")
        enforcer.mark_panic()
        assert enforcer.current_state == HardHaltState.HALTED, "HALTED 不被 PAUSED 降级"

    async def test_TC_WP04_HE11_clear_panic_noop_when_halted(
        self, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-HE11 · HALTED 期间 clear_panic 不翻到 RUNNING (不可逆)。"""
        await enforcer.halt(halt_id="halt-1", red_line_id="DATA_LOSS")
        enforcer.clear_panic()
        assert enforcer.current_state == HardHaltState.HALTED

    def test_TC_WP04_HE12_assert_can_dispatch_rejects_paused(
        self, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-HE12 · PAUSED 期间 assert_can_dispatch → E_TICK_PAUSED_REJECT。"""
        enforcer.mark_panic()
        with pytest.raises(TickError) as exc:
            enforcer.assert_can_dispatch()
        assert exc.value.error_code == E_TICK_PAUSED_REJECT
        assert enforcer.reject_count == 1

    async def test_TC_WP04_HE13_assert_can_dispatch_rejects_halted(
        self, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-HE13 · HALTED 期间 assert_can_dispatch → E_TICK_HALTED_REJECT。"""
        await enforcer.halt(halt_id="h1", red_line_id="IRREVERSIBLE_HALT")
        with pytest.raises(TickError) as exc:
            enforcer.assert_can_dispatch()
        assert exc.value.error_code == E_TICK_HALTED_REJECT

    def test_TC_WP04_HE14_constructor_validates(self) -> None:
        """TC-WP04-HE14 · 构造参数校验(空 pid · 非正 slo)。"""
        with pytest.raises(ValueError, match="project_id"):
            HaltEnforcer(project_id="")
        with pytest.raises(ValueError, match="slo_ms"):
            HaltEnforcer(project_id="pid-x", slo_ms=0)
