"""L1-04 L2-03 测试用例生成器 · package entry。

WP03 scope：
  - blueprint_reader — 读 WP02 `TDDBlueprint`（AC/slot 矩阵）
  - pytest_renderer — jinja2 渲染 pytest 骨架 · 恒红灯
  - generator        — 主编排 + ac_coverage=1.0 检查

依赖 WP02 `app.quality_loop.tdd_blueprint.schemas.TDDBlueprint`（Protocol 非 import）。
"""

from __future__ import annotations

from .schemas import (
    AC_COVERAGE_NOT_100,
    AC_MATRIX_INVALID,
    BLUEPRINT_NOT_FOUND,
    DOCSTRING_MISSING,
    FRAMEWORK_UNSUPPORTED,
    SKIP_MARK_DETECTED,
    STUB_CODE_DETECTED,
    SYNTAX_INVALID,
    CaseSlot,
    CaseState,
    RenderOptions,
    SuiteState,
    TestCaseGeneratorError,
    TestCaseSkeleton,
    TestSuite,
    hash_blueprint_signature,
)

__all__ = [
    "AC_COVERAGE_NOT_100",
    "AC_MATRIX_INVALID",
    "BLUEPRINT_NOT_FOUND",
    "DOCSTRING_MISSING",
    "FRAMEWORK_UNSUPPORTED",
    "SKIP_MARK_DETECTED",
    "STUB_CODE_DETECTED",
    "SYNTAX_INVALID",
    "CaseSlot",
    "CaseState",
    "RenderOptions",
    "SuiteState",
    "TestCaseGeneratorError",
    "TestCaseSkeleton",
    "TestSuite",
    "hash_blueprint_signature",
]
