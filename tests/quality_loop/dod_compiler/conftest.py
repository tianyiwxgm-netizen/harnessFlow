"""L1-04 L2-02 · 共享 fixture.

与 3-2 tdd tests.md §7 fixture 对齐;
因为 main-1 的包结构走 app/quality_loop/dod_compiler/,不走 app.l1_04.l2_02.*,
fixture 名保持 brief 期望的 mock_project_id / make_compile_request / ... 风格.
"""
from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.quality_loop.dod_compiler import (
    CompileBatchCommand,
    DoDEvaluator,
    DoDExpressionCompiler,
    EvalCommand,
)
from app.quality_loop.dod_compiler.predicate_eval import WhitelistRegistry
from app.quality_loop.dod_compiler.schemas import (
    AddWhitelistRuleCommand,
    DoDClause,
    DoDExpressionKind,
    EvalCaller,
    OfflineReviewMemo,
    Priority,
    VersionBumpType,
)


@pytest.fixture
def mock_project_id() -> str:
    return "pid-l202-default"


@pytest.fixture
def other_project_id() -> str:
    return "pid-l202-foreign"


@pytest.fixture
def fresh_registry() -> WhitelistRegistry:
    return WhitelistRegistry()


@pytest.fixture
def mock_event_bus() -> MagicMock:
    bus = MagicMock()
    bus.append_event.return_value = {"ok": True}
    return bus


@pytest.fixture
def mock_fs() -> MagicMock:
    fs = MagicMock()
    fs._store = {}

    def _exists(p: str) -> bool:
        return p in fs._store

    def _write(p: str, c: str) -> None:
        fs._store[p] = c

    def _read(p: str) -> str:
        return fs._store.get(p, "")

    fs.exists = _exists
    fs.write = _write
    fs.read = _read
    return fs


@pytest.fixture
def sut(fresh_registry: WhitelistRegistry) -> DoDExpressionCompiler:
    return DoDExpressionCompiler(
        whitelist_registry=fresh_registry,
        offline_admin_mode=False,
    )


@pytest.fixture
def sut_offline_admin(fresh_registry: WhitelistRegistry) -> DoDExpressionCompiler:
    return DoDExpressionCompiler(
        whitelist_registry=fresh_registry,
        offline_admin_mode=True,
    )


@pytest.fixture
def evaluator(sut: DoDExpressionCompiler) -> DoDEvaluator:
    return DoDEvaluator(
        sut,
        whitelist_registry=sut.registry,
        eval_timeout_ms=500,
    )


_CLAUSE_POOL = [
    ("line_coverage() >= 0.8", DoDExpressionKind.HARD),
    ("lint_errors() == 0", DoDExpressionKind.HARD),
    ("p0_cases_all_pass()", DoDExpressionKind.HARD),
    ("high_severity_count() == 0", DoDExpressionKind.HARD),
    ("p95_ms() < 500", DoDExpressionKind.METRIC),
    ("test_pass_rate() >= 0.95", DoDExpressionKind.SOFT),
    ("branch_coverage() >= 0.7", DoDExpressionKind.SOFT),
]


@pytest.fixture
def make_compile_request() -> Callable[..., CompileBatchCommand]:
    def _factory(**overrides: Any) -> CompileBatchCommand:
        clause_count = overrides.pop("clause_count", 5)
        unmappable_texts: list[str] = list(overrides.pop("inject_unmappable_texts", []))
        danger_texts: list[str] = list(overrides.pop("inject_danger_texts", []))
        syntax_err_indices: set[int] = set(overrides.pop("inject_syntax_error_indices", []))
        invalid_ac_indices: set[int] = set(overrides.pop("inject_invalid_ac_indices", []))
        missing_ac_for_index: set[int] = set(overrides.pop("inject_missing_ac_for_index", []))
        clauses: list[DoDClause] = []
        for i in range(clause_count):
            text, kind = _CLAUSE_POOL[i % len(_CLAUSE_POOL)]
            if i in syntax_err_indices:
                text = "coverage.line_rate >>>>=== 0.8"
            elif unmappable_texts:
                text = unmappable_texts.pop(0)
            elif danger_texts:
                text = danger_texts.pop(0)
            ac_id = f"ac-{i:04d}"
            if i in invalid_ac_indices:
                ac_id = f"ac-ghost-{i}"
            clauses.append(DoDClause(
                clause_id=f"clause-{uuid.uuid4()}",
                clause_text=text,
                source_ac_ids=[ac_id],
                priority=Priority.P0 if kind == DoDExpressionKind.HARD else Priority.P1,
                wp_id=overrides.get("wp_id"),
                kind=kind,
            ))
        # build ac_matrix (except missing ones)
        ac_entries = []
        for i, c in enumerate(clauses):
            if i in missing_ac_for_index:
                continue
            if c.source_ac_ids[0].startswith("ac-ghost"):
                continue
            ac_entries.append({"id": c.source_ac_ids[0]})
        ac_matrix = overrides.pop("ac_matrix", {"acs": ac_entries})
        return CompileBatchCommand(
            command_id=overrides.get("command_id", f"cmd-{uuid.uuid4()}"),
            project_id=overrides.get("project_id", "pid-l202-default"),
            blueprint_id=overrides.get("blueprint_id", "bp-0001"),
            clauses=clauses,
            ac_matrix=ac_matrix,
            wp_id=overrides.get("wp_id"),
            whitelist_version=overrides.get("whitelist_version"),
            timeout_s=overrides.get("timeout_s", 120),
            ts="2026-04-22T00:00:00Z",
        )

    return _factory


