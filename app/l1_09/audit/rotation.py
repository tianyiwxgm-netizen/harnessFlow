"""L2-03 · AuditRotation · 按 size 或 month 切文件 · 对齐 3-1 §7.6.

特性：
- size >= 200MB 触发
- 月末最后一天 23:59 自动
- 命名：`audit.jsonl.YYYYMM.NN`
- 保留 rotation history
"""
from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path


ROTATION_SIZE_BYTES = 200 * 1024 * 1024  # 200 MB


class AuditRotation:
    """每 project 独立文件 rotate · 被 AuditWriter 调."""

    def __init__(
        self,
        audit_path: Path,
        *,
        size_limit: int = ROTATION_SIZE_BYTES,
    ) -> None:
        self._audit_path = audit_path
        self._size_limit = size_limit
        self._archive_dir = audit_path.parent / "archive"
        self._archive_dir.mkdir(parents=True, exist_ok=True)

    def should_rotate_by_size(self) -> bool:
        if not self._audit_path.exists():
            return False
        return self._audit_path.stat().st_size >= self._size_limit

    def should_rotate_by_month(self, now: datetime | None = None) -> bool:
        """月末最后日 23:59 触发."""
        if not self._audit_path.exists():
            return False
        if now is None:
            now = datetime.now()
        # 月最后一天 · 23:59
        next_day = now.replace(day=28) + __import__("datetime").timedelta(days=4)
        last_day = next_day - __import__("datetime").timedelta(days=next_day.day)
        return (
            now.day == last_day.day
            and now.hour == 23
            and now.minute >= 59
        )

    def rotate(self, *, reason: str = "size") -> Path | None:
        """执行 rotation · 返回归档后文件路径."""
        if not self._audit_path.exists():
            return None
        # 命名：audit.jsonl.YYYYMM.NN
        now = datetime.now()
        ym = now.strftime("%Y%m")
        # 找下一个 NN
        nn = 0
        while True:
            candidate = self._archive_dir / f"{self._audit_path.name}.{ym}.{nn:02d}"
            if not candidate.exists():
                break
            nn += 1

        shutil.move(str(self._audit_path), str(candidate))
        self._audit_path.touch(mode=0o644)  # 新空文件
        return candidate

    def list_archives(self) -> list[Path]:
        return sorted(self._archive_dir.glob(f"{self._audit_path.name}.*"))


__all__ = ["AuditRotation", "ROTATION_SIZE_BYTES"]
