"""L1-02 公共错误基类 · 所有 L2 的 ErrorCode 都从此派生。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class L102Error(Exception):
    """基础异常 · 所有 L1-02 子 L2 错误继承。

    error_code: `E_L102_L20N_NNN` 格式。
    caller_l2 / project_id: 审计字段。
    context: 触发时快照（slots / state 等）。
    """

    error_code: str = ""
    message: str = ""
    caller_l2: str | None = None
    project_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # 让 Exception 的 args 非空，便于 pytest/str 输出
        Exception.__init__(self, str(self))

    def __str__(self) -> str:
        base = f"[{self.error_code}] {self.message}" if self.error_code else self.message
        if self.project_id:
            base += f" (pid={self.project_id})"
        if self.caller_l2:
            base += f" (caller={self.caller_l2})"
        return base
