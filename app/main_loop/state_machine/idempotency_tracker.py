"""L2-03 · 幂等键追踪器 · LRU 1024 · TTL 5min。

设计对齐 D-03e:
  - 主幂等键: transition_id (上游 uuid-v7)
  - 同 transition_id 多次调用返回同一 cached result (LRU hit)
  - 同 transition_id · 不同 payload (from/to/project_id mismatch)
    → 抛 E_TRANS_IDEMPOTENT_REPLAY (DeveloperError · 不静默)
  - LRU 满 → 淘汰最早访问(move_to_end 模式)
"""
from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable

from app.main_loop.state_machine.schemas import (
    E_TRANS_IDEMPOTENT_REPLAY,
    StateMachineError,
    TransitionRequest,
    TransitionResult,
)


DEFAULT_CAPACITY = 1024
DEFAULT_TTL_SECONDS = 300  # 5 min


@dataclass
class _Entry:
    """内部条目 · 维护 result + 原始 request 的身份三元组 · expires_at。"""

    request_identity: tuple[str, str, str, str]
    # (project_id, from_state, to_state, reason[:64])
    result: TransitionResult
    expires_at: float


class IdempotencyTracker:
    """transition_id → (request_identity, result) LRU 缓存。

    典型用法:
        tracker = IdempotencyTracker()
        cached = tracker.lookup(req)
        if cached is not None:
            return cached
        # ... do real work ...
        tracker.put(req, result)
    """

    def __init__(
        self,
        *,
        capacity: int = DEFAULT_CAPACITY,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if capacity <= 0:
            raise ValueError(f"capacity must be positive · got {capacity}")
        self._capacity = capacity
        self._ttl = float(ttl_seconds)
        self._clock: Callable[[], float] = clock or time.monotonic
        self._cache: OrderedDict[str, _Entry] = OrderedDict()

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def lookup(self, req: TransitionRequest) -> TransitionResult | None:
        """查 transition_id · miss / 过期 → None · hit → 校验 payload 一致。

        payload 不一致 → 抛 E_TRANS_IDEMPOTENT_REPLAY (DeveloperError)。
        """
        entry = self._cache.get(req.transition_id)
        if entry is None:
            return None
        now = self._clock()
        if entry.expires_at <= now:
            # 过期 · 清理
            self._cache.pop(req.transition_id, None)
            return None
        # payload 一致性校验
        current_identity = self._identity(req)
        if current_identity != entry.request_identity:
            raise StateMachineError(
                error_code=E_TRANS_IDEMPOTENT_REPLAY,
                message=(
                    f"transition_id {req.transition_id!r} replayed with "
                    f"DIFFERENT payload: cached={entry.request_identity!r} "
                    f"now={current_identity!r}"
                ),
                project_id=req.project_id,
                context={
                    "transition_id": req.transition_id,
                    "cached_identity": entry.request_identity,
                    "current_identity": current_identity,
                },
            )
        # 命中 · LRU 提到最新
        self._cache.move_to_end(req.transition_id)
        return entry.result

    def put(self, req: TransitionRequest, result: TransitionResult) -> None:
        """缓存 result · 如果 cache 满 · 淘汰最早。"""
        entry = _Entry(
            request_identity=self._identity(req),
            result=result,
            expires_at=self._clock() + self._ttl,
        )
        self._cache[req.transition_id] = entry
        self._cache.move_to_end(req.transition_id)
        while len(self._cache) > self._capacity:
            self._cache.popitem(last=False)  # 淘汰 FIFO head

    def size(self) -> int:
        return len(self._cache)

    def clear(self) -> None:
        self._cache.clear()

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    @staticmethod
    def _identity(req: TransitionRequest) -> tuple[str, str, str, str]:
        """取 request 的四元组作幂等身份 · (pid, from, to, reason[:64])。

        reason 截断到 64 字符 · 避免长 reason 占内存;同 transition_id 的
        重试通常 reason 相同 · 差异极小。
        """
        return (
            req.project_id or "",
            str(req.from_state),
            str(req.to_state),
            (req.reason or "")[:64],
        )
