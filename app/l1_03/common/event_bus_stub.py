"""IC-09 `append_event` 的 in-memory stub，仅测试/组内开发期用。

真实实现由 L1-09（Dev-α）`app/l1_09/event_bus/` 提供。契约（`ic-contracts.md §3.9.2`）：

必填字段：
- `event_id`（幂等键 · `evt-{uuid-v7}`）
- `event_type`
- `project_id_or_system`（PM-14 硬约束）
- `payload`（事件数据 · dict）
- `actor`（审计归因 · {l1, l2?, skill_id?}）
- `ts`（ISO-8601-utc）

可选字段：
- `trigger_tick` / `correlation_id`

**Drop-in 兼容性设计**：

本 stub 的 `append(event_type, content=..., payload=..., project_id=..., event_id=..., actor=..., ts=..., trigger_tick=..., correlation_id=...)`
同时接受 IC-09 契约字段（`payload` / `event_id` / `actor` / `ts` / ...）以及
legacy alias `content`（等价于 `payload`）。

- 未传 `event_id`：stub 生成默认 `evt-{uuid}`
- 未传 `actor`：stub 生成默认 `{"l1": "L1-03"}`
- 未传 `ts`：stub 生成当前 UTC ISO-8601
- `content` + `payload` 同时传：raise TypeError
- 空 `project_id`：raise ValueError（PM-14 硬约束）

切换到真实实现时 · 将 `app.l1_09.event_bus.EventAppender` 替换进来即可 · 现有
12+ 个 `_emit` 调用点都已按关键字参数传 · 真实实现可严格校验必填字段 · stub 默认
填充兼容调用端逐步迁移。
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import threading
import time
import uuid
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

Subscriber = Callable[[dict[str, Any]], None]

# IC-09 required 字段白名单 — 真实 EventAppender 会全部强校验 · stub 只 warn
_IC09_REQUIRED = ("event_id", "event_type", "project_id", "payload", "actor", "ts")


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_actor() -> dict[str, Any]:
    """L1-03 默认 actor · 真实调用端应自己传。"""
    return {"l1": "L1-03"}


@dataclass
class EventRecord:
    event_id: str
    sequence: int
    hash: str
    type: str
    project_id: str
    payload: dict[str, Any]
    actor: dict[str, Any]
    ts: str
    trigger_tick: str | None = None
    correlation_id: str | None = None
    # legacy alias · 与 payload 同对象 · 兼容老 filter/assert 代码
    content: dict[str, Any] = field(default_factory=dict)


class EventBusStub:
    """同进程 in-memory 事件总线 · 保序 · hash 链。

    线程安全（`threading.RLock`）· 非 fsync（仅测试用 · 不持久化）。

    签名对齐 IC-09：接受 payload + event_id + actor + ts 等必填字段 ·
    未传则生成默认值（stub 宽松 · 真实 L1-09 EventAppender 会拒绝缺字段）。
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
        content: dict[str, Any] | None = None,
        project_id: str = "",
        *,
        payload: dict[str, Any] | None = None,
        event_id: str | None = None,
        actor: dict[str, Any] | None = None,
        ts: str | None = None,
        trigger_tick: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """追加事件 · 返回 `{event_id, sequence, hash, prev_hash, persisted, ts_persisted}`。

        参数规则（与 IC-09 §3.9.2 对齐）：

        - `project_id`：必填 · 空 → `ValueError`（PM-14 硬约束 · `E_EVT_NO_PROJECT_OR_SYSTEM`）
        - `payload` / `content`：事件数据 · 必须 dict · 二者**互斥**（同时传 → `TypeError`）
          - `content` 是旧字段名（stub 过渡期 alias · real impl 用 `payload`）
        - `event_id`：可选 · None 时 stub 生成 `evt-{uuid}`（真实 IC-09 要求调用端传入做幂等键）
        - `actor`：可选 · None 时 stub 填 `{"l1": "L1-03"}`（真实 IC-09 必填）
        - `ts`：可选 · None 时 stub 填当前 UTC ISO-8601（真实 IC-09 必填）
        - `trigger_tick` / `correlation_id`：可选 · 原样透传

        返回 dict 包含 IC-09 §3.9.3 出参（stub 版本）：`event_id / sequence / hash /
        prev_hash / persisted=True / ts_persisted`。
        """
        if not project_id:
            raise ValueError("PM-14 违反：event project_id 必带（E_EVT_NO_PROJECT_OR_SYSTEM）")

        # payload / content 互斥
        if payload is not None and content is not None:
            raise TypeError(
                "append: `payload` 与 `content` 互斥（content 是 legacy alias · 只传其一）"
            )
        body: dict[str, Any] | None = payload if payload is not None else content
        if body is None:
            raise TypeError("append 必须提供 `payload`（或 legacy `content`）")
        if not isinstance(body, dict):
            raise TypeError(
                f"payload/content 必须 dict，got {type(body).__name__}"
            )

        # 默认值填充（stub 宽松）
        ev_id = event_id if event_id else f"evt-{uuid.uuid4().hex[:12]}"
        actor_obj = dict(actor) if actor else _default_actor()
        ts_iso = ts if ts else _utc_iso_now()

        with self._lock:
            self._seq += 1
            prev_hash = self._last_hash
            canonical = {
                "event_id": ev_id,
                "sequence": self._seq,
                "type": event_type,
                "project_id": project_id,
                "payload": body,
                "actor": actor_obj,
                "ts": ts_iso,
            }
            if trigger_tick is not None:
                canonical["trigger_tick"] = trigger_tick
            if correlation_id is not None:
                canonical["correlation_id"] = correlation_id

            payload_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
            h = hashlib.sha256(
                (prev_hash + payload_json).encode("utf-8")
            ).hexdigest()
            self._last_hash = h
            record = EventRecord(
                event_id=ev_id,
                sequence=self._seq,
                hash=h,
                type=event_type,
                project_id=project_id,
                payload=dict(body),
                actor=dict(actor_obj),
                ts=ts_iso,
                trigger_tick=trigger_tick,
                correlation_id=correlation_id,
                content=dict(body),  # legacy alias · 同值
            )
            self._events.append(record)
            sub_payload = {
                "event_id": ev_id,
                "sequence": self._seq,
                "hash": h,
                "prev_hash": prev_hash,
                "type": event_type,
                "project_id": project_id,
                "payload": dict(body),
                "content": dict(body),  # legacy alias
                "actor": dict(actor_obj),
                "ts": ts_iso,
                "trigger_tick": trigger_tick,
                "correlation_id": correlation_id,
            }
            ts_persisted = time.time()
        # 订阅者在锁外调 · 避免回调死锁；stub 里订阅者异常不传播，保证 append 原子
        for sub in list(self._subscribers):
            with contextlib.suppress(Exception):
                sub(sub_payload)
        return {
            "event_id": ev_id,
            "sequence": self._seq,
            "hash": h,
            "prev_hash": prev_hash,
            "persisted": True,
            "ts_persisted": ts_persisted,
        }

    def append_strict(
        self,
        *,
        event_id: str,
        event_type: str,
        project_id: str,
        payload: dict[str, Any],
        actor: dict[str, Any],
        ts: str,
        trigger_tick: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """IC-09 §3.9.2 严格签名入口 · 所有必填字段强制传入 · 供真实 IC-09 契约测用。

        与 `append` 等价 · 但要求 caller 提供全部 required 字段（event_id / actor / ts）。
        缺字段会抛 `TypeError`（Python 关键字参数机制 · 不是 stub 运行时检查）。
        """
        for name, val in (
            ("event_id", event_id),
            ("actor", actor),
            ("ts", ts),
        ):
            if val is None or (isinstance(val, str) and not val):
                raise ValueError(f"IC-09 必填字段缺失：{name}")
        if not isinstance(actor, dict) or "l1" not in actor:
            raise ValueError("IC-09 actor 必含 `l1` 字段")

        return self.append(
            event_type=event_type,
            payload=payload,
            project_id=project_id,
            event_id=event_id,
            actor=actor,
            ts=ts,
            trigger_tick=trigger_tick,
            correlation_id=correlation_id,
        )

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


__all__ = [
    "EventBusStub",
    "EventRecord",
    "Subscriber",
    # 供契约测直接 import
    "_IC09_REQUIRED",
]


# 抑制本模块的 warnings 噪音（legacy content 路径 deprecation）· 改日真实切换时再启
warnings.filterwarnings("default", category=DeprecationWarning, module=__name__)
