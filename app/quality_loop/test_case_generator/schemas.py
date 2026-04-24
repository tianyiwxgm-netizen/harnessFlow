"""L1-04 L2-03 测试用例生成器 · schema / 错误码。

对齐 3-1 §3 核心字段；WP03 scope 先聚焦 pytest 单框架（jest/go/cargo 留下次）。

职责：
  - 从 `TDDBlueprint`（WP02）读 AC 条款 + 矩阵 → 生成 pytest 骨架代码
  - slot → 1 test 函数 · 命名格式 `test_<ac_id>_<layer>_<seq>`
  - 每 test 至少 1 assert + docstring · raise NotImplementedError 保持红灯
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# 错误码（§3.6 / §11.1 · WP03 裁 16 → 8 核心 · 其余错误码留 hook）
# ---------------------------------------------------------------------------


class TestCaseGeneratorError(Exception):
    """L2-03 统一异常 · code + severity 二元暴露 · 调用方路由用 code 不用 isinstance。"""

    # pytest 别收这个以 Test 开头的异常类（我们是产线代码）
    __test__ = False

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
        return f"TestCaseGeneratorError(code={self.code!r}, severity={self.severity!r})"


# 8 个 WP03 scope 内核心错误码（前缀按 §11.1 原样）
BLUEPRINT_NOT_FOUND = "E_L204_L203_BLUEPRINT_NOT_FOUND"
AC_MATRIX_INVALID = "E_L204_L203_AC_MATRIX_INVALID"
AC_COVERAGE_NOT_100 = "E_L204_L203_AC_COVERAGE_NOT_100"
SYNTAX_INVALID = "E_L204_L203_SYNTAX_INVALID"
STUB_CODE_DETECTED = "E_L204_L203_STUB_CODE_DETECTED"
SKIP_MARK_DETECTED = "E_L204_L203_SKIP_MARK_DETECTED"
DOCSTRING_MISSING = "E_L204_L203_DOCSTRING_MISSING"
FRAMEWORK_UNSUPPORTED = "E_L204_L203_FRAMEWORK_UNSUPPORTED"


# ---------------------------------------------------------------------------
# State machine（§8 · INITIALIZING → GENERATING → READY / FAILED）
# ---------------------------------------------------------------------------


class SuiteState(str, Enum):
    INITIALIZING = "INITIALIZING"
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"


class CaseState(str, Enum):
    RED = "red"  # 生成即红灯（§10.5）
    GREEN_IN_REPAIR = "green_in_repair"
    GREEN = "green"


# ---------------------------------------------------------------------------
# Value Objects（§2.4 ~ §2.5 · WP03 裁）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CaseSlot:
    """§6.4 stage_3 产出 · 单槽位（layer × ac_id × seq）。"""

    slot_id: str
    ac_id: str
    layer: str  # unit / integration / e2e
    seq: int = 1
    priority: str = "P1"

    def __post_init__(self) -> None:
        if self.layer not in ("unit", "integration", "e2e"):
            raise TestCaseGeneratorError(
                code=AC_MATRIX_INVALID,
                message=f"slot layer {self.layer!r} not in {{unit, integration, e2e}}",
            )


@dataclass
class TestCaseSkeleton:
    """§2.5 渲染产物 · 单 pytest 函数 · 含 code + 元数据。"""

    # pytest 别收（产线 dataclass · 不是测试类）
    __test__ = False

    case_id: str
    slot_id: str
    ac_id: str
    wp_id: str | None
    layer: str
    code: str
    docstring: str
    file_path: str
    state: CaseState = CaseState.RED
    test_framework: str = "pytest"

    def as_payload(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "slot_id": self.slot_id,
            "ac_id": self.ac_id,
            "wp_id": self.wp_id,
            "layer": self.layer,
            "file_path": self.file_path,
            "state": self.state.value,
            "test_framework": self.test_framework,
        }


@dataclass
class TestSuite:
    """§2.4 聚合根 · 整组测试骨架 + 元数据。"""

    # pytest 别收（产线 dataclass · 不是测试类）
    __test__ = False

    suite_id: str
    project_id: str
    blueprint_id: str
    blueprint_version: int
    cases: list[TestCaseSkeleton] = field(default_factory=list)
    state: SuiteState = SuiteState.INITIALIZING
    created_at: str = ""
    ready_at: str | None = None
    test_framework: str = "pytest"

    @property
    def total_count(self) -> int:
        return len(self.cases)

    @property
    def red_count(self) -> int:
        return sum(1 for c in self.cases if c.state == CaseState.RED)

    @property
    def green_count(self) -> int:
        return sum(1 for c in self.cases if c.state == CaseState.GREEN)

    @property
    def not_green_count(self) -> int:
        return sum(1 for c in self.cases if c.state != CaseState.GREEN)

    @property
    def ac_coverage_pct(self) -> float:
        """§10.1 locked ac_coverage_threshold=1.0 · AC 全部 ≥ 1 slot 即 100%。"""
        ac_ids = {c.ac_id for c in self.cases}
        return 1.0 if ac_ids and len(ac_ids) >= 1 else 0.0


# ---------------------------------------------------------------------------
# Render options
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RenderOptions:
    """pytest_renderer 渲染开关 · 所有默认值按 §10.5 红线。"""

    test_framework: str = "pytest"  # WP03 scope · 其他框架 hook
    project_id: str = ""
    wp_id: str | None = None
    module_root: str = "app"  # 生成代码中假设的被测模块根（留给调用方覆盖）
    include_header_comment: bool = True
    enforce_docstring: bool = True
    enforce_assert: bool = True  # §10.5 禁 6/7 · 必须 1 assert
    fallback_on_unsupported_framework: bool = False
    seed: int = 0  # 决定 id 稳定

    def __post_init__(self) -> None:
        if self.test_framework != "pytest" and not self.fallback_on_unsupported_framework:
            raise TestCaseGeneratorError(
                code=FRAMEWORK_UNSUPPORTED,
                message=(
                    f"framework {self.test_framework!r} 暂未实现 · WP03 只支持 pytest · "
                    f"set fallback_on_unsupported_framework=True 强制降级"
                ),
                severity="WARNING",
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def hash_blueprint_signature(blueprint_id: str, version: int, slot_ids: list[str]) -> str:
    """§6 algo 6 简化版 · 用于 suite_id 稳定 · 不是 manifest hash-chain。"""
    h = hashlib.sha256()
    h.update(blueprint_id.encode("utf-8"))
    h.update(f"|v{version}|".encode("utf-8"))
    for sid in sorted(slot_ids):
        h.update(sid.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


__all__ = [
    "TestCaseGeneratorError",
    "SuiteState",
    "CaseState",
    "CaseSlot",
    "TestCaseSkeleton",
    "TestSuite",
    "RenderOptions",
    "hash_blueprint_signature",
    "BLUEPRINT_NOT_FOUND",
    "AC_MATRIX_INVALID",
    "AC_COVERAGE_NOT_100",
    "SYNTAX_INVALID",
    "STUB_CODE_DETECTED",
    "SKIP_MARK_DETECTED",
    "DOCSTRING_MISSING",
    "FRAMEWORK_UNSUPPORTED",
]
