"""L2-01 schemas · IC-19 严格对齐 `ic-contracts.md §3.19`。

- `RequestWBSDecompositionCommand` · 入参（同步 dispatch）
- `RequestWBSDecompositionResult` · 出参（dispatch 同步）
- `DecompositionSession` · 异步拆解进行中的会话
- `WBSDraft` · 异步拆解产物（内部流转到 L2-02 装图）

`FourSetPlan` + `ArchitectureOutput` 是 2-prd 4 件套 + TOGAF 产出的承载。
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.l1_03.topology.schemas import DAGEdge, WorkPackage


class TargetGranularity(StrEnum):
    """WP 粒度档位 · 影响 LLM 拆解深度。"""

    FINE = "fine"        # WP 平均 1-2 天
    MEDIUM = "medium"    # WP 平均 2-4 天（默认）
    COARSE = "coarse"    # WP 平均 3-5 天


class FourSetPlan(BaseModel):
    """2-prd 4 件套 reference · 只存路径指针，真实内容由 skill 读。"""

    charter_path: str = Field(min_length=1)
    plan_path: str = Field(min_length=1)
    requirements_path: str = Field(min_length=1)
    risk_path: str = Field(min_length=1)


class ArchitectureOutput(BaseModel):
    """TOGAF Phase D 产出引用。"""

    togaf_phases: list[str] = Field(default_factory=list)
    adr_path: str = Field(min_length=1)


class RequestWBSDecompositionCommand(BaseModel):
    """IC-19 入参。

    严格对齐 `ic-contracts.md §3.19.2`。任一 required 字段缺失 → pydantic ValidationError，
    factory 层再二次映射成 `E_WBS_*` 错误码。
    """

    command_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    artifacts_4_pack: FourSetPlan
    architecture_output: ArchitectureOutput
    target_wp_granularity: TargetGranularity = TargetGranularity.MEDIUM
    mode: Literal["full", "incremental"] = "full"
    target_wp_id: str | None = None  # incremental 时必带
    ts: str | None = None  # optional ISO-8601

    @model_validator(mode="after")
    def _incremental_requires_target(self) -> RequestWBSDecompositionCommand:
        if self.mode == "incremental" and not self.target_wp_id:
            raise ValueError("mode=incremental 时 target_wp_id 必带")
        return self


class DecompositionSession(BaseModel):
    """异步拆解会话 · 在 IC-19 dispatch 同步返回、拆解异步完成。"""

    model_config = ConfigDict(frozen=True)

    decomposition_session_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    mode: Literal["full", "incremental"]
    target_wp_id: str | None = None


class RequestWBSDecompositionResult(BaseModel):
    """IC-19 同步出参。"""

    command_id: str = Field(min_length=1)
    accepted: bool
    decomposition_session_id: str | None = None
    reason: str | None = None
    error_code: str | None = None


class WBSDraft(BaseModel):
    """L2-01 拆解产出 · L2-02 装图入口。

    内部携带完整的 WP list + edges · 由 factory 保证 `WorkPackage.project_id == project_id`
    + 每 WP 4 要素完整 · effort_estimate ≤ 5 天。
    """

    project_id: str = Field(min_length=1)
    topology_version: str = Field(min_length=1)
    wp_list: list[WorkPackage]
    dag_edges: list[DAGEdge] = Field(default_factory=list)
    estimated_duration_h: float | None = Field(default=None, ge=0)
    critical_path_wp_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _pid_closure(self) -> WBSDraft:
        bad = [w.wp_id for w in self.wp_list if w.project_id != self.project_id]
        if bad:
            raise ValueError(
                f"WBSDraft PM-14 不一致 · wps={bad} · expected_pid={self.project_id!r}"
            )
        return self

    @property
    def wp_count(self) -> int:
        return len(self.wp_list)
