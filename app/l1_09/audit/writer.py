"""L2-03 · AuditWriter · record_audit 高层 API.

L2-03 不独立写 · 复用 L2-01 append · 但提供高层语义.
对齐 3-1 §3.1 M2 record_audit.
"""
from __future__ import annotations

import ulid
from datetime import UTC, datetime


class AuditWriter:
    """高层 API · 内部 compose Event 调 L2-01.append()."""

    def __init__(self, event_bus, gate_registry) -> None:
        self._bus = event_bus
        self._gates = gate_registry

    def record_audit(
        self,
        *,
        project_id: str,
        action: str,
        actor: str,
        payload: dict,
    ) -> str:
        """§3.1 M2 · 返 AuditID（其实 = event_id）."""
        from app.l1_09.event_bus.schemas import Event

        # audit_id 返给 caller · event_id 走 bus 生成
        audit_id = f"audit_{ulid.new()}"
        safe_action = action.replace(":", "_").replace("-", "_")
        merged_payload = dict(payload)
        merged_payload["audit_id"] = audit_id
        evt = Event(
            project_id=project_id,
            type=f"L1-09:audit_{safe_action}",
            actor=actor,
            payload=merged_payload,
            timestamp=datetime.now(UTC),
        )
        self._bus.append(evt)
        return audit_id


__all__ = ["AuditWriter"]
