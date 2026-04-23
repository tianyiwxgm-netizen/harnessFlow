"""L2-05 异步结果回收期 VO.

- ValidationResult: schema 校验输出 (passed / format_invalid / schema_unavailable / silent_patch)
- PendingEntry: 超时表条目 (持久化到 pending.jsonl)
- CollectionRecord: 最终装配结果（供调用方消费）
- idempotency_key(): 稳定 hash · 同 (invocation_id, skill_id, started_at) → 同 key

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-05-异步结果回收器.md §3
  - docs/superpowers/plans/Dev-γ-impl.md §7 Task 05.1
"""
from __future__ import annotations

import hashlib
from typing import Any, Literal

from pydantic import BaseModel, Field

ValidationStatus = Literal["passed", "format_invalid", "schema_unavailable", "silent_patch"]
CollectionStatus = Literal["passed", "rejected", "timeout"]
Verdict = Literal["PASS", "FAIL_L1", "FAIL_L2", "FAIL_L3", "FAIL_L4"]


class ValidationResult(BaseModel):
    model_config = {"frozen": True}

    status: ValidationStatus
    errors: list[dict[str, Any]] = Field(default_factory=list)


class PendingEntry(BaseModel):
    """超时监控表条目 · append-only 到 pending.jsonl."""

    model_config = {"frozen": True}

    result_id: str = Field(min_length=1)
    deadline_ts_ns: int = Field(gt=0)
    capability: str = Field(min_length=1)
    project_id: str = Field(min_length=1)


class CollectionRecord(BaseModel):
    """最终装配结果 · 给调用方消费."""

    model_config = {"frozen": True}

    result_id: str
    project_id: str
    capability: str
    status: CollectionStatus
    result: dict[str, Any] | None = None
    dod_verdict: Verdict | None = None
    validation_errors: list[dict[str, Any]] = Field(default_factory=list)
    assembled_at_ts_ns: int


def idempotency_key(invocation_id: str, skill_id: str, started_at_ts_ns: int) -> str:
    """稳定 32-char hex · 供 5min 缓存窗口去重."""
    s = f"{invocation_id}|{skill_id}|{started_at_ts_ns}"
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:32]
