"""L1-06 L2-02 · positive (15 TC) · 3-2 §2."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.knowledge_base.reader.schemas import (
    ApplicableContext,
    ReadRequest,
    RerankResponse,
)
from app.knowledge_base.reader.service import KBReadService


class TestL2_02_KBRead_Positive:

    def test_TC_L106_L202_001_read_happy_path(
        self, sut: KBReadService, mock_project_id, mock_session_id, mock_l2_05, fake_repo
    ) -> None:
        fake_repo.seed(session=3, project=4, global_=3)
        mock_l2_05.rerank.side_effect = lambda req, *_a, **_kw: RerankResponse(
            ranked=list(req.candidates[:5]), signals_used=["bm25"]
        )
        req = ReadRequest(
            trace_id="tr-001",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(route="S2"),
            top_k=5,
            cache_enabled=True,
        )
        res = sut.read(req)
        assert res.trace_id == "tr-001"
        assert res.error_hint is None
        assert len(res.entries) == 5
        assert res.meta.cache_hit is False

    def test_TC_L106_L202_002_read_cache_hit_short_circuit(
        self, sut: KBReadService, mock_project_id, mock_session_id
    ) -> None:
        req = ReadRequest(
            trace_id="tr-002",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(route="S2"),
            top_k=5,
            cache_enabled=True,
        )
        sut.read(req)
        sut._repo.read_session = MagicMock(side_effect=AssertionError("should be cached"))
        second = sut.read(req)
        assert second.meta.cache_hit is True

    def test_TC_L106_L202_003_read_spg_priority_merge(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed_conflict(
            entry_id="kbe-0001SAME",
            session_title="S ver",
            project_title="P ver",
            global_title="G ver",
        )
        req = ReadRequest(
            trace_id="tr-003",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(route="S2"),
            top_k=5,
            cache_enabled=False,
        )
        res = sut.read(req)
        titles = [e.title for e in res.entries]
        assert "S ver" in titles
        assert "P ver" not in titles

    def test_TC_L106_L202_004_read_kind_filter(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed_kinds(["pattern", "trap", "recipe"], count_each=3)
        req = ReadRequest(
            trace_id="tr-004",
            project_id=mock_project_id,
            session_id=mock_session_id,
            kind=["pattern"],
            applicable_context=ApplicableContext(),
            top_k=10,
            cache_enabled=False,
        )
        res = sut.read(req)
        assert all(e.kind == "pattern" for e in res.entries)

    def test_TC_L106_L202_005_context_match_and(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed_contexts(
            [("S2", ["python"]), ("S2", ["go"]), ("S3", ["python"])]
        )
        req = ReadRequest(
            trace_id="tr-005",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(route="S2", tech_stack=["python"]),
            top_k=10,
            strict_mode=True,
        )
        res = sut.read(req)
        assert len(res.entries) == 1

    def test_TC_L106_L202_006_candidate_overflow_truncated(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed(session=300, project=300, global_=200)
        req = ReadRequest(
            trace_id="tr-006",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=10,
        )
        res = sut.read(req)
        assert res.meta.candidate_overflow is True
        assert res.meta.candidate_count == 500

    def test_TC_L106_L202_007_rerank_invoked_with_candidates(
        self,
        sut: KBReadService,
        mock_l2_05,
        fake_repo,
        mock_project_id,
        mock_session_id,
    ) -> None:
        fake_repo.seed(session=2, project=2, global_=2)
        req = ReadRequest(
            trace_id="tr-007",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(route="S2"),
            top_k=3,
        )
        sut.read(req)
        mock_l2_05.rerank.assert_called_once()
        call_args = mock_l2_05.rerank.call_args[0][0]
        assert len(call_args.candidates) == 6

    def test_TC_L106_L202_008_reverse_recall_allowed_for_l2_05(
        self, sut: KBReadService, mock_project_id, mock_session_id, fake_repo
    ) -> None:
        fake_repo.seed(session=2, project=2, global_=2)
        res = sut.reverse_recall(
            project_id=mock_project_id,
            session_id=mock_session_id,
            stage="S3",
            kinds=["pattern"],
            caller_identity="L2-05",
        )
        assert len(res) >= 1

    def test_TC_L106_L202_009_merge_scope_priority_session_wins(
        self, sut: KBReadService
    ) -> None:
        s = [MagicMock(id="kbe-SAME", scope="session", title="S-win",
                       observed_count=1, last_observed_at="t")]
        p = [MagicMock(id="kbe-SAME", scope="project", title="P-lose",
                       observed_count=1, last_observed_at="t")]
        g = [MagicMock(id="kbe-OTHER", scope="global", title="G-only",
                       observed_count=1, last_observed_at="t")]
        merged = sut._merger.merge(s, p, g)
        titles = [m.title for m in merged]
        assert "S-win" in titles
        assert "G-only" in titles
        assert "P-lose" not in titles

    def test_TC_L106_L202_010_context_match_strict_true(
        self, sut: KBReadService
    ) -> None:
        e1 = MagicMock(applicable_context=MagicMock(route=None, tech_stack=["python"],
                                                     task_type=None, wbs_node_id=None))
        ctx = ApplicableContext(route="S2", tech_stack=["python"])
        assert sut._matcher.match(e1, ctx, strict_mode=True) is False

    def test_TC_L106_L202_011_context_match_default_pass(
        self, sut: KBReadService
    ) -> None:
        e1 = MagicMock(applicable_context=MagicMock(route=None, tech_stack=[],
                                                     task_type=None, wbs_node_id=None))
        ctx = ApplicableContext(route="S2", tech_stack=["python"])
        assert sut._matcher.match(e1, ctx, strict_mode=False) is True

    def test_TC_L106_L202_012_kind_allowed_by_stage(
        self, sut: KBReadService
    ) -> None:
        e = MagicMock(kind="effective_combo")
        assert sut._kind_policy.allowed(e, stage="S4_execute") is True
        assert sut._kind_policy.allowed(e, stage="S1_plan") is False

    def test_TC_L106_L202_013_audit_event_on_every_read(
        self, sut: KBReadService, mock_audit, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed(session=1, project=1, global_=1)
        req = ReadRequest(
            trace_id="tr-013",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=3,
        )
        sut.read(req)
        mock_audit.append.assert_called()
        first = mock_audit.append.call_args_list[0]
        et = first.kwargs.get("event_type") or first.args[0]
        assert et.startswith("kb_read")

    def test_TC_L106_L202_014_trace_id_round_trip(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed(session=1)
        req = ReadRequest(
            trace_id="my-trace-XYZ",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=1,
        )
        res = sut.read(req)
        assert res.trace_id == "my-trace-XYZ"

    def test_TC_L106_L202_015_top_k_truncates_rerank_output(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed(session=10, project=10, global_=0)
        req = ReadRequest(
            trace_id="tr-015",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=5,
        )
        res = sut.read(req)
        assert len(res.entries) == 5
