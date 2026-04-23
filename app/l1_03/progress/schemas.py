"""L2-04 schemas · ProgressSnapshot + BurndownPoint（VO · frozen）。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BurndownPoint(BaseModel):
    """Burndown 曲线上的一个点 · `(ts, remaining_effort)`。"""

    model_config = ConfigDict(frozen=True)

    ts: float  # epoch seconds
    remaining_effort: float = Field(ge=0.0)
    done_wp_count: int = Field(ge=0)


class ProgressSnapshot(BaseModel):
    """L2-04 对外导出的只读进度快照。

    UI（L1-10）+ Supervisor（L1-07）消费。所有字段 immutable。
    """

    model_config = ConfigDict(frozen=True)

    project_id: str
    topology_version: str
    total_effort: float = Field(ge=0.0)
    done_effort: float = Field(ge=0.0)
    remaining_effort: float = Field(ge=0.0)
    completion_rate: float = Field(ge=0.0, le=1.0)
    done_wps: list[str] = Field(default_factory=list)
    failed_wps: list[str] = Field(default_factory=list)
    running_wps: list[str] = Field(default_factory=list)
    ready_wps: list[str] = Field(default_factory=list)
    blocked_wps: list[str] = Field(default_factory=list)
    stuck_wps: list[str] = Field(default_factory=list)
    burndown_series: list[BurndownPoint] = Field(default_factory=list)
