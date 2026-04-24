"""L2-03 TestCaseGenerator 主入口（WP03 scope · TC-200 + 200b/c/d/e/f + 002）。

WP03 TDD 逐步构建：
  - TC-200  · generate 产 READY TestSuite
  - TC-200b · suite.cases 数 = slot 矩阵展开数
  - TC-200c · 生成即红灯（全部 CaseState.RED）
  - TC-200d · §10.1 locked · suite.ac_coverage_pct == 1.0
  - TC-200e · suite_id 稳定（hash_blueprint_signature）
  - TC-200f · PM-14 · case.file_path 前缀 projects/<pid>/testing/generated/
             （pytest_renderer.build_file_path 组装 · generator 传递 options.project_id）
  - TC-002  · §6.10 algo 10 · 同 (blueprint_id, version, project_id) 幂等
             · 第二次调用直接返回 cache · 不再 render
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

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
        """§2 正向 · 蓝图 → TestSuite（READY）。

        algo 顺序：
          1. §6.10 algo 10 · 幂等：命中 cache 直接返回 READY 实例
          2. algo 1 · blueprint_reader.read（含 ac_coverage=1.0 硬检）
          3. §6 algo 6 · suite_id 稳定派生
          4. INITIALIZING → GENERATING · 逐 slot 渲染
          5. GENERATING → READY + 落 cache
        """
        cache_key = (
            blueprint.blueprint_id,
            blueprint.version,
            options.project_id,
        )

        # §6.10 algo 10 · 幂等（命中即返回 · 不再 render）
        cached = self._cache.get(cache_key)
        if cached is not None and cached.state == SuiteState.READY:
            return cached

        # algo 1 · 展开 slot（含 ac_coverage=1.0 检查）
        slots = self._reader.read(blueprint)

        # §6 algo 6 · suite_id 稳定派生（TC-200e · 同 (blueprint_id, version, slot_ids)
        # 两次 generate 得同一 suite_id · 基于 sha256 prefix 16 hex）
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

        # INITIALIZING → GENERATING
        suite.state = SuiteState.GENERATING

        # ac_id → raw_text 索引（renderer intent_line 源）
        ac_text_by_id = self._ac_text_index(blueprint)

        for slot in slots:
            intent_line = ac_text_by_id.get(slot.ac_id, slot.ac_id)
            skeleton = self._renderer.render(
                slot,
                intent_line=intent_line,
                blueprint_id=blueprint.blueprint_id,
                blueprint_version=blueprint.version,
                options=options,
                wp_id=options.wp_id,
            )
            suite.cases.append(skeleton)
            self.render_call_count += 1

        # GENERATING → READY
        suite.state = SuiteState.READY
        suite.ready_at = _utcnow_iso()
        # §10.5 · 生成即红灯
        for c in suite.cases:
            c.state = CaseState.RED

        # §6.10 落 cache（下次同 key 直接返回同一实例）
        self._cache[cache_key] = suite
        return suite

    @staticmethod
    def _ac_text_index(blueprint: TDDBlueprint) -> dict[str, str]:
        """从 blueprint.ac_items 取 raw_text · 没有就回退空串。"""
        idx: dict[str, str] = {}
        items: Any = getattr(blueprint, "ac_items", None) or []
        for item in items:
            ac_id = getattr(item, "id", None)
            raw = getattr(item, "raw_text", None)
            if isinstance(ac_id, str):
                idx[ac_id] = raw if isinstance(raw, str) else ""
        return idx


__all__ = ["TestCaseGenerator"]
