"""IC-17 集成 fixtures · 真实 PanicHandler + HaltEnforcer.

铁律:
- 真实 import L2-01 panic_handler / halt_enforcer
- 100ms SLO 硬约束 · panic_latency_ms <= 100
- PanicSignal 必须 panic_id / project_id / user_id 齐全(schema 强校)
- pid 格式 ^pid-[A-Za-z0-9_-]{3,}$
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.panic_handler import (
    PanicHandler,
    PanicSignal,
)


@pytest.fixture
def project_id() -> str:
    """IC-17 默认 pid · panic_handler schema 要求 ^pid-[A-Za-z0-9_-]{3,}$ ."""
    return "pid-ic17-default"


@pytest.fixture
def other_project_id() -> str:
    return "pid-ic17-other"


@pytest.fixture
def halt_enforcer(project_id: str) -> HaltEnforcer:
    """干净 HaltEnforcer · 初始 RUNNING."""
    return HaltEnforcer(project_id=project_id)


@pytest.fixture
def panic_handler(project_id: str, halt_enforcer: HaltEnforcer) -> PanicHandler:
    return PanicHandler(
        project_id=project_id, halt_enforcer=halt_enforcer,
    )


@pytest.fixture
def make_panic_signal(project_id: str):
    """工厂 · panic_id / user_id / scope 默认齐全."""

    def _mk(
        *,
        panic_id: str = "panic-default-evt",
        user_id: str = "user-admin",
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
