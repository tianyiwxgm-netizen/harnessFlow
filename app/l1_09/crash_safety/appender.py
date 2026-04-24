"""L2-05 · append_atomic · jsonl 行原子追加 · 对齐 3-1 §3.3 / §6.2.

POSIX 3 步：
    1. open(target, O_WRONLY | O_APPEND | O_CREAT)
    2. lseek CUR 记 offset + write(fd, line_bytes) + assert written == len
    3. fsync(fd)（**不 fsync 父目录** · §6.2 性能优化）

关键不变量：
- `len(line.encode("utf-8")) + 1 < PIPE_BUF_LIMIT(4096)` · POSIX 保证 `O_APPEND` + size < PIPE_BUF
  下并发写不交错
- 不 fsync 父目录：append 不改 inode · 无需持久化目录 entry
- line 内部无 `\n`：上层用 canonical_json 保证 single-line
- `line_hash = sha256(line.encode("utf-8"))` · **不含** `\n`
- `bytes_written = len(line.encode("utf-8")) + 1` · **含** `\n`
"""
from __future__ import annotations

import contextlib
import errno
import hashlib
import os
import time
from pathlib import Path

import ulid

from app.l1_09.crash_safety.schemas import (
    PIPE_BUF_LIMIT,
    RETRY_BACKOFF_MS,
    RETRY_MAX,
    AppendResult,
    DiskFullError,
    FilesystemReadOnly,
    FsyncFailed,
    InvalidArgumentError,
    IOErrorCS,
    LineTooLargeError,
    PartialWriteError,
    PathError,
)
from app.l1_09.crash_safety.schemas import (
    PermissionError as CSPermissionError,
)


def _sleep_backoff(retry_index: int) -> None:
    if retry_index <= 0:
        return
    idx = min(retry_index - 1, len(RETRY_BACKOFF_MS) - 1)
    time.sleep(RETRY_BACKOFF_MS[idx] / 1000.0)


def _is_retryable(err: OSError) -> bool:
    return err.errno in (errno.ENOSPC, errno.EIO)


def _map_oserror(err: OSError, *, target: str, retry_count: int, retries_exhausted: bool) -> Exception:
    e = err.errno
    if e == errno.ENOSPC:
        return DiskFullError(
            f"disk full appending {target}",
            errno=e,
            retry_count=retry_count,
            retries_exhausted=retries_exhausted,
            target=target,
        )
    if e == errno.EIO:
        return IOErrorCS(
            f"I/O error appending {target}",
            errno=e,
            retry_count=retry_count,
            retries_exhausted=retries_exhausted,
            target=target,
        )
    if e == errno.EROFS:
        return FilesystemReadOnly(
            f"read-only FS {target}", errno=e, retry_count=retry_count, target=target
        )
    if e in (errno.EACCES, errno.EPERM):
        return CSPermissionError(
            f"permission denied {target}", errno=e, retry_count=retry_count, target=target
        )
    if e == errno.ENOENT:
        return PathError(
            f"path not found {target}", errno=e, retry_count=retry_count, target=target
        )
    if e == errno.EINVAL:
        return InvalidArgumentError(
            f"invalid argument {target}", errno=e, retry_count=retry_count, target=target
        )
    return IOErrorCS(
        f"unexpected OSError ({e}) appending {target}",
        errno=e,
        retry_count=retry_count,
        retries_exhausted=retries_exhausted,
        target=target,
    )


