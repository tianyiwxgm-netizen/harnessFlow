"""L1-06 L2-02 · negative (14 TC · 14 error codes) · 3-2 §3."""
from __future__ import annotations

import pytest

from app.knowledge_base.reader.errors import KBSecurityError
from app.knowledge_base.reader.schemas import ApplicableContext, ReadRequest
from app.knowledge_base.reader.service import KBReadService


class TestL2_02_Negative:

    def test_TC_L106_L202_101_invalid_top_k(
        self, sut: KBReadService, mock_project_id, mock_session_id
    ) -> None:
        req = ReadRequest(
            trace_id="tr",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=-1,
        )
        res = sut.read(req)
        assert res.error_hint == "kb_rejected"
        assert res.error_code == "KBR-001"

    def test_TC_L106_L202_102_nl_query_rejected(
        self, sut: KBReadService, mock_project_id, mock_session_id
    ) -> None:
        req = ReadRequest(
            trace_id="tr",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=3,
            nlq="find all FastAPI patterns please",
        )
        res = sut.read(req)
        assert res.error_code == "KBR-002"

    def test_TC_L106_L202_103_scope_denied(
        self, sut: KBReadService, mock_l2_01, mock_project_id, mock_session_id
    ) -> None:
        mock_l2_01.scope_check.return_value.allowed_scopes = []
        req = ReadRequest(
            trace_id="tr",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=3,
        )
        res = sut.read(req)
        assert res.error_code == "KBR-003"
        assert res.error_hint == "kb_rejected"

    def test_TC_L106_L202_104_cross_project(
        self, sut: KBReadService, mock_l2_01, mock_project_id
    ) -> None:
        from app.knowledge_base.tier_manager.errors import ScopeCheckError

        mock_l2_01.scope_check.side_effect = ScopeCheckError("cross-project")
        req = ReadRequest(
            trace_id="tr",
            project_id=mock_project_id,
            session_id="s-OTHER",
            applicable_context=ApplicableContext(),
            top_k=3,
        )
        res = sut.read(req)
        assert res.error_code == "KBR-003"

    def test_TC_L106_L202_105_kind_policy_forbidden_for_stage(
        self, sut: KBReadService, mock_project_id, mock_session_id
    ) -> None:
        req = ReadRequest(
            trace_id="tr",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(route="S1"),
            kind=["effective_combo"],
            top_k=3,
        )
        res = sut.read(req)
        assert res.error_code == "KBR-005"

    def test_TC_L106_L202_106_storage_all_layers_io_error(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.fail_all_layers(OSError("disk bad"))
        req = ReadRequest(
            trace_id="tr",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=3,
        )
        res = sut.read(req)
        assert res.entries == []
        assert res.error_hint == "kb_degraded"
        assert res.error_code == "KBR-006"

    def test_TC_L106_L202_107_global_timeout(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.slow_all_layers(delay_ms=300)
        req = ReadRequest(
            trace_id="tr",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=3,
            global_timeout_ms=100,
        )
        res = sut.read(req)
        assert res.error_code == "KBR-007"
        assert res.error_hint == "kb_timeout"

    def test_TC_L106_L202_108_rerank_fallback(
        self,
        sut: KBReadService,
        mock_l2_05,
        fake_repo,
        mock_project_id,
        mock_session_id,
    ) -> None:
        from app.knowledge_base.retrieval.errors import RerankTimeout

        mock_l2_05.rerank.side_effect = RerankTimeout()
        fake_repo.seed(session=2, project=2, global_=0)
        req = ReadRequest(
            trace_id="tr",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=3,
        )
        res = sut.read(req)
        assert res.error_hint is None
        assert res.meta.rerank_fallback is True
        assert res.meta.fallback_reason == "KBR-008"

    def test_TC_L106_L202_109_cache_corrupt_retry_succeeds(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed(session=1)
        sut._tick_cache.force_corrupt()
        req = ReadRequest(
            trace_id="tr",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=1,
            cache_enabled=True,
        )
        res = sut.read(req)
        assert res.error_hint is None
        assert res.meta.cache_recovered is True

    def test_TC_L106_L202_110_candidate_overflow_audit(
        self,
        sut: KBReadService,
        fake_repo,
        mock_audit,
        mock_project_id,
        mock_session_id,
    ) -> None:
        fake_repo.seed(session=300, project=300, global_=0)
        req = ReadRequest(
            trace_id="tr",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=3,
        )
        sut.read(req)
        events = [
            c.kwargs.get("event_type") or (c.args[0] if c.args else None)
            for c in mock_audit.append.call_args_list
        ]
        assert "kb_read_candidate_overflow" in events

    def test_TC_L106_L202_111_entry_schema_invalid_skipped(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed_with_bad_entries(session_good=2, session_bad=1)
        req = ReadRequest(
            trace_id="tr",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=5,
        )
        res = sut.read(req)
        assert res.meta.schema_invalid_skipped == 1
        assert len(res.entries) == 2

    def test_TC_L106_L202_112_missing_trace_id(
        self, sut: KBReadService, mock_project_id, mock_session_id
    ) -> None:
        req = ReadRequest(
            trace_id=None,
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=3,
        )
        res = sut.read(req)
        assert res.error_code == "KBR-012"

    def test_TC_L106_L202_113_reverse_recall_unauthorized(
        self, sut: KBReadService, mock_project_id, mock_session_id
    ) -> None:
        with pytest.raises(KBSecurityError) as exc:
            sut.reverse_recall(
                project_id=mock_project_id,
                session_id=mock_session_id,
                stage="S3",
                kinds=["pattern"],
                caller_identity="attacker",
            )
        assert exc.value.code == "KBR-013"

    def test_TC_L106_L202_114_jsonl_corrupt_line_skipped(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed_with_truncated_jsonl(good_lines=3, bad_last_line=True)
        req = ReadRequest(
            trace_id="tr",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=5,
        )
        res = sut.read(req)
        assert res.meta.jsonl_line_corrupt_skipped >= 1
        assert len(res.entries) == 3
