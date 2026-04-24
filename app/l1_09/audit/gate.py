"""L2-03 · AuditGate 三态机 · 对齐 3-1 §8.

状态：OPEN / CLOSED / REBUILDING
合法转换：
- REBUILDING → OPEN（只允许 L2-04 on_system_resumed 触发）
- OPEN → CLOSED（halt 时）
- CLOSED → REBUILDING（clear_halt + restart）
- REBUILDING → CLOSED 直跳 禁止
- OPEN → REBUILDING 需经 CLOSED
"""
from __future__ import annotations

import threading
from datetime import UTC, datetime

from app.l1_09.audit.schemas import (
    AuditGateClosed,
    AuditGateRebuilding,
    AuditInvalidStateTransition,
    GateState,
    GateStateEnum,
)


# 允许的转换表 · §8.1
_ALLOWED_TRANSITIONS: dict[GateStateEnum, set[GateStateEnum]] = {
    GateStateEnum.REBUILDING: {GateStateEnum.OPEN, GateStateEnum.CLOSED},
    GateStateEnum.OPEN: {GateStateEnum.CLOSED, GateStateEnum.REBUILDING},
    GateStateEnum.CLOSED: {GateStateEnum.REBUILDING},
}

# 哪些 caller 被授权做 REBUILDING → OPEN
_AUTHORIZED_OPEN_CALLERS: frozenset[str] = frozenset({
    "L2-04:on_system_resumed",
    "L2-04-on-system-resumed",
    "admin",  # 测试/管理接口
})


class AuditGate:
    """每 project 独立 gate · §3.2.4."""

    def __init__(self, project_id: str, *, initial_state: GateStateEnum = GateStateEnum.OPEN) -> None:
        self._project_id = project_id
        self._state = initial_state
        self._opened_at = datetime.now(UTC).isoformat()
        self._reason: str | None = "boot_initial"
        self._lock = threading.Lock()

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def state(self) -> GateStateEnum:
        with self._lock:
            return self._state

    def snapshot(self) -> GateState:
        with self._lock:
            return GateState(
                state=self._state,
                project_id=self._project_id,
                opened_at=self._opened_at,
                reason=self._reason,
            )

    def transition(
        self,
        to_state: GateStateEnum,
        *,
        reason: str,
        caller: str | None = None,
    ) -> None:
        """守护转换 · 非法转换 raise AuditInvalidStateTransition."""
        with self._lock:
            current = self._state
            allowed = _ALLOWED_TRANSITIONS.get(current, set())
            if to_state not in allowed:
                raise AuditInvalidStateTransition(
                    f"invalid transition: {current} -> {to_state}"
                )
            # REBUILDING → OPEN 必须授权
            if (
                current == GateStateEnum.REBUILDING
                and to_state == GateStateEnum.OPEN
                and caller not in _AUTHORIZED_OPEN_CALLERS
            ):
                raise AuditInvalidStateTransition(
                    f"REBUILDING -> OPEN requires authorized caller (got {caller})"
                )
            self._state = to_state
            self._opened_at = datetime.now(UTC).isoformat()
            self._reason = reason

    def check_open_or_raise(self) -> None:
        """若 state != OPEN · raise 对应 error（query 前调）."""
        with self._lock:
            if self._state == GateStateEnum.CLOSED:
                raise AuditGateClosed(f"gate CLOSED for {self._project_id}")
            if self._state == GateStateEnum.REBUILDING:
                raise AuditGateRebuilding(
                    f"gate REBUILDING for {self._project_id} · retry later"
                )


class AuditGateRegistry:
    """多 project gate 登记."""

    def __init__(self) -> None:
        self._gates: dict[str, AuditGate] = {}
        self._lock = threading.Lock()

    def get_or_create(self, project_id: str) -> AuditGate:
        with self._lock:
            g = self._gates.get(project_id)
            if g is None:
                g = AuditGate(project_id)
                self._gates[project_id] = g
            return g


__all__ = [
    "AuditGate",
    "AuditGateRegistry",
]