@pytest.fixture
def make_eval_request() -> Callable[..., EvalCommand]:
    def _factory(**overrides: Any) -> EvalCommand:
        coverage_value = overrides.pop("coverage_value", 0.85)
        lint_error_count = overrides.pop("lint_error_count", None)
        include_perf = overrides.pop("include_perf", False)
        include_artifact = overrides.pop("include_artifact", False)
        inject_unknown: dict[str, Any] | None = overrides.pop("inject_unknown_data_source", None)
        snapshot: dict[str, Any] = {
            "coverage": {"line_rate": coverage_value},
        }
        if lint_error_count is not None:
            snapshot["lint"] = {"error_count": lint_error_count}
        if include_perf:
            snapshot["perf"] = {"p95_ms": 400}
        if include_artifact:
            snapshot["artifact"] = {"files": ["dist/app.js"]}
        if inject_unknown:
            snapshot.update(inject_unknown)
        return EvalCommand(
            command_id=overrides.get("command_id", f"cmd-eval-{uuid.uuid4()}"),
            project_id=overrides.get("project_id", "pid-l202-default"),
            expr_id=overrides.get("expr_id", "expr-placeholder"),
            data_sources_snapshot=snapshot,
            caller=overrides.get("caller", EvalCaller.L2_05_WP_SELF_CHECK),
            timeout_ms=overrides.get("timeout_ms", 500),
            ts="2026-04-22T00:00:00Z",
        )

    return _factory


@pytest.fixture
def make_add_whitelist_rule_request() -> Callable[..., AddWhitelistRuleCommand]:
    def _factory(**overrides: Any) -> AddWhitelistRuleCommand:
        return AddWhitelistRuleCommand(
            rule=overrides.get("rule", {"name": "math_sqrt", "arg_count": 1}),
            offline_review_memo=OfflineReviewMemo(
                review_date="2026-04-22",
                reviewers=overrides.get("reviewers", ["sre-alice", "sec-bob"]),
                rationale=("金融项目需要平方根判别波动率阈值,经 2026-Q2 安全评审通过。" * 2)[:200],
                test_coverage_plan="新增 12 条单元测试覆盖 sqrt 输入边界 + NaN + 负数",
            ),
            version_bump_type=VersionBumpType(overrides.get("version_bump_type", "minor")),
            operator=overrides.get("operator", "sre-alice"),
            signature="gpg:mock-signature",
        )

    return _factory


@pytest.fixture
def ready_expr_id(
    sut: DoDExpressionCompiler,
    mock_project_id: str,
    make_compile_request,
) -> str:
    """编译一条 line_coverage >= 0.8 表达式 · 返回 expr_id."""
    cmd = make_compile_request(project_id=mock_project_id, clause_count=1)
    resp = sut.compile_batch(cmd)
    assert resp.compiled is not None
    assert resp.compiled.all_expressions()
    return resp.compiled.all_expressions()[0].expr_id


@pytest.fixture
def ready_expr_id_of_other_project(
    sut: DoDExpressionCompiler,
    other_project_id: str,
    make_compile_request,
) -> str:
    cmd = make_compile_request(project_id=other_project_id, clause_count=1)
    resp = sut.compile_batch(cmd)
    return resp.compiled.all_expressions()[0].expr_id
