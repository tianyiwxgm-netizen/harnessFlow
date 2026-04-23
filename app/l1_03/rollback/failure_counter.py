"""FailureCounter 5 态机 · 每 wp_id 独立。

状态（`Dev-ε md §3.5`）：
    NORMAL → RETRY_1 → RETRY_2 → RETRY_3 → ESCALATED

转换规则：
- NORMAL + failed → RETRY_1（本级 retry）
- RETRY_1 + failed → RETRY_2（本级 retry）
- RETRY_2 + failed → RETRY_3（即 ESCALATED · 升级 IC-14 / IC-15）
- ESCALATED 后：新 failed 保持 ESCALATED（需外部 reset）
- 任意状态 + done_reset → NORMAL（幂等）
"""

from __future__ import annotations

import threading
from enum import StrEnum


class FailureCounterState(StrEnum):
    NORMAL = "NORMAL"
    RETRY_1 = "RETRY_1"
    RETRY_2 = "RETRY_2"
    RETRY_3 = "RETRY_3"
    ESCALATED = "ESCALATED"


# 连续失败转换表（同一 wp 连续 failed 事件）
_FAILURE_TRANSITIONS: dict[FailureCounterState, FailureCounterState] = {
    FailureCounterState.NORMAL: FailureCounterState.RETRY_1,
    FailureCounterState.RETRY_1: FailureCounterState.RETRY_2,
    FailureCounterState.RETRY_2: FailureCounterState.RETRY_3,  # 升级临界
    FailureCounterState.RETRY_3: FailureCounterState.ESCALATED,
    FailureCounterState.ESCALATED: FailureCounterState.ESCALATED,  # 粘性
}

# ESCALATED 状态等价于 failure_count ≥ 3（同时进）· RETRY_3 也当作升级信号
ESCALATION_STATES: frozenset[FailureCounterState] = frozenset(
    {FailureCounterState.RETRY_3, FailureCounterState.ESCALATED}
)


class FailureCounter:
    """所有 wp 共享一个实例 · wp_id → state map · 每 wp 独立转换。

    线程安全（RLock）· 支持并发 on_failed / on_done_reset。
    """

    def __init__(self) -> None:
        self._states: dict[str, FailureCounterState] = {}
        self._counts: dict[str, int] = {}
        self._lock = threading.RLock()

    def state_of(self, wp_id: str) -> FailureCounterState:
        with self._lock:
            return self._states.get(wp_id, FailureCounterState.NORMAL)

    def count_of(self, wp_id: str) -> int:
        with self._lock:
            return self._counts.get(wp_id, 0)

    def on_failed(self, wp_id: str) -> FailureCounterState:
        """记录一次失败 · 返回转换后的状态。"""
        with self._lock:
            cur = self._states.get(wp_id, FailureCounterState.NORMAL)
            nxt = _FAILURE_TRANSITIONS[cur]
            self._states[wp_id] = nxt
            self._counts[wp_id] = self._counts.get(wp_id, 0) + 1
            return nxt

    def on_done_reset(self, wp_id: str) -> None:
        """成功后 reset · 幂等（无 counter 时也不 raise）。"""
        with self._lock:
            self._states[wp_id] = FailureCounterState.NORMAL
            self._counts[wp_id] = 0

    def is_escalated(self, wp_id: str) -> bool:
        """连续失败是否已到升级态（RETRY_3 或 ESCALATED）。"""
        return self.state_of(wp_id) in ESCALATION_STATES

    def reset_all(self) -> None:
        """批量清空（测试用 · 生产不要调）。"""
        with self._lock:
            self._states.clear()
            self._counts.clear()
