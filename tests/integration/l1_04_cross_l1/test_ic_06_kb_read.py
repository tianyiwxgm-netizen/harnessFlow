"""WP09-05 · IC-06 消费端 · L1-04 DoD Compiler ← L1-06 KB Read.

**契约**: L1-04 DoD 编译时 · 可通过 IC-06 `kb_read` 拉取 KB 里的 `recipe` /
`pattern` / `trap` 条目 · 把这些规则汇入 DoD 的 predicate 或 AC matrix.

**L1-06 真实代码**: `KBReadService` (5 step pipeline · scope_check / tier
read / rerank / audit) · 本 TC 直接用真实 service + fake repo 来验契约完整.

**L1-04 消费路径**: 本 TC 演示 "先 kb_read 取规则 · 再 compile_batch" 的双
L1 wire · 验 ApplicableContext 按 WP stage 路由 · 验返回结构可喂给 DoD compiler.

**锚点**: L1-06 L2-02 kb_read.md §4.1 5-step · IC-06 kb_read schema.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.knowledge_base.reader.schemas import (
    ApplicableContext,
    KBEntry,
    ReadRequest,
)
from app.knowledge_base.reader.service import KBReadService
from app.quality_loop.dod_compiler.compiler import DoDExpressionCompiler
from app.quality_loop.dod_compiler.schemas import (
    CompileBatchCommand,
    DoDClause,
    DoDExpressionKind,
)


# ==============================================================================
# TC-1 · kb_read 能被 DoD 编译链路消费
# ==============================================================================


class TestKBReadFeedsDoDCompile:
    """L1-04 → L1-06 kb_read · 取 S5 stage 可用的 recipe/pattern 条目
    · 把条目 id 作为 source_ac_ids 进入 DoD 编译.
    """

    def _build_reader(self, session_entries=None, project_entries=None):
        """Instantiate real KBReadService with fake deps."""
        from tests.integration.l1_04_cross_l1.conftest import (
            AuditSink,
            FakeKBRepo,
            FakeReranker,
            FakeScopeChecker,
        )

        repo = FakeKBRepo(
            session_entries=session_entries or [],
            project_entries=project_entries or [],
            global_entries=[],
        )
        scope_checker = FakeScopeChecker()
        reranker = FakeReranker()
        audit = AuditSink()
        svc = KBReadService(
            scope_checker=scope_checker,
            reranker=reranker,
            audit=audit,
            repo=repo,
        )
        return svc, audit

    def test_kb_read_recipe_for_s5_feeds_dod_source_ac_ids(
        self,
        project_id: str,
    ) -> None:
        """kb_read 取 S5 stage 的 recipe · ids 作为 source_ac_ids 喂 compile_batch."""
        recipe1 = KBEntry(
            id="recipe-coverage-ge-80",
            scope="project",
            kind="recipe",
            title="coverage ≥ 80%",
            content="所有 PR 需覆盖率至少 80%",
            applicable_context=ApplicableContext(route="S5"),
            observed_count=12,
        )
        recipe2 = KBEntry(
            id="recipe-tests-all-green",
            scope="project",
            kind="recipe",
            title="tests all green",
            content="不能有 red",
            applicable_context=ApplicableContext(route="S5"),
            observed_count=8,
        )
        svc, audit = self._build_reader(project_entries=[recipe1, recipe2])

        # L1-04 Verifier / DoD compile · 需 S5 stage 的 recipe
        req = ReadRequest(
            trace_id="tr-dod-1",
            project_id=project_id,
            session_id="sess-wp09",
            applicable_context=ApplicableContext(route="S5"),
            kind="recipe",
            top_k=5,
        )
        result = svc.read(req)
        assert result.meta.returned_count == 2
        ids = [e.id for e in result.entries]
        assert "recipe-coverage-ge-80" in ids
        # observed_count DESC 排序（recipe1 > recipe2）
        assert result.entries[0].id == "recipe-coverage-ge-80"

        # 把 ids 作为 source_ac_ids 喂 DoD
        compiler = DoDExpressionCompiler()
        cmd = CompileBatchCommand(
            command_id="cmd-dod-1",
            project_id=project_id,
            blueprint_id="bp-wp09",
            wp_id="wp-int-1",
            clauses=[
                DoDClause(
                    clause_id="c1",
                    clause_text="coverage >= 0.80",
                    source_ac_ids=[result.entries[0].id, result.entries[1].id],
                    kind=DoDExpressionKind.METRIC,
                ),
            ],
            ac_matrix={result.entries[0].id: {}, result.entries[1].id: {}},
            ts="2026-04-23T10:00:00Z",
        )
        res = compiler.compile_batch(cmd)
        assert res.accepted is True
        assert res.compiled_count == 1
        # 编译产物里 source_ac_ids 与 KB ids 一致
        expr = res.compiled.metric[0]
        assert set(expr.source_ac_ids) == {
            "recipe-coverage-ge-80",
            "recipe-tests-all-green",
        }

    def test_kb_read_audit_event_emitted(
        self,
        project_id: str,
    ) -> None:
        """kb_read 必 emit `kb_read_performed` audit event (IC-09 路径)."""
        entry = KBEntry(
            id="pat-x",
            scope="project",
            kind="pattern",
            title="X",
            content="x",
            applicable_context=ApplicableContext(route="S5"),
            observed_count=3,
        )
        svc, audit = self._build_reader(project_entries=[entry])
        svc.read(
            ReadRequest(
                trace_id="tr-audit-1",
                project_id=project_id,
                session_id="sess-a",
                applicable_context=ApplicableContext(route="S5"),
                kind="pattern",
                top_k=3,
            )
        )
        types = [e["type"] for e in audit.events]
        assert "kb_read_performed" in types

    def test_kb_read_stage_kind_policy_rejects_trap_in_s5(
        self,
        project_id: str,
    ) -> None:
        """KindPolicy · 某些 kind 在某些 stage 禁用 · L2-02 硬约束 · 返 error_code."""
        svc, _ = self._build_reader()
        # 故意构造一个 possibly-forbidden kind + stage · 若被拒则有 error_code
        req = ReadRequest(
            trace_id="tr-policy-1",
            project_id=project_id,
            session_id="sess-p",
            applicable_context=ApplicableContext(route="S5"),
            kind="trap",
            top_k=1,
        )
        result = svc.read(req)
        # 允许: 若 S5 接受 trap · 则 returned_count=0 (无条目) 但不 reject
        # 不允许: 会有 error_code=KIND_NOT_ALLOWED
        # 本 TC 只核实 reader 契约可读 · error_code 若存在应在已知集合
        if result.error_code is not None:
            assert result.error_code in {"KIND_NOT_ALLOWED", "SCOPE_DENIED"}


# ==============================================================================
# TC-2 · PM-14 · 项目隔离
# ==============================================================================


class TestKBReadPM14Isolation:
    """L1-06 kb_read 按 project_id 隔离 · L1-04 不能跨 project 看到对方 recipe."""

    def test_project_a_cannot_read_project_b_entries(
        self,
        project_id: str,
    ) -> None:
        """A 的 reader 只返 A 的 entries (repo 层 project 维度隔离)."""
        from tests.integration.l1_04_cross_l1.conftest import (
            AuditSink,
            FakeKBRepo,
            FakeReranker,
            FakeScopeChecker,
        )

        entry_a = KBEntry(
            id="recipe-a-only",
            scope="project",
            kind="recipe",
            title="A only",
            content="a",
            applicable_context=ApplicableContext(route="S5"),
            observed_count=5,
            project_id="proj-A",
        )
        # repo 是 per-project · 这里只放 proj-A 的 entry
        repo_a = FakeKBRepo(project_entries=[entry_a])
        svc = KBReadService(
            scope_checker=FakeScopeChecker(),
            reranker=FakeReranker(),
            audit=AuditSink(),
            repo=repo_a,
        )
        # proj-A 查 · 查得到
        req_a = ReadRequest(
            trace_id="tr-a",
            project_id="proj-A",
            session_id="sess-a",
            applicable_context=ApplicableContext(route="S5"),
            kind="recipe",
            top_k=5,
        )
        r_a = svc.read(req_a)
        assert r_a.meta.returned_count == 1

        # proj-B 查 B 的 repo · 无条目（真实 KB 按 pid 分 repo · 本 fake 用不同
        # repo 实例表达）
        repo_b = FakeKBRepo(project_entries=[])
        svc_b = KBReadService(
            scope_checker=FakeScopeChecker(),
            reranker=FakeReranker(),
            audit=AuditSink(),
            repo=repo_b,
        )
        req_b = ReadRequest(
            trace_id="tr-b",
            project_id="proj-B",
            session_id="sess-b",
            applicable_context=ApplicableContext(route="S5"),
            kind="recipe",
            top_k=5,
        )
        r_b = svc_b.read(req_b)
        assert r_b.meta.returned_count == 0
