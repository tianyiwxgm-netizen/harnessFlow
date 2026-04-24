"""L2-02 · LockJanitor · 守护协程 · 对齐 3-1 §6.4.

特性：
- 定期扫描 held_locks · 找 TTL 超（+ TTL_GRACE）的 lock · 强制 release
- 发 L1-09:lock_leaked WARN 事件
- thread 生命周期：start / stop · daemon 不阻塞进程
"""
from __future__ import annotations

import threading
import time

from app.l1_09.lock_manager.schemas import JANITOR_SCAN_INTERVAL_SEC, TTL_GRACE_MS


class LockJanitor:
    """泄漏锁回收守护."""

    def __init__(self, manager, *, interval_sec: float = JANITOR_SCAN_INTERVAL_SEC) -> None:
        self._manager = manager
        self._interval = interval_sec
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="LockJanitor", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.scan_once()
            except Exception:
                pass
            self._stop_event.wait(self._interval)

    def scan_once(self) -> int:
        """扫描一次 · 返回回收的锁数."""
        now_ms = int(time.time() * 1000)
        reclaimed = 0
        # 取 snapshot（避免持锁遍历）
        with self._manager._state_lock:
            locks = list(self._manager._held_locks.values())

        for lock in locks:
            age_ms = now_ms - lock.acquired_at
            if age_ms > (lock.ttl_ms + TTL_GRACE_MS):
                # TTL 超 · force release
                self._force_release_one(lock)
                reclaimed += 1
        return reclaimed

    def _force_release_one(self, lock) -> None:
        """强制释放单个 lock."""
        import fcntl
        import os

        with self._manager._state_lock:
            if self._manager._held_locks.get(lock.resource) is not lock:
                return  # 已被其他释放
            del self._manager._held_locks[lock.resource]
            self._manager._tokens.pop(lock.token.token_id, None)
            self._manager._force_released_tokens.add(lock.token.token_id)

        if lock.fd is not None:
            try:
                fcntl.flock(lock.fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(lock.fd)
            except OSError:
                pass

        q = self._manager._get_queue(lock.resource)
        with q.condition:
            q.condition.notify_all()

        self._manager._emit("L1-09:lock_leaked", {
            "lock_id": lock.lock_id,
            "resource": lock.resource,
            "holder": lock.holder,
            "age_ms": int(time.time() * 1000) - lock.acquired_at,
            "ttl_ms": lock.ttl_ms,
        })


__all__ = ["LockJanitor"]
