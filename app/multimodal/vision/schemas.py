"""L2-03 vision · VisionRequest / VisionResult / BatchResult schemas."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class VisionTask(StrEnum):
    describe = "describe"
    extract_text = "extract_text"
    structured_extract = "structured_extract"


class VisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image_path: str
    project_id: str
    task: VisionTask
    timeout_s: float = 15.0


class VisionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: bool
    task: VisionTask
    structured_output: dict[str, Any] | None = None
    fallback_tier: int                # 1=VLM primary, 2=VLM lite, 3=OCR, 4=pure-rule
    cache_hit: bool = False
    error_message: str | None = None


class BatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total: int
    succeeded: int
    failed: int
    results: list[VisionResult]
