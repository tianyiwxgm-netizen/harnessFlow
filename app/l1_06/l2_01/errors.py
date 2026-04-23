"""L1-06 L2-01 error codes · 12 entries · 3-1 §3.7."""
from __future__ import annotations

from enum import StrEnum


class TierErrorCode(StrEnum):
    TIER_NOT_ACTIVATED = "E-TIER-001"
    CROSS_PROJECT_READ_DENIED = "E-TIER-002"
    INVALID_KIND = "E-TIER-003"
    SCHEMA_VIOLATION = "E-TIER-004"
    WRONG_SCOPE_FOR_WRITE = "E-TIER-005"
    PROMOTION_SKIP_LEVEL = "E-TIER-006"
    PROMOTION_BELOW_THRESHOLD = "E-TIER-007"
    PROMOTION_MISSING_APPROVAL = "E-TIER-008"
    EXPIRED_ENTRY_ACCESS = "E-TIER-009"
    PATH_RESOLUTION_FAIL = "E-TIER-010"
    TIER_REGISTRY_CORRUPT = "E-TIER-011"
    SESSION_ID_NOT_FOUND = "E-TIER-012"


class TierError(Exception):
    """Domain-level error with a stable code for audit + negative tests."""

    def __init__(self, code: str | TierErrorCode, message: str = "") -> None:
        self.code = code.value if isinstance(code, TierErrorCode) else code
        self.message = message or self.code
        super().__init__(f"{self.code}: {self.message}")
