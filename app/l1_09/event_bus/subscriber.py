"""L2-01 · Subscriber registration + dispatch · 对齐 3-1 §3.3 / §6.4.

V1 仅 fire_and_forget delivery_mode（at_least_once_memory 留 V2+）.

核心组件：
- `Subscriber`：注册时的配置 VO（pydantic）· filter + callback
- `SubscriberHandle`：注册成功返回 · 含 registration_token 用于注销
- `SubscriberRegistry`：进程内注册表 · thread-safe
- `dispatch(event_body)`：append 完成后按 filter 匹配广播 · fire_and_forget
  · V1 同步直接调 Python callable · queue / sse_channel 留后续扩展
"""
from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import Any, Literal

import ulid
from pydantic import BaseModel, ConfigDict, Field


class SubscriberFilter(BaseModel):
    """§3.3 filter schema · 空字段 = 订阅全部."""
    model_config = ConfigDict(frozen=True)

    type_prefix: list[str] = Field(
        default_factory=list,
        description="形如 ['L1-01:', 'L1-07:'] · 空 = 所有 L1",
    )
    actor: list[str] = Field(default_factory=list)
    state: list[str] = Field(default_factory=list)
    project_id: list[str] = Field(
        default_factory=list,
        description="限定 project · 空 = 跨全项目订阅（global subscriber）",
    )
    exclude_meta: bool = Field(default=False, description="默认广播元事件 · L2-04 可关")


class Subscriber(BaseModel):
    """§3.3 register_subscriber_request."""
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    subscriber_id: str = Field(
        ...,
        pattern=r"^(audit_mirror|recoverer|supervisor|ui_sse|retro_auto|[a-z_]+)$",
    )
    filter: SubscriberFilter = Field(default_factory=SubscriberFilter)
    callback: Callable[[dict[str, Any]], None] = Field(
        ...,
        description="Python callable · 接收 jsonl body dict",
    )
    delivery_mode: Literal["fire_and_forget", "at_least_once_memory"] = Field(
        default="fire_and_forget",
    )
    max_lag_ms: int = Field(default=2000, ge=0)


class SubscriberHandle(BaseModel):
    """§3.3 register_subscriber_response."""
    model_config = ConfigDict(frozen=True)

    registration_token: str
    subscriber_id: str
    registered_at: datetime


class SubscriberRegistry:
    """进程内订阅者注册表 · thread-safe · 按 subscriber_id 幂等覆盖."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # subscriber_id → (subscriber, token)
        self._by_id: dict[str, tuple[Subscriber, str]] = {}

    def register(self, subscriber: Subscriber) -> SubscriberHandle:
        """注册 · 相同 subscriber_id 覆盖（§3.3 幂等）· 新 token."""
        token = f"sub_{ulid.new()}"
        with self._lock:
            self._by_id[subscriber.subscriber_id] = (subscriber, token)
        return SubscriberHandle(
            registration_token=token,
            subscriber_id=subscriber.subscriber_id,
            registered_at=datetime.now(tz=UTC),
        )

    def unregister(self, *, subscriber_id: str, registration_token: str) -> bool:
        """注销 · token 不匹配则拒（避免误注销被覆盖后的订阅）."""
        with self._lock:
            entry = self._by_id.get(subscriber_id)
            if entry is None:
                return False
            sub, tok = entry
            _ = sub
            if tok != registration_token:
                return False
            del self._by_id[subscriber_id]
            return True

    def snapshot(self) -> list[Subscriber]:
        """当前快照 · dispatch 用（复制出来再迭代 · 不长持锁）."""
        with self._lock:
            return [sub for sub, _ in self._by_id.values()]

    def __len__(self) -> int:
        with self._lock:
            return len(self._by_id)


def event_matches(subscriber: Subscriber, body: dict[str, Any]) -> bool:
    """§3.3 filter 语义 · 全部条件 AND.

    - 空 type_prefix → 不过滤
    - exclude_meta=True 且 body.is_meta=True → 不匹配
    - project_id 非空 → body.project_id 必在列表
    """
    f = subscriber.filter

    if f.exclude_meta and body.get("is_meta", False):
        return False

    if f.type_prefix:
        ev_type = str(body.get("type", ""))
        if not any(ev_type.startswith(prefix) for prefix in f.type_prefix):
            return False

    if f.actor and body.get("actor") not in f.actor:
        return False

    if f.state and body.get("state") not in f.state:
        return False

    return not (f.project_id and body.get("project_id") not in f.project_id)


def dispatch(
    subscribers: Iterable[Subscriber],
    body: dict[str, Any],
) -> tuple[int, list[tuple[str, BaseException]]]:
    """同步 fire_and_forget 广播 · 失败不影响其他订阅者.

    返回 (delivered_count, failures) · failures = [(subscriber_id, exc), ...]
    V1 同步实现；若订阅者 callback 耗时大 · 由订阅者自行 offload 到自己的线程.
    """
    delivered = 0
    failures: list[tuple[str, BaseException]] = []
    for sub in subscribers:
        if not event_matches(sub, body):
            continue
        try:
            sub.callback(body)
            delivered += 1
        except BaseException as exc:  # noqa: BLE001 · fire_and_forget 吞所有异常
            failures.append((sub.subscriber_id, exc))
    return delivered, failures


__all__ = [
    "Subscriber",
    "SubscriberFilter",
    "SubscriberHandle",
    "SubscriberRegistry",
    "event_matches",
    "dispatch",
]
