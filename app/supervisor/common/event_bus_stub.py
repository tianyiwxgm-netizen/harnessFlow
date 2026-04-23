"""内存 IC-09 append + IC-11 read_event_stream / read_event_bus_stats · 测试期 stub。

生产替代：L1-09 真实 event_bus。本 stub 供 L1-07 单元/集成测试驱动 · 不进 prod。
锁：asyncio.Lock 包装写 · 保证 event_id 单调。
事件时间：逻辑 monotonic_ms 自增 · 便于 deterministic 断言。
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Event:
    """IC-09 事件 envelope · 最小可用字段集。"""

    event_id: str
    type: str
    project_id: str
    triggered_at_ms: int
    payload: dict[str, Any]
    evidence_refs: tuple[str, ...] = ()


class EventBusStub:
    """L1-07 依赖的 IC-09 + IC-11 双接口内存实现。"""

    def __init__(self) -> None:
        self._events: list[Event] = []
        self._lock = asyncio.Lock()
        self._wall_ms = 0  # monotonic 逻辑时钟 · 每 append +1

    async def append_event(
        self,
        project_id: str,
        type: str,
        payload: dict[str, Any],
        evidence_refs: tuple[str, ...] = (),
    ) -> str:
        if not project_id:
            raise ValueError("project_id is required (PM-14)")
        async with self._lock:
            self._wall_ms += 1
            ev = Event(
                event_id=f"ev-{uuid.uuid4().hex[:12]}",
                type=type,
                project_id=project_id,
                triggered_at_ms=self._wall_ms,
                payload=dict(payload),
                evidence_refs=tuple(evidence_refs),
            )
            self._events.append(ev)
            return ev.event_id

    async def read_event_stream(
        self,
        project_id: str,
        types: list[str] | None = None,
        window_sec: int = 60,
    ) -> list[Event]:
        async with self._lock:
            cutoff = self._wall_ms - window_sec * 1000
            return [
                e
                for e in self._events
                if e.project_id == project_id
                and e.triggered_at_ms >= cutoff
                and (types is None or e.type in types)
            ]

    async def read_event_bus_stats(
        self, project_id: str, window_sec: int = 30
    ) -> dict[str, Any]:
        evs = await self.read_event_stream(
            project_id=project_id, types=None, window_sec=window_sec
        )
        return {
            "event_count_last_30s": len(evs),
            "event_lag_ms": 0 if not evs else max(0, self._wall_ms - evs[-1].triggered_at_ms),
            "event_types": sorted({e.type for e in evs}),
        }
