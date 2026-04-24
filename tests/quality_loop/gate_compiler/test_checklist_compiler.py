"""L1-04 · L2-04 · ChecklistCompiler tests · DoD → 可勾选验收 checklist.

映射:
- brief · checklist_compiler.py(验收 checklist 产出)
- `app.quality_loop.gate_compiler.checklist_compiler`

职责:
- 消费 WP01 `CompiledDoD` + 本轮 `EvaluatedDoD` · 产 `AcceptanceChecklist`
- 每 hard/soft 表达式一条 `ChecklistItem`
- item 含 pass/fail 状态 + source_ac_ids + reason
- 可 render 为 Markdown（简版 · 供 L1-05 stage_gate_card 消费）
"""
from __future__ import annotations

import pytest

from app.quality_loop.dod_compiler import (
    CompiledDoD,
    DoDExpression,
    DoDExpressionKind,
)
from app.quality_loop.gate_compiler.checklist_compiler import (
    AcceptanceChecklist,
    ChecklistCompiler,
    ChecklistItem,
)
from app.quality_loop.gate_compiler.dod_adapter import (
    EvaluatedDoD,
    EvaluatedExpression,
)


def _make_compiled_dod(hard_count: int, soft_count: int) -> CompiledDoD:
    """辅助 · 造 CompiledDoD。"""
    hard = [
        DoDExpression(
            expr_id=f"h{i}",
            project_id="p1",
            expression_text=f"hard_{i} >= 1",
            kind=DoDExpressionKind.HARD,
            source_ac_ids=[f"AC-{i:03d}"],
        )
        for i in range(hard_count)
    ]
    soft = [
        DoDExpression(
            expr_id=f"s{i}",
            project_id="p1",
            expression_text=f"soft_{i} >= 0.5",
            kind=DoDExpressionKind.SOFT,
            source_ac_ids=[f"AC-S{i:03d}"],
        )
        for i in range(soft_count)
    ]
    return CompiledDoD(
        set_id="set-1",
        project_id="p1",
        blueprint_id="bp-1",
        wp_id="wp-1",
        hard=hard,
        soft=soft,
        dod_hash="dod-hash-1",
        version=1,
    )


def _make_evaluated(
    compiled: CompiledDoD,
    hard_pass: list[bool],
    soft_pass: list[bool],
) -> EvaluatedDoD:
    """辅助 · 造 EvaluatedDoD 与 compiled 对齐。"""
    return EvaluatedDoD(
        dod_set_id=compiled.set_id,
        dod_hash=compiled.dod_hash,
        project_id=compiled.project_id,
        hard=[
            EvaluatedExpression(
                expr_id=expr.expr_id,
                kind=DoDExpressionKind.HARD,
                passed=passed,
                reason="ok" if passed else "failed",
            )
            for expr, passed in zip(compiled.hard, hard_pass, strict=True)
        ],
        soft=[
            EvaluatedExpression(
                expr_id=expr.expr_id,
                kind=DoDExpressionKind.SOFT,
                passed=passed,
                reason="ok" if passed else "low",
            )
            for expr, passed in zip(compiled.soft, soft_pass, strict=True)
        ],
        missing=[],
    )


class TestChecklistCompile:
    def test_TC_L204_CL_001_compile_basic_hard_and_soft(self) -> None:
        """TC-L204-CL-001 · 2 hard 1 soft · 生 3 条 item。"""
        compiled = _make_compiled_dod(hard_count=2, soft_count=1)
        evaluated = _make_evaluated(compiled, [True, True], [False])
        compiler = ChecklistCompiler()
        checklist = compiler.compile(compiled=compiled, evaluated=evaluated)
        assert isinstance(checklist, AcceptanceChecklist)
        assert len(checklist.items) == 3
        assert checklist.total == 3
        assert checklist.passed == 2
        assert checklist.failed == 1

    def test_TC_L204_CL_002_items_carry_expr_id_and_ac_ids(self) -> None:
        """TC-L204-CL-002 · item 包含 expr_id + source_ac_ids + kind。"""
        compiled = _make_compiled_dod(hard_count=1, soft_count=1)
        evaluated = _make_evaluated(compiled, [True], [True])
        checklist = ChecklistCompiler().compile(compiled=compiled, evaluated=evaluated)
        h_item = next(i for i in checklist.items if i.expr_id == "h0")
        assert h_item.kind == DoDExpressionKind.HARD
        assert h_item.source_ac_ids == ["AC-000"]
        assert h_item.passed is True

    def test_TC_L204_CL_003_hard_items_come_before_soft(self) -> None:
        """TC-L204-CL-003 · item 顺序 · hard 在前 · soft 在后（便于 Markdown 阅读）。"""
        compiled = _make_compiled_dod(hard_count=2, soft_count=3)
        evaluated = _make_evaluated(
            compiled,
            [True, False],
            [True, True, False],
        )
        checklist = ChecklistCompiler().compile(compiled=compiled, evaluated=evaluated)
        kinds = [i.kind for i in checklist.items]
        hard_positions = [i for i, k in enumerate(kinds) if k == DoDExpressionKind.HARD]
        soft_positions = [i for i, k in enumerate(kinds) if k == DoDExpressionKind.SOFT]
        assert max(hard_positions) < min(soft_positions)

    def test_TC_L204_CL_004_empty_dod_produces_empty_checklist(self) -> None:
        """TC-L204-CL-004 · hard=0 soft=0 · 空 checklist · total=0。"""
        compiled = _make_compiled_dod(hard_count=0, soft_count=0)
        evaluated = _make_evaluated(compiled, [], [])
        checklist = ChecklistCompiler().compile(compiled=compiled, evaluated=evaluated)
        assert checklist.items == []
        assert checklist.total == 0
        assert checklist.passed == 0
        assert checklist.failed == 0

    def test_TC_L204_CL_005_project_id_propagated(self) -> None:
        """TC-L204-CL-005 · checklist.project_id 来自 compiled。"""
        compiled = _make_compiled_dod(1, 0)
        evaluated = _make_evaluated(compiled, [True], [])
        checklist = ChecklistCompiler().compile(compiled=compiled, evaluated=evaluated)
        assert checklist.project_id == "p1"
        assert checklist.dod_set_id == "set-1"


