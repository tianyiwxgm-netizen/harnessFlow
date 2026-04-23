"""WP 6 状态机 · LEGAL_TRANSITIONS 单点定义。

规约见 `docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度/architecture.md §5.4`。

6 状态：READY / RUNNING / DONE / FAILED / BLOCKED / STUCK
7 条合法跃迁：
    (READY, RUNNING)      · IC-L2-03 锁定成功
    (RUNNING, DONE)       · wp_done
    (RUNNING, FAILED)     · wp_failed
    (FAILED, READY)       · 失败次数 < 3 · L2-05 放回
    (FAILED, STUCK)       · 连续失败 ≥ 3 · IC-L2-06
    (READY, BLOCKED)      · 依赖链出现 FAILED/STUCK
    (BLOCKED, READY)      · 依赖重新满足

注：Dev-ε md §3.1 写 "12 条" 是包含 BLOCKED 派生，本模块按 architecture §5.4 字面 7 条（
BLOCKED 进入由依赖链扫描派生，不是用户 request）。STUCK 不可主动出，必须经 L2-01 差量拆解替换。
"""

from __future__ import annotations

from enum import StrEnum

from app.l1_03.common.errors import IllegalTransition


class State(StrEnum):
    """WP 6 状态。`StrEnum` 允许 `State.READY == "READY"`，便于 JSON 序列化。"""

    READY = "READY"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    STUCK = "STUCK"


LEGAL_TRANSITIONS: frozenset[tuple[State, State]] = frozenset(
    {
        (State.READY, State.RUNNING),
        (State.RUNNING, State.DONE),
        (State.RUNNING, State.FAILED),
        (State.FAILED, State.READY),
        (State.FAILED, State.STUCK),
        (State.READY, State.BLOCKED),
        (State.BLOCKED, State.READY),
    }
)
"""7 条合法跃迁 · 唯一定义点 · L2-03/04/05 全部从此处 import。"""


def is_legal(from_state: State, to_state: State) -> bool:
    return (from_state, to_state) in LEGAL_TRANSITIONS


def assert_transition(from_state: State, to_state: State, wp_id: str) -> None:
    """校验跃迁合法，不合法则 raise `IllegalTransition`（E_L103_L202_303）。"""
    if not is_legal(from_state, to_state):
        raise IllegalTransition(
            from_state=str(from_state),
            to_state=str(to_state),
            wp_id=wp_id,
        )
