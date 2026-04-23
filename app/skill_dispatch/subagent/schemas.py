"""L2-04 子 Agent 委托 Pydantic v2 schemas · IC-05/12/20 字段级对齐.

IC-05 delegate_subagent (通用):
  DelegationRequest → DispatchAck (同步) · FinalReport (异步 via IC-09)
IC-12 delegate_codebase_onboarding (特化 IC-05):
  CodebaseOnboardingRequest → DispatchAck · OnboardingFinalReport
IC-20 delegate_verifier (PM-03 硬约束 · 独立 session):
  VerifierRequest → DispatchAck · VerifierVerdict

Lifecycle 状态机 (5 状态):
  provisioning → running → completed{success|partial|failed}
                        → killed (SIGTERM + 5s + SIGKILL)

源:
  - docs/3-1-Solution-Technical/integration/ic-contracts.md §3.5 / §3.12 / §3.20
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-04-子 Agent 委托器.md §3
  - docs/superpowers/plans/Dev-γ-impl.md §6 Task 04.1
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


def _iso_now_utc() -> str:
    """ISO-8601 UTC 时间戳（Z 后缀 · 对齐 IC 契约 `ts: {type: string}`）.

    用途：IC-05/12/20 入参 `ts` 字段的 default_factory · 调用方未显式传时自动补.
    """
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

# ----------------------------------------------------------------------------
# Enums
# ----------------------------------------------------------------------------


class LifecycleState(str, Enum):
    PROVISIONING = "provisioning"
    RUNNING = "running"
    COMPLETED = "completed"
    KILLED = "killed"


class VerdictOutcome(str, Enum):
    PASS = "PASS"
    FAIL_L1 = "FAIL_L1"
    FAIL_L2 = "FAIL_L2"
    FAIL_L3 = "FAIL_L3"
    FAIL_L4 = "FAIL_L4"


SubagentRole = Literal["researcher", "coder", "reviewer", "codebase_onboarding", "verifier"]
FinalStatus = Literal["success", "partial", "failed", "timeout"]

# ----------------------------------------------------------------------------
# IC-05 · delegate_subagent (通用)
# ----------------------------------------------------------------------------


class DelegationRequest(BaseModel):
    """IC-05 §3.5.2 · 通用子 Agent 委托入参."""

    model_config = {"frozen": True}

    delegation_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    role: SubagentRole
    task_brief: str
    context_copy: dict[str, Any]
    caller_l1: str = Field(min_length=2)
    allowed_tools: list[str] = Field(default_factory=lambda: ["Read", "Glob", "Grep", "Bash"])
    timeout_s: int = Field(default=1800, gt=0, le=7200)
    # IC-05 §3.5.2 ts: required string · default_factory 自动补 UTC ISO-8601
    ts: str = Field(default_factory=_iso_now_utc, min_length=1)

    @model_validator(mode="after")
    def _validate_semantics(self) -> DelegationRequest:
        # task_brief 长度 ≥ 50（PRD 约束）
        if len(self.task_brief) < 50:
            raise ValueError(
                f"task_brief must be ≥ 50 chars (got {len(self.task_brief)})"
            )
        # PM-14 context_copy.project_id 必须与顶层镜像
        ctx_pid = self.context_copy.get("project_id")
        if ctx_pid and ctx_pid != self.project_id:
            raise ValueError(
                f"project_id mismatch: top={self.project_id} ctx={ctx_pid} (PM-14)"
            )
        return self


class DispatchAck(BaseModel):
    """IC-05 / IC-12 / IC-20 共用 · 同步 dispatch 返回."""

    model_config = {"frozen": True}

    delegation_id: str
    dispatched: bool
    subagent_session_id: str | None = None


class FinalReport(BaseModel):
    """IC-05 异步终报（via IC-09）."""

    model_config = {"frozen": True}

    delegation_id: str
    subagent_session_id: str
    status: FinalStatus
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    final_message: str | None = None
    usage: dict[str, Any] | None = None


# ----------------------------------------------------------------------------
# IC-12 · delegate_codebase_onboarding
# ----------------------------------------------------------------------------


class CodebaseOnboardingRequest(BaseModel):
    """IC-12 §3.12.2 · 代码仓 onboarding."""

    model_config = {"frozen": True}

    delegation_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    repo_path: str = Field(min_length=1)
    kb_write_back: bool
    focus: dict[str, Any] | None = None
    timeout_s: int = Field(default=600, gt=0, le=3600)
    # IC-12 §3.12.2 ts: required string · default_factory 自动补 UTC ISO-8601
    ts: str = Field(default_factory=_iso_now_utc, min_length=1)


class OnboardingFinalReport(BaseModel):
    """IC-12 异步终报."""

    model_config = {"frozen": True}

    delegation_id: str
    status: Literal["success", "partial", "failed"]
    structure_summary: dict[str, Any] | None = None
    kb_entries_written: list[str] = Field(default_factory=list)


# ----------------------------------------------------------------------------
# IC-20 · delegate_verifier (PM-03 硬约束)
# ----------------------------------------------------------------------------

_VERIFIER_ALLOWED_TOOLS: frozenset[str] = frozenset({"Read", "Glob", "Grep", "Bash"})


class AcceptanceCriteria(BaseModel):
    """IC-20 §3.20.2 `acceptance_criteria` · type: object · quality_gates 子集结构.

    与 L1-04 DoD 求值侧（Dev-ε / 主-1）类型对齐 · 三段：
      - hard  : 硬门（DoD AST 表达式字符串）· PRD 必 pass · FAIL_L1 判定
      - soft  : 软门（品质建议）· FAIL_L4 判定
      - metric: 度量项（覆盖率 / 性能阈值）· 含表达式 + threshold

    源：docs/3-1-Solution-Technical/integration/ic-contracts.md §3.20.2
        `acceptance_criteria: {type: object, description: quality_gates 的 WP 子集}`
    """

    model_config = {"frozen": True}

    hard: list[str] = Field(default_factory=list)
    soft: list[str] = Field(default_factory=list)
    metric: list[dict[str, Any]] = Field(default_factory=list)


class VerifierRequest(BaseModel):
    """IC-20 §3.20.2 · S5 独立验证 · allowed_tools 严格限制."""

    model_config = {"frozen": True}

    delegation_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    wp_id: str = Field(min_length=1)
    blueprint_slice: dict[str, Any]
    s4_snapshot: dict[str, Any]
    # P1-02 修：合约 §3.20.2 要求 type: object · 原实现为 list[str] 与 quality_gates 不兼容.
    # AcceptanceCriteria 嵌套模型对齐 hard/soft/metric 结构 · 波 4 L1-04 接入零阻力.
    acceptance_criteria: AcceptanceCriteria
    allowed_tools: list[str] = Field(default_factory=lambda: ["Read", "Glob", "Grep", "Bash"])
    timeout_s: int = Field(default=1200, gt=0, le=3600)
    # IC-20 §3.20.2 ts: required string · default_factory 自动补 UTC ISO-8601
    ts: str = Field(default_factory=_iso_now_utc, min_length=1)

    @model_validator(mode="after")
    def _strict_whitelist(self) -> VerifierRequest:
        extras = set(self.allowed_tools) - _VERIFIER_ALLOWED_TOOLS
        if extras:
            raise ValueError(
                f"IC-20: allowed_tools restricted to {sorted(_VERIFIER_ALLOWED_TOOLS)}; "
                f"extras rejected: {sorted(extras)}"
            )
        return self


class VerifierVerdict(BaseModel):
    """IC-20 异步裁决."""

    model_config = {"frozen": True}

    delegation_id: str
    verdict: VerdictOutcome
    three_segment_evidence: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    duration_ms: int = Field(ge=0)


# ----------------------------------------------------------------------------
# DelegationSignature · PM-08 审计超集
# ----------------------------------------------------------------------------


class DelegationSignature(BaseModel):
    """IC-09 落盘审计 · spawn/complete/abort 全链可追."""

    delegation_id: str
    project_id: str
    role: str
    caller_l1: str
    subagent_session_id: str
    started_at_ts_ns: int = Field(gt=0)
    lifecycle: LifecycleState = LifecycleState.PROVISIONING
    duration_ms: int | None = None
    final_status: FinalStatus | None = None
    tool_uses: int | None = None
    total_tokens: int | None = None
