"""L1-03 的错误类型 + 错误码常量。

错误码命名按 3-2 TDD spec §11：`E_L103_L{2-XX}_{NNN}`，三位数字按类：
- 1xx：装图期（load_topology）
- 2xx：PM-14 归属
- 3xx：状态跃迁
- 4xx：审计 / 事件写入
- 5xx：外部 bypass / 一致性
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class L103Error(Exception):
    """L1-03 所有错误的基类。携带 `code` 常量 + 结构化 `context` dict。"""

    code: str = "E_L103_UNKNOWN"

    def __init__(self, message: str = "", **context: Any) -> None:
        self.context = context
        detail = ", ".join(f"{k}={v!r}" for k, v in context.items())
        full = f"[{self.code}] {message}" + (f" ({detail})" if detail else "")
        super().__init__(full)


# --- 1xx 装图期 ---

class CycleError(L103Error):
    """DAG 检测到环。`cycle` 字段是环节点序列（from_wp, to_wp, ...）。"""

    code = "E_L103_L202_101"

    def __init__(self, cycle: list[tuple[str, str]]) -> None:
        self.cycle = cycle
        super().__init__("DAG 检测到环", cycle=cycle)


class DanglingDepsError(L103Error):
    """WP 的 deps 指向不存在的 wp_id。"""

    code = "E_L103_L202_102"

    def __init__(self, wp_id: str, missing_deps: list[str]) -> None:
        self.wp_id = wp_id
        self.missing_deps = missing_deps
        super().__init__("悬空依赖", wp_id=wp_id, missing_deps=missing_deps)


class IncompleteWPError(L103Error):
    """WP 4 要素（goal / dod_expr_ref / deps / effort_estimate）缺失。"""

    code = "E_L103_L202_103"

    def __init__(self, wp_id: str, missing_fields: list[str]) -> None:
        self.wp_id = wp_id
        self.missing_fields = missing_fields
        super().__init__("4 要素不完整", wp_id=wp_id, missing_fields=missing_fields)


class OversizeError(L103Error):
    """WP 粒度超限（effort_estimate > 5 天）。"""

    code = "E_L103_L202_104"

    def __init__(self, wp_id: str, effort: float, limit: float = 5.0) -> None:
        self.wp_id = wp_id
        self.effort = effort
        self.limit = limit
        super().__init__("WP 粒度超限", wp_id=wp_id, effort=effort, limit=limit)


class CrossProjectDepError(L103Error):
    """跨 project 依赖 · PM-14 硬红线。"""

    code = "E_L103_L202_105"

    def __init__(self, wp_id: str, expected_pid: str, got_pid: str) -> None:
        self.wp_id = wp_id
        self.expected_pid = expected_pid
        self.got_pid = got_pid
        super().__init__(
            "跨 project 依赖",
            wp_id=wp_id, expected_pid=expected_pid, got_pid=got_pid,
        )


# --- 2xx PM-14 归属 ---

class PM14MismatchError(L103Error):
    """`WorkPackage.project_id != WBSTopology.project_id`。"""

    code = "E_L103_L202_201"

    def __init__(self, wp_id: str, expected_pid: str, got_pid: str) -> None:
        self.wp_id = wp_id
        self.expected_pid = expected_pid
        self.got_pid = got_pid
        super().__init__(
            "PM-14 归属不一致",
            wp_id=wp_id, expected_pid=expected_pid, got_pid=got_pid,
        )


# --- 3xx 状态跃迁 ---

class ParallelismCapError(L103Error):
    """并行度上限超出（默认 parallelism_limit=2）。"""

    code = "E_L103_L202_301"

    def __init__(self, limit: int, running: int) -> None:
        self.limit = limit
        self.running = running
        super().__init__("并行度上限", limit=limit, running=running)


class DepsNotMetError(L103Error):
    """尝试 READY→RUNNING 但 deps 未全 DONE。"""

    code = "E_L103_L202_302"

    def __init__(self, wp_id: str, unmet_deps: list[str]) -> None:
        self.wp_id = wp_id
        self.unmet_deps = unmet_deps
        super().__init__("deps 未 satisfied", wp_id=wp_id, unmet_deps=unmet_deps)


class IllegalTransition(L103Error):
    """状态跃迁不在 LEGAL_TRANSITIONS 集合内。"""

    code = "E_L103_L202_303"

    def __init__(self, from_state: str, to_state: str, wp_id: str) -> None:
        self.from_state = from_state
        self.to_state = to_state
        self.wp_id = wp_id
        super().__init__(
            "非法状态跃迁",
            from_state=from_state, to_state=to_state, wp_id=wp_id,
        )


class StaleStateError(L103Error):
    """transition_state 时 wp 当前实际状态与 from_state 不符（并发竞态）。"""

    code = "E_L103_L202_304"

    def __init__(self, wp_id: str, expected_from: str, actual: str) -> None:
        self.wp_id = wp_id
        self.expected_from = expected_from
        self.actual = actual
        super().__init__(
            "stale state",
            wp_id=wp_id, expected_from=expected_from, actual=actual,
        )


class WPNotFoundError(L103Error):
    """wp_id 不在 topology 中。"""

    code = "E_L103_L202_305"

    def __init__(self, wp_id: str) -> None:
        self.wp_id = wp_id
        super().__init__("wp_id 不存在", wp_id=wp_id)


# --- 4xx 审计 / 事件 ---

class EventAppendError(L103Error):
    """向事件总线（IC-09）追加事件失败。"""

    code = "E_L103_L202_401"

    def __init__(self, event_type: str, reason: str) -> None:
        self.event_type = event_type
        self.reason = reason
        super().__init__("事件写入失败", event_type=event_type, reason=reason)


class RebuildFailedError(L103Error):
    """跨 session 重建（on_system_resumed）失败。"""

    code = "E_L103_L202_402"

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__("跨 session 重建失败", reason=reason)


# --- 5xx 一致性 / bypass ---

class ConsistencyBypassError(L103Error):
    """外部试图绕过 manager 直写内部状态（只读视图被篡改）。"""

    code = "E_L103_L202_501"

    def __init__(self, attempted: str) -> None:
        self.attempted = attempted
        super().__init__("外部 bypass 直写尝试", attempted=attempted)


# --- 业务层补充 ---

class RunningWPCannotBeDropped(L103Error):
    """diff_merge 尝试移除 state=RUNNING 的 WP（L2-01 差量合并守护）。"""

    code = "E_L103_L201_201"

    def __init__(self, wp_id: str) -> None:
        self.wp_id = wp_id
        super().__init__("RUNNING WP 不可被丢弃", wp_id=wp_id)


# --- 映射：错误码 → 类 ---

ERROR_CODE_INDEX: dict[str, type[L103Error]] = {
    cls.code: cls
    for cls in (
        CycleError, DanglingDepsError, IncompleteWPError, OversizeError,
        CrossProjectDepError, PM14MismatchError, ParallelismCapError,
        DepsNotMetError, IllegalTransition, StaleStateError, WPNotFoundError,
        EventAppendError, RebuildFailedError, ConsistencyBypassError,
        RunningWPCannotBeDropped,
    )
}


@dataclass(frozen=True)
class ErrorCodes:
    """3-2 TDD spec §11 14 条错误码常量（方便 test assertion）。"""

    E_L103_L202_101: str = "E_L103_L202_101"  # cycle
    E_L103_L202_102: str = "E_L103_L202_102"  # dangling deps
    E_L103_L202_103: str = "E_L103_L202_103"  # incomplete wp
    E_L103_L202_104: str = "E_L103_L202_104"  # oversize
    E_L103_L202_105: str = "E_L103_L202_105"  # cross project dep
    E_L103_L202_201: str = "E_L103_L202_201"  # PM-14 mismatch
    E_L103_L202_301: str = "E_L103_L202_301"  # parallelism cap
    E_L103_L202_302: str = "E_L103_L202_302"  # deps not met
    E_L103_L202_303: str = "E_L103_L202_303"  # illegal transition
    E_L103_L202_304: str = "E_L103_L202_304"  # stale state
    E_L103_L202_305: str = "E_L103_L202_305"  # wp not found
    E_L103_L202_401: str = "E_L103_L202_401"  # event append failed
    E_L103_L202_402: str = "E_L103_L202_402"  # rebuild failed
    E_L103_L202_501: str = "E_L103_L202_501"  # consistency bypass


ERROR_CODES = ErrorCodes()
