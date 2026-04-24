"""L2-02 · FIFO ticket 队列 · 对齐 3-1 §6.1 Stage 3.

特性：
- 每 resource 一个 queue
- 单调 ticket_id（避免饥饿）
- condition 唤醒 + 出队
- 使用 RLock 允许在 condition wait 期间检查 is_head 不死锁
"""
from __future__ import annotations

import itertools
import threading
from collections import deque
from dataclasses import dataclass, field


@dataclass
class FIFOTicketQueue:
    """FIFO 等待队列 · per resource.

    使用 RLock · 允许 condition.wait 持锁期间调 is_head/size 等只读方法.
    """

    lock: threading.RLock = field(default_factory=threading.RLock)
    condition: threading.Condition = field(init=False)
    tickets: deque[int] = field(default_factory=deque)
    _seq: itertools.count = field(default_factory=lambda: itertools.count(1))
    waiters_enqueue_ts_ms: dict[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.condition = threading.Condition(self.lock)

    def enqueue(self, ts_ms: int) -> int:
        """入队 · 返回 ticket_id."""
        with self.lock:
            tid = next(self._seq)
            self.tickets.append(tid)
            self.waiters_enqueue_ts_ms[tid] = ts_ms
            return tid

    def is_head(self, ticket_id: int) -> bool:
        with self.lock:
            return bool(self.tickets) and self.tickets[0] == ticket_id

    def dequeue(self, ticket_id: int) -> None:
        """只允许队头出队."""
        with self.lock:
            if self.tickets and self.tickets[0] == ticket_id:
                self.tickets.popleft()
                self.waiters_enqueue_ts_ms.pop(ticket_id, None)

    def remove(self, ticket_id: int) -> None:
        """非队头也可删（超时退出时清理）."""
        with self.lock:
            try:
                self.tickets.remove(ticket_id)
            except ValueError:
                pass
            self.waiters_enqueue_ts_ms.pop(ticket_id, None)

    def size(self) -> int:
        with self.lock:
            return len(self.tickets)

    def oldest_wait_ms(self, now_ms: int) -> int:
        with self.lock:
            if not self.waiters_enqueue_ts_ms:
                return 0
            return max(0, now_ms - min(self.waiters_enqueue_ts_ms.values()))

    def notify(self) -> None:
        with self.condition:
            self.condition.notify_all()


__all__ = ["FIFOTicketQueue"]
