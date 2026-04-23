"""L2-03 4 件套数据类型 · 对齐 tech §3.3。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


DocType = Literal["requirements", "goals", "acceptance_criteria", "quality_standards"]
TrimLevel = Literal["full", "minimal", "custom"]
FailedStep = Literal[
    "REQUIREMENTS_GEN", "GOALS_GEN", "AC_GEN", "QUALITY_GEN", "CROSS_CHECK",
] | None
QCStatus = Literal["pass", "warnings_only", "fail"]


@dataclass(frozen=True)
class FourSetContext:
    """IC-L2-01 trigger 入参的 context 字段。"""

    charter_path: str
    stakeholders_path: str
    goal_anchor_hash: str
    project_manifest_path: str | None = None


@dataclass(frozen=True)
class FourSetRequest:
    """IC-L2-01 trigger_four_set 入参 · 对齐 tech §3.2。"""

    project_id: str
    request_id: str
    stage: str  # "S2"
    context: FourSetContext
    trim_level: TrimLevel = "full"
    target_subset: tuple[DocType, ...] | None = None
    change_requests: tuple[str, ...] | None = None
    caller_l2: str = "L2-01"


@dataclass(frozen=True)
class DocRef:
    """FourSetManifest.docs 单条目。"""

    doc_type: DocType
    doc_id: str
    path: str
    hash: str
    version: str
    item_count: int
    qc_status: QCStatus = "pass"
    qc_warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CrossCheckReport:
    """交叉引用校验结果。"""

    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    total_refs_checked: int = 0


@dataclass(frozen=True)
class FourSetManifest:
    """assemble_four_set 成功返回。"""

    manifest_path: str
    manifest_hash: str
    version: str
    docs: dict[DocType, DocRef]
    cross_check_report: CrossCheckReport
    produced_at_ns: int
    produced_by: str = "L2-03"


@dataclass(frozen=True)
class StructuredErr:
    """assemble_four_set 失败返回。"""

    err_type: str
    reason: str
    project_id: str
    suggested_action: str | None = None
    failed_step: FailedStep = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FourSetResponse:
    """IC-L2-01 出参。"""

    project_id: str
    request_id: str
    status: Literal["ok", "err"]
    result: FourSetManifest | StructuredErr
    audit_ref: str = ""
    latency_ms: int = 0
