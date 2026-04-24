"""L1-01 L2-06 · Supervisor 建议接收器 · schemas。

Dev-ζ 侧 3 条 IC（producer 侧已 merged 到 main）分别对应本模块 3 个 inbox envelope:

- IC-13 `PushSuggestionCommand` → `SuggestionInbox`：按 `level` 分发 INFO/SUGG/WARN
- IC-14 `PushRollbackRouteCommand` → `RollbackInbox`：转发 `quality_loop.rollback_router.IC14Consumer`
- IC-15 `RequestHardHaltCommand` → `HaltSignal`：Sync ≤ 100ms 硬约束（HRL-05）

严格对齐 3-1 L2-06 §3 的对外接口 · 但 WP06 范围 = receiver shim（最小可消费）·
完整 AdviceQueue / 4 级 counter / watchdog 留给后续 WP 扩展。
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.supervisor.event_sender.schemas import (
    HardHaltState,
    PushRollbackRouteCommand,
    PushSuggestionCommand,
    RequestHardHaltCommand,
    SuggestionLevel,
)


class AdviceLevel(str, Enum):
    """receiver 内部 3 级路由 enum · 对齐 Dev-ζ `SuggestionLevel` 但更显式。

    BLOCK 不是本接口接收（BLOCK 走 IC-15 halt 通道），这里只 3 级。
    """

    INFO = "INFO"
    SUGG = "SUGG"
    WARN = "WARN"


class SuggestionInbox(BaseModel):
    """IC-13 消费端 envelope · 内部 wrap 生产端 `PushSuggestionCommand`。

    - `command`：原始 Dev-ζ IC-13 payload（frozen）
    - `level`：冗余派生 · 供 receiver 路由 O(1) 判级
    - `received_at_ms`：monotonic 时间戳 · latency 度量
    """

    model_config = {"frozen": True}

    command: PushSuggestionCommand
    level: AdviceLevel
    received_at_ms: int = Field(..., ge=0)

    @classmethod
    def from_command(
        cls, cmd: PushSuggestionCommand, *, received_at_ms: int,
    ) -> "SuggestionInbox":
        """自 Dev-ζ producer 命令组装 inbox · 派生 level。"""
        return cls(
            command=cmd,
            level=AdviceLevel(cmd.level.value),
            received_at_ms=received_at_ms,
        )


class SuggestionAck(BaseModel):
    """IC-13 消费端 ack · 对 Dev-ζ `PushSuggestionAck` 的补充。

    Dev-ζ 生产端只关心 "push 成功"，消费端补充：
    - `routed_to`：分到哪一级 queue（INFO/SUGG/WARN）
    - `queue_depth_after`：本级 queue 入队后深度 · 背压依据
    """

    model_config = {"frozen": True}

    suggestion_id: str
    accepted: bool
    routed_to: AdviceLevel
    queue_depth_after: int = Field(..., ge=0)
    reject_reason: str | None = None


class RollbackInbox(BaseModel):
    """IC-14 消费端 envelope · 转发 `quality_loop.rollback_router.IC14Consumer`。

    - `command`：原始 Dev-ζ IC-14 payload
    - `received_at_ms`：monotonic 时间戳
    """

    model_config = {"frozen": True}

    command: PushRollbackRouteCommand
    received_at_ms: int = Field(..., ge=0)

    @classmethod
    def from_command(
        cls, cmd: PushRollbackRouteCommand, *, received_at_ms: int,
    ) -> "RollbackInbox":
        return cls(command=cmd, received_at_ms=received_at_ms)


class RollbackAck(BaseModel):
    """IC-14 消费端 ack · 记录是否转发成功 + 幂等命中。"""

    model_config = {"frozen": True}

    route_id: str
    forwarded: bool
    idempotent_hit: bool = False
    target_new_state: str | None = None
    reject_reason: str | None = None


class HaltState(str, Enum):
    """IC-15 receiver 侧返回状态 · 与 Dev-ζ `HardHaltState` 一致。"""

    RUNNING = HardHaltState.RUNNING.value
    PAUSED = HardHaltState.PAUSED.value
    HALTED = HardHaltState.HALTED.value


class HaltSignal(BaseModel):
    """IC-15 消费端 envelope · Sync ≤ 100ms 硬约束（HRL-05）。

    - `command`：原始 Dev-ζ IC-15 payload
    - `received_at_ms`：monotonic 时间戳 · bench 对账起点
    """

    model_config = {"frozen": True}

    command: RequestHardHaltCommand
    received_at_ms: int = Field(..., ge=0)

    @classmethod
    def from_command(
        cls, cmd: RequestHardHaltCommand, *, received_at_ms: int,
    ) -> "HaltSignal":
        return cls(command=cmd, received_at_ms=received_at_ms)


class HaltAck(BaseModel):
    """IC-15 消费端 ack · **必带 latency_ms · P99 ≤ 100ms 硬约束（HRL-05）**。

    - `halted`：是否执行了 halt（幂等命中时也为 true）
    - `latency_ms`：从 `received_at_ms` 到 halt 完成的端到端延迟
    - `state_before` / `state_after`：halt 前后状态
    - `slo_violated`：latency_ms > 100 · pytest-benchmark 判红标志
    """

    model_config = {"frozen": True}

    halt_id: str
    halted: bool
    latency_ms: int = Field(..., ge=0)
    state_before: HaltState
    state_after: HaltState = HaltState.HALTED
    slo_violated: bool = False
    idempotent_hit: bool = False

    @field_validator("slo_violated")
    @classmethod
    def _coerce_slo_violated(cls, v: bool) -> bool:
        # latency_ms > 100 时建议自觉标 true · 但不强制（留给调用侧感知）
        return v


__all__ = [
    "AdviceLevel",
    "HaltAck",
    "HaltSignal",
    "HaltState",
    "RollbackAck",
    "RollbackInbox",
    "SuggestionAck",
    "SuggestionInbox",
]
