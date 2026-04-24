"""L2-03 · 12 合法转换定义 + 只读 allowed_next 查询。

单一来源: app.project_lifecycle.stage_gate.schemas.ALLOWED_TRANSITIONS
(Dev-δ · L1-02 · 已 merged) · 本模块直接引用 · 不复制。

AllowedNextTable 启动加载一次 · frozenset 存储 · 运行时不可变(I-12 / D-03b)。
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from app.main_loop.state_machine.schemas import (
    E_TRANS_INVALID_STATE_ENUM,
    STATES,
    State,
    StateMachineError,
    Transition,
)
from app.project_lifecycle.stage_gate.schemas import (
    ALLOWED_TRANSITIONS as _SG_ALLOWED,
)


def _build_allowed() -> tuple[Transition, ...]:
    """从 L1-02 (stage_gate) 的单一事实表构造本 L2 的 Transition tuple。

    12 条边:
        NOT_EXIST → INITIALIZED
        INITIALIZED → PLANNING
        PLANNING → TDD_PLANNING
        TDD_PLANNING → EXECUTING
        EXECUTING → CLOSING
        CLOSING → CLOSED
        PLANNING → PLANNING (Re-open)
        TDD_PLANNING → TDD_PLANNING (Re-open)
        EXECUTING → TDD_PLANNING (L1-04 回退)
        EXECUTING → PLANNING (L1-04 回退)
        PLANNING → CLOSED (紧急终止)
        TDD_PLANNING → CLOSED (紧急终止)
    """
    edges: list[Transition] = []
    for frm, to in _SG_ALLOWED:
        edges.append(Transition(from_state=frm, to_state=to))
    return tuple(edges)


ALLOWED_TRANSITIONS: tuple[Transition, ...] = _build_allowed()


# allowed_next[from_state] = frozenset(to_state, ...)
# 运行时不可变(MappingProxyType 包裹)
def _build_allowed_next() -> Mapping[State, frozenset[State]]:
    acc: dict[State, set[State]] = {}
    for t in ALLOWED_TRANSITIONS:
        acc.setdefault(t.from_state, set()).add(t.to_state)
    # 补齐终态 (CLOSED · 无 out edge · 空集)
    for st in STATES:
        acc.setdefault(st, set())
    # 冻结为 frozenset + MappingProxyType
    return MappingProxyType({k: frozenset(v) for k, v in acc.items()})


ALLOWED_NEXT: Mapping[State, frozenset[State]] = _build_allowed_next()


def is_allowed(from_state: State, to_state: State) -> bool:
    """纯函数 · frozenset lookup O(1) · P99 ≤ 10ms (§3.2 SLO)。"""
    if from_state not in ALLOWED_NEXT:
        return False
    return to_state in ALLOWED_NEXT[from_state]


def allowed_next(from_state: State) -> tuple[State, ...]:
    """查询 from_state 的所有合法 next state (sorted 稳定序)。

    非 7 枚举之一 → StateMachineError(E_TRANS_INVALID_STATE_ENUM)。
    终态无出边 → 空 tuple。
    """
    if from_state not in STATES:
        raise StateMachineError(
            error_code=E_TRANS_INVALID_STATE_ENUM,
            message=f"from_state {from_state!r} not in 7-enum {STATES!r}",
            context={"from_state": from_state},
        )
    return tuple(sorted(ALLOWED_NEXT[from_state]))


def count_edges() -> int:
    """用于启动 assert · 确认 12 条边完整。"""
    return len(ALLOWED_TRANSITIONS)
