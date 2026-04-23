"""IC-09 append_event mock · Dev-α L1-09 未就绪期间的本地替代。

契约（对齐 ic-contracts.md §3.9 + L2-07 tech §7.5）：
  - emit(project_id, event_type, payload, severity="INFO", caller_l2=None) -> None
  - 正常态：append 到 events 列表
  - DEGRADED_AUDIT：buffer 而非 events · 不 raise
  - 测试辅助：force_fail / recover
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal


EventSeverity = Literal["INFO", "WARN", "CRITICAL"]


@dataclass
class EmittedEvent:
    ts: float
    project_id: str
    event_type: str
    payload: dict[str, Any]
    severity: EventSeverity
    caller_l2: str | None = None


@dataclass
class EventEmitter:
    """In-memory · 测试 + mock 阶段用。Dev-α IC-09 就绪后换 adapter。"""

    events: list[EmittedEvent] = field(default_factory=list)
    state: str = "NORMAL"
    buffer: list[EmittedEvent] = field(default_factory=list)
    _fail_count: int = 0
    _fail_threshold: int = 3
    buffer_max: int = 1024

    def emit(
        self,
        project_id: str,
        event_type: str,
        payload: dict[str, Any],
        severity: EventSeverity = "INFO",
        caller_l2: str | None = None,
    ) -> None:
        evt = EmittedEvent(
            ts=time.time(),
            project_id=project_id,
            event_type=event_type,
            payload=payload,
            severity=severity,
            caller_l2=caller_l2,
        )
        if self.state == "NORMAL":
            self.events.append(evt)
            return
        # DEGRADED_AUDIT：buffer，不 raise
        if len(self.buffer) < self.buffer_max:
            self.buffer.append(evt)

    def emitted_events(self) -> list[dict[str, Any]]:
        """扁平化事件列表 · 测试用。payload 展开为顶层字段便于 assert。"""
        out: list[dict[str, Any]] = []
        for e in self.events:
            row: dict[str, Any] = {
                "ts": e.ts,
                "project_id": e.project_id,
                "event_type": e.event_type,
                "payload": e.payload,
                "severity": e.severity,
                "caller_l2": e.caller_l2,
            }
            # 将 payload 顶层字段提升，便于测试直接读
            for k, v in e.payload.items():
                row.setdefault(k, v)
            out.append(row)
        return out

    def force_fail(self) -> None:
        """测试辅助 · 模拟 IC-09 连续失败进 DEGRADED_AUDIT。"""
        self._fail_count += 1
        if self._fail_count >= self._fail_threshold:
            self.state = "DEGRADED_AUDIT"

    def recover(self) -> None:
        """测试辅助 · buffer flush 到 events 并回 NORMAL。"""
        self.events.extend(self.buffer)
        self.buffer.clear()
        self._fail_count = 0
        self.state = "NORMAL"
