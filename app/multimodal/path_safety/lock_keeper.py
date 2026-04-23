"""Per-path asyncio.Lock keeper with acquisition timeout (L2-04 §6.3)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.multimodal.common.errors import L108Error


class ConcurrencyLockKeeper:
    """One asyncio.Lock per path · timeout guard against deadlock / stuck writer."""

    def __init__(self, timeout_s: float = 30.0) -> None:
        if timeout_s <= 0:
            raise ValueError("timeout_s must be > 0")
        self._timeout_s = timeout_s
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_or_create(self, path: str) -> asyncio.Lock:
        lock = self._locks.get(path)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[path] = lock
        return lock

    @asynccontextmanager
    async def acquire(self, path: str) -> AsyncIterator[None]:
        lock = self._get_or_create(path)
        try:
            await asyncio.wait_for(lock.acquire(), timeout=self._timeout_s)
        except TimeoutError:
            raise L108Error("concurrency_lock_timeout", f"lock wait > {self._timeout_s}s for {path}")
        try:
            yield
        finally:
            lock.release()
