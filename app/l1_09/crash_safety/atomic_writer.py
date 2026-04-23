"""L2-05 Crash Safety · `write_atomic` 原子替换式写整个文件.

对齐 3-1 §3.2 / §6.1 · POSIX 5 步 syscall 序：

    1. open(tmp_path, O_WRONLY|O_CREAT|O_EXCL) · tmp 同目录
    2. write(fd, content) · 检测 partial write → retry
    3. fsync(fd) → close(fd) · **fsync 失败不重试**（§3.6 铁律）
    4. rename(tmp_path, target_path) · POSIX 原子（同 FS）
    5. fsync(parent_dir_fd) · 让 rename 本身持久化

错误分类（§3.6 12 错误码）与重试策略：

- ENOSPC (E_DISK_FULL)         · 重试 2 × · 耗尽 → DiskFullError(halt)
- EIO    (E_IO_ERROR)          · 重试 2 × · 耗尽 → IOErrorCS(halt)
- EIO on fsync (E_FSYNC_FAILED)· **不重试** · FsyncFailed(halt)
- EROFS  (E_FILESYSTEM_READONLY)· 不重试 · FilesystemReadOnly(halt)
- EACCES/EPERM (E_PERMISSION)   · 不重试 · PermissionError
- EXDEV/EBUSY  (E_RENAME_FAILED)· 重试 1 × · 耗尽 → RenameFailed(halt)
- EINVAL (E_INVALID_ARGUMENT)   · 不重试 · InvalidArgumentError
- partial write (E_PARTIAL_WRITE)· 重试 2 ×（可恢复）
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
    MAX_SNAPSHOT_SIZE_BYTES,
    RETRY_BACKOFF_MS,
    RETRY_MAX,
    ChecksumMismatch,
    DiskFullError,
    FilesystemReadOnly,
    FsyncFailed,
    InvalidArgumentError,
    IOErrorCS,
    PartialWriteError,
    PathError,
    RenameFailed,
    WriteMethod,
    WriteResult,
)
from app.l1_09.crash_safety.schemas import (
    PermissionError as CSPermissionError,
)

# Rename has a dedicated retry budget (EXDEV 通常是配置错，偶尔 EBUSY 可瞬态恢复).
_RENAME_RETRY_MAX: int = 1


def _tmp_name(target: Path, op_id: str) -> Path:
    """§7.1 tmp_path = target + '.tmp.' + op_id · 必同目录保证同 FS."""
    return target.with_suffix(target.suffix + f".tmp.{op_id}")


def _sleep_backoff(retry_index: int) -> None:
    """§10 指数 backoff · retry_index ∈ [1, RETRY_MAX]."""
    if retry_index <= 0:
        return
    idx = min(retry_index - 1, len(RETRY_BACKOFF_MS) - 1)
    time.sleep(RETRY_BACKOFF_MS[idx] / 1000.0)


def _try_cleanup_tmp(tmp_path: Path) -> None:
    """best-effort 清理 · 失败不抛（孤儿留给 recover_partial_write）."""
    try:
        if tmp_path.exists():
            tmp_path.unlink()
    except OSError:
        pass


def _map_oserror_to_cs(
    err: OSError, *, retry_count: int, retries_exhausted: bool, target: str
) -> Exception:
    """§3.6 errno → CrashSafety 异常映射."""
    e = err.errno
    if e == errno.ENOSPC:
        return DiskFullError(
            f"disk full writing {target}",
            errno=e,
            retry_count=retry_count,
            retries_exhausted=retries_exhausted,
            target=target,
        )
    if e == errno.EIO:
        return IOErrorCS(
            f"I/O error writing {target}",
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
    # 其他 OSError 当 IO 处理（保守 · halt 路径）
    return IOErrorCS(
        f"unexpected OSError ({e}) writing {target}",
        errno=e,
        retry_count=retry_count,
        retries_exhausted=retries_exhausted,
        target=target,
    )


def _is_retryable(err: OSError) -> bool:
    """可重试的 errno · §6.1."""
    return err.errno in (errno.ENOSPC, errno.EIO)


def _one_shot_write(target_path: Path, tmp_path: Path, content: bytes) -> None:
    """单次完整 5 步 syscall 序 · 失败抛 OSError / FsyncFailed / PartialWriteError."""
    # Step 1: open tmp（O_EXCL 防并发互覆）
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_EXCL
    tmp_fd = os.open(str(tmp_path), flags, 0o644)

    try:
        # Step 2: write · 检测 partial write
        written = os.write(tmp_fd, content)
        if written != len(content):
            raise PartialWriteError(
                f"partial write: wrote {written}/{len(content)} bytes to {tmp_path}",
                target=str(tmp_path),
            )
        # Step 3: fsync tmp · 铁律：失败不重试
        try:
            os.fsync(tmp_fd)
        except OSError as e:
            raise FsyncFailed(
                f"fsync failed on tmp {tmp_path}",
                errno=e.errno,
                target=str(tmp_path),
            ) from e
    finally:
        with contextlib.suppress(OSError):
            os.close(tmp_fd)

    # Step 4: rename（POSIX 原子 · 同 FS 保证）· 独立重试策略
    _rename_with_retry(tmp_path, target_path)

    # Step 5: fsync 父目录 · 让 rename 持久化
    parent_dir = str(target_path.parent)
    parent_fd = os.open(parent_dir, os.O_RDONLY)
    try:
        try:
            os.fsync(parent_fd)
        except OSError as e:
            raise FsyncFailed(
                f"fsync failed on parent dir {parent_dir}",
                errno=e.errno,
                target=parent_dir,
            ) from e
    finally:
        with contextlib.suppress(OSError):
            os.close(parent_fd)


def _rename_with_retry(tmp_path: Path, target_path: Path) -> None:
    """§6.1 Step 4 · rename 单独重试（EXDEV 首次即可抛 · EBUSY 可尝试 1 次）."""
    last_err: OSError | None = None
    for attempt in range(_RENAME_RETRY_MAX + 1):
        try:
            os.rename(str(tmp_path), str(target_path))
            return
        except OSError as e:
            last_err = e
            # EXDEV 配置错 · 不重试
            if e.errno == errno.EXDEV:
                raise RenameFailed(
                    f"cross-FS rename ({tmp_path} -> {target_path}); tmp must be in same dir",
                    errno=e.errno,
                    retry_count=attempt,
                    target=str(target_path),
                ) from e
            # 其他 rename 错误 · 仅 EBUSY 重试
            if e.errno != errno.EBUSY or attempt >= _RENAME_RETRY_MAX:
                raise RenameFailed(
                    f"rename failed ({tmp_path} -> {target_path}): errno={e.errno}",
                    errno=e.errno,
                    retry_count=attempt,
                    target=str(target_path),
                ) from e
            # EBUSY · backoff 然后再试
            _sleep_backoff(attempt + 1)
    assert last_err is not None  # for mypy
    raise RenameFailed(
        f"rename retries exhausted: {last_err}",
        errno=last_err.errno,
        retry_count=_RENAME_RETRY_MAX,
        target=str(target_path),
    )


def write_atomic(
    target_path: Path,
    content: bytes,
    *,
    method: WriteMethod = "snapshot",
    checksum: str | None = None,
) -> WriteResult:
    """原子替换式写整个 `target_path` · POSIX 5 步 syscall 序.

    前置不变量（§3.2）：
        - target_path 绝对路径
        - target_path 非目录
        - content 是 bytes
        - len(content) < MAX_SNAPSHOT_SIZE_BYTES (10 MB)
        - 父目录存在

    返回 `WriteResult(op_id, target_path, bytes_written, content_hash, duration_ms, retry_count)`.

    失败详见 §3.6 · 抛出 CrashSafetyError 子类.
    """
    # 0. 前置断言（§3.2 输入不变量）
    assert target_path.is_absolute(), f"target_path must be absolute, got {target_path!r}"
    assert not target_path.is_dir(), f"target_path cannot be a directory: {target_path}"
    assert isinstance(content, (bytes, bytearray)), "content must be bytes"
    assert len(content) < MAX_SNAPSHOT_SIZE_BYTES, (
        f"content too large: {len(content)} >= {MAX_SNAPSHOT_SIZE_BYTES}"
    )
    assert target_path.parent.exists(), f"parent dir must exist: {target_path.parent}"
    # method 参数必须是合法 Literal（mypy/pydantic 层面已约束 · runtime 再保险）
    if method not in ("snapshot", "replace"):
        raise InvalidArgumentError(
            f"method must be 'snapshot' or 'replace', got {method!r}", target=str(target_path)
        )

    op_id = str(ulid.new())  # ULID: 26 chars Crockford Base32

    # content hash + 可选 checksum 复核
    actual_hash = hashlib.sha256(bytes(content)).hexdigest()
    if checksum is not None and checksum != actual_hash:
        raise ChecksumMismatch(
            f"checksum mismatch: passed={checksum}, computed={actual_hash}",
            target=str(target_path),
        )

    tmp_path = _tmp_name(target_path, op_id)
    start_ms = time.monotonic() * 1000.0
    retry_count = 0
    # 外层重试循环 · 仅处理可重试错误（ENOSPC/EIO/PartialWrite）
    while True:
        try:
            _one_shot_write(target_path, tmp_path, bytes(content))
            duration_ms = time.monotonic() * 1000.0 - start_ms
            return WriteResult(
                op_id=op_id,
                target_path=str(target_path),
                bytes_written=len(content),
                content_hash=actual_hash,
                duration_ms=duration_ms,
                retry_count=retry_count,
            )
        except FsyncFailed:
            # fsync 失败铁律：不重试 · 清 tmp · 直接上抛 halt
            _try_cleanup_tmp(tmp_path)
            raise
        except RenameFailed:
            # rename 已自带重试 · 外层不再重试
            _try_cleanup_tmp(tmp_path)
            raise
        except PartialWriteError:
            # 可重试
            _try_cleanup_tmp(tmp_path)
            retry_count += 1
            if retry_count > RETRY_MAX:
                raise
            _sleep_backoff(retry_count)
            continue
        except OSError as e:
            # 映射 · 不可重试的立即抛 · 可重试的进 backoff
            _try_cleanup_tmp(tmp_path)
            if not _is_retryable(e):
                # EACCES/EPERM/EROFS/ENOENT/EINVAL/EXDEV(rare-外层) 等 · 不重试
                raise _map_oserror_to_cs(
                    e, retry_count=retry_count, retries_exhausted=False, target=str(target_path)
                ) from e
            retry_count += 1
            if retry_count > RETRY_MAX:
                raise _map_oserror_to_cs(
                    e,
                    retry_count=RETRY_MAX,
                    retries_exhausted=True,
                    target=str(target_path),
                ) from e
            _sleep_backoff(retry_count)
            continue
