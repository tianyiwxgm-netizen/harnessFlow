"""L2-02 算法层 facade · 对齐 3-2 TDD md §6（5 算法）。

聚合导出 · 测试里统一 `from app.project_lifecycle.kickoff.algo import ...`。
"""
from __future__ import annotations

from app.project_lifecycle.kickoff.activator import activate_project_id
from app.project_lifecycle.kickoff.anchor_hash import compute_anchor_hash
from app.project_lifecycle.kickoff.atomic_writer import atomic_write_chart
from app.project_lifecycle.kickoff.pid_gen import ensure_pid, generate_pid, is_valid_pid
from app.project_lifecycle.kickoff.producer_core import produce_kickoff
from app.project_lifecycle.kickoff.recovery import recover_draft

__all__ = [
    "atomic_write_chart",
    "compute_anchor_hash",
    "produce_kickoff",
    "activate_project_id",
    "recover_draft",
    "generate_pid",
    "is_valid_pid",
    "ensure_pid",
]
