"""L1-04 · L2-06 · S5 Verifier schemas.

**锚点**：
- docs/3-1-Solution-Technical/integration/ic-contracts.md §3.20 IC-20
- docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-06-S5 TDDExe Verifier 编排器.md §2.3~2.4 (VO)

**核心类型**：
- `VerifierVerdict`        · 5 档枚举（PASS / FAIL_L1 / FAIL_L2 / FAIL_L3 / FAIL_L4）
- `VerificationRequest`    · orchestrate_s5 入参（trace + 蓝图切片 + AC）
- `IC20Command`            · IC-20 delegate_verifier 出站 payload（§3.20.2）
- `IC20DispatchResult`     · IC-20 dispatch 同步回包（§3.20.3）
- `SignatureCheckResult`   · 双签校验结果（blueprint 对齐 + s4 diff）
- `VerifiedResult`         · 主入口出参（含 verdict + three_segment_evidence + signatures）
- `VerifierError`          · 统一错误基类（子错误按错误码细分）

**PM-14**：所有顶层 VO 首字段 `project_id`（IC-20 根字段强制 · §3.20.2）。
**IC-20 幂等**：Non-idempotent（每次独立验证）· 去重由上游 L2-06 自己记录 (wp_id, git_head)。
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==============================================================================
# 错误基类
# ==============================================================================


class VerifierError(Exception):
    """L2-06 Verifier 统一错误基类.

    子错误码见 L2-06 tech-design §3.12（E01-E33 共 33 码 · 7 条 CRITICAL 硬红线）。
    """


# ==============================================================================
# 枚举
# ==============================================================================


class VerifierVerdict(StrEnum):
    """IC-20 verifier_verdict 5 档枚举 · §3.20.3.

    - `PASS`    · 三段证据链齐 + 无 diff + DoD PASS
    - `FAIL_L1` · 信任坍塌 · 主 session 声称与 verifier 独立跑结果不一致
    - `FAIL_L2` · 三段证据链缺段（INSUFFICIENT）
    - `FAIL_L3` · DoD/Gate 未过阈值（quality 段 fail）
    - `FAIL_L4` · verifier 超时或委托 3 次失败（BLOCK 级）
    """

    PASS = "PASS"
    FAIL_L1 = "FAIL_L1"
    FAIL_L2 = "FAIL_L2"
    FAIL_L3 = "FAIL_L3"
    FAIL_L4 = "FAIL_L4"


# ==============================================================================
# 主入口入参 · VerificationRequest
# ==============================================================================


class VerificationRequest(BaseModel):
    """`orchestrate_s5(request)` 入参（frozen Pydantic v2）.

    入站源：S4 Driver 执行完成后把 ExecutionTrace 经 trace_adapter 适配 → 本 VO。

    **字段来源**：
    - `project_id`        · PM-14（IC-20 根字段）
    - `wp_id`             · 当前 S5 验证的 WP（IC-20 §3.20.2）
    - `blueprint_slice`   · TDD 蓝图切片（含 dod_expression / red_tests · IC-20 §3.20.2）
    - `s4_snapshot`       · S4 执行快照（artifact_refs / git_head / test_report · IC-20 §3.20.2）
    - `acceptance_criteria` · quality_gates 的 WP 子集（IC-20 §3.20.2）
    - `main_session_id`   · 用于独立 session 前缀校验（L2-06 §6.7 硬约束 2）
    - `delegation_id`     · `ver-{uuid-v7}` 幂等 key（IC-20 §3.20.2）
    - `timeout_s`         · verifier 超时（默认 1200 秒 = 20 min · §3.20.2）
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_id: str = Field(..., min_length=1)
    wp_id: str = Field(..., min_length=1)
    blueprint_slice: dict[str, Any] = Field(...)
    s4_snapshot: dict[str, Any] = Field(...)
    acceptance_criteria: dict[str, Any] = Field(default_factory=dict)
    main_session_id: str = Field(..., min_length=1)
    delegation_id: str = Field(..., pattern=r"^ver-[A-Za-z0-9_-]{3,}$")
    timeout_s: int = Field(default=1200, ge=1, le=1800)
    ts: str = Field(..., min_length=1)

    @field_validator("project_id")
    @classmethod
    def _pid_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("E_VER_NO_PROJECT_ID")  # IC-20 §3.20.4
        return v

    @field_validator("blueprint_slice")
    @classmethod
    def _blueprint_non_empty(cls, v: dict[str, Any]) -> dict[str, Any]:
        if not v:
            raise ValueError("E_VER_BLUEPRINT_MISSING")  # IC-20 §3.20.4
        return v


# ==============================================================================
# IC-20 Command（出站 · §3.20.2 delegate_verifier_command）
# ==============================================================================


