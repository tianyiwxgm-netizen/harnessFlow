"""L2-01 Event Bus · Pydantic schemas + exception hierarchy.

对齐：
- 3-1 L2-01 §3.2 append_event_request / response
- 3-1 L2-01 §7.1 EventEntry 字段级 schema
- 3-1 L2-01 §3.2 错误码表（14 条）

L2-01 的入参（Event）在 L1-01~L1-10 之间形成 PM-08 单一事实源 · 每个字段都是契约。
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# 合法 L1 前缀 · §3.2 TypePrefixValidator
VALID_L1_PREFIXES: tuple[str, ...] = (
    "L1-01", "L1-02", "L1-03", "L1-04", "L1-05",
    "L1-06", "L1-07", "L1-08", "L1-09", "L1-10",
)

# 合法 actor 命名前缀 · §3.2 actor pattern
VALID_ACTORS: tuple[str, ...] = (
    "main_loop", "planner", "executor", "verifier", "supervisor",
    "ui", "recoverer", "audit_mirror",
)

VALID_STATES: tuple[str, ...] = (
    "NOT_EXIST", "INIT", "PLAN", "EXEC", "CLOSE", "CLOSED", "HALTED",
)


class BusState(StrEnum):
    """§8 bus_state · 完整 9 态简化版（WP04 只用 3 态 · WP05/06 扩展）."""
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    HALTED = "HALTED"


class Event(BaseModel):
    """append() 入参 · PM-08 单一事实源的物理承载.

    对齐 §3.2 入参 schema（YAML）· 精确到字段 pattern.

    不变量（pydantic 校验）：
        - project_id 匹配 PM-14 分片键格式
        - type 前缀属于合法 L1 白名单
        - actor 属于合法 actor 白名单（或 human:*）
        - timestamp 是 ISO8601（datetime）
    """
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    # === 路由必填 ===
    project_id: str = Field(
        ...,
        pattern=r"^[a-z0-9_-]{1,40}$",
        description="PM-14 分片键 · ≤ 40 chars snake-case",
    )
    # === 事件本体 ===
    type: str = Field(
        ...,
        pattern=r"^L1-(01|02|03|04|05|06|07|08|09|10):[a-z0-9_]+$",
        description="L1 前缀白名单 · L1-XX:event_name",
    )
    actor: str = Field(
        ...,
        pattern=r"^(main_loop|planner|executor|verifier|supervisor|ui|recoverer|audit_mirror|human:.+)$",
        description="事件产生者 · 受限白名单",
    )
    timestamp: datetime = Field(..., description="ISO 8601 带时区")
    state: str | None = Field(
        None,
        description="调用方 L1-01 state 快照（可选）· 便于 replay",
    )
    payload: dict[str, Any] = Field(default_factory=dict, description="业务字段 · 自由")
    links: list[dict[str, Any]] = Field(
        default_factory=list,
        description="跨 L1 关联（kind + ref）· L2-03 建反向索引",
    )
    # === 元字段（调用方可选）===
    event_id: str | None = Field(
        None,
        pattern=r"^evt_[0-9A-HJKMNP-TV-Z]{26}$",
        description="ULID · 调用方可不传 · L2-01 自动生成",
    )
    is_meta: bool = Field(
        default=False,
        description="I-08 防递归 · 元事件不触发元事件",
    )
    idempotency_key: str | None = Field(
        None,
        description="相同 key 10 min 内重复 → 返 idempotent_replay",
    )


class AppendEventResult(BaseModel):
    """append() 成功返回 · §3.2 response_ok schema."""
    model_config = ConfigDict(frozen=True)

    event_id: str = Field(..., pattern=r"^evt_[0-9A-HJKMNP-TV-Z]{26}$")
    sequence: int = Field(..., ge=0)
    hash: str = Field(..., pattern=r"^[a-f0-9]{64}$")
    prev_hash: str = Field(..., description="^[a-f0-9]{64}$ 或 'GENESIS'")
    persisted_at: datetime
    jsonl_offset: int = Field(..., ge=0)
    file_path: str
    broadcast_enqueued: bool = Field(default=False)
    # 幂等重放标志（§3.2 E_BUS_IDEMPOTENT_REPLAY）
    idempotent_replay: bool = Field(default=False)


class ProjectMeta(BaseModel):
    """project 内 seq + last_hash 持久化 · §6.3 SequenceAllocator 配套."""
    model_config = ConfigDict(frozen=False)  # 可变 · 随 append 更新

    project_id: str
    last_sequence: int = Field(default=-1, ge=-1)
    last_hash: str = Field(default="GENESIS", description="64-hex 或 GENESIS")
    updated_at: datetime | None = None


# =========================================================
# Exception hierarchy · §3.2 错误码（14 条）
# =========================================================

class EventBusError(Exception):
    """L2-01 所有错误基类."""
    error_code: str = "E_BUS_BASE"
    halt_system: bool = False
    retryable: bool = False

    def __init__(
        self,
        message: str = "",
        *,
        cause: str | None = None,
        correlation_id: str | None = None,
        **extra: Any,
    ) -> None:
        super().__init__(message or self.error_code)
        self.cause = cause
        self.correlation_id = correlation_id
        self.extra = extra


class BusProjectNotRegistered(EventBusError):
    error_code = "E_BUS_PROJECT_NOT_REGISTERED"


class BusTypePrefixViolation(EventBusError):
    error_code = "E_BUS_TYPE_PREFIX_VIOLATION"


class BusSchemaInvalid(EventBusError):
    error_code = "E_BUS_SCHEMA_INVALID"


class BusLockTimeout(EventBusError):
    error_code = "E_BUS_LOCK_TIMEOUT"
    retryable = True


class BusDeadlockDetected(EventBusError):
    error_code = "E_BUS_DEADLOCK_DETECTED"
    retryable = True


class BusWriteFailed(EventBusError):
    """L2-05 atomic_append 重试耗尽 · 响应面 4 硬 halt."""
    error_code = "E_BUS_WRITE_FAILED"
    halt_system = True


class BusDiskFull(EventBusError):
    error_code = "E_BUS_DISK_FULL"
    halt_system = True


class BusHashChainBroken(EventBusError):
    """启动时 verify 发现链断 · 拒启动."""
    error_code = "E_BUS_HASH_CHAIN_BROKEN"
    halt_system = True


class BusHalted(EventBusError):
    """bus_state = HALTED · 禁自动重试."""
    error_code = "E_BUS_HALTED"
    halt_system = True


class BusShutdownRejected(EventBusError):
    error_code = "E_BUS_SHUTDOWN_REJECTED"


class BusFsyncFailed(EventBusError):
    """fsync 失败 · 响应面 4 · halt."""
    error_code = "E_BUS_FSYNC_FAILED"
    halt_system = True


class BusUnsafeWriteWithoutLock(EventBusError):
    """断言：调用 atomic_append 时未持锁."""
    error_code = "E_BUS_UNSAFE_WRITE_WITHOUT_LOCK"
    halt_system = True


class BusNoProjectOrSystem(EventBusError):
    """payload 缺 project_id 且非 system 级事件."""
    error_code = "E_EVT_NO_PROJECT_OR_SYSTEM"


__all__ = [
    "VALID_L1_PREFIXES",
    "VALID_ACTORS",
    "VALID_STATES",
    "BusState",
    "Event",
    "AppendEventResult",
    "ProjectMeta",
    # Errors
    "EventBusError",
    "BusProjectNotRegistered",
    "BusTypePrefixViolation",
    "BusSchemaInvalid",
    "BusLockTimeout",
    "BusDeadlockDetected",
    "BusWriteFailed",
    "BusDiskFull",
    "BusHashChainBroken",
    "BusHalted",
    "BusShutdownRejected",
    "BusFsyncFailed",
    "BusUnsafeWriteWithoutLock",
    "BusNoProjectOrSystem",
]
_ = Literal  # re-exported for type hints in core
