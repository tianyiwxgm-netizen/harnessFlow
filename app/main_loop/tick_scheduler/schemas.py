"""L2-01 Tick 调度器 · Value Objects / DTO / Error · WP04 简化范围。

对齐 3-1 tech §3 + §10 配置 · §11 错误码:
- TickBudget: 本 tick 预算(tick_interval_ms / tick_deadline_ns · monotonic)
- TickState: 4 态运行态机 (IDLE/RUNNING/PAUSED/HALTED)
- TickEvent: schedule/dispatch/panic/halt/drift_violation 单条可观测审计点
- TickResult: 单 tick 返回(含 latency_ms · drift_ms · action 指针)
- TickDriftViolation/TickError: 硬约束违反异常

HRL-04(HarnessFlow Release Blocker 04):
- tick drift ≤ 100ms P99 (pytest-benchmark 强校验)
- 与 HRL-05 (IC-15 halt ≤ 100ms) 同级红线
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

# ------------------------------------------------------------------
# 4 态运行态 · 简化版 (对齐 §8 但缩减 · 对齐 HardHaltState 命名)
# ------------------------------------------------------------------
TickStateName = Literal["IDLE", "RUNNING", "PAUSED", "HALTED"]


class TickState(str, Enum):
    """Tick 调度器运行态 · 4 态简化版 (WP04 范围)。

    - IDLE:     未启动 / 已停止
    - RUNNING:  主 loop 正常 tick 中
    - PAUSED:   收到 IC-17 user_panic 后 · 主 loop 拒绝 dispatch
    - HALTED:   收到 IC-15 hard_halt 后 · 主 loop 拒绝一切 · 仅用户 IC-17 authorize 可清除

    对齐 app.supervisor.event_sender.schemas.HardHaltState (RUNNING/PAUSED/HALTED 三值一致)。
    """

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    HALTED = "HALTED"


# 可终止态集合 (不再从此迁出 · 只能 restart)
TERMINAL_STATES: frozenset[TickState] = frozenset({TickState.HALTED})


# ------------------------------------------------------------------
# 配置 · 默认值 (§10 配置清单 + HRL-04)
# ------------------------------------------------------------------
TICK_INTERVAL_MS_DEFAULT: int = 100  # 心脏 tick
TICK_DRIFT_SLO_MS: int = 100  # 硬约束 · release blocker HRL-04
HARD_HALT_SLO_MS: int = 100  # §12.1 硬约束 · 与 HRL-05 对齐
PANIC_SLO_MS: int = 100  # §12.1 硬约束


# ------------------------------------------------------------------
# TickBudget · 单 tick 预算 (不可变)
# ------------------------------------------------------------------
@dataclass(frozen=True)
class TickBudget:
    """单 tick 预算 · monotonic 时间戳。

    字段级契约:
    - tick_id:           tick-{int · monotonic counter}
    - interval_ms:       本 tick 周期 (default 100)
    - started_at_ns:     perf_counter_ns 起点
    - deadline_ns:       started_at_ns + interval_ms * 1_000_000 (硬截止)
    - drift_slo_ms:      本 tick 判红阈值(default 100)
    """

    tick_id: str
    interval_ms: int
    started_at_ns: int
    deadline_ns: int
    drift_slo_ms: int = TICK_DRIFT_SLO_MS

    def __post_init__(self) -> None:
        if self.interval_ms <= 0:
            raise ValueError(f"interval_ms must be positive · got {self.interval_ms}")
        if self.drift_slo_ms <= 0:
            raise ValueError(f"drift_slo_ms must be positive · got {self.drift_slo_ms}")
        if self.deadline_ns <= self.started_at_ns:
            raise ValueError(
                f"deadline_ns {self.deadline_ns} must be > started_at_ns {self.started_at_ns}"
            )

    @property
    def budget_ms(self) -> int:
        """本 tick 总预算 (ms)。"""
        return (self.deadline_ns - self.started_at_ns) // 1_000_000


# ------------------------------------------------------------------
# TickEvent · 每 tick 审计事件(对 L2-05 IC-L2-05 的 payload 投影)
# ------------------------------------------------------------------
class TickEventType(str, Enum):
    """tick loop 产生的审计事件类型 · 对齐 §3.1/§3.2/§3.3 tick_scheduled 等。"""

    TICK_SCHEDULED = "tick_scheduled"
    TICK_DISPATCHED = "tick_dispatched"
    TICK_COMPLETED = "tick_completed"
    TICK_DRIFT_VIOLATED = "tick_drift_violated"  # P99 判红证据
    HALT_RECEIVED = "halt_received"
    PANIC_RECEIVED = "panic_received"
    STATE_CHANGED = "state_changed"
    ACTION_REJECTED = "action_rejected"  # HALTED 期间


@dataclass(frozen=True)
class TickEvent:
    """tick loop 单 event · 审计追溯基本单位。

    - event_type:     TickEventType enum (see above)
    - tick_id:        关联 tick
    - project_id:     PM-14 根字段
    - state_before:   state 变更前
    - state_after:    state 变更后
    - latency_ms:     单 tick 耗时 (tick_completed 必有)
    - drift_ms:       偏离 interval 量 (tick_completed / drift_violated 必有)
    - extra:          额外上下文 (panic_id / halt_id / red_line_id 等)
    """

    event_type: TickEventType
    tick_id: str
    project_id: str
    ts_ns: int  # monotonic
    state_before: TickState | None = None
    state_after: TickState | None = None
    latency_ms: int | None = None
    drift_ms: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


# ------------------------------------------------------------------
# TickResult · 单 tick 返回 (供测试/观测)
# ------------------------------------------------------------------
@dataclass(frozen=True)
class TickResult:
    """单 tick 调度结果。

    - tick_id:        关联 tick
    - dispatched:     是否真正派发了 action (PAUSED / HALTED 期间 false)
    - action_kind:    派发 action 类型 (invoke_skill / no_op 等 · 可为 None 表未派发)
    - latency_ms:     loop iteration 耗时
    - drift_ms:       偏离 interval 量 · abs(actual_interval - target_interval)
    - drift_violated: drift_ms > drift_slo_ms
    - state:          tick 完成后 state
    - reject_reason:  dispatched=false 时 · 拒绝原因 (HALTED/PAUSED/NO_DECISION)
    """

    tick_id: str
    dispatched: bool
    action_kind: str | None
    latency_ms: int
    drift_ms: int
    drift_violated: bool
    state: TickState
    reject_reason: str | None = None


# ------------------------------------------------------------------
# 错误码 (E_TICK_*)  · §11 简化子集(WP04 范围 · 10 项核心红线)
# ------------------------------------------------------------------
E_TICK_NO_PROJECT_ID = "E_TICK_NO_PROJECT_ID"
E_TICK_CROSS_PROJECT = "E_TICK_CROSS_PROJECT"
E_TICK_HALTED_REJECT = "E_TICK_HALTED_REJECT"
E_TICK_PAUSED_REJECT = "E_TICK_PAUSED_REJECT"
E_TICK_DRIFT_VIOLATION = "E_TICK_DRIFT_VIOLATION"
E_TICK_HALT_SLO_VIOLATION = "E_TICK_HALT_SLO_VIOLATION"
E_TICK_HALT_INVALID_STATE = "E_TICK_HALT_INVALID_STATE"
E_TICK_PANIC_SLO_VIOLATION = "E_TICK_PANIC_SLO_VIOLATION"
E_TICK_PANIC_NO_USER_ID = "E_TICK_PANIC_NO_USER_ID"
E_TICK_PANIC_ALREADY_PAUSED = "E_TICK_PANIC_ALREADY_PAUSED"
E_TICK_LOOP_ALREADY_STARTED = "E_TICK_LOOP_ALREADY_STARTED"
E_TICK_LOOP_NOT_RUNNING = "E_TICK_LOOP_NOT_RUNNING"
E_TICK_INVALID_INTERVAL = "E_TICK_INVALID_INTERVAL"
E_TICK_DECISION_TIMEOUT = "E_TICK_DECISION_TIMEOUT"


class TickError(Exception):
    """基础异常 · 携带 error_code / project_id / context (审计追溯)。"""

    def __init__(
        self,
        *,
        error_code: str,
        message: str = "",
        project_id: str = "",
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message or error_code)
        self.error_code = error_code
        self.project_id = project_id
        self.context = context or {}

    def __repr__(self) -> str:  # pragma: no cover - 调试
        return (
            f"TickError(error_code={self.error_code!r}, "
            f"project_id={self.project_id!r}, context={self.context!r})"
        )


# ------------------------------------------------------------------
# DriftViolation · release blocker 证据
# ------------------------------------------------------------------
@dataclass(frozen=True)
class DriftViolationRecord:
    """单条 drift 违反记录 · 供 HRL-04 审计 + L1-07 升级。"""

    tick_id: str
    project_id: str
    expected_interval_ms: int
    actual_interval_ms: int
    drift_ms: int
    ts_ns: int
    context: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "E_TICK_CROSS_PROJECT",
    "E_TICK_DECISION_TIMEOUT",
    "E_TICK_DRIFT_VIOLATION",
    "E_TICK_HALTED_REJECT",
    "E_TICK_HALT_INVALID_STATE",
    "E_TICK_HALT_SLO_VIOLATION",
    "E_TICK_INVALID_INTERVAL",
    "E_TICK_LOOP_ALREADY_STARTED",
    "E_TICK_LOOP_NOT_RUNNING",
    "E_TICK_NO_PROJECT_ID",
    "E_TICK_PANIC_ALREADY_PAUSED",
    "E_TICK_PANIC_NO_USER_ID",
    "E_TICK_PANIC_SLO_VIOLATION",
    "E_TICK_PAUSED_REJECT",
    "HARD_HALT_SLO_MS",
    "PANIC_SLO_MS",
    "TERMINAL_STATES",
    "TICK_DRIFT_SLO_MS",
    "TICK_INTERVAL_MS_DEFAULT",
    "DriftViolationRecord",
    "TickBudget",
    "TickError",
    "TickEvent",
    "TickEventType",
    "TickResult",
    "TickState",
    "TickStateName",
]
