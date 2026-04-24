"""L1-04 · L2-02 · 错误码 + 异常层级.

锚点:docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-02-DoD 表达式编译器.md §3.6 + §11.1
错误码前缀:`E_L204_L202_`(L1-04 · L2-02)

分类:
    - compile 期 (AST_SYNTAX / AST_ILLEGAL_NODE / AST_ILLEGAL_FUNCTION / RECURSION_LIMIT / AC_* / ...)
    - eval 期 (EVAL_TIMEOUT / DATA_SOURCE_INVALID / CALLER_UNAUTHORIZED / CACHE_POISON / ...)
    - 安全(WHITELIST_TAMPERING / SANDBOX_ESCAPE / ONLINE_WHITELIST_MUTATION)
    - 幂等(IDEMPOTENCY_VIOLATION)
    - 资源(CONCURRENT_EVAL_CAP / EVAL_MEMORY_EXCEEDED)
"""
from __future__ import annotations

# ========== 错误码常量 ==========

# 入参/PM-14
E_NO_PROJECT_ID = "E_L204_L202_NO_PROJECT_ID"
E_CROSS_PROJECT = "E_L204_L202_CROSS_PROJECT"

# AST / 白名单
E_AST_SYNTAX_ERROR = "E_L204_L202_AST_SYNTAX_ERROR"
E_AST_ILLEGAL_NODE = "E_L204_L202_AST_ILLEGAL_NODE"
E_AST_ILLEGAL_FUNCTION = "E_L204_L202_AST_ILLEGAL_FUNCTION"
E_RECURSION_LIMIT = "E_L204_L202_RECURSION_LIMIT"

# 条款映射
E_AC_NOT_MAPPABLE = "E_L204_L202_AC_NOT_MAPPABLE"
E_AC_REVERSE_LOOKUP_FAILED = "E_L204_L202_AC_REVERSE_LOOKUP_FAILED"

# eval 运行期
E_EVAL_TIMEOUT = "E_L204_L202_EVAL_TIMEOUT"
E_DATA_SOURCE_INVALID = "E_L204_L202_DATA_SOURCE_INVALID"
E_DATA_SOURCE_UNKNOWN_TYPE = "E_L204_L202_DATA_SOURCE_UNKNOWN_TYPE"
E_WHITELIST_VERSION_MISMATCH = "E_L204_L202_WHITELIST_VERSION_MISMATCH"
E_CALLER_UNAUTHORIZED = "E_L204_L202_CALLER_UNAUTHORIZED"
E_CACHE_POISON = "E_L204_L202_CACHE_POISON"
E_EVAL_MEMORY_EXCEEDED = "E_L204_L202_EVAL_MEMORY_EXCEEDED"
E_CONCURRENT_EVAL_CAP = "E_L204_L202_CONCURRENT_EVAL_CAP"
E_SANDBOX_ESCAPE_DETECTED = "E_L204_L202_SANDBOX_ESCAPE_DETECTED"

# 安全
E_WHITELIST_TAMPERING = "E_L204_L202_WHITELIST_TAMPERING"
E_ONLINE_WHITELIST_MUTATION = "E_L204_L202_ONLINE_WHITELIST_MUTATION"

# compile 批
E_COMPILE_TIMEOUT = "E_L204_L202_COMPILE_TIMEOUT"
E_COMPILE_OVERSIZED = "E_L204_L202_COMPILE_OVERSIZED"
E_IDEMPOTENCY_VIOLATION = "E_L204_L202_IDEMPOTENCY_VIOLATION"

ALL_ERROR_CODES = frozenset({
    E_NO_PROJECT_ID,
    E_CROSS_PROJECT,
    E_AST_SYNTAX_ERROR,
    E_AST_ILLEGAL_NODE,
    E_AST_ILLEGAL_FUNCTION,
    E_RECURSION_LIMIT,
    E_AC_NOT_MAPPABLE,
    E_AC_REVERSE_LOOKUP_FAILED,
    E_EVAL_TIMEOUT,
    E_DATA_SOURCE_INVALID,
    E_DATA_SOURCE_UNKNOWN_TYPE,
    E_WHITELIST_VERSION_MISMATCH,
    E_CALLER_UNAUTHORIZED,
    E_CACHE_POISON,
    E_EVAL_MEMORY_EXCEEDED,
    E_CONCURRENT_EVAL_CAP,
    E_SANDBOX_ESCAPE_DETECTED,
    E_WHITELIST_TAMPERING,
    E_ONLINE_WHITELIST_MUTATION,
    E_COMPILE_TIMEOUT,
    E_COMPILE_OVERSIZED,
    E_IDEMPOTENCY_VIOLATION,
})


# ========== 异常类层级 ==========


