"""L2-05 → Dev-α(l1_09.event_bus) 适配层 · 唯一 IC-09 出口.

为什么需要 Adapter:
    - Dev-α `EventBus.append(event: Event) -> AppendEventResult` 是强类型 pydantic 接口 ·
      Event.actor 必须是 `main_loop|planner|...` 白名单 · Event.type 必须是 `L1-XX:*` 格式.
    - TDD mock 断言 `mock_event_bus.append_event.call_args.kwargs["event_type"]` · 即
      kwarg-style 调用签名 · 不走 Event 对象.
    - 本 Adapter 对上暴露统一 `append(**kwargs) -> dict` 风格 · 对下区分是否连 Dev-α 真实 bus.

默认行为(TDD mock 模式):
    调用方传任意 bus · 只要实现 `append_event(**kwargs)` 就用之 · 不构造 Event.

Real mode(生产):
    调用方传 `app.l1_09.event_bus.EventBus` 实例 · Adapter 自动映射:
      - event_type → Event.type(L1-01:xxx)
      - actor → "main_loop"(L1-01 所有 L2 统一 actor)
      - payload/links/project_id/ts → Event.payload/links/project_id/timestamp
      - hash / prev_hash / sequence → 由 Dev-α 自己计算 · 本层不覆盖

如何区分:
    若 bus 有 `append_event` method → kwarg 风格(mock 或 adapter-compatible wrapper)
    否则若有 `append` method 且入参是 Event → real Dev-α mode
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Optional, Protocol


class EventBusLike(Protocol):
    """duck-typed bus interface · 满足二者之一即可."""

    def append_event(self, **kwargs: Any) -> Any: ...  # kwarg 风格(mock 或 adapter-wrapped)


class EventBusAdapter:
    """适配 · 对 L2-05 暴露统一 kwarg-style 调用 · 对下桥接 real/mock.

    Usage:
        adapter = EventBusAdapter(bus_like)
        result = adapter.append_event(
            event_type="L1-01:decision_made",
            project_id="pid-xxx",
            payload={...},
            prev_hash="abc...",
            hash="def...",
            sequence=5,
            actor="main_loop",
            ts="2026-04-23T00:00:00Z",
            idempotency_key="evt-123",
        )
        # result: {event_id, sequence, hash, persisted}
    """

    def __init__(self, bus: Any) -> None:
        self._bus = bus
        # 嗅探模式:mock/kwarg wrapper 直接用 append_event · real Dev-α 要 wrap 到 Event
        self._mode = "kwarg" if hasattr(bus, "append_event") else "real"

    @property
    def mode(self) -> str:
        return self._mode

    def append_event(self, **kwargs: Any) -> dict[str, Any]:
        """统一入口 · 返回 dict(event_id / sequence / hash / persisted)."""
        if self._mode == "kwarg":
            raw = self._bus.append_event(**kwargs)
            # 若是 MagicMock 的 side_effect 返 dict · 直接返
            # 若是 pydantic model(AppendEventResult)· 转 dict
            if isinstance(raw, dict):
                return raw
            if hasattr(raw, "model_dump"):
                return raw.model_dump()
            if hasattr(raw, "__dict__"):
                return dict(raw.__dict__)
            return {"raw": raw}
        # real mode(Dev-α EventBus.append(event))
        return self._real_append(**kwargs)

    def get_last_hash(self, project_id: str) -> str:
        """供 HashChainCalculator 查 tip · 兼容 kwarg / real."""
        if hasattr(self._bus, "get_last_hash"):
            return self._bus.get_last_hash(project_id)
        # real mode · 读 meta
        if hasattr(self._bus, "_project_dir"):
            # 尝试读 Dev-α 的 ProjectMeta
            try:
                from app.l1_09.event_bus.meta import load_meta  # type: ignore

                pdir = self._bus._project_dir(project_id)
                pdir.mkdir(parents=True, exist_ok=True)
                meta = load_meta(pdir, project_id=project_id)
                if meta.last_hash == "GENESIS":
                    return "0" * 64
                return meta.last_hash
            except Exception:
                return "0" * 64
        return "0" * 64

    def _real_append(self, **kwargs: Any) -> dict[str, Any]:
        """走 Dev-α `EventBus.append(Event)` 强类型路径."""
        from app.l1_09.event_bus.schemas import Event  # type: ignore

        event_type = kwargs["event_type"]
        project_id = kwargs["project_id"]
        payload = kwargs.get("payload", {})
        ts = kwargs.get("ts") or datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
        # str → datetime(pydantic 能自动解析 · 为保险显式)
        try:
            timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            timestamp = datetime.now(tz=UTC)
        event = Event(
            project_id=project_id,
            type=event_type,
            actor="main_loop",  # L1-01 统一 actor
            timestamp=timestamp,
            payload=dict(payload),
            links=kwargs.get("links", []),
            idempotency_key=kwargs.get("idempotency_key"),
        )
        result = self._bus.append(event)
        # AppendEventResult 转 dict
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return dict(result)


# -----------------------------------------------------------------
# HashChainCalculator · sha256(prev_hash + canonical_json(content))
# -----------------------------------------------------------------


def canonical_json(obj: Any) -> str:
    """canonical JSON · sort_keys + 无空格分隔 · 对齐 TDD §4.1 TC-206."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_hash(prev_hash: str, payload: dict[str, Any]) -> str:
    """sha256(prev_hash + canonical(payload)) · 64-hex."""
    content = canonical_json(payload)
    return hashlib.sha256((prev_hash + content).encode()).hexdigest()


__all__ = [
    "EventBusAdapter",
    "EventBusLike",
    "canonical_json",
    "compute_hash",
]
