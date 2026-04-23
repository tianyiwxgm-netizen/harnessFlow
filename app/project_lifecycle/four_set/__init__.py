"""L2-03 4 件套生产器 · 串行 REQ → GOAL → AC → QS。

public API:
  - FourPiecesProducer(template, skill, event_bus)
  - assemble_four_set(FourSetRequest, project_root) → FourSetResponse
"""
from app.project_lifecycle.four_set.errors import FourSetError
from app.project_lifecycle.four_set.producer import FourPiecesProducer
from app.project_lifecycle.four_set.schemas import (
    CrossCheckReport,
    DocRef,
    DocType,
    FourSetContext,
    FourSetManifest,
    FourSetRequest,
    FourSetResponse,
    StructuredErr,
)

__all__ = [
    "FourPiecesProducer",
    "FourSetError",
    "FourSetRequest",
    "FourSetResponse",
    "FourSetContext",
    "FourSetManifest",
    "StructuredErr",
    "DocRef",
    "DocType",
    "CrossCheckReport",
]
