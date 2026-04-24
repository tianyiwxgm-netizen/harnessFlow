"""L1-04 · L2-04 · ChecklistCompiler · 产出人类可读验收 checklist.

**职责**（brief · checklist_compiler.py · 验收 checklist 产出）：
1. 消费 WP01 `CompiledDoD`（hard/soft 表达式）+ 本轮 `EvaluatedDoD`（pass/fail 结果）。
2. 产 `AcceptanceChecklist` 聚合根 VO · 每表达式一条 `ChecklistItem`。
3. 提供 `to_markdown()` 渲染（简版 · 供 L1-05 stage_gate_card / 文档生成消费）。

**与 L2-04 Gate 的分工**：
- `BaselineEvaluator` 产 `GateVerdict`（5 基线 + action）→ 下游路由决策
- `ChecklistCompiler` 产 `AcceptanceChecklist`（逐条 checkbox）→ 人类验收/签收

**稳定性**：item 顺序 = `hard 列表顺序 + soft 列表顺序`（与 CompiledDoD 内部顺序一致）。
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.quality_loop.dod_compiler import (
    CompiledDoD,
    DoDExpression,
    DoDExpressionKind,
)
from app.quality_loop.gate_compiler.dod_adapter import (
    EvaluatedDoD,
    EvaluatedExpression,
)
from app.quality_loop.gate_compiler.schemas import GateCompilerError


class ChecklistCompilerError(GateCompilerError):
    """ChecklistCompiler 层错误。"""


class ChecklistItem(BaseModel):
    """单条验收 item · frozen VO。

    映射到 Markdown 一行：`- [x] <expr_id> (<kind>) · <reason> · AC-xxx, AC-yyy`
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    expr_id: str = Field(..., min_length=1)
    kind: DoDExpressionKind
    passed: bool
    reason: str = Field(..., min_length=1, max_length=2000)
    source_ac_ids: list[str] = Field(default_factory=list)
    expression_text: str = Field(default="", max_length=2500)