class TestChecklistCompileValidation:
    def test_TC_L204_CL_010_pid_mismatch_raises(self) -> None:
        """TC-L204-CL-010 · compiled.pid != evaluated.pid · ValueError."""
        compiled = _make_compiled_dod(1, 0)
        evaluated = EvaluatedDoD(
            dod_set_id="set-1",
            dod_hash="dod-hash-1",
            project_id="p2",  # 不同
            hard=[
                EvaluatedExpression(
                    expr_id="h0",
                    kind=DoDExpressionKind.HARD,
                    passed=True,
                    reason="ok",
                ),
            ],
            soft=[],
            missing=[],
        )
        with pytest.raises(ValueError, match="E_L204_CL_PID_MISMATCH"):
            ChecklistCompiler().compile(compiled=compiled, evaluated=evaluated)

    def test_TC_L204_CL_011_set_id_mismatch_raises(self) -> None:
        """TC-L204-CL-011 · compiled.set_id != evaluated.dod_set_id · ValueError."""
        compiled = _make_compiled_dod(1, 0)
        evaluated = EvaluatedDoD(
            dod_set_id="set-OTHER",
            dod_hash="dod-hash-1",
            project_id="p1",
            hard=[
                EvaluatedExpression(
                    expr_id="h0",
                    kind=DoDExpressionKind.HARD,
                    passed=True,
                    reason="ok",
                ),
            ],
            soft=[],
            missing=[],
        )
        with pytest.raises(ValueError, match="E_L204_CL_SET_ID_MISMATCH"):
            ChecklistCompiler().compile(compiled=compiled, evaluated=evaluated)


class TestChecklistMarkdownRender:
    def test_TC_L204_CL_020_render_markdown_has_title(self) -> None:
        """TC-L204-CL-020 · Markdown 含 h1 + summary。"""
        compiled = _make_compiled_dod(2, 1)
        evaluated = _make_evaluated(compiled, [True, True], [False])
        checklist = ChecklistCompiler().compile(compiled=compiled, evaluated=evaluated)
        md = checklist.to_markdown()
        assert md.startswith("# "), "h1 title required"
        assert "p1" in md
        assert "2 / 3" in md or "2/3" in md or "passed" in md.lower()

    def test_TC_L204_CL_021_markdown_contains_checkbox_for_each_item(self) -> None:
        """TC-L204-CL-021 · 每 item 渲染成 `- [x]` 或 `- [ ]`。"""
        compiled = _make_compiled_dod(2, 1)
        evaluated = _make_evaluated(compiled, [True, False], [True])
        md = ChecklistCompiler().compile(compiled=compiled, evaluated=evaluated).to_markdown()
        # 2 pass + 1 pass = 2 x · 1 fail = 1 空格
        assert md.count("- [x]") == 2
        assert md.count("- [ ]") == 1

    def test_TC_L204_CL_022_markdown_contains_expr_ids(self) -> None:
        """TC-L204-CL-022 · 每 item 列出 expr_id。"""
        compiled = _make_compiled_dod(1, 1)
        evaluated = _make_evaluated(compiled, [True], [True])
        md = ChecklistCompiler().compile(compiled=compiled, evaluated=evaluated).to_markdown()
        assert "h0" in md
        assert "s0" in md

    def test_TC_L204_CL_023_markdown_preserves_ac_ids(self) -> None:
        """TC-L204-CL-023 · item 的 source_ac_ids 出现在渲染结果。"""
        compiled = _make_compiled_dod(1, 0)
        evaluated = _make_evaluated(compiled, [True], [])
        md = ChecklistCompiler().compile(compiled=compiled, evaluated=evaluated).to_markdown()
        assert "AC-000" in md


class TestChecklistItemVO:
    def test_TC_L204_CL_030_item_is_frozen(self) -> None:
        """TC-L204-CL-030 · ChecklistItem frozen."""
        item = ChecklistItem(
            expr_id="h0",
            kind=DoDExpressionKind.HARD,
            passed=True,
            reason="ok",
            source_ac_ids=["AC-001"],
        )
        with pytest.raises((TypeError, ValueError)):
            item.passed = False  # type: ignore[misc]

    def test_TC_L204_CL_031_checklist_is_frozen(self) -> None:
        """TC-L204-CL-031 · AcceptanceChecklist frozen."""
        compiled = _make_compiled_dod(1, 0)
        evaluated = _make_evaluated(compiled, [True], [])
        checklist = ChecklistCompiler().compile(compiled=compiled, evaluated=evaluated)
        with pytest.raises((TypeError, ValueError)):
            checklist.total = 99  # type: ignore[misc]
