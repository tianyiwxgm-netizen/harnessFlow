"""Effort-based burndown 计算。

`remaining_effort = total_effort - sum(effort for wp in wps if state == DONE)`

严格按 effort 累加 · 非 WP-count（Dev-ε md §3.4 DoD 硬约束）。
"""

from __future__ import annotations

from app.l1_03.topology.schemas import WorkPackage
from app.l1_03.topology.state_machine import State


def compute_burndown(wps: list[WorkPackage]) -> tuple[float, float]:
    """返回 `(total_effort, done_effort)`。

    total_effort：所有 WP 的 effort_estimate 之和（包括未 DONE 的）。
    done_effort：state==DONE 的 WP 之 effort_estimate 和。
    """
    total = 0.0
    done = 0.0
    for wp in wps:
        total += wp.effort_estimate
        if wp.state == State.DONE:
            done += wp.effort_estimate
    return total, done


def completion_rate(total: float, done: float) -> float:
    """完成率 ∈ [0, 1]。total=0 返 0.0（空 topology · 不是 1.0 避免误判）。"""
    if total <= 0.0:
        return 0.0
    return min(1.0, max(0.0, done / total))