class AcceptanceChecklist(BaseModel):
    """验收 checklist 聚合根 · frozen VO。

    - `items`         · 逐条 ChecklistItem（hard 在前 · soft 在后）
    - `total`         · len(items)
    - `passed`        · 通过 item 数
    - `failed`        · 失败 item 数
    - `dod_set_id`    · 来自 CompiledDoD.set_id
    - `project_id`    · PM-14
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_id: str = Field(..., min_length=1)
    dod_set_id: str = Field(..., min_length=1)
    dod_hash: str = Field(..., min_length=1)
    items: list[ChecklistItem] = Field(default_factory=list)
    total: int = Field(..., ge=0)
    passed: int = Field(..., ge=0)
    failed: int = Field(..., ge=0)

    def to_markdown(self, *, title: str | None = None) -> str:
        """渲染 Markdown 验收清单（简版 · 可被 pandoc 解析）。

        结构:
            # 验收 checklist · <project_id>
            Total: N · Passed: P / N

            ## Hard 表达式
            - [x] h0 · AC-000 · reason
            ## Soft 表达式
            - [ ] s0 · AC-S000 · reason
        """
        header = title or f"验收 checklist · {self.project_id}"
        lines: list[str] = [
            f"# {header}",
            "",
            f"- dod_set_id: `{self.dod_set_id}`",
            f"- dod_hash: `{self.dod_hash}`",
            f"- summary: **{self.passed} / {self.total}** passed · {self.failed} failed",
            "",
        ]

        hard_items = [i for i in self.items if i.kind == DoDExpressionKind.HARD]
        soft_items = [i for i in self.items if i.kind == DoDExpressionKind.SOFT]

        if hard_items:
            lines.append("## Hard 表达式")
            lines.append("")
            for item in hard_items:
                lines.append(_render_item_line(item))
            lines.append("")

        if soft_items:
            lines.append("## Soft 表达式")
            lines.append("")
            for item in soft_items:
                lines.append(_render_item_line(item))
            lines.append("")

        return "\n".join(lines)


def _render_item_line(item: ChecklistItem) -> str:
    """单 item 渲染为 markdown checkbox 行。"""
    checkbox = "- [x]" if item.passed else "- [ ]"
    ac_str = ", ".join(item.source_ac_ids) if item.source_ac_ids else "-"
    return f"{checkbox} **{item.expr_id}** · {ac_str} · {item.reason}"


class ChecklistCompiler:
    """DoD + 评估结果 → AcceptanceChecklist.

    用法:
        checklist = ChecklistCompiler().compile(compiled=dod, evaluated=evaluated)
        md = checklist.to_markdown()
    """

    def compile(
        self,
        *,
        compiled: CompiledDoD,
        evaluated: EvaluatedDoD,
    ) -> AcceptanceChecklist:
        """合成 `AcceptanceChecklist`.

        Args:
            compiled: WP01 `CompiledDoD`（源于 DoD YAML 编译）。
            evaluated: 本轮 `EvaluatedDoD`（由 DoDAdapter 产出）。

        Raises:
            ValueError:
                - `E_L204_CL_PID_MISMATCH`       · compiled.project_id != evaluated.project_id
                - `E_L204_CL_SET_ID_MISMATCH`    · compiled.set_id != evaluated.dod_set_id
        """
        if compiled.project_id != evaluated.project_id:
            raise ValueError(
                f"E_L204_CL_PID_MISMATCH: compiled.project_id={compiled.project_id!r} "
                f"!= evaluated.project_id={evaluated.project_id!r}",
            )
        if compiled.set_id != evaluated.dod_set_id:
            raise ValueError(
                f"E_L204_CL_SET_ID_MISMATCH: compiled.set_id={compiled.set_id!r} "
                f"!= evaluated.dod_set_id={evaluated.dod_set_id!r}",
            )

        items: list[ChecklistItem] = []
        # 索引 evaluated by expr_id 便于拉 reason/passed
        hard_by_id: dict[str, EvaluatedExpression] = {e.expr_id: e for e in evaluated.hard}
        soft_by_id: dict[str, EvaluatedExpression] = {e.expr_id: e for e in evaluated.soft}

        for expr in compiled.hard:
            ev = hard_by_id.get(expr.expr_id)
            items.append(_build_item(expr, ev))
        for expr in compiled.soft:
            ev = soft_by_id.get(expr.expr_id)
            items.append(_build_item(expr, ev))

        total = len(items)
        passed = sum(1 for i in items if i.passed)
        failed = total - passed

        dod_hash = compiled.dod_hash or evaluated.dod_hash
        return AcceptanceChecklist(
            project_id=compiled.project_id,
            dod_set_id=compiled.set_id,
            dod_hash=dod_hash,
            items=items,
            total=total,
            passed=passed,
            failed=failed,
        )


def _build_item(expr: DoDExpression, ev: EvaluatedExpression | None) -> ChecklistItem:
    """合并 DoDExpression + EvaluatedExpression → ChecklistItem."""
    if ev is None:
        # compiled 里有表达式但 evaluated 缺 · 标失败 + 占位 reason
        return ChecklistItem(
            expr_id=expr.expr_id,
            kind=expr.kind,
            passed=False,
            reason="evaluation missing for this expression",
            source_ac_ids=list(expr.source_ac_ids),
            expression_text=expr.expression_text,
        )
    return ChecklistItem(
        expr_id=expr.expr_id,
        kind=expr.kind,
        passed=ev.passed,
        reason=ev.reason,
        source_ac_ids=list(expr.source_ac_ids),
        expression_text=expr.expression_text,
    )


__all__ = [
    "AcceptanceChecklist",
    "ChecklistCompiler",
    "ChecklistCompilerError",
    "ChecklistItem",
]
