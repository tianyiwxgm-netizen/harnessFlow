"""IC-13 · SuggestionPusher · L1-07 → L1-01 · fire-and-forget。

**主会话仲裁**（2026-04-23）：IC-13 方向 = L1-01 · push_suggestion · 3 级 INFO/SUGG/WARN
（BLOCK 走 IC-15）。fire-and-forget · L1-01 L2-06 作为唯一入口接收并入队。

内存队列 + 背压策略：
- bounded 1000（可配置 max_queue_len）
- 满时优先 drop oldest WARN · 若队列无 WARN 才 drop oldest overall
- 每次 push 立即 return ack（不等 consumer ACK）· 异步 drain 由 consumer.pull_and_deliver 做
- IC-09 append `L1-07:suggestion_pushed` 审计事件（payload 含 suggestion_id + level + queue_len）

生产环境的 consumer 是 L1-01 L2-06 的接收器。本模块用 MockSuggestionConsumer 驱动 TC。
"""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Protocol

from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.schemas import (
    PushSuggestionAck,
    PushSuggestionCommand,
    SuggestionLevel,
)


class SuggestionConsumer(Protocol):
    """L1-01 L2-06 接收协议。生产替代 → 真实 L1-01 handler。"""

    async def deliver(self, command: PushSuggestionCommand) -> None: ...


class MockSuggestionConsumer:
    """测试 consumer · 支持 pause / unpause · 计数 delivered。"""

    def __init__(self) -> None:
        self.delivered_count = 0
        self._paused = False
        self._delivered: list[PushSuggestionCommand] = []

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    async def deliver(self, command: PushSuggestionCommand) -> None:
        if self._paused:
            # 模拟背压 · 长时间不消费
            return
        self.delivered_count += 1
        self._delivered.append(command)

    @property
    def delivered(self) -> list[PushSuggestionCommand]:
        return list(self._delivered)


@dataclass
class SuggestionPusher:
    """IC-13 push_suggestion 实现。"""

    session_pid: str
    consumer: SuggestionConsumer
    event_bus: EventBusStub
    max_queue_len: int = 1000

    _queue: deque[PushSuggestionCommand] = field(default_factory=deque)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def push_suggestion(
        self, command: PushSuggestionCommand
    ) -> PushSuggestionAck:
        """fire-and-forget 入队 · 立即返回 ack · 不等 consumer。"""
        # 跨 project 拒绝（§3.13.4 E_SUGG_CROSS_PROJECT）
        if command.project_id != self.session_pid:
            raise ValueError(f"E_SUGG_CROSS_PROJECT: {command.project_id} != {self.session_pid}")

        evicted_id: str | None = None
        async with self._lock:
            if len(self._queue) >= self.max_queue_len:
                evicted_id = self._evict_one()
            self._queue.append(command)
            queue_len = len(self._queue)

        # fire-and-forget · 启异步派发 · 不 await
        asyncio.create_task(self._drain_once())

        # IC-09 审计事件（独立 await · 不阻塞 consumer）
        await self.event_bus.append_event(
            project_id=self.session_pid,
            type="L1-07:suggestion_pushed",
            payload={
                "suggestion_id": command.suggestion_id,
                "level": command.level.value,
                "queue_len": queue_len,
                "evicted_suggestion_id": evicted_id,
            },
            evidence_refs=tuple(command.observation_refs),
        )

        return PushSuggestionAck(
            suggestion_id=command.suggestion_id,
            enqueued=True,
            queue_len=queue_len,
            evicted_suggestion_id=evicted_id,
        )

    def queue_len(self) -> int:
        return len(self._queue)

    def _evict_one(self) -> str:
        """背压策略：优先 drop oldest WARN · 若队列无 WARN 才 drop oldest overall。

        返回被 evict 的 suggestion_id（用于告警 / ack）。
        """
        # 优先找 WARN
        for idx, item in enumerate(self._queue):
            if item.level == SuggestionLevel.WARN:
                evicted = self._queue[idx]
                del self._queue[idx]
                return evicted.suggestion_id
        # 无 WARN · drop oldest
        evicted = self._queue.popleft()
        return evicted.suggestion_id

    async def _drain_once(self) -> None:
        """异步从队首取一条交给 consumer · fire-and-forget（不回写 queue_len）。"""
        async with self._lock:
            if not self._queue:
                return
            cmd = self._queue.popleft()
        try:
            await self.consumer.deliver(cmd)
        except Exception:
            # consumer 抛错 · 静默 · L1-07 侧不应被 downstream 失败卡住
            pass
