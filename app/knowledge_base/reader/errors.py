"""L1-06 L2-02 error codes · 14 entries · 3-1 §2.7."""
from __future__ import annotations

from enum import StrEnum


class KBReadErrorCode(StrEnum):
    INVALID_REQUEST = "KBR-001"
    NL_QUERY_REJECTED = "KBR-002"
    SCOPE_DENIED = "KBR-003"
    CROSS_PROJECT_VIOLATION = "KBR-004"
    KIND_NOT_ALLOWED = "KBR-005"
    KB_DEGRADED = "KBR-006"
    KB_TIMEOUT = "KBR-007"
    RERANK_FAILED = "KBR-008"
    CACHE_CORRUPTION = "KBR-009"
    CANDIDATE_OVERFLOW = "KBR-010"
    SCHEMA_MISMATCH = "KBR-011"
    TRACE_ID_MISSING = "KBR-012"
    REVERSE_RECALL_UNAUTHORIZED = "KBR-013"
    CONCURRENT_READ_CONFLICT = "KBR-014"


class KBReadError(Exception):
    def __init__(self, code: str | KBReadErrorCode, message: str = "") -> None:
        self.code = code.value if isinstance(code, KBReadErrorCode) else code
        self.message = message or self.code
        super().__init__(f"{self.code}: {self.message}")


class KBReadRejected(KBReadError):
    """Hard rejection (KBR-001/002/003/004/005/012)."""


class KBSecurityError(KBReadError):
    """KBR-013 · reverse_recall called by non-L2-05 actor."""

    def __init__(self, message: str = "reverse_recall unauthorized") -> None:
        super().__init__(KBReadErrorCode.REVERSE_RECALL_UNAUTHORIZED, message)
