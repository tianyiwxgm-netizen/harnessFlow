"""L2-03 IC-04 invoke_skill 字段级 schemas · 严格对齐 ic-contracts.md §3.4.

契约红线:
  - InvocationRequest: PM-14 · timeout_ms hard-cap 300000ms (5min)
  - InvocationResponse: success xor error · success→result · failure→error
  - InvocationSignature: ⊇ Response 可落盘字段 + params_hash + attempt + started_at

源:
  - docs/3-1-Solution-Technical/integration/ic-contracts.md §3.4 IC-04
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-03-Skill 调用执行器.md §3
  - docs/superpowers/plans/Dev-γ-impl.md §5 Task 03.1
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class InvocationRequest(BaseModel):
    """IC-04 入参 · 严格对齐 §3.4.2."""

    model_config = {"frozen": True}

    invocation_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    capability: str = Field(min_length=1)
    params: dict[str, Any]
    caller_l1: str = Field(min_length=2)
    context: dict[str, Any]
    timeout_ms: int = Field(default=30000, gt=0, le=300000)  # hard-cap 5min
    allow_fallback: bool = True
    trigger_tick: int | None = None

    @model_validator(mode="after")
    def _mirror_check(self) -> InvocationRequest:
        ctx_pid = self.context.get("project_id")
        if ctx_pid and ctx_pid != self.project_id:
            raise ValueError(
                f"project_id mismatch: top={self.project_id} ctx={ctx_pid} (PM-14)"
            )
        return self


class InvocationResponse(BaseModel):
    """IC-04 出参 · 严格对齐 §3.4.3."""

    model_config = {"frozen": True}

    invocation_id: str
    success: bool
    skill_id: str
    duration_ms: int = Field(ge=0)
    fallback_used: bool
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    fallback_trace: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _success_xor_result_error(self) -> InvocationResponse:
        if self.success and self.error is not None:
            raise ValueError("IC-04: success=True cannot carry error")
        if not self.success and self.result is not None:
            raise ValueError("IC-04: success=False cannot carry result")
        return self


class InvocationSignature(BaseModel):
    """审计签名 · IC-09 落盘 · Response 超集 + params_hash + attempt + started_at.

    两次写:
      - started: attempt / params_hash / started_at_ts_ns / validate_status='pending'
      - finished: 追加 duration_ms / success / fallback_used / result_summary / validate_status
    """

    invocation_id: str
    project_id: str
    capability: str
    skill_id: str
    caller_l1: str
    attempt: int = Field(ge=1)
    params_hash: str = Field(min_length=64, max_length=64)   # sha256 hex
    started_at_ts_ns: int = Field(gt=0)
    duration_ms: int | None = None
    success: bool | None = None
    fallback_used: bool | None = None
    validate_status: Literal["pending", "passed", "failed"] = "pending"
    result_summary: str | None = None
