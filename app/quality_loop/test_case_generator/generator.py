"""L2-03 TestCaseGenerator 主入口（WP03 scope · skeleton）。

WP03 TDD 逐步构建：先过 TC-200（generate 产 READY TestSuite）。
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.quality_loop.tdd_blueprint.schemas import TDDBlueprint

from .blueprint_reader import BlueprintReader
from .pytest_renderer import PytestRenderer
from .schemas import (
    CaseState,
    RenderOptions,
    SuiteState,
    TestSuite,
    hash_blueprint_signature,
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TestCaseGenerator:
    """L2-03 主编排 · factory.generate 入口（§2 正向）。"""

    _reader: BlueprintReader
    _renderer: PytestRenderer
    _cache: dict
    render_call_count: int

    def __init__(
        self,
        *,
        reader: BlueprintReader | None = None,
        renderer: PytestRenderer | None = None,
    ) -> None:
        self._reader = reader or BlueprintReader()
        self._renderer = renderer or PytestRenderer()
        self._cache = {}
        self.render_call_count = 0

    def generate(
        self,
        blueprint: TDDBlueprint,
        *,
        options: RenderOptions,
    ) -> TestSuite:
        """§2 正向 · 蓝图 → TestSuite（READY）· skeleton 版（TC-200）。"""
        # algo 1 · 展开 slot（含 ac_coverage=1.0 检查）
        slots = self._reader.read(blueprint)

        # §6 algo 6 · suite_id 稳定派生
        suite_id = "suite-" + hash_blueprint_signature(
            blueprint.blueprint_id,
            blueprint.version,
            [s.slot_id for s in slots],
        )[:16]

        suite = TestSuite(
            suite_id=suite_id,
            project_id=options.project_id,
            blueprint_id=blueprint.blueprint_id,
            blueprint_version=blueprint.version,
            cases=[],
            state=SuiteState.INITIALIZING,
            created_at=_utcnow_iso(),
            test_framework=options.test_framework,
        )

        # INITIALIZING → GENERATING（skeleton 版不渲染 · 直通 READY）
        suite.state = SuiteState.GENERATING
        # GENERATING → READY
        suite.state = SuiteState.READY
        suite.ready_at = _utcnow_iso()
        # RED 归零
        for c in suite.cases:
            c.state = CaseState.RED

        return suite


__all__ = ["TestCaseGenerator"]