def _one_shot_append(target_path: Path, line_bytes: bytes) -> int:
    """单次 append · 返 offset（append 前的文件尾部偏移 · 审计用）· 失败抛 OSError/Fsync/Partial.

    §6 自修正（情形 B）：原 3-1 §6.2 伪码用 `os.lseek(fd, 0, SEEK_CUR)` · 但在 `O_APPEND`
    刚 open 时 cursor 位于 0 · 返 0 与 §3.3 输出不变量 `offset + bytes_written == st_size`
    不一致。改用 `os.fstat(fd).st_size` 读真实尾部偏移 · 兼容 §3.3 语义.
    """
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
    fd = os.open(str(target_path), flags, 0o644)
    try:
        # 读 append 前的文件尺寸 · POSIX `O_APPEND` 下真实尾部偏移
        offset_before = os.fstat(fd).st_size
        written = os.write(fd, line_bytes)
        if written != len(line_bytes):
            raise PartialWriteError(
                f"partial append: wrote {written}/{len(line_bytes)} bytes to {target_path}",
                target=str(target_path),
            )
        try:
            os.fsync(fd)
        except OSError as e:
            raise FsyncFailed(
                f"fsync failed on {target_path}", errno=e.errno, target=str(target_path)
            ) from e
    finally:
        with contextlib.suppress(OSError):
            os.close(fd)
    return offset_before


def append_atomic(
    target_path: Path,
    line: str,
    *,
    expected_prev_hash: str | None = None,
) -> AppendResult:
    """原子追加一行 jsonl · POSIX `O_APPEND` + fsync（§3.3 / §6.2）.

    前置不变量（assertion · 运行时拦截 · 调用方 bug）：
        - line 是 str
        - line 不含 \\n
        - len(line.encode('utf-8')) + 1 < PIPE_BUF_LIMIT (4096)
        - target_path.parent 存在

    返回 `AppendResult(op_id, target_path, offset, bytes_written, line_hash, duration_ms, retry_count)`.

    `expected_prev_hash` 由调用方或 verify_integrity 校验 · 本层不检查（§6.2 注记）.
    """
    # 0. 前置断言
    assert isinstance(line, str), f"line must be str, got {type(line).__name__}"
    assert "\n" not in line, "line must not contain newline (canonical_json 单行输出)"
    assert target_path.parent.exists(), f"parent dir must exist: {target_path.parent}"

    line_bytes = line.encode("utf-8") + b"\n"
    if len(line_bytes) >= PIPE_BUF_LIMIT:
        # B-4 · §3.6 E_LINE_TOO_LARGE · 用 LineTooLargeError（CrashSafetyError 子类）
        # 不用 AssertionError（Python -O 会吞 assert · halt_system 不可设）
        raise LineTooLargeError(
            f"line too large: {len(line_bytes)} >= {PIPE_BUF_LIMIT} (PIPE_BUF_LIMIT); "
            f"use canonical_json compression or link-ref pattern (L1-08 责任)",
            target=str(target_path),
        )
    _ = expected_prev_hash  # 本层不校验 · 传递给调用方审计

    op_id = str(ulid.new())
    line_hash = hashlib.sha256(line.encode("utf-8")).hexdigest()
    start_ms = time.monotonic() * 1000.0
    retry_count = 0

    while True:
        try:
            offset_before = _one_shot_append(target_path, line_bytes)
            duration_ms = time.monotonic() * 1000.0 - start_ms
            return AppendResult(
                op_id=op_id,
                target_path=str(target_path),
                offset=offset_before,
                bytes_written=len(line_bytes),
                line_hash=line_hash,
                duration_ms=duration_ms,
                retry_count=retry_count,
            )
        except FsyncFailed:
            # fsync 不重试铁律
            raise
        except PartialWriteError:
            retry_count += 1
            if retry_count > RETRY_MAX:
                raise
            _sleep_backoff(retry_count)
            continue
        except OSError as e:
            if not _is_retryable(e):
                raise _map_oserror(
                    e, target=str(target_path), retry_count=retry_count, retries_exhausted=False
                ) from e
            retry_count += 1
            if retry_count > RETRY_MAX:
                raise _map_oserror(
                    e,
                    target=str(target_path),
                    retry_count=RETRY_MAX,
                    retries_exhausted=True,
                ) from e
            _sleep_backoff(retry_count)
            continue


# 触发 `LineTooLargeError` 的显式调用接口（未来需要精细化错误码时切换 · 现在 TC-108 走 assert）
__all__ = ["append_atomic", "LineTooLargeError"]
