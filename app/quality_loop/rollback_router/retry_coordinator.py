"""`RetryCoordinator` · 同级连续失败计数 + 升级 dedup。

对齐 Dev-ε `app/l1_03/rollback/coordinator.py._escalated_wps` dedup 模式 ·
**同 (wp, verdict_level) 已升级过 · 后续失败不重复通知**（IC-14 升级事件静默吃掉）。

计数语义（对齐 Dev-ζ `escalator` 5 态机）：
- `on_failed(wp, level)` → 递增 counter · 返回新 count
- `count >= 3` → `is_escalated=True`
- `should_notify_escalation(wp, level)`：首次到达 >= 3 返回 True · 之后返回 False（dedup）
- `on_wp_done_reset(wp, level)` → 清零 + 解除 dedup · 下轮可再升级
- per-project 隔离（PM-14）· per-(wp, verdict_level) 独立
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

ESCALATION_THRESHOLD: int = 3  # 硬常量 · 对齐 stage_mapper


@dataclass
class RetryCoordinator:
    """同一 `RetryCoordinator` 实例 = 一个 project_id 下的计数器。

    - `_counts`: (wp_id, verdict_level) → count
    - `_notified`: (wp_id, verdict_level) · 已 fire 过升级通知的 key 集合（dedup）
    - RLock 线程安全（对齐 Dev-ε `FailureCounter`）
    """

    project_id: str
    _counts: dict[tuple[str, str], int] = field(default_factory=dict)
    _notified: set[tuple[str, str]] = field(default_factory=set)
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def __post_init__(self) -> None:
        if not self.project_id or not self.project_id.strip():
            raise ValueError("E_ROUTE_NO_PROJECT_ID: project_id 必带（PM-14）")

    # --- public API ---

    def on_failed(self, wp_id: str, verdict_level: str) -> int:
        """记录一次失败 · 递增 counter · 返回新计数。"""
        key = (wp_id, verdict_level)
        with self._lock:
            new = self._counts.get(key, 0) + 1
            self._counts[key] = new
            return new

    def on_wp_done_reset(self, wp_id: str, verdict_level: str) -> None:
        """幂等 · 清零计数 + 解除升级 dedup 标记。

        语义：Quality Loop 重跑成功（或外部强 reset）后 · 若该 (wp, verdict_level)
        之后又连续 3 次失败 · 应当重新升级（重 fire IC-14）。
        """
        key = (wp_id, verdict_level)
        with self._lock:
            self._counts.pop(key, None)
            self._notified.discard(key)

    def count_of(self, wp_id: str, verdict_level: str) -> int:
        """查询当前计数（无记录则 0）。"""
        with self._lock:
            return self._counts.get((wp_id, verdict_level), 0)

    def is_escalated(self, wp_id: str, verdict_level: str) -> bool:
        """是否已到升级阈值（count >= 3）· 不包含 dedup 状态。"""
        return self.count_of(wp_id, verdict_level) >= ESCALATION_THRESHOLD

    def was_escalation_notified(self, wp_id: str, verdict_level: str) -> bool:
        """是否已 fire 过升级通知（供外部审计 / 调试）。"""
        with self._lock:
            return (wp_id, verdict_level) in self._notified

    def should_notify_escalation(self, wp_id: str, verdict_level: str) -> bool:
        """**首次** 到达升级阈值返回 True；之后返回 False（dedup · 对齐 Dev-ε）。

        **副作用**：首次返回 True 时把 key 加入 `_notified`。
        """
        key = (wp_id, verdict_level)
        with self._lock:
            count = self._counts.get(key, 0)
            if count < ESCALATION_THRESHOLD:
                return False
            if key in self._notified:
                return False
            # 首次 fire · 打 dedup 标记
            self._notified.add(key)
            return True
