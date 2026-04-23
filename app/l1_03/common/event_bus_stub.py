"""IC-09 `append_event` 的 in-memory stub，仅测试/组内开发期用。

真实实现由 L1-09（Dev-α）`app/l1_09/event_bus/` 提供 · 契约：
- `append(event_type, content, project_id) -> {event_id, sequence, hash}`
- 所有事件必带 `project_id`（PM-14 硬约束）
- 同步分发给已注册订阅者（L2-04 / L2-05 消费 wp_done / wp_failed）

切换到真实实现时，只需把 `app.l1_09.event_bus.EventAppender` 替换进来即可。
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

Subscriber = Callable[[dict[str, Any]], None]


@dataclass
class EventRecord:
    event_id: str
    sequence: int
    hash: str
    type: str
    project_id: str
    content: dict[str, Any]
    ts: float


class EventBusStub:
    """同进程 in-memory 事件总线 · 保序 · hash 链。

    线程安全（`threading.RLock`）· 非 fsync（仅测试用 · 不持久化）。
    """

    def __init__(self) -> None:
        self._events: list[EventRecord] = []
        self._subscribers: list[Subscriber] = []
        self._lock = threading.RLock()
        self._seq = 0
        self._last_hash = "0" * 64

    def append(
        self,
        event_type: str,
        content: dict[str, Any],
        project_id: str,
    ) -> dict[str, Any]:
        """追加事件 · 返回 `{event_id, sequence, hash}`。

        - `project_id` 空 → ValueError（PM-14 硬约束）
        - hash = SHA256(prev_hash || JCS(payload))
        """
        if not project_id:
            raise ValueError("PM-14 违反：event project_id 必带")
        if not isinstance(content, dict):
            raise TypeError(f"content 必须 dict，got {type(content).__name__}")
        with self._lock:
            self._seq += 1
            event_id = f"evt-{uuid.uuid4().hex[:12]}"
            payload = {
                "event_id": event_id,
                "sequence": self._seq,
                "type": event_type,
                "project_id": project_id,
                "content": content,
            }
            payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            h = hashlib.sha256(
                (self._last_hash + payload_json).encode("utf-8")
            ).hexdigest()
            self._last_hash = h
            record = EventRecord(
                event_id=event_id,
                sequence=self._seq,
                hash=h,
                type=event_type,
                project_id=project_id,
                content=dict(content),
                ts=time.time(),
            )
            self._events.append(record)
            payload_for_sub = {
                "event_id": event_id,
                "sequence": self._seq,
                "hash": h,
                "type": event_type,
                "project_id": project_id,
                "content": dict(content),
            }
        # 订阅者在锁外调 · 避免回调死锁；stub 里订阅者异常不传播，保证 append 原子
        for sub in list(self._subscribers):
            with contextlib.suppress(Exception):
                sub(payload_for_sub)
        return {"event_id": event_id, "sequence": self._seq, "hash": h}

    def subscribe(self, sub: Subscriber) -> None:
        with self._lock:
            self._subscribers.append(sub)

    def unsubscribe(self, sub: Subscriber) -> None:
        with self._lock:
            if sub in self._subscribers:
                self._subscribers.remove(sub)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
            self._subscribers.clear()
            self._seq = 0
            self._last_hash = "0" * 64

    @property
    def events(self) -> list[EventRecord]:
        with self._lock:
            return list(self._events)

    def filter(
        self,
        *,
        event_type: str | None = None,
        project_id: str | None = None,
    ) -> list[EventRecord]:
        with self._lock:
            out: list[EventRecord] = []
            for e in self._events:
                if event_type and e.type != event_type:
                    continue
                if project_id and e.project_id != project_id:
                    continue
                out.append(e)
            return out
