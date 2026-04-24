"""L2-01 TDD 蓝图 · 对外 schema + 聚合 + 错误码。

对齐 3-1 §2 / §3 字段级 YAML。优先保核心契约 · perf / PM-14 分片 / 冷启动细节
留下次。
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# 错误码 / 异常（§3.5 19 项 + §11 降级扩展）
# ---------------------------------------------------------------------------


class TDDBlueprintError(Exception):
    """L2-01 统一异常 · code + severity 二元暴露 · 调用方路由用 code 不用 isinstance。"""

    def __init__(
        self,
        code: str,
        *,
        message: str | None = None,
        severity: str = "ERROR",
        **context: Any,
    ) -> None:
        super().__init__(message or code)
        self.code = code
        self.severity = severity
        self.context = context

    def __repr__(self) -> str:  # pragma: no cover - debug only
        return f"TDDBlueprintError(code={self.code!r}, severity={self.severity!r})"


# ---------------------------------------------------------------------------
# 状态机（§8 DRAFT → VALIDATING → READY → PUBLISHED → FROZEN + AWAITING_CLARIFY）
# ---------------------------------------------------------------------------


class BlueprintState(str, Enum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    AWAITING_CLARIFY = "AWAITING_CLARIFY"
    READY = "READY"
    PUBLISHED = "PUBLISHED"
    FROZEN = "FROZEN"
    FAILED = "FAILED"


# ---------------------------------------------------------------------------
# Value Objects / Entities（§2.4 ~ §2.5）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TestPyramid:
    unit_ratio: float
    integration_ratio: float
    e2e_ratio: float

    def __post_init__(self) -> None:
        total = self.unit_ratio + self.integration_ratio + self.e2e_ratio
        if abs(total - 1.0) > 0.01:
            raise TDDBlueprintError(
                code="E_L204_L201_PYRAMID_RATIO_SUM_INVALID",
                message=f"pyramid ratios sum={total:.4f} not 1.0 ± 0.01",
            )

    def as_dict(self) -> dict[str, float]:
        return {
            "unit_ratio": self.unit_ratio,
            "integration_ratio": self.integration_ratio,
            "e2e_ratio": self.e2e_ratio,
        }


@dataclass(frozen=True)
class CoverageTarget:
    """§2.4 D-L201-04 · AC 硬锁 1.0 · line/branch ∈ [0.60, 1.0]。"""

    line: float = 0.80
    branch: float = 0.70
    ac: float = 1.0  # 硬锁 · 构造时禁止其他值

    def __post_init__(self) -> None:
        if self.ac != 1.0:
            raise TDDBlueprintError(
                code="E_L204_L201_COVERAGE_AC_NOT_LOCKED",
                message=f"ac coverage must be 1.0 (hard lock), got {self.ac}",
            )
        for name, val in (("line", self.line), ("branch", self.branch)):
            if not (0.60 <= val <= 1.0):
                raise TDDBlueprintError(
                    code="E_L204_L201_COVERAGE_OUT_OF_RANGE",
                    message=f"{name} coverage {val} not in [0.60, 1.0]",
                )

    def as_dict(self) -> dict[str, float]:
        return {"line": self.line, "branch": self.branch, "ac": self.ac}


@dataclass(frozen=True)
class ACItem:
    """单条 AC 条款 + parser 产出的结构化信息。"""

    id: str
    raw_text: str
    kind: str = "mixed"  # data / collab / ui / mixed（§6.4 _classify_ac_kind）
    parse_tier: int = 1  # 1=template · 2=spaCy · 3=LLM fallback
    confidence: float = 1.0
    structured: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ACMatrixRow:
    """§6.4 stage_3 · AC → 三层用例槽位。"""

    ac_id: str
    unit_slots: int = 0
    integration_slots: int = 0
    e2e_slots: int = 0
    priority: str = "P1"  # P0 / P1 / P2
    layer: str = "unit"   # 主层级（用于 schema §3.2 出参）

    def total_slots(self) -> int:
        return self.unit_slots + self.integration_slots + self.e2e_slots

    def slot_ids(self) -> list[str]:
        """每层展开成稳定 slot_id（基于 ac_id + seq）· 仅用于 §3.2 出参 schema。"""
        out: list[str] = []
        for i in range(self.unit_slots):
            out.append(f"slot-{self.ac_id}-u{i+1}")
        for i in range(self.integration_slots):
            out.append(f"slot-{self.ac_id}-i{i+1}")
        for i in range(self.e2e_slots):
            out.append(f"slot-{self.ac_id}-e{i+1}")
        return out


@dataclass(frozen=True)
class ACMatrix:
    rows: dict[str, ACMatrixRow]

    def total_slots(self) -> int:
        return sum(r.total_slots() for r in self.rows.values())

    def missing_ac_ids(self) -> list[str]:
        """AC 覆盖率校验 · 任一槽位数为 0 即视为 missing（I-L201-04）。"""
        return sorted(
            ac_id for ac_id, row in self.rows.items() if row.total_slots() == 0
        )

    def to_payload(self) -> list[dict[str, Any]]:
        """§3.2 出参 · ac_matrix 数组。"""
        return [
            {
                "ac_id": row.ac_id,
                "ac_text": "",  # builder 组装时补 raw_text
                "layer": row.layer,
                "priority": row.priority,
                "slot_ids": row.slot_ids(),
            }
            for row in self.rows.values()
        ]


@dataclass(frozen=True)
class TestEnvBlueprint:
    mock_profiles: list[dict[str, Any]] = field(default_factory=list)
    fixtures: dict[str, Any] = field(default_factory=dict)
    timeouts: dict[str, int] = field(
        default_factory=lambda: {"unit_ms": 50, "integration_ms": 500, "e2e_ms": 5000}
    )
    isolation_prefix: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "mock_strategy": {mp["ac_id"]: mp for mp in self.mock_profiles},
            "fixture_design": self.fixtures,
            "data_prep_plan": {"timeouts": self.timeouts, "isolation": self.isolation_prefix},
        }


@dataclass(frozen=True)
class SourceRefs:
    four_pieces_hash: str
    wbs_version: int
    ac_clauses_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "four_pieces_hash": self.four_pieces_hash,
            "wbs_version": self.wbs_version,
            "ac_clauses_hash": self.ac_clauses_hash,
        }


# ---------------------------------------------------------------------------
# Aggregate Root · TDDBlueprint（§2.2）
# ---------------------------------------------------------------------------


@dataclass
class TDDBlueprint:
    blueprint_id: str
    project_id: str
    version: int
    state: BlueprintState
    test_pyramid: TestPyramid
    ac_matrix: ACMatrix
    coverage_target: CoverageTarget
    test_env: TestEnvBlueprint
    source_refs: SourceRefs
    ac_items: list[ACItem]
    created_at: str
    published_at: str | None = None
    frozen_at: str | None = None
    source_refs_hash: str = ""
    # 诊断元数据（供 _debug_build_meta 用）
    build_meta: dict[str, Any] = field(default_factory=dict)

    def assert_invariants(self) -> None:
        """§2.2 I-L201-01 ~ I-L201-07。"""
        if not self.project_id:
            raise TDDBlueprintError(code="E_L204_L201_BLUEPRINT_NO_PROJECT_ID")
        if self.version < 1:
            raise TDDBlueprintError(
                code="E_L204_L201_VERSION_INVALID",
                message=f"version must be >= 1, got {self.version}",
            )
        if self.coverage_target.ac != 1.0:
            raise TDDBlueprintError(code="E_L204_L201_COVERAGE_AC_NOT_LOCKED")
        missing = self.ac_matrix.missing_ac_ids()
        if missing:
            raise TDDBlueprintError(
                code="E_L204_L201_BLUEPRINT_AC_MISSING",
                missing_ac_ids=missing,
            )


# ---------------------------------------------------------------------------
# 对外请求 / 响应 schema（§3.1 ~ §3.4）
# ---------------------------------------------------------------------------


def _gen_bp_id() -> str:
    return f"bp-{uuid.uuid4()}"


def _gen_event_id() -> str:
    return f"evt-{uuid.uuid4()}"


def _compute_source_refs_hash(
    four_pieces_hash: str,
    wbs_version: int,
    ac_clauses_hash: str,
    clause_count: int,
    config_overrides: dict[str, Any] | None,
    nonce: Any = None,
    previous_blueprint_id: str | None = None,
    retry_focus: list[str] | None = None,
) -> str:
    """幂等 cache key（§3.1 幂等性）· 基于输入快照稳定 hash。

    FAIL-L2 retry · previous_blueprint_id / retry_focus / nonce 均进入 hash ·
    否则两次重建会命中 cache · 无法递增 version。
    """
    payload = json.dumps(
        {
            "four_pieces_hash": four_pieces_hash,
            "wbs_version": wbs_version,
            "ac_clauses_hash": ac_clauses_hash,
            "clause_count": clause_count,
            "config_overrides": config_overrides or {},
            "nonce": str(nonce) if nonce is not None else None,
            "previous_blueprint_id": previous_blueprint_id,
            "retry_focus": sorted(retry_focus) if retry_focus else None,
        },
        sort_keys=True,
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class GenerateBlueprintRequest:
    command_id: str
    project_id: str | None
    entry_phase: str
    four_pieces_refs: dict[str, Any]
    wbs_refs: dict[str, Any]
    ac_clauses_refs: dict[str, Any]
    previous_blueprint_id: str | None = None
    retry_focus: list[str] | None = None
    config_overrides: dict[str, Any] | None = None
    trigger_tick_id: str | None = None

    # parser 用的调试注入（仅 test · 默认 0）
    inject_unmapped_ac_count: int = 0
    inject_ac_case_explosion_on_ac_index: int | None = None
    # 冷启动 / 超时模拟（留下次实现）
    simulate_stage_delay_s: float = 0.0
    nonce: Any = None  # 便于 perf fixture 构造不同 source_refs_hash

    @property
    def clause_count(self) -> int:
        return int(self.ac_clauses_refs.get("clause_count", 0))

    @property
    def four_pieces_hash(self) -> str:
        return str(self.four_pieces_refs.get("four_pieces_hash", ""))

    @property
    def wbs_version(self) -> int:
        return int(self.wbs_refs.get("wbs_version", 1))

    def source_refs_hash(self) -> str:
        return _compute_source_refs_hash(
            four_pieces_hash=self.four_pieces_hash,
            wbs_version=self.wbs_version,
            ac_clauses_hash=str(self.ac_clauses_refs.get("ac_manifest_path", "")),
            clause_count=self.clause_count,
            config_overrides=self.config_overrides,
            nonce=self.nonce,
            previous_blueprint_id=self.previous_blueprint_id,
            retry_focus=self.retry_focus,
        )


@dataclass
class GenerateBlueprintResponse:
    blueprint_id: str
    project_id: str
    status: str  # ACCEPTED / CACHED
    ts_accepted: str
    version: int
    estimated_completion_ts: str | None = None


@dataclass
class GetBlueprintQuery:
    query_id: str
    project_id: str
    blueprint_id: str
    mode: str = "full"  # full / wp_slice / metadata_only
    wp_id: str | None = None
    version: int | None = None


@dataclass
class GetBlueprintResponse:
    blueprint_id: str
    project_id: str
    version: int
    state: str
    created_at: str
    published_at: str | None = None
    frozen_at: str | None = None
    test_pyramid: dict[str, float] | None = None
    ac_matrix: list[dict[str, Any]] | None = None
    coverage_target: dict[str, float] | None = None
    test_env_blueprint: dict[str, Any] | None = None
    source_refs: dict[str, Any] | None = None
    wp_slice: dict[str, Any] | None = None


@dataclass
class ValidateCoverageQuery:
    query_id: str
    project_id: str
    blueprint_id: str
    strict_mode: bool = True


@dataclass
class ValidateCoverageResponse:
    valid: bool
    ac_coverage: float
    line_coverage_target: float
    branch_coverage_target: float
    pyramid_ratios_valid: bool
    priority_annotation_complete: bool
    missing_ac_ids: list[str] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class BroadcastReadyRequest:
    blueprint_id: str
    project_id: str
    ts_publish: str
    subscribers: list[str] = field(default_factory=lambda: ["L2-02", "L2-03", "L2-04"])
    retry_max: int = 3


@dataclass
class BroadcastReadyResponse:
    published: bool
    event_id: str
    fanout_acks: list[dict[str, Any]]
    latency_ms: int


__all__ = [
    "TDDBlueprintError",
    "BlueprintState",
    "TestPyramid",
    "CoverageTarget",
    "ACItem",
    "ACMatrixRow",
    "ACMatrix",
    "TestEnvBlueprint",
    "SourceRefs",
    "TDDBlueprint",
    "GenerateBlueprintRequest",
    "GenerateBlueprintResponse",
    "GetBlueprintQuery",
    "GetBlueprintResponse",
    "ValidateCoverageQuery",
    "ValidateCoverageResponse",
    "BroadcastReadyRequest",
    "BroadcastReadyResponse",
]
