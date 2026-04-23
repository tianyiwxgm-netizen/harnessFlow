"""L2-02 算法层 facade · 对齐 3-2 TDD md §6（5 算法）。

聚合导出 · 测试里统一 `from app.project_lifecycle.kickoff.algo import ...`。
"""
from __future__ import annotations

from app.project_lifecycle.kickoff.anchor_hash import compute_anchor_hash
from app.project_lifecycle.kickoff.atomic_writer import atomic_write_chart

__all__ = [
    "atomic_write_chart",
    "compute_anchor_hash",
    # produce_kickoff / recover_draft 后续批次加
]
