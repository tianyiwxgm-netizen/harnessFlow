"""L1-08 Multimodal domain errors · 21 error codes (15 L2-04 + 6 IC-11)."""

from __future__ import annotations

L2_04_ERROR_CODES: frozenset[str] = frozenset({
    "path_forbidden", "path_escape", "cross_project", "not_found",
    "permission_denied", "not_a_file", "binary_unsupported",
    "type_mismatch", "size_exceeded", "format_unsupported",
    "invalid_path", "invalid_project_id", "external_endpoint_blocked",
    "concurrency_lock_timeout", "halted_denied",
})

IC_11_ERROR_CODES: frozenset[str] = frozenset({
    "E_PC_NO_PROJECT_ID", "E_PC_PATH_OUT_OF_PROJECT", "E_PC_PATH_NOT_FOUND",
    "E_PC_TYPE_TASK_MISMATCH", "E_PC_LARGE_CODE_BASE", "E_PC_VISION_API_FAIL",
})


class L108Error(Exception):
    """L1-08 Multimodal domain error carrying a known error code."""

    def __init__(self, code: str, detail: str = "") -> None:
        if code not in (L2_04_ERROR_CODES | IC_11_ERROR_CODES):
            raise ValueError(f"unknown L1-08 error code: {code}")
        super().__init__(f"[{code}] {detail}")
        self.code = code
        self.detail = detail
