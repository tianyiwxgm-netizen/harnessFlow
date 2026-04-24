"""ProjectId / SnapshotId · PM-14 pid 根字段硬约束的生成入口。

所有 supervisor 事件、snapshot 必须通过这里构造 id · 不允许裸字符串拼接。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProjectId:
    """Harness 项目 id。PM-14 合规：非空 + 前缀 proj-。"""

    value: str

    @classmethod
    def generate(cls) -> "ProjectId":
        return cls(value=f"proj-{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:  # pragma: no cover - 简单 repr
        return self.value


@dataclass(frozen=True, slots=True)
class SnapshotId:
    """EightDimensionSnapshot id · snap- 前缀。"""

    value: str

    @classmethod
    def generate(cls) -> "SnapshotId":
        return cls(value=f"snap-{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:  # pragma: no cover
        return self.value
