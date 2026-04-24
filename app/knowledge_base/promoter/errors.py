"""L1-06 L2-04 error codes · 3-1 §3.4 table (≥ 12 codes)."""
from __future__ import annotations

from enum import StrEnum


class PromoterErrorCode(StrEnum):
    # Rule violations
    SKIP_LAYER_DENIED = "E_L204_L201_SKIP_LAYER_DENIED"
    GLOBAL_THRESHOLD_UNMET = "E_L204_L201_GLOBAL_THRESHOLD_UNMET"
    PROJECT_THRESHOLD_UNMET = "E_L204_L201_PROJECT_THRESHOLD_UNMET"
    INVALID_FROM_TO = "E_L204_INVALID_FROM_TO"
    USER_APPROVAL_MISSING = "E_L204_USER_APPROVAL_MISSING"
    REJECTED_CANNOT_UNDO = "E_L204_REJECTED_CANNOT_UNDO"

    # Collaborators
    CANDIDATE_PULL_FAIL = "E_L204_L203_CANDIDATE_PULL_FAIL"
    WRITE_TARGET_FAIL = "E_L204_WRITE_TARGET_FAIL"
    SOURCE_MARK_FAIL = "E_L204_SOURCE_MARK_FAIL"
    STRIP_PROJECT_ID_FAIL = "E_L204_STRIP_PROJECT_ID_FAIL"

    # Concurrency / isolation
    PROMOTION_LOCKED = "E_L204_PROMOTION_LOCKED"
    CEREMONY_ALREADY_RUNNING = "E_L204_CEREMONY_ALREADY_RUNNING"
    PROJECT_ID_MISMATCH = "E_L204_PROJECT_ID_MISMATCH"
    PROJECT_ID_MISSING = "E_L204_PROJECT_ID_MISSING"
    REPEAT_ATTEMPT_EXHAUSTED = "E_L204_REPEAT_ATTEMPT_EXHAUSTED"
    SUPERVISOR_HALT = "E_L204_SUPERVISOR_HALT"

    # Missing source
    SOURCE_NOT_FOUND = "E_L204_SOURCE_NOT_FOUND"


class PromoterError(Exception):
    def __init__(
        self, code: str | PromoterErrorCode, message: str = ""
    ) -> None:
        self.code = (
            code.value if isinstance(code, PromoterErrorCode) else code
        )
        self.message = message or self.code
        super().__init__(f"{self.code}: {self.message}")
