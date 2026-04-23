"""L2-05 TOGAF ADM 架构生产器 · Phase 严格顺序 + profile 3 档 + togaf_d_ready 提前信号。

public API:
  - TogafProducer(template, event_bus, reviewer=None)
  - produce_togaf(project_id, project_root, profile='STANDARD', caller_l2='L2-01', adr_list=None) → TogafResult
"""
from app.project_lifecycle.togaf.errors import TogafError
from app.project_lifecycle.togaf.producer import (
    PhaseResult,
    Profile,
    TogafProducer,
    TogafResult,
)

__all__ = [
    "TogafProducer",
    "TogafError",
    "TogafResult",
    "PhaseResult",
    "Profile",
]
