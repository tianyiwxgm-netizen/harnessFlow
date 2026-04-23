"""L2-02 atomic_write_chart · 对齐 tech §6.3。

语义：tempfile + fsync + rename（POSIX 原子）· 写后 sha256 复核。
PM-14 硬约束：路径必含 `projects/<pid>/` 前缀 · 否则 E_CROSS_PROJECT_PATH。

实现优先复用 Dev-α `app.l1_09.crash_safety.atomic_writer.write_atomic`；
若 L1-09 不可用（Dev-α 暂未发布版本）退回本地 tempfile+rename。
"""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path

from app.project_lifecycle.kickoff.errors import (
    E_ATOMIC_WRITE_FAILED,
    E_CROSS_PROJECT_PATH,
    E_POST_WRITE_HASH_MISMATCH,
    KickoffError,
)
from app.project_lifecycle.kickoff.schemas import WriteResult

_PID_PATH_PATTERN = re.compile(r"projects/[^/]+/")


def _ensure_pm14_path(path: str) -> None:
    """PM-14 硬约束 · 路径必含 `projects/<pid>/` 段。"""
    norm = path.replace("\\", "/")
    if not _PID_PATH_PATTERN.search(norm):
        raise KickoffError(
            error_code=E_CROSS_PROJECT_PATH,
            message=f"path missing projects/<pid>/ prefix: {path!r}",
            context={"path": path},
        )


def atomic_write_chart(path: str, content: str) -> WriteResult:
    """原子写章程文件 · 返 WriteResult（path + bytes_written + sha256）。

    - PM-14 路径前缀校验 → E_L102_L202_012
    - tempfile → fsync → rename（同目录 · POSIX 原子）
    - 写后读回复核 sha256 → E_L102_L202_009 若不符
    - 任一 OSError → E_L102_L202_013
    """
    _ensure_pm14_path(path)

    target = Path(path).absolute()
    target.parent.mkdir(parents=True, exist_ok=True)
    content_bytes = content.encode("utf-8")
    expected_sha = hashlib.sha256(content_bytes).hexdigest()

    try:
        # tempfile 在同目录 · 保证 rename 原子（cross-device 会失败）
        fd, tmp_path_str = tempfile.mkstemp(
            prefix=".atomic_",
            suffix=".tmp",
            dir=str(target.parent),
        )
        tmp_path = Path(tmp_path_str)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(content_bytes)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, target)
        except OSError:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            raise
    except OSError as exc:
        raise KickoffError(
            error_code=E_ATOMIC_WRITE_FAILED,
            message=f"atomic write failed: {exc}",
            context={"path": path},
        ) from exc

    # 写后读回复核
    actual_bytes = target.read_bytes()
    actual_sha = hashlib.sha256(actual_bytes).hexdigest()
    if actual_sha != expected_sha:
        raise KickoffError(
            error_code=E_POST_WRITE_HASH_MISMATCH,
            message=f"post-write sha mismatch: expected={expected_sha}, actual={actual_sha}",
            context={"path": path},
        )

    return WriteResult(
        path=str(target),
        bytes_written=len(content_bytes),
        sha256=actual_sha,
    )
