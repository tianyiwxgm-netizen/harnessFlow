"""L1-08 L2-04 Path Safety · IC-11 ProcessContentCommand + Result schemas."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

# ============================================================================
# Enums
# ============================================================================


class ContentType(StrEnum):
    """Content type enum · mapped to IC-11 schema §3.11.2."""
    md = "md"
    code = "code"
    image = "image"
    pdf = "pdf"
    markdown_batch = "markdown_batch"


class Task(StrEnum):
    """Task type enum · mapped to IC-11 schema §3.11.2."""
    summarize = "summarize"
    structure_extract = "structure_extract"
    vision_describe = "vision_describe"
    code_understand = "code_understand"
    diff_analyze = "diff_analyze"


class CallerL1(StrEnum):
    """Caller L1 layer enum."""
    L1_01 = "L1-01"
    L1_02 = "L1-02"
    L1_04 = "L1-04"


class RouteDecision(StrEnum):
    """Degradation route decision enum · four-tier routing."""
    DIRECT = "DIRECT"
    PAGED = "PAGED"
    DELEGATE = "DELEGATE"
    REJECT = "REJECT"


# ============================================================================
# Validators (regex patterns)
# ============================================================================


_PC_CMD_RE = re.compile(r"^pc-[0-9a-zA-Z]+$")
_ASYNC_TASK_RE = re.compile(r"^async-[0-9a-zA-Z]+$")


# ============================================================================
# Models
# ============================================================================


class ProcessContentCommand(BaseModel):
    """IC-11 process_content_command · input schema."""

    model_config = ConfigDict(extra="forbid")

    command_id: str
    project_id: str
    content_type: ContentType
    target_path: str
    task: Task
    caller_l1: CallerL1
    context: dict[str, Any] | None = None
    sync_mode: bool = True
    ts: str

    @field_validator("command_id")
    @classmethod
    def _validate_command_id(cls, v: str) -> str:
        if not _PC_CMD_RE.match(v):
            raise ValueError("command_id must match ^pc-[0-9a-zA-Z]+$")
        return v

    @field_validator("project_id")
    @classmethod
    def _validate_project_id(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("project_id must not be empty")
        return v

    @field_validator("target_path")
    @classmethod
    def _validate_target_path(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("target_path must not be empty")
        return v


class ErrorBody(BaseModel):
    """Error response body · IC-11 error schema."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class ProcessContentResult(BaseModel):
    """IC-11 process_content_result · output schema."""

    model_config = ConfigDict(extra="forbid")

    command_id: str
    success: bool
    structured_output: dict[str, Any] | None = None
    async_task_id: str | None = None
    error: ErrorBody | None = None
    duration_ms: int

    @field_validator("async_task_id")
    @classmethod
    def _validate_async_task_id(cls, v: str | None) -> str | None:
        if v is not None and not _ASYNC_TASK_RE.match(v):
            raise ValueError("async_task_id must match ^async-[0-9a-zA-Z]+$ when present")
        return v

    @field_validator("duration_ms")
    @classmethod
    def _validate_duration_ms(cls, v: int) -> int:
        if v < 0:
            raise ValueError("duration_ms must be >= 0")
        return v


class ValidationResult(BaseModel):
    """Path validation result · internal VO."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    realpath: str | None = None
    allowlist_match: str | None = None
    error_code: str | None = None
