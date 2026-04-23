"""L2-01 Skill 注册表 Pydantic v2 schemas · 注册表数据结构.

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-01-Skill 注册表.md §3.2-3.6
  - docs/superpowers/plans/Dev-γ-impl.md §3 Task 01.1

硬约束（PM-09）:
  - 每 CapabilityPoint 至少 2 个 candidates
  - 每 CapabilityPoint 至少 1 个 builtin_fallback（is_builtin_fallback=True）
  - 缺 schema_pointer 的 capability 由 loader 层（非本模块）拒绝
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SkillSpec(BaseModel):
    """单个 skill 候选的静态 metadata."""

    model_config = {"frozen": True}

    skill_id: str = Field(min_length=1)
    availability: bool
    cost_usd: float = Field(ge=0.0)
    timeout_s: int = Field(gt=0)
    is_builtin_fallback: bool = False


class CapabilityPoint(BaseModel):
    """单个 capability 及其候选链（PM-09：≥2 + builtin_fallback）."""

    model_config = {"frozen": True}

    name: str = Field(min_length=1)
    description: str
    schema_pointer: str = Field(min_length=1)
    candidates: list[SkillSpec]

    @model_validator(mode="after")
    def _check_candidates(self) -> CapabilityPoint:
        if len(self.candidates) < 2:
            raise ValueError(
                "at_least_2_candidates: PM-09 requires ≥2 candidates per capability"
            )
        if not any(c.is_builtin_fallback for c in self.candidates):
            raise ValueError(
                "builtin_fallback_required: PM-09 requires at least one builtin fallback candidate"
            )
        return self


SubagentRole = Literal[
    "codebase_onboarding",
    "verifier",
    "researcher",
    "coder",
    "reviewer",
]


class SubagentEntry(BaseModel):
    """子 Agent 角色注册条目 · 供 L2-04 query_subagent 读."""

    model_config = {"frozen": True}

    role: SubagentRole
    tool_whitelist: list[str]
    timeout_s: int = Field(gt=0)
    schema_pointer: str = Field(min_length=1)


class ToolEntry(BaseModel):
    """原子 / 组合工具注册条目 · 供 L2-04 query_tool 读."""

    model_config = {"frozen": True}

    kind: Literal["atomic", "composed"] = "atomic"


class LedgerEntry(BaseModel):
    """账本条目 · success_count / failure_count 非负 · IC-L2-07 由 L2-02 回写."""

    capability: str
    skill_id: str
    success_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    last_attempt_ts: int = Field(ge=0)
    failure_reason: str | None = None


class RegistrySnapshot(BaseModel):
    """启动加载后的快照 · 双 buffer 读指针指向此对象.

    双 buffer 约定：
      - 读请求永远拿 current snapshot 的指针 · 不可变
      - 热更新时生成新 snapshot · 原子 swap 指针
    """

    model_config = {"arbitrary_types_allowed": True}

    version: str
    capability_points: dict[str, CapabilityPoint]
    subagents: dict[str, SubagentEntry]
    tools: dict[str, ToolEntry]
    loaded_at_ts_ns: int
    # ledger_index key: (capability, skill_id) · value: LedgerEntry
    # 用 dict[str, LedgerEntry] 按 "capability|skill_id" 字符串做 key 以便 Pydantic 序列化.
    ledger_index: dict[str, "LedgerEntry"] = Field(default_factory=dict)

    def ledger_get(self, capability: str, skill_id: str) -> "LedgerEntry | None":
        return self.ledger_index.get(f"{capability}|{skill_id}")
