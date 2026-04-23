"""L2-03 schemas · IC-02 严格对齐 `ic-contracts.md §3.2`。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class WaitingReason(StrEnum):
    """IC-02 出参 `waiting_reason` 的合法值（null wp_id 时必带）。"""

    ALL_DONE = "all_done"
    AWAITING_DEPS = "awaiting_deps"
    CONCURRENCY_CAP = "concurrency_cap"
    DEADLOCK = "deadlock"
    LOCK_CONTENTION = "lock_contention"


class GetNextWPQuery(BaseModel):
    """IC-02 入参 · 严格对齐 `ic-contracts.md §3.2.2`。"""

    model_config = ConfigDict(frozen=True)

    query_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    requester_tick: str = Field(min_length=1)
    prefer_critical_path: bool = True
    exclude_wp_ids: list[str] = Field(default_factory=list)
    ts: str | None = None


class WPDefOut(BaseModel):
    """IC-02 出参 wp_def · WP 完整定义（见 L1-03/L2-02 WP schema）。"""

    wp_id: str
    project_id: str
    goal: str
    dod_expr_ref: str
    deps: list[str] = Field(default_factory=list)
    effort_estimate: float
    recommended_skills: list[str] = Field(default_factory=list)


class GetNextWPResult(BaseModel):
    """IC-02 出参 · 严格对齐 `ic-contracts.md §3.2.3`。

    三态：
    - `wp_id != None` + `deps_met=True` · 成功
    - `wp_id is None` + `waiting_reason=all_done` · 全 DONE
    - `wp_id is None` + `waiting_reason in {awaiting_deps, concurrency_cap, lock_contention, deadlock}` · 等待
    """

    query_id: str
    wp_id: str | None = None
    wp_def: WPDefOut | None = None
    deps_met: bool = True
    waiting_reason: WaitingReason | None = None
    in_flight_wp_count: int = Field(ge=0)
    topology_version: str
    error_code: str | None = None
