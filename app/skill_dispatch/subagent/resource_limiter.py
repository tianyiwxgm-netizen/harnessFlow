"""L2-04 ResourceLimiter · 并发上限 max_concurrent=3 + queue=10.

为何限制:
  - Claude Agent SDK / Anthropic API 有 rate limit · 并发过高触发限流
  - 子 Agent 生命周期较长（minute-scale）· 队列过长会 starvation

模式:
  - asyncio.Semaphore(max_concurrent) 控制实际跑的数量
  - 自维护 waiter counter 控制 pending 队列长度（async lock 保）
  - async with limiter.slot(): ...  上下文 · finally 释放

错误码: E_SUB_SESSION_LIMIT

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-04-子 Agent 委托器.md §6
  - docs/superpowers/plans/Dev-γ-impl.md §6 Task 04.3
"""
from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator


class SessionLimitError(RuntimeError):
    """E_SUB_SESSION_LIMIT · 超过 queue 上限."""


class ResourceLimiter:
    """并发 + 队列长度 双重上限 · asyncio 友好."""

    def __init__(self, max_concurrent: int = 3, max_queue: int = 10) -> None:
        """max_concurrent: 同时 running 的上限 · max_queue: 额外允许排队等 slot 的上限.

        总可容量 = max_concurrent + max_queue
        """
        if max_concurrent < 1:
            raise ValueError("max_concurrent ≥ 1")
        if max_queue < 0:
            raise ValueError("max_queue ≥ 0")
        self._sem = asyncio.Semaphore(max_concurrent)
        self._max_total = max_concurrent + max_queue
        self._in_flight = 0
        self._lock = asyncio.Lock()

    @contextlib.asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        """上下文管理器 · 取 slot · 退出时释放."""
        async with self._lock:
            if self._in_flight >= self._max_total:
                raise SessionLimitError(
                    f"E_SUB_SESSION_LIMIT: capacity full ({self._max_total})"
                )
            self._in_flight += 1
        try:
            async with self._sem:
                yield
        finally:
            async with self._lock:
                self._in_flight -= 1
