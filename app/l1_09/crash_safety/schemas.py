"""L2-05 Crash Safety · Pydantic schemas + exception hierarchy.

对齐源文档：
- docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-05-崩溃安全层.md §3.2 / §3.6 / §7.2-§7.6
- docs/3-2-Solution-TDD/L1-09-韧性+审计/L2-05-崩溃安全层-tests.md §2/§3 TC-001 ~ TC-112

本模块**纯数据**（Pydantic frozen=True）· 无副作用 · 由 atomic_writer / appender / hash_chain /
integrity_checker 4 个算法模块 import。
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ============================================================
# 结果类型 · Value Objects (frozen)
# ============================================================

class WriteResult(BaseModel):
    """write_atomic 返回值 · 对应 §3.2."""
    model_config = ConfigDict(frozen=True)

    op_id: str = Field(..., pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$", description="ULID")
    target_path: str
    bytes_written: int = Field(..., ge=0)
    content_hash: str = Field(..., pattern=r"^[a-f0-9]{64}$", description="sha256(content) hex")
    duration_ms: float = Field(..., ge=0)
    retry_count: int = Field(..., ge=0, le=2)


class AppendResult(BaseModel):
    """append_atomic 返回值 · 对应 §3.3."""
    model_config = ConfigDict(frozen=True)

    op_id: str = Field(..., pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$")
    target_path: str
    offset: int = Field(..., ge=0, description="本次 write 前的文件 offset")
    bytes_written: int = Field(..., ge=0)
    line_hash: str = Field(..., pattern=r"^[a-f0-9]{64}$", description="sha256(line) hex · 不含 \\n")
    duration_ms: float = Field(..., ge=0)
    retry_count: int = Field(..., ge=0, le=2)


class IntegrityMethod(StrEnum):
    """§3.4 IntegrityMethod · 对齐源文档 `class IntegrityMethod(str, Enum)`（StrEnum 等价）."""
    HASH_CHAIN = "hash_chain"
    HEADER_CHECKSUM = "header_checksum"
    TAIL_CONSISTENCY = "tail_consistency"


class IntegrityState(StrEnum):
    OK = "OK"
    CORRUPT = "CORRUPT"
    PARTIAL = "PARTIAL"


class IntegrityReport(BaseModel):
    """verify_integrity 返回值 · 对应 §3.4 / §7.4."""
    model_config = ConfigDict(frozen=True)

    target_path: str
    method: IntegrityMethod
    state: IntegrityState
    scan_duration_ms: float = Field(..., ge=0)
    total_items: int = Field(..., ge=0)
    failure_range: tuple[int, int] | None = None
    first_bad_hash: str | None = Field(None, pattern=r"^[a-f0-9]{64}$")
    first_good_hash: str | None = Field(None, pattern=r"^[a-f0-9]{64}$")
    details: dict[str, Any] = Field(default_factory=dict)


class RecoveryActionKind(StrEnum):
    NO_ACTION = "NO_ACTION"
    DELETE_ORPHAN_TMP = "DELETE_ORPHAN_TMP"
    TRUNCATE_TAIL = "TRUNCATE_TAIL"
    RESTORE_FROM_BACKUP = "RESTORE_FROM_BACKUP"
    ABORT = "ABORT"


class RecoveryAction(BaseModel):
    """recover_partial_write 返回值 · 对应 §3.5 / §7.6."""
    model_config = ConfigDict(frozen=True)

    target_path: str
    action_kind: RecoveryActionKind
    affected_bytes: int | None = Field(None, ge=0)
    orphan_tmp_paths: list[str] = Field(default_factory=list)
    rationale: str = Field(..., min_length=1)
    post_integrity: IntegrityReport | None = None


class HashChainLink(BaseModel):
    """§7.5 纯计算 VO · hash 链一环."""
    model_config = ConfigDict(frozen=True)

    prev_hash: str = Field(..., pattern=r"^[a-f0-9]{64}$")
    curr_hash: str = Field(..., pattern=r"^[a-f0-9]{64}$")
    sequence: int | None = Field(None, ge=0)
    body_canonical_json: bytes


# ============================================================
# 异常体系 · §3.6 错误码
# ============================================================

class CrashSafetyError(Exception):
    """L2-05 所有错误基类."""

    error_code: str = "E_CRASH_SAFETY_BASE"
    halt_required: bool = False  # 是否触发响应面 4 硬 halt

    def __init__(
        self,
        message: str = "",
        *,
        errno: int | None = None,
        retry_count: int = 0,
        retries_exhausted: bool = False,
        target: str | None = None,
        **extra: Any,
    ) -> None:
        super().__init__(message or self.error_code)
        self.errno = errno
        self.retry_count = retry_count
        self.retries_exhausted = retries_exhausted
        self.target = target
        self.extra = extra


class DiskFullError(CrashSafetyError):
    """§3.6 E_DISK_FULL · ENOSPC · 重试 2 次 · 硬 halt 响应面 4."""

    error_code = "E_DISK_FULL"
    halt_required = True


class PermissionError(CrashSafetyError):  # noqa: A001 - override builtin intentional to match spec
    """§3.6 E_PERMISSION · EACCES/EPERM · 不重试 · 需人工介入."""

    error_code = "E_PERMISSION"
    halt_required = False


class IOErrorCS(CrashSafetyError):
    """§3.6 E_IO_ERROR · EIO · 重试 2 次 · 硬 halt.

    别名 `IOError` 在 crash_safety.__init__ 导出时使用（避免 shadow builtin）.
    """

    error_code = "E_IO_ERROR"
    halt_required = True


class FilesystemReadOnly(CrashSafetyError):
    """§3.6 E_FILESYSTEM_READONLY · EROFS · 不重试 · 硬 halt."""

    error_code = "E_FILESYSTEM_READONLY"
    halt_required = True


class PathError(CrashSafetyError):
    """§3.6 E_PATH_NOT_FOUND · ENOENT · 不重试 · 调用方 bug."""

    error_code = "E_PATH_NOT_FOUND"
    halt_required = False


class InvalidArgumentError(CrashSafetyError):
    """§3.6 E_INVALID_ARGUMENT · EINVAL · 不重试."""

    error_code = "E_INVALID_ARGUMENT"
    halt_required = False


class LineTooLargeError(CrashSafetyError):
    """§3.6 E_LINE_TOO_LARGE · ≥ PIPE_BUF · 不重试 · L1-08 压缩或拆分."""

    error_code = "E_LINE_TOO_LARGE"
    halt_required = False


class PartialWriteError(CrashSafetyError):
    """§3.6 E_PARTIAL_WRITE · write 返回字节数 < len · 重试 2 次."""

    error_code = "E_PARTIAL_WRITE"
    halt_required = False


class HashMismatchError(CrashSafetyError):
    """§3.6 E_HASH_MISMATCH · IntegrityReport(CORRUPT/PARTIAL) · 不重试."""

    error_code = "E_HASH_MISMATCH"
    halt_required = False


class RenameFailed(CrashSafetyError):
    """§3.6 E_RENAME_FAILED · EXDEV/EBUSY · 重试 1 次 · 硬 halt."""

    error_code = "E_RENAME_FAILED"
    halt_required = True


class FsyncFailed(CrashSafetyError):
    """§3.6 E_FSYNC_FAILED · fsync EIO · **不重试**（重试即掩盖） · 硬 halt."""

    error_code = "E_FSYNC_FAILED"
    halt_required = True


class OrphanTmpError(CrashSafetyError):
    """§3.6 E_ORPHAN_TMP_DETECTED · 信号（非错误）."""

    error_code = "E_ORPHAN_TMP_DETECTED"
    halt_required = False


class ChecksumMismatch(CrashSafetyError):
    """§3.2 write_atomic `checksum` 参数不符 · 调用方断言错 · 不重试."""

    error_code = "E_CHECKSUM_MISMATCH"
    halt_required = False


# ============================================================
# 配置常量（§10 Config · 可后续拆到 app/config/crash_safety.py）
# ============================================================

MAX_SNAPSHOT_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB · §3.2 content 上限
PIPE_BUF_LIMIT: int = 4096  # §3.3 line + \n 上限 · POSIX PIPE_BUF 保证
RETRY_MAX: int = 2  # §10 write/append 重试上限（rename 为 1 · 由 atomic_writer 单独判）
RETRY_BACKOFF_MS: tuple[int, ...] = (100, 300)  # §10 指数 backoff
TMP_ORPHAN_AGE_HOURS: int = 24  # §7.1 孤儿 tmp 判定年龄


# Literal type aliases
WriteMethod = Literal["snapshot", "replace"]


__all__ = [
    # Results
    "WriteResult",
    "AppendResult",
    "IntegrityReport",
    "IntegrityMethod",
    "IntegrityState",
    "RecoveryAction",
    "RecoveryActionKind",
    "HashChainLink",
    # Errors
    "CrashSafetyError",
    "DiskFullError",
    "PermissionError",
    "IOErrorCS",
    "FilesystemReadOnly",
    "PathError",
    "InvalidArgumentError",
    "LineTooLargeError",
    "PartialWriteError",
    "HashMismatchError",
    "RenameFailed",
    "FsyncFailed",
    "OrphanTmpError",
    "ChecksumMismatch",
    # Constants
    "MAX_SNAPSHOT_SIZE_BYTES",
    "PIPE_BUF_LIMIT",
    "RETRY_MAX",
    "RETRY_BACKOFF_MS",
    "TMP_ORPHAN_AGE_HOURS",
    "WriteMethod",
]
