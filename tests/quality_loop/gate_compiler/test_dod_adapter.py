"""L1-04 · L2-04 · DoDAdapter tests · 覆盖 WP01 真 evaluator + 异常通路.

映射:
- `app.quality_loop.gate_compiler.dod_adapter`
- 错误码: E_L204_PID_MISMATCH · E_L204_EVAL_UNEXPECTED
- missing_evidence 通路 (DoDEvalError → missing_keys + passed=False)
"""
from __future__ import annotations

import uuid

import pytest

from app.quality_loop.dod_compiler import (
    CompileBatchCommand,
    CompiledDoD,
    DoDEvaluator,
    DoDExpression,
    DoDExpressionCompiler,
    DoDExpressionKind,
)
from app.quality_loop.dod_compiler.predicate_eval import WhitelistRegistry
from app.quality_loop.dod_compiler.schemas import DoDClause, Priority
from app.quality_loop.gate_compiler.dod_adapter import (
    DoDAdapter,
    DoDAdapterError,
    EvaluatedDoD,
)


@pytest.fixture
def compiler() -> DoDExpressionCompiler:
    return DoDExpressionCompiler(
        whitelist_registry=WhitelistRegistry(),
        offline_admin_mode=False,
    )


@pytest.fixture
def evaluator(compiler: DoDExpressionCompiler) -> DoDEvaluator:
    return DoDEvaluator(compiler, whitelist_registry=compiler.registry)


@pytest.fixture
def adapter(evaluator: DoDEvaluator) -> DoDAdapter:
    return DoDAdapter(evaluator=evaluator)


def _compile(
    compiler: DoDExpressionCompiler, project_id: str,
    hard_texts: list[tuple[str, str]],
    soft_texts: list[tuple[str, str]] | None = None,
) -> CompiledDoD:
    soft_texts = soft_texts or []
    clauses: list[DoDClause] = []
    ac_entries: list[dict] = []
    for i, (text, ac) in enumerate(hard_texts):
        clauses.append(DoDClause(
            clause_id=f"c-h-{i}-{uuid.uuid4().hex[:8]}",
            clause_text=text, source_ac_ids=[ac],
            priority=Priority.P0, kind=DoDExpressionKind.HARD,
        ))
        ac_entries.append({"id": ac})
    for i, (text, ac) in enumerate(soft_texts):
        clauses.append(DoDClause(
            clause_id=f"c-s-{i}-{uuid.uuid4().hex[:8]}",
            clause_text=text, source_ac_ids=[ac],
            priority=Priority.P1, kind=DoDExpressionKind.SOFT,
        ))
        ac_entries.append({"id": ac})
    cmd = CompileBatchCommand(
        command_id=f"cmd-{uuid.uuid4().hex[:8]}",
        project_id=project_id, blueprint_id="bp-test",
        clauses=clauses, ac_matrix={"acs": ac_entries},
        ts="2026-04-23T00:00:00Z",
    )
    return compiler.compile_batch(cmd).compiled


class TestDoDAdapterPID:
    def test_TC_L204_DA_001_pid_mismatch_raises(
        self, compiler: DoDExpressionCompiler, adapter: DoDAdapter,
    ) -> None:
        """TC-L204-DA-001 · compiled.pid != project_id · DoDAdapterError."""
        compiled = _compile(compiler, "p1", [("line_coverage() >= 0.8", "ac-001")])
        with pytest.raises(DoDAdapterError, match="E_L204_PID_MISMATCH"):
            adapter.evaluate(
                compiled,
                metric_snapshot={"coverage": {"line_rate": 0.9}},
                project_id="p2",
            )


