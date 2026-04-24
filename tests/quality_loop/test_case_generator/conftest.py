"""main-1 WP03 · L2-03 测试用例生成器 · 共享 fixture。

WP03 裁 schema（详见 `app/quality_loop/test_case_generator/__init__.py`）
聚焦 pytest 单框架 · 输入直接是 WP02 `TDDBlueprint` 实例（不走事件总线），
blueprint_reader 只做"读 + 展开 slot 矩阵"这一件事。
"""

from __future__ import annotations

from typing import Any, Callable

import pytest

from app.quality_loop.tdd_blueprint.schemas import (
    ACItem,
    ACMatrix,
    ACMatrixRow,
    BlueprintState,
    CoverageTarget,
    SourceRefs,
    TDDBlueprint,
    TestEnvBlueprint,
    TestPyramid,
)


@pytest.fixture
def mock_project_id() -> str:
    return "pid-wp03"


@pytest.fixture
def make_blueprint() -> Callable[..., TDDBlueprint]:
    """构造合法 TDDBlueprint · 默认 3 条 AC · 每条 unit=1 slot。

    **override**:
      - project_id / version / state
      - ac_rows: [(ac_id, unit, integration, e2e, priority, layer)]
      - ac_items: 按 ac_id 透传 raw_text / kind
    """

    def _factory(**kw: Any) -> TDDBlueprint:
        project_id = kw.pop("project_id", "pid-wp03")
        version = kw.pop("version", 1)
        state = kw.pop("state", BlueprintState.PUBLISHED)
        ac_rows = kw.pop(
            "ac_rows",
            [
                ("AC-001", 1, 0, 0, "P1", "unit"),
                ("AC-002", 1, 1, 0, "P1", "unit"),
                ("AC-003", 1, 0, 1, "P0", "unit"),
            ],
        )
        ac_text_overrides = kw.pop("ac_text_overrides", {})

        rows: dict[str, ACMatrixRow] = {}
        items: list[ACItem] = []
        for ac_id, u, i, e, pr, layer in ac_rows:
            rows[ac_id] = ACMatrixRow(
                ac_id=ac_id,
                unit_slots=u,
                integration_slots=i,
                e2e_slots=e,
                priority=pr,
                layer=layer,
            )
            items.append(
                ACItem(
                    id=ac_id,
                    raw_text=ac_text_overrides.get(ac_id, f"{ac_id} sample acceptance text"),
                    kind=kw.get("ac_kind", "mixed"),
                )
            )

        return TDDBlueprint(
            blueprint_id=kw.pop("blueprint_id", "bp-wp03-test"),
            project_id=project_id,
            version=version,
            state=state,
            test_pyramid=TestPyramid(unit_ratio=0.7, integration_ratio=0.2, e2e_ratio=0.1),
            ac_matrix=ACMatrix(rows=rows),
            coverage_target=CoverageTarget(),
            test_env=TestEnvBlueprint(),
            source_refs=SourceRefs(
                four_pieces_hash="sha256:" + "b" * 64,
                wbs_version=1,
                ac_clauses_hash="sha256:" + "c" * 64,
            ),
            ac_items=items,
            created_at="2026-04-23T00:00:00Z",
        )

    return _factory


@pytest.fixture
def tiny_blueprint(make_blueprint: Callable[..., TDDBlueprint]) -> TDDBlueprint:
    return make_blueprint()
