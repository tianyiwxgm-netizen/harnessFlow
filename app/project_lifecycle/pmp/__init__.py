"""L2-04 PMP 9 计划生产器 · 9 并发 + 分级降级。

public API:
  - PmpPlansProducer(template, event_bus, togaf_cross_check=None)
  - produce_all_9(project_id, project_root, caller_l2='L2-01') → PmpBundleResult (async)
"""
from app.project_lifecycle.pmp.errors import PmpError
from app.project_lifecycle.pmp.producer import (
    CORE_KDAS,
    PMP_9_KDAS,
    PmpBundleResult,
    PmpKdaResult,
    PmpPlansProducer,
)

__all__ = [
    "PmpPlansProducer",
    "PmpError",
    "PmpBundleResult",
    "PmpKdaResult",
    "PMP_9_KDAS",
    "CORE_KDAS",
]
