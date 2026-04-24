"""TC-WP04-PH01..PH10 · PanicHandler · IC-17 user_panic ≤ 100ms → PAUSED。"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.panic_handler import (
    PanicHandler,
    PanicResult,
    PanicSignal,
)
from app.main_loop.tick_scheduler.schemas import (
    E_TICK_CROSS_PROJECT,
    E_TICK_PANIC_ALREADY_PAUSED,
    TickError,
    TickState,
)


def _mk_signal(**overrides) -> PanicSignal:
    defaults = dict(
        panic_id="panic-user-001",
        project_id="pid-test-001",
        user_id="user-alice",
        reason="too slow",
        ts="2026-04-23T00:00:00Z",
        scope="tick",
    )
    defaults.update(overrides)
    return PanicSignal(**defaults)


@pytest.fixture
def enforcer() -> HaltEnforcer:
    return HaltEnforcer(project_id="pid-test-001")


@pytest.fixture
def handler(enforcer: HaltEnforcer) -> PanicHandler:
    return PanicHandler(project_id="pid-test-001", halt_enforcer=enforcer)


class TestPanicHandler:
    """PanicHandler · IC-17 panic 主路径 + 异常路径。"""

    def test_TC_WP04_PH01_happy_path_paused_within_100ms(
        self, handler: PanicHandler, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-PH01 · 正常 panic · PAUSED + latency ≤ 100ms (HRL 同级)。"""
        sig = _mk_signal()
        result: PanicResult = handler.handle(sig)
        assert result.paused is True
        assert result.panic_latency_ms <= 100
        assert result.slo_violated is False
        assert result.scope == "tick"
        assert enforcer.as_tick_state() == TickState.PAUSED
        assert handler.active_panic_id == "panic-user-001"

    def test_TC_WP04_PH02_panic_records_history(
        self, handler: PanicHandler,
    ) -> None:
        """TC-WP04-PH02 · history 挂 panic_id / user_id / reason。"""
        handler.handle(_mk_signal(reason="angry"))
        h = handler.panic_history
        assert len(h) == 1
        assert h[0]["panic_id"] == "panic-user-001"
        assert h[0]["user_id"] == "user-alice"
        assert h[0]["reason"] == "angry"
        assert h[0]["scope"] == "tick"
        assert "latency_ms" in h[0]
        assert "slo_violated" in h[0]

    def test_TC_WP04_PH03_cross_project_rejected(
        self, handler: PanicHandler,
    ) -> None:
        """TC-WP04-PH03 · signal.project_id ≠ bound · E_TICK_CROSS_PROJECT 抛。"""
        sig = _mk_signal(project_id="pid-other-999")
        with pytest.raises(TickError) as exc:
            handler.handle(sig)
        assert exc.value.error_code == E_TICK_CROSS_PROJECT

    def test_TC_WP04_PH04_already_paused_raises(
        self, handler: PanicHandler,
    ) -> None:
        """TC-WP04-PH04 · 重复 panic · E_TICK_PANIC_ALREADY_PAUSED 抛(静默处理)。"""
        handler.handle(_mk_signal(panic_id="panic-user-001"))
        sig2 = _mk_signal(panic_id="panic-user-002")
        with pytest.raises(TickError) as exc:
            handler.handle(sig2)
        assert exc.value.error_code == E_TICK_PANIC_ALREADY_PAUSED

    def test_TC_WP04_PH05_resume_returns_running(
        self, handler: PanicHandler, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-PH05 · handler.resume() · PAUSED → RUNNING · panic_id 清。"""
        handler.handle(_mk_signal())
        assert enforcer.as_tick_state() == TickState.PAUSED
        handler.resume()
        assert enforcer.as_tick_state() == TickState.RUNNING
        assert handler.active_panic_id is None

    async def test_TC_WP04_PH06_panic_during_halted_stays_halted(
        self, handler: PanicHandler, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-PH06 · 已 HALTED · panic 不降级 · 但 history 记。"""
        await enforcer.halt(halt_id="halt-001", red_line_id="DATA_LOSS")
        assert enforcer.as_tick_state() == TickState.HALTED
        # HALTED 不等于 PAUSED · 所以 ALREADY_PAUSED 不抛
        result = handler.handle(_mk_signal())
        # paused 名义上 true(返回)· 但 state 仍 HALTED
        assert result.paused is True
        assert enforcer.as_tick_state() == TickState.HALTED
        # history 带 was_halted=True
        assert handler.panic_history[0]["was_halted"] is True

    def test_TC_WP04_PH07_schema_rejects_bad_user_id(self) -> None:
        """TC-WP04-PH07 · schema: user_id 空串被 pydantic 拒(字段级校验)。"""
        with pytest.raises(ValidationError):
            _mk_signal(user_id="")

    def test_TC_WP04_PH08_schema_rejects_bad_project_id_format(self) -> None:
        """TC-WP04-PH08 · schema: project_id 格式不合 · pydantic 拒。"""
        with pytest.raises(ValidationError):
            _mk_signal(project_id="badpid")

    def test_TC_WP04_PH09_schema_rejects_bad_panic_id_format(self) -> None:
        """TC-WP04-PH09 · schema: panic_id 格式不合 (应以 panic- 开头)。"""
        with pytest.raises(ValidationError):
            _mk_signal(panic_id="user-001")

    def test_TC_WP04_PH10_scope_session_preserved(
        self, handler: PanicHandler,
    ) -> None:
        """TC-WP04-PH10 · scope=session 透传到 result。"""
        sig = _mk_signal(scope="session")
        result = handler.handle(sig)
        assert result.scope == "session"

    def test_TC_WP04_PH11_constructor_validates(
        self, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-PH11 · 构造参数校验。"""
        with pytest.raises(ValueError, match="project_id"):
            PanicHandler(project_id="", halt_enforcer=enforcer)
        with pytest.raises(ValueError, match="slo_ms"):
            PanicHandler(project_id="pid-x", halt_enforcer=enforcer, slo_ms=0)

    def test_TC_WP04_PH12_latency_non_negative(
        self, handler: PanicHandler,
    ) -> None:
        """TC-WP04-PH12 · latency_ms 非负(常见问题: perf_counter_ns 起止 wrap)。"""
        result = handler.handle(_mk_signal())
        assert result.panic_latency_ms >= 0
