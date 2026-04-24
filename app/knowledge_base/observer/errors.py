"""L1-06 L2-03 error codes · 3-1 §3.1 error code table (≥ 12 codes)."""
from __future__ import annotations

from enum import StrEnum


class ObserverErrorCode(StrEnum):
    # Schema / validation
    SCHEMA_VALIDATION_FAILED = "E_L203_SCHEMA_VALIDATION_FAILED"
    KIND_NOT_WHITELISTED = "E_L203_KIND_NOT_WHITELISTED"
    TITLE_EMPTY_OR_TOO_LONG = "E_L203_TITLE_EMPTY_OR_TOO_LONG"
    SOURCE_LINKS_EMPTY = "E_L203_SOURCE_LINKS_EMPTY"
    RAW_TEXT_DENIED = "E_L203_RAW_TEXT_DENIED"

    # PM-14 / cross-layer
    PM14_PROJECT_ID_MISSING = "E_L203_PM14_PROJECT_ID_MISSING"
    PM14_PROJECT_ID_MISMATCH = "E_L203_PM14_PROJECT_ID_MISMATCH"
    CROSS_LAYER_DENIED = "E_L203_CROSS_LAYER_DENIED"

    # Dedup / idempotency
    COUNT_OVERRIDE_IGNORED = "E_L203_COUNT_OVERRIDE_IGNORED"
    IDEMPOTENCY_KEY_CONFLICT = "E_L203_IDEMPOTENCY_KEY_CONFLICT"

    # Capacity
    CAPACITY_SOFT_WARNING = "E_L203_CAPACITY_SOFT_WARNING"
    CAPACITY_HARD_REJECTED = "E_L203_CAPACITY_HARD_REJECTED"

    # Storage / collaborators
    STORAGE_WRITE_FAILED = "E_L203_STORAGE_WRITE_FAILED"
    TIER_MANAGER_UNAVAILABLE = "E_L203_TIER_MANAGER_UNAVAILABLE"
    L201_SCHEMA_INVALID = "E_L203_L201_SCHEMA_INVALID"
    L201_SLOT_DENIED = "E_L203_L201_SLOT_DENIED"

    # Snapshot
    SNAPSHOT_PROJECT_NOT_FOUND = "E_L203_SNAPSHOT_PROJECT_NOT_FOUND"
    SNAPSHOT_KIND_EMPTY = "E_L203_SNAPSHOT_KIND_EMPTY"
    SNAPSHOT_STORAGE_READ_FAILED = "E_L203_SNAPSHOT_STORAGE_READ_FAILED"


class ObserverError(Exception):
    """Domain-level error with stable code for audit + negative tests."""

    def __init__(
        self, code: str | ObserverErrorCode, message: str = ""
    ) -> None:
        self.code = (
            code.value if isinstance(code, ObserverErrorCode) else code
        )
        self.message = message or self.code
        super().__init__(f"{self.code}: {self.message}")
