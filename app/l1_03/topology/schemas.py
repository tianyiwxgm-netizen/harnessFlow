"""L2-02 pydantic schemas · 聚合根 WBSTopology + Entity WorkPackage + VO。

不变量 I-1 ~ I-7 的静态部分在 pydantic validator 中拦（不变量）；
动态部分（DAG 无环 / 关键路径 / 并行度守卫）由 `manager.py` 在 load_topology / transition_state 层强制。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.l1_03.common.errors import OversizeError
from app.l1_03.topology.state_machine import State

EFFORT_LIMIT_DAYS: float = 5.0
"""硬限：WP 粒度 ≤ 5 天（PRD §10.4 硬约束 + architecture §5.4）。"""

DEFAULT_PARALLELISM: int = 2
"""默认 parallelism_limit = 2（PM-04）。scope 原定 1-2 · 默认 2。"""


class DAGEdge(BaseModel):
    """DAG 边 · frozen VO · 可 hash 进 set 去重。"""

    model_config = ConfigDict(frozen=True)

    from_wp_id: str
    to_wp_id: str

    @field_validator("from_wp_id", "to_wp_id")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("edge wp_id 不可空")
        return v


class WorkPackage(BaseModel):
    """WBSTopology 聚合内 Entity。

    4 要素硬约束（`goal / dod_expr_ref / deps / effort_estimate`）由 pydantic validator 拦。
    `effort_estimate > EFFORT_LIMIT_DAYS` → `OversizeError`（不是 pydantic ValueError · 方便外层捕获分类）。
    """

    wp_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    dod_expr_ref: str = Field(min_length=1)
    deps: list[str] = Field(default_factory=list)
    effort_estimate: float = Field(gt=0.0)
    recommended_skills: list[str] = Field(default_factory=list)
    state: State = State.READY
    failure_count: int = Field(default=0, ge=0)

    @field_validator("deps")
    @classmethod
    def _deps_str_list(cls, v: list[str]) -> list[str]:
        for x in v:
            if not isinstance(x, str) or not x:
                raise ValueError(f"deps 元素必须非空 str，got {x!r}")
        return v

    @model_validator(mode="after")
    def _effort_limit(self) -> WorkPackage:
        if self.effort_estimate > EFFORT_LIMIT_DAYS:
            raise OversizeError(
                wp_id=self.wp_id,
                effort=self.effort_estimate,
                limit=EFFORT_LIMIT_DAYS,
            )
        return self


class CriticalPath(BaseModel):
    """关键路径 VO · frozen。`wp_ids` 严格按拓扑序。"""

    model_config = ConfigDict(frozen=True)

    wp_ids: list[str] = Field(default_factory=list)

    def __len__(self) -> int:
        return len(self.wp_ids)

    def __contains__(self, wp_id: object) -> bool:
        return wp_id in self.wp_ids

    def as_set(self) -> frozenset[str]:
        return frozenset(self.wp_ids)


class WBSTopology(BaseModel):
    """聚合根 · 由 `WBSTopologyManager` 持有、唯一真值源。"""

    project_id: str = Field(min_length=1)
    topology_id: str = Field(min_length=1)
    wp_list: list[WorkPackage]
    dag_edges: list[DAGEdge] = Field(default_factory=list)
    critical_path: CriticalPath = Field(default_factory=CriticalPath)
    parallelism_limit: int = Field(default=DEFAULT_PARALLELISM, ge=1, le=8)
    current_running_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _pid_consistency(self) -> WBSTopology:
        """I-2 PM-14 归属闭包：`WorkPackage.project_id == WBSTopology.project_id`。

        不一致由 manager.load_topology 二次拦（这里 pydantic 层给出早期反馈）。
        """
        mismatched = [w.wp_id for w in self.wp_list if w.project_id != self.project_id]
        if mismatched:
            raise ValueError(
                f"PM-14 归属不一致：wps={mismatched} 与 topology.project_id={self.project_id!r} 不符"
            )
        return self