class DoDExpressionError(Exception):
    """L2-02 DoD 表达式编译器的根异常."""

    error_code: str = "E_L204_L202_UNKNOWN"

    def __init__(self, message: str = "", *, error_code: str | None = None) -> None:
        super().__init__(message)
        if error_code is not None:
            self.error_code = error_code

    def __str__(self) -> str:  # pragma: no cover - trivial
        base = super().__str__()
        return f"[{self.error_code}] {base}" if base else f"[{self.error_code}]"


class DoDCompileError(DoDExpressionError):
    """编译期错误基类."""


class DoDEvalError(DoDExpressionError):
    """运行期错误基类."""


class DoDSecurityError(DoDExpressionError):
    """安全相关错误基类(SA-01/02/06/07)."""


# compile 期 --------------


class ASTSyntaxError(DoDCompileError):
    error_code = E_AST_SYNTAX_ERROR


class IllegalNodeError(DoDSecurityError):
    error_code = E_AST_ILLEGAL_NODE


class IllegalFunctionError(DoDSecurityError):
    error_code = E_AST_ILLEGAL_FUNCTION


class RecursionLimitExceeded(DoDCompileError):
    error_code = E_RECURSION_LIMIT


class ACReverseLookupFailedError(DoDCompileError):
    error_code = E_AC_REVERSE_LOOKUP_FAILED


class CompileOversizedError(DoDCompileError):
    error_code = E_COMPILE_OVERSIZED


class IdempotencyViolationError(DoDCompileError):
    error_code = E_IDEMPOTENCY_VIOLATION


# eval 期 ---------------


class NoProjectIdError(DoDEvalError):
    error_code = E_NO_PROJECT_ID


class CrossProjectError(DoDSecurityError):
    error_code = E_CROSS_PROJECT


class EvalTimeoutError(DoDEvalError):
    error_code = E_EVAL_TIMEOUT


class DataSourceInvalidError(DoDEvalError):
    error_code = E_DATA_SOURCE_INVALID


class DataSourceUnknownTypeError(DoDEvalError):
    error_code = E_DATA_SOURCE_UNKNOWN_TYPE


class WhitelistVersionMismatchError(DoDEvalError):
    error_code = E_WHITELIST_VERSION_MISMATCH


class CallerUnauthorizedError(DoDSecurityError):
    error_code = E_CALLER_UNAUTHORIZED


class CachePoisonError(DoDSecurityError):
    error_code = E_CACHE_POISON


class EvalMemoryExceededError(DoDEvalError):
    error_code = E_EVAL_MEMORY_EXCEEDED


class ConcurrentEvalCapError(DoDEvalError):
    error_code = E_CONCURRENT_EVAL_CAP


class SandboxEscapeDetectedError(DoDSecurityError):
    error_code = E_SANDBOX_ESCAPE_DETECTED


# 安全 ---------------


class WhitelistTamperingError(DoDSecurityError):
    error_code = E_WHITELIST_TAMPERING


class OnlineWhitelistMutationError(DoDSecurityError):
    error_code = E_ONLINE_WHITELIST_MUTATION


__all__ = [
    "ACReverseLookupFailedError",
    "ALL_ERROR_CODES",
    "ASTSyntaxError",
    "CachePoisonError",
    "CallerUnauthorizedError",
    "CompileOversizedError",
    "ConcurrentEvalCapError",
    "CrossProjectError",
    "DataSourceInvalidError",
    "DataSourceUnknownTypeError",
    "DoDCompileError",
    "DoDEvalError",
    "DoDExpressionError",
    "DoDSecurityError",
    "E_AC_NOT_MAPPABLE",
    "E_AC_REVERSE_LOOKUP_FAILED",
    "E_AST_ILLEGAL_FUNCTION",
    "E_AST_ILLEGAL_NODE",
    "E_AST_SYNTAX_ERROR",
    "E_CACHE_POISON",
    "E_CALLER_UNAUTHORIZED",
    "E_COMPILE_OVERSIZED",
    "E_COMPILE_TIMEOUT",
    "E_CONCURRENT_EVAL_CAP",
    "E_CROSS_PROJECT",
    "E_DATA_SOURCE_INVALID",
    "E_DATA_SOURCE_UNKNOWN_TYPE",
    "E_EVAL_MEMORY_EXCEEDED",
    "E_EVAL_TIMEOUT",
    "E_IDEMPOTENCY_VIOLATION",
    "E_NO_PROJECT_ID",
    "E_ONLINE_WHITELIST_MUTATION",
    "E_RECURSION_LIMIT",
    "E_SANDBOX_ESCAPE_DETECTED",
    "E_WHITELIST_TAMPERING",
    "E_WHITELIST_VERSION_MISMATCH",
    "EvalMemoryExceededError",
    "EvalTimeoutError",
    "IdempotencyViolationError",
    "IllegalFunctionError",
    "IllegalNodeError",
    "NoProjectIdError",
    "OnlineWhitelistMutationError",
    "RecursionLimitExceeded",
    "SandboxEscapeDetectedError",
    "WhitelistTamperingError",
    "WhitelistVersionMismatchError",
]