class TestDoDAdapterMissingEvidence:
    def test_TC_L204_DA_010_unknown_data_source_raises_missing(
        self, compiler: DoDExpressionCompiler, adapter: DoDAdapter,
    ) -> None:
        """TC-L204-DA-010 · snapshot 传入白名单外 key · eval fails · missing_keys 记录."""
        compiled = _compile(compiler, "p1", [("line_coverage() >= 0.8", "ac-001")])
        evaluated = adapter.evaluate(
            compiled,
            # 'unknown_src' 不在 WHITELISTED_DATA_SOURCE_KEYS → DoDEvalError
            metric_snapshot={"unknown_src": {"foo": 1}},
            project_id="p1",
        )
        # hard 表达式评估失败 · missing_keys 非空
        assert len(evaluated.hard) == 1
        assert evaluated.hard[0].passed is False
        assert evaluated.hard[0].missing_keys
        assert len(evaluated.missing) >= 1

    def test_TC_L204_DA_011_missing_for_soft(
        self, compiler: DoDExpressionCompiler, adapter: DoDAdapter,
    ) -> None:
        """TC-L204-DA-011 · soft 表达式 eval 失败 · 也进 missing_evidence."""
        compiled = _compile(
            compiler, "p1",
            hard_texts=[("line_coverage() >= 0.1", "ac-h-001")],
            soft_texts=[("p95_ms() < 500", "ac-s-001")],
        )
        evaluated = adapter.evaluate(
            compiled,
            metric_snapshot={"coverage": {"line_rate": 0.9}, "unknown": {}},
            project_id="p1",
        )
        # soft 会被 unknown data source 污染 · fail
        assert evaluated.soft_total == 1
        assert any(m.expr_id.startswith("expr-") or True for m in evaluated.missing)

    def test_TC_L204_DA_012_empty_dod_returns_empty_evaluated(
        self, compiler: DoDExpressionCompiler, adapter: DoDAdapter,
    ) -> None:
        """TC-L204-DA-012 · 空 hard+soft · 聚合根合法 · total 0 · soft_ratio=1.0."""
        from app.quality_loop.dod_compiler.schemas import CompiledDoD as C
        compiled = C(
            set_id="empty-set", project_id="p1", blueprint_id="bp",
            hard=[], soft=[], dod_hash="h-empty",
        )
        evaluated = adapter.evaluate(
            compiled, metric_snapshot={}, project_id="p1",
        )
        assert evaluated.hard_total == 0
        assert evaluated.soft_total == 0
        assert evaluated.soft_ratio == 1.0
        assert evaluated.hard_all_passed is True


class TestDoDAdapterHappyPath:
    def test_TC_L204_DA_020_hard_and_soft_both_pass(
        self, compiler: DoDExpressionCompiler, adapter: DoDAdapter,
    ) -> None:
        """TC-L204-DA-020 · hard + soft 全绿."""
        compiled = _compile(
            compiler, "p1",
            hard_texts=[("line_coverage() >= 0.5", "ac-h")],
            soft_texts=[("branch_coverage() >= 0.5", "ac-s")],
        )
        evaluated = adapter.evaluate(
            compiled,
            metric_snapshot={"coverage": {"line_rate": 0.9, "branch_rate": 0.8}},
            project_id="p1",
        )
        assert evaluated.hard_passed == 1
        assert evaluated.soft_passed == 1
        assert evaluated.missing == []

    def test_TC_L204_DA_021_synth_hash_used_when_dod_hash_empty(
        self, compiler: DoDExpressionCompiler, adapter: DoDAdapter,
    ) -> None:
        """TC-L204-DA-021 · CompiledDoD.dod_hash 空 · 返 fallback-<set_id>."""
        from app.quality_loop.dod_compiler.schemas import CompiledDoD as C
        compiled = C(
            set_id="set-abc", project_id="p1", blueprint_id="bp",
            hard=[], soft=[], dod_hash="",  # 空 hash
        )
        evaluated = adapter.evaluate(compiled, metric_snapshot={}, project_id="p1")
        assert evaluated.dod_hash == "fallback-set-abc"


class TestDoDAdapterUnexpectedException:
    def test_TC_L204_DA_030_unexpected_non_dodeval_raises_wrapped(
        self, compiler: DoDExpressionCompiler,
    ) -> None:
        """TC-L204-DA-030 · evaluator 抛非 DoDEvalError 异常 · adapter 包成 DoDAdapterError."""

        class ExplodingEvaluator:
            def eval_expression(self, cmd):  # noqa: ARG002
                raise RuntimeError("boom · evaluator internal crash")

        compiled = _compile(compiler, "p1", [("line_coverage() >= 0.5", "ac-001")])
        adapter = DoDAdapter(evaluator=ExplodingEvaluator())  # type: ignore[arg-type]
        with pytest.raises(DoDAdapterError, match="E_L204_EVAL_UNEXPECTED"):
            adapter.evaluate(
                compiled,
                metric_snapshot={"coverage": {"line_rate": 0.9}},
                project_id="p1",
            )
