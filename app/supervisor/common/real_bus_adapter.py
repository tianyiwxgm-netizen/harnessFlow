"""L1-09 真实 event_bus 的 supervisor-friendly 适配器。

在 ζ1 阶段 supervisor 代码依赖 `EventBusStub.append_event()` 的 async 接口。
本适配器把 `app.l1_09.event_bus.EventBus.append(Event)` 同步接口包一层 async ·
保留同样签名 · 生产可无缝切换。

注意 L1-09 的 Event 约束：
- type 必须匹配 `^L1-(01|02|...|10):[a-z0-9_]+$`
- actor 必须白名单 · supervisor 事件用 actor='supervisor'
- project_id 必须 `^[a-z0-9_-]{1,40}$` 或字面 'system'
- timestamp 必须 datetime
- payload 是 dict[str, Any]
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.l1_09.event_bus import Event, EventBus


class L109EventBusAdapter:
    """把 L1-09 EventBus 暴露为 supervisor 侧 event_bus_stub 同签名。"""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    async def append_event(
        self,
        project_id: str,
        type: str,
        payload: dict[str, Any],
        evidence_refs: tuple[str, ...] = (),
    ) -> str:
        """append 一条 L1-07 supervisor 事件。"""
        ev = Event(
            project_id=project_id,
            type=type,
            actor="supervisor",
            timestamp=datetime.now(tz=UTC),
            payload={
                **payload,
                "evidence_refs": list(evidence_refs),
            },
        )
        result = self._bus.append(ev)
        return result.event_id

    async def read_event_stream(
        self,
        project_id: str,
        types: list[str] | None = None,
        window_sec: int = 60,
    ) -> list[Any]:
        """read range 包装为 list。

        L1-09.read_range 返回 dict · 为兼容 stub（访问 .type 的用法）·
        转成 _EventWrap · 提供 .type / .payload / .project_id 属性。
        """
        raw = list(self._bus.read_range(project_id=project_id))
        events = [_EventWrap(d) for d in raw]
        if types is None:
            return events
        return [e for e in events if e.type in types]


class _EventWrap:
    """Wrap dict 为 attribute-accessible 对象 · 兼容 stub 接口。"""

    def __init__(self, d: dict[str, Any]) -> None:
        self._d = d

    @property
    def type(self) -> str:
        return str(self._d.get("type", ""))

    @property
    def project_id(self) -> str:
        return str(self._d.get("project_id", ""))

    @property
    def event_id(self) -> str:
        return str(self._d.get("event_id", ""))

    @property
    def payload(self) -> dict[str, Any]:
        return dict(self._d.get("payload", {}))

    @property
    def evidence_refs(self) -> list[str]:
        return list(self.payload.get("evidence_refs", []))


def make_adapter_with_tmp_root(tmp_path: Path) -> L109EventBusAdapter:
    """测试助手 · 在 tmp_path 下起一个 L1-09 EventBus。"""
    bus = EventBus(root=tmp_path)
    return L109EventBusAdapter(bus)
