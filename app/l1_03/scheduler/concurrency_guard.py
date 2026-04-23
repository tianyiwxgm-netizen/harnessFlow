"""并发度守卫 · PM-04 硬约束 `parallelism_limit <= 2`。"""

from __future__ import annotations


class ConcurrencyGuard:
    """纯函数化守卫（无状态）。"""

    def __init__(self, limit: int = 2) -> None:
        if limit < 1:
            raise ValueError(f"parallelism_limit 必 ≥ 1，got {limit}")
        self.limit = limit

    def can_dispatch(self, current_running: int) -> bool:
        return current_running < self.limit

    def at_cap(self, current_running: int) -> bool:
        return current_running >= self.limit
