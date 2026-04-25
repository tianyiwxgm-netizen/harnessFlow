"""Scenario 06 · panic fixtures · 真实 PanicHandler + HaltEnforcer + L1-09 EventBus.

PanicSignal pid 强约束 ^pid-[A-Za-z0-9_-]{3,}$ · 与 scenario_05 不一样.
3 panic 模式由 reason 字段区分 (M1: bus_fsync · M2: hash_chain · M3: bus_write).
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.halt_guard import HaltGuard
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.panic_handler import (
    PanicHandler,
    PanicSignal,
)
# 共享 GWT DSL · acceptance 必用
from tests.shared.gwt_helpers import gwt  # noqa: F401


@pytest.fixture
def project_id() -> str:
    """scenario_06 panic 用 pid · PanicSignal 要求 ^pid-[A-Za-z0-9_-]{3,}$."""
    return "pid-acc06-panic"


@pytest.fixture
def event_bus_root(tmp_path: Path) -> Path:
    """L1-09 真实 event bus 根目录."""
    root = tmp_path / "bus_root"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def real_event_bus(event_bus_root: Path) -> EventBus:
    """真实 L1-09 EventBus · panic 期间 audit 闭环测."""
    return EventBus(event_bus_root)


@pytest.fixture
def halt_enforcer(project_id: str) -> HaltEnforcer:
    """真实 HaltEnforcer · 干净初态 RUNNING."""
    return HaltEnforcer(project_id=project_id)


@pytest.fixture
def panic_handler(project_id: str, halt_enforcer: HaltEnforcer) -> PanicHandler:
    """真实 PanicHandler · 100ms SLO 强约束."""
    return PanicHandler(project_id=project_id, halt_enforcer=halt_enforcer)


# ============================================================================
# 3 panic 模式工厂
# ============================================================================


@pytest.fixture
def make_panic_signal(project_id: str):
    """工厂 · panic_id / user_id / reason / scope 默认齐."""

    def _mk(
        *,
        panic_id: str = "panic-default",
        user_id: str = "system-supervisor",
        reason: str | None = None,
        scope: str = "tick",
        pid_override: str | None = None,
    ) -> PanicSignal:
        return PanicSignal(
            panic_id=panic_id,
            project_id=pid_override or project_id,
            user_id=user_id,
            reason=reason,
            ts=datetime.now(UTC).isoformat(),
            scope=scope,  # type: ignore[arg-type]
        )

    return _mk


# 3 模式 reason 常量 (T1-T3 用)
PANIC_MODE_M1_BUS_FSYNC = "M1: bus_fsync_failed (events.jsonl ENOSPC simulated)"
PANIC_MODE_M2_HASH_CHAIN = "M2: hash_chain_broken (prev_hash mismatch at seq=42)"
PANIC_MODE_M3_BUS_WRITE = "M3: bus_write_failed (append_atomic POSIX EIO retries)"
