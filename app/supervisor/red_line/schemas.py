"""L2-03 · 硬红线拦截器 · schemas · 5 HRL · P99 ≤ 500ms。

Brief §4 简化版 5 条 HRL：
- HRL-01 PM-14 违规 · 写缺 pid / 跨 pid 污染
- HRL-02 审计链破损 · hash chain broken
- HRL-03 可追溯率 < 100%
- HRL-04 UI panic 未 100ms 响应
- HRL-05 halt 请求未 100ms 响应

命中即调 halt_requester（ζ1 已实装）· IC-15 request_hard_halt。
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class RedLineId(str, Enum):
    """5 HRL 编号 (brief §4)。"""

    HRL_01_PM14_VIOLATION = "HRL-01"     # PM-14 违规
    HRL_02_AUDIT_BROKEN = "HRL-02"       # 审计链破损
    HRL_03_TRACEABILITY = "HRL-03"       # 可追溯率 < 100%
    HRL_04_PANIC_MISS = "HRL-04"         # UI panic 未 100ms
    HRL_05_HALT_MISS = "HRL-05"          # halt 请求未 100ms


class RedLineSeverity(str, Enum):
    """单条红线严重度（供统计 / 告警分级）。"""

    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Evidence(BaseModel):
    """命中证据 · 至少 1 条 event_id。"""

    model_config = {"frozen": True}

    observation_refs: tuple[str, ...] = Field(..., min_length=1)
    detector_name: str = Field(..., min_length=1)
    detected_at_ms: int = Field(..., ge=0)
    extra: dict[str, Any] = Field(default_factory=dict)


class RedLineHit(BaseModel):
    """单 detector 命中结果。"""

    model_config = {"frozen": True}

    red_line_id: RedLineId
    project_id: str = Field(..., min_length=1)
    severity: RedLineSeverity
    evidence: Evidence
    reason: str = Field(..., min_length=1)
    hit_id: str = Field(..., min_length=1)

    @field_validator("project_id")
    @classmethod
    def _pid(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("E_REDLINE_NO_PROJECT_ID")
        return v


class DetectionResult(BaseModel):
    """单 detector 运行结果。hit=None 表示未命中。"""

    model_config = {"frozen": True}

    detector_name: str
    red_line_id: RedLineId
    hit: RedLineHit | None = None
    latency_us: int = Field(..., ge=0)  # 微秒 · 便于 P99 统计


class RedLineError(str, Enum):
    NO_PROJECT_ID = "E_REDLINE_NO_PROJECT_ID"
    DETECTOR_TIMEOUT = "E_REDLINE_DETECTOR_TIMEOUT"
    SLO_VIOLATION = "E_REDLINE_SLO_VIOLATION_500MS"
    HALT_REQUEST_FAILED = "E_REDLINE_HALT_REQUEST_FAILED"
