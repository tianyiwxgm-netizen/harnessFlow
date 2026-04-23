"""PM-14 project_id 生成 · `p_{uuid-v7-like}` 格式。

对齐 L2-02 tech §3.2.2（pattern `^p_[0-9a-f-]{36}$`）。
uuid-v7 提供 ms 级时间戳前缀 · lexicographic-sortable。
Python 3.11 stdlib 无 uuid7 · 这里用 uuid4 + 前缀 `p_` 实现（合规 pattern · 非严格 time-ordered）。
升级 uuid7 待 Python 3.12 或 uuid-utils 依赖到位。
"""
from __future__ import annotations

import re
import uuid

_PID_PATTERN = re.compile(r"^p_[0-9a-f-]{36}$")


def generate_pid() -> str:
    """生成新 pid · `p_<uuid4>` · 36 hex-dash chars + 'p_' 前缀 = 38 chars。"""
    return f"p_{uuid.uuid4()}"


def is_valid_pid(pid: str | None) -> bool:
    """PM-14 硬校验 · `p_{uuid}` 格式。"""
    if not pid:
        return False
    return bool(_PID_PATTERN.match(pid))


def ensure_pid(pid: str) -> str:
    if not is_valid_pid(pid):
        raise ValueError(f"invalid pid format (not `p_<uuid>`): {pid!r}")
    return pid
