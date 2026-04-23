"""IC-L2-07 account lock mock — 波4 替换为 Dev-α L1-09 真实锁管理器.

TODO:MOCK-REPLACE-FROM-DEV-α — α WP07 交付后删除本 mock · 改为
`from app.l1_09.lock_manager import LockManager` 或对齐的真实接口。

契约：每 (project_id, capability) 一把可重入锁 · 支持 timeout_s acquire。
"""
from __future__ import annotations

import contextlib
import threading
from collections.abc import Iterator


class AccountLockMock:
    """进程内 RLock · 按 (project_id, capability) 维度分锁."""

    def __init__(self) -> None:
        self._locks: dict[tuple[str, str], threading.RLock] = {}
        self._registry_lock = threading.Lock()

    def _get(self, project_id: str, capability: str) -> threading.RLock:
        key = (project_id, capability)
        with self._registry_lock:
            if key not in self._locks:
                self._locks[key] = threading.RLock()
            return self._locks[key]

    @contextlib.contextmanager
    def acquire(
        self,
        project_id: str,
        capability: str,
        timeout_s: float = 5.0,
    ) -> Iterator[None]:
        lock = self._get(project_id, capability)
        got = lock.acquire(timeout=timeout_s)
        if not got:
            raise TimeoutError(f"lock timeout for ({project_id}, {capability})")
        try:
            yield
        finally:
            lock.release()
