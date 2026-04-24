"""Supervisor L1-07 统一错误码。

L2-01 8-dim collector 相关 18 个（TC-L107-L201-101~120）。
其他 L2 后续扩充 · 放在同一 enum 便于对外引用。
"""
from __future__ import annotations

from enum import Enum


class SupervisorError(str, Enum):
    """L1-07 对外错误码 · 对应 §1.2 error table。"""

    # PM-14 / schema
    MISSING_PROJECT_ID = "E_MISSING_PROJECT_ID"
    INVALID_PROJECT_ID_FORMAT = "E_INVALID_PROJECT_ID_FORMAT"
    SCHEMA_VERSION_MISMATCH = "E_SCHEMA_VERSION_MISMATCH"
    SCHEMA_VALIDATION_FAILED = "E_SCHEMA_VALIDATION_FAILED"

    # IC timeouts / unavailable
    IC_L1_02_TIMEOUT = "E_IC_L1_02_TIMEOUT"
    IC_L1_02_UNAVAILABLE = "E_IC_L1_02_UNAVAILABLE"
    IC_L1_03_TIMEOUT = "E_IC_L1_03_TIMEOUT"
    IC_L1_03_UNAVAILABLE = "E_IC_L1_03_UNAVAILABLE"
    IC_L1_04_TIMEOUT = "E_IC_L1_04_TIMEOUT"
    IC_L1_04_UNAVAILABLE = "E_IC_L1_04_UNAVAILABLE"
    IC_L1_09_TIMEOUT = "E_IC_L1_09_TIMEOUT"
    IC_L1_09_UNAVAILABLE = "E_IC_L1_09_UNAVAILABLE"

    # 8-dim state degradation
    ALL_DIMS_MISSING = "E_ALL_DIMS_MISSING"
    LAST_KNOWN_GOOD_EXPIRED = "E_LAST_KNOWN_GOOD_EXPIRED"
    PHASE_UNKNOWN = "E_PHASE_UNKNOWN"

    # budget / quota / operation
    HOOK_BUDGET_EXCEEDED = "E_HOOK_BUDGET_EXCEEDED"
    CONSUMER_QUOTA_EXCEEDED = "E_CONSUMER_QUOTA_EXCEEDED"
    PERSIST_FAILED = "E_PERSIST_FAILED"
    EMIT_EVENT_FAILED = "E_EMIT_EVENT_FAILED"
    READ_ONLY_VIOLATION = "E_READ_ONLY_VIOLATION"


class SupervisorException(Exception):
    """统一异常封装 · 带 error-code + 上下文。"""

    def __init__(self, code: SupervisorError, message: str = "", **ctx: object) -> None:
        self.code = code
        self.ctx = ctx
        suffix = f" · {ctx}" if ctx else ""
        super().__init__(f"[{code.value}] {message}{suffix}")
