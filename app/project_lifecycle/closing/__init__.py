"""L2-06 收尾阶段执行器 · PM-14 归档唯一入口（tar.zst）。

public API:
  - ClosingExecutor(template, event_bus)
  - produce_closing(project_id, project_root, caller_l2='L2-01') → ClosingResult
  - archive_project(project_id, project_root, caller_l2='L2-01') → ArchiveManifest
  - purge_project(project_id, project_root, confirm_token, caller_l2='L2-01') → PurgeResult
"""
from app.project_lifecycle.closing.errors import ClosingError
from app.project_lifecycle.closing.producer import (
    ArchiveManifest,
    ClosingExecutor,
    ClosingResult,
    PurgeResult,
)

__all__ = [
    "ClosingExecutor",
    "ClosingError",
    "ClosingResult",
    "ArchiveManifest",
    "PurgeResult",
]
