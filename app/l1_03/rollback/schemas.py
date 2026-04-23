"""L2-05 · RollbackAdvice + FailureCounter 快照 · frozen VO。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AdviceOption(StrEnum):
    """回退建议三选一（2-prd §12）。L1-07 supervisor 选一个发给 L1-01。"""

    SPLIT_WP = "split_wp"          # WP 过大 · L2-01 差量拆解成子 WP
    MODIFY_WBS = "modify_wbs"      # WBS 整体有误 · L1-02 发起变更请求
    MODIFY_AC = "modify_ac"        # DoD/AC 不合理 · L1-04 调整验收标准


class FailureCounterSnapshot(BaseModel):
    """某 wp 的 FailureCounter 当前状态快照（只读 · 用于 UI / 审计）。"""

    model_config = ConfigDict(frozen=True)

    wp_id: str
    state: str
    consecutive_failures: int = Field(ge=0)


class RollbackAdvice(BaseModel):
    """回退建议（L2-05 产生 · 通过 IC-14 发给 L1-01 / L1-04 / L1-07）。"""

    model_config = ConfigDict(frozen=True)

    wp_id: str
    project_id: str
    failure_count: int = Field(ge=1)
    options: list[AdviceOption] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    reason: str = ""
