"""L1-06 L2-05 error codes · 3-1 §3 + §11."""
from __future__ import annotations

from enum import StrEnum


class RerankErrorCode(StrEnum):
    # IC-L2-04 rerank
    EMPTY_CANDIDATES = "E_L205_IC04_EMPTY_CANDIDATES"
    INVALID_TOP_K = "E_L205_IC04_INVALID_TOP_K"
    PROJECT_ID_MISSING = "E_L205_IC04_PROJECT_ID_MISSING"
    CONTEXT_INVALID = "E_L205_IC04_CONTEXT_INVALID"
    SCORE_COMPUTE_FAIL = "E_L205_IC04_SCORE_COMPUTE_FAIL"
    ALL_SCORERS_FAILED = "E_L205_IC04_ALL_SCORERS_FAILED"
    WEIGHTS_SUM_INVALID = "E_L205_IC04_WEIGHTS_SUM_INVALID"
    TOP_K_CAPPED = "E_L205_IC04_TOP_K_CAPPED"
    ISOLATION_VIOLATION = "E_L205_IC04_ISOLATION_VIOLATION"
    TIMEOUT = "E_L205_IC04_TIMEOUT"
    TRACE_CACHE_FAIL = "E_L205_IC04_TRACE_CACHE_FAIL"
    ENTRY_FIELD_TAMPERED = "E_L205_IC04_ENTRY_FIELD_TAMPERED"
    # IC-L2-05 reverse_recall
    L202_UNAVAILABLE = "E_L205_IC05_L202_UNAVAILABLE"
    RECALL_EMPTY = "E_L205_IC05_EMPTY_RECALL"
    RECALL_TIMEOUT = "E_L205_IC05_TIMEOUT"
    # stage_transitioned
    STAGE_UNKNOWN = "E_L205_STAGE_UNKNOWN"
    STRATEGY_NOT_FOUND = "E_L205_STRATEGY_NOT_FOUND"
    STAGE_INJECT_TIMEOUT = "E_L205_STAGE_INJECT_TIMEOUT"
    L101_PUSH_FAIL = "E_L205_L101_PUSH_FAIL"
    DUPLICATE_EVENT = "E_L205_DUPLICATE_EVENT"


class RerankError(Exception):
    def __init__(self, code: str | RerankErrorCode, message: str = "") -> None:
        self.code = code.value if isinstance(code, RerankErrorCode) else code
        self.message = message or self.code
        super().__init__(f"{self.code}: {self.message}")


class WeightsSumError(RerankError):
    """Raised by RerankService._validate_weights when weights sum ≠ 1.0 ± ε."""

    def __init__(self, message: str = "") -> None:
        super().__init__(RerankErrorCode.WEIGHTS_SUM_INVALID, message)
