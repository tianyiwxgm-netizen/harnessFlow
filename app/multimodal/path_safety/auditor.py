"""ContentAuditor · hash-chained audit events → IC-09 (L2-04 §6.4)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.multimodal.common.event_bus_stub import EventBusStub

_EVENT_TYPES = frozenset({"content_read", "content_written", "path_rejected"})


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class ContentAuditor:
    bus: EventBusStub
    _prev_hash: str = "0" * 64  # genesis

    def emit(self, event_type: str, body: dict[str, Any]) -> dict[str, Any]:
        if event_type not in _EVENT_TYPES:
            raise ValueError(f"unknown audit event_type: {event_type}")
        ts = datetime.now(UTC).isoformat()
        base = {
            "event_type": event_type,
            "ts": ts,
            "prev_hash": self._prev_hash,
            "body": body,
        }
        body_hash = _sha256(_canonical_json(base))
        record = {**base, "body_hash": body_hash}
        self.bus.append_event(record)
        self._prev_hash = body_hash
        return record