class IC20Command(BaseModel):
    """IC-20 `delegate_verifier_command` 出站 payload（生产端 · L1-04 → L1-05）.

    字段级对齐 `ic-contracts.md §3.20.2`：
    - `delegation_id`       · `ver-{uuid-v7}` 格式
    - `project_id`          · PM-14 根字段
    - `wp_id`               · `wp-{uuid-v7}` 格式
    - `blueprint_slice`     · 本 WP 蓝图切片（含 dod_expression / red_tests）
    - `s4_snapshot`         · (artifact_refs, git_head, test_report?)
    - `acceptance_criteria` · quality_gates 的 WP 子集
    - `timeout_s`           · 默认 1200
    - `allowed_tools`       · verifier session 工具白名单（严格限制 · default [Read, Glob, Grep, Bash]）
    - `ts`                  · ISO8601

    **幂等**：Non-idempotent（§3.20.5）· 上游自记 (wp_id, git_head) → delegation_id。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    delegation_id: str = Field(..., pattern=r"^ver-[A-Za-z0-9_-]{3,}$")
    project_id: str = Field(..., min_length=1)
    wp_id: str = Field(..., min_length=1)
    blueprint_slice: dict[str, Any] = Field(...)
    s4_snapshot: dict[str, Any] = Field(...)
    acceptance_criteria: dict[str, Any] = Field(default_factory=dict)
    timeout_s: int = Field(default=1200, ge=1, le=1800)
    allowed_tools: tuple[str, ...] = Field(default=("Read", "Glob", "Grep", "Bash"))
    ts: str = Field(..., min_length=1)

    @field_validator("project_id")
    @classmethod
    def _pid_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("E_VER_NO_PROJECT_ID")
        return v

    @field_validator("blueprint_slice")
    @classmethod
    def _blueprint_non_empty(cls, v: dict[str, Any]) -> dict[str, Any]:
        if not v:
            raise ValueError("E_VER_BLUEPRINT_MISSING")
        return v


# ==============================================================================
# IC-20 dispatch 同步回包（§3.20.3 delegate_verifier_dispatch_result）
# ==============================================================================


class IC20DispatchResult(BaseModel):
    """IC-20 `delegate_verifier_dispatch_result` 同步回包.

    字段级对齐 `ic-contracts.md §3.20.3`：
    - `delegation_id`        · 幂等 key（回显）
    - `dispatched`           · 是否成功派发（True/False）
    - `verifier_session_id`  · `sub-{uuid-v7}` 格式 · 由 L1-05 分配
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    delegation_id: str
    dispatched: bool
    verifier_session_id: str | None = None


# ==============================================================================
# 双签校验结果 · SignatureCheckResult
# ==============================================================================


class SignatureCheckResult(BaseModel):
    """双签校验结果（blueprint_alignment + s4_diff_analysis）.

    **两签**：
    1. `blueprint_alignment` · 蓝图对齐：verifier 看到的 dod_expression / red_tests 与原始 blueprint 一致
    2. `s4_diff_analysis`    · S4 快照 diff：verifier 复跑结果 vs 主 session 声称 snapshot

    **任意一签失败 → verdict 降级**：
    - blueprint_alignment=False → FAIL_L2 (INSUFFICIENT)
    - s4_diff_analysis=False    → FAIL_L1 (信任坍塌)
    """

    model_config = ConfigDict(frozen=True)

    blueprint_alignment_ok: bool
    s4_diff_analysis_ok: bool
    blueprint_detail: dict[str, Any] = Field(default_factory=dict)
    s4_diff_detail: dict[str, Any] = Field(default_factory=dict)

    @property
    def both_ok(self) -> bool:
        """两签均通过 → 进入 dod_evaluation 判 verdict."""
        return self.blueprint_alignment_ok and self.s4_diff_analysis_ok

    @property
    def failed_signatures(self) -> tuple[str, ...]:
        """返回失败的签名清单（用于 verdict 降级决策）."""
        failed: list[str] = []
        if not self.blueprint_alignment_ok:
            failed.append("blueprint_alignment")
        if not self.s4_diff_analysis_ok:
            failed.append("s4_diff_analysis")
        return tuple(failed)


# ==============================================================================
# 主入口出参 · VerifiedResult
# ==============================================================================


class VerifiedResult(BaseModel):
    """`orchestrate_s5(request)` 出参（frozen · IC-20 §3.20.3 verifier_verdict 外裹）.

    三段证据链（§3.20.3 `three_segment_evidence`）：
    - `blueprint_alignment` · 蓝图对齐证据（SignatureCheckResult.blueprint_detail）
    - `s4_diff_analysis`    · S4 快照 diff 分析（SignatureCheckResult.s4_diff_detail）
    - `dod_evaluation`      · DoD 表达式求值结果（来自 verifier 独立 session 回调）

    **最终 verdict 规则**：
    1. 两签均通过 + dod_evaluation PASS → `PASS`
    2. blueprint_alignment 失败       → `FAIL_L2` (INSUFFICIENT)
    3. s4_diff_analysis 失败          → `FAIL_L1` (信任坍塌)
    4. dod_evaluation FAIL            → `FAIL_L3` (质量未过阈值)
    5. 超时/委托失败                   → `FAIL_L4` (BLOCK)
    """

    model_config = ConfigDict(frozen=True)

    project_id: str = Field(..., min_length=1)
    delegation_id: str
    wp_id: str = Field(..., min_length=1)
    verdict: VerifierVerdict
    signatures: SignatureCheckResult
    dod_evaluation: dict[str, Any] = Field(default_factory=dict)
    three_segment_evidence: dict[str, Any] = Field(default_factory=dict)
    verifier_session_id: str | None = None
    duration_ms: int = Field(default=0, ge=0)
    verifier_report_id: str | None = None

    @field_validator("project_id")
    @classmethod
    def _pid_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("E_VER_NO_PROJECT_ID")
        return v

    @property
    def is_pass(self) -> bool:
        """便捷 getter · 供上游 L2-07 route 决策."""
        return self.verdict == VerifierVerdict.PASS
