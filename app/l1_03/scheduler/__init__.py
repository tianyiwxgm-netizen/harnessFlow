"""L2-03 · WP 调度器 · IC-02 入口。

职责：L1-01 决策引擎每 tick 进 Quality Loop 前调 `get_next_wp(query)`
响应三态（有 WP / 全 DONE null / awaiting_deps null）· 并发 ≤ 2 硬守 · 关键路径优先 · PM-14 跨 pid 拒绝。

架构原则（`architecture.md §6.3`）：L2-03 **无状态** · 每次调用从 L2-02 真值源读快照。
"""

from app.l1_03.scheduler.concurrency_guard import ConcurrencyGuard
from app.l1_03.scheduler.dispatcher import WPDispatcher, get_next_wp
from app.l1_03.scheduler.priority_queue import prioritize_candidates
from app.l1_03.scheduler.schemas import (
    GetNextWPQuery,
    GetNextWPResult,
    WaitingReason,
    WPDefOut,
)

__all__ = [
    "GetNextWPQuery",
    "GetNextWPResult",
    "WPDefOut",
    "WaitingReason",
    "ConcurrencyGuard",
    "WPDispatcher",
    "get_next_wp",
    "prioritize_candidates",
]
