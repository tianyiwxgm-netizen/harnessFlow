"""L1-06 L2-05 · positive · 3-2 §2."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.knowledge_base.retrieval.schemas import (
    RerankContext,
    RerankRequest,
    ReverseRecallRequest,
    StageTransitionedEvent,
)


class TestL2_05_Positive:

    def test_TC_L106_L205_001_rerank_100_top_k_5(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        cands = make_candidates(count=100)
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r-001",
                candidates=cands,
                context=RerankContext(
                    current_stage="S3", task_type="coding", tech_stack=["python"]
                ),
                top_k=5,
                include_trace=False,
                trace_id="t",
            )
        )
        assert resp.status == "success"
        assert len(resp.entries) == 5
        assert resp.entries[0].rank == 1
        assert resp.entries[0].score >= resp.entries[-1].score

    def test_TC_L106_L205_002_empty_candidates_not_degraded(
        self, sut, mock_project_id
    ) -> None:
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r-002",
                candidates=[],
                context=RerankContext(
                    current_stage="S3", task_type=None, tech_stack=[]
                ),
                top_k=5,
                trace_id="t",
            )
        )
        assert resp.entries == []
        assert resp.degraded is False

    def test_TC_L106_L205_003_five_signals_weighted(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r-003",
                candidates=make_candidates(count=10),
                context=RerankContext(
                    current_stage="S3", task_type="coding", tech_stack=["python"]
                ),
                top_k=5,
                trace_id="t",
            )
        )
        for k in (
            "context_match",
            "stage_match",
            "observed_count",
            "recency",
            "kind_priority",
        ):
            assert k in resp.weights_applied

    def test_TC_L106_L205_004_include_trace_reason(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r-004",
                candidates=make_candidates(count=5),
                context=RerankContext(
                    current_stage="S3", task_type="coding", tech_stack=["python"]
                ),
                top_k=3,
                include_trace=True,
                trace_id="t",
            )
        )
        assert resp.entries[0].reason is not None
        assert resp.entries[0].reason.top_signal

    def test_TC_L106_L205_005_idem_same_id(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        cands = make_candidates(count=5)
        ctx = RerankContext(
            current_stage="S3", task_type="coding", tech_stack=["python"]
        )
        r1 = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r-idem",
                candidates=cands,
                context=ctx,
                top_k=3,
                trace_id="t",
            )
        )
        r2 = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r-idem",
                candidates=cands,
                context=ctx,
                top_k=3,
                trace_id="t",
            )
        )
        assert [e.entry_id for e in r1.entries] == [e.entry_id for e in r2.entries]

    def test_TC_L106_L205_006_reverse_recall_forwards_to_l2_02(
        self, sut, mock_project_id, mock_l2_02
    ) -> None:
        mock_l2_02.reverse_recall.return_value = MagicMock(
            candidates=[{"entry_id": f"c-{i}"} for i in range(18)],
            recalled_count=18,
            scope_layers_hit=["session", "project"],
            duration_ms=45,
        )
        resp = sut.reverse_recall(
            ReverseRecallRequest(
                project_id=mock_project_id,
                injection_id="i-001",
                stage_to="S3",
                kinds=["anti_pattern"],
                scope_priority=["session", "project", "global"],
                recall_top_k=20,
                trace_id="t",
            )
        )
        assert resp.recalled_count == 18

    def test_TC_L106_L205_007_stage_s3_injection(
        self, sut, mock_project_id, mock_l2_02, mock_l1_01
    ) -> None:
        mock_l2_02.reverse_recall.return_value = MagicMock(
            candidates=[{"entry_id": "c-1", "kind": "anti_pattern"}],
            recalled_count=1,
            scope_layers_hit=["project"],
            duration_ms=30,
        )
        sut.on_stage_transitioned(
            StageTransitionedEvent(
                event_id="e-1",
                event_type="L1-02:stage_transitioned",
                project_id=mock_project_id,
                stage_from="S2",
                stage_to="S3",
                transition_reason="gate_approved",
                transition_at="2026-04-22T10:00:00Z",
                trace_id="t",
            )
        )
        mock_l2_02.reverse_recall.assert_called_once()
        mock_l1_01.push_context.assert_called_once()

    def test_TC_L106_L205_008_stage_s7_reverse_collect(
        self, sut, mock_project_id, mock_l2_03
    ) -> None:
        sut.on_stage_transitioned(
            StageTransitionedEvent(
                event_id="e-2",
                event_type="L1-02:stage_transitioned",
                project_id=mock_project_id,
                stage_from="S6",
                stage_to="S7",
                transition_reason="gate_approved",
                transition_at="2026-04-22T10:00:00Z",
                trace_id="t",
            )
        )
        mock_l2_03.provide_candidate_snapshot.assert_called()

    def test_TC_L106_L205_009_push_to_l101_success(
        self, sut, mock_l1_01, mock_project_id
    ) -> None:
        mock_l1_01.push_context.return_value = MagicMock(
            accepted=True, context_id="ctx-001", rejection_reason=None
        )
        resp = sut._push_to_l101(
            project_id=mock_project_id,
            injection_id="i",
            stage="S3",
            entries=[{"entry_id": "c"}],
            trace_id="t",
        )
        assert resp.accepted is True

    def test_TC_L106_L205_010_scorer_stage_match(self, sut) -> None:
        score = sut._scorers.stage_match(
            entry=MagicMock(
                applicable_context=MagicMock(stages=["S3", "S4"])
            ),
            context=MagicMock(current_stage="S3"),
        )
        assert score == 1.0

    def test_TC_L106_L205_011_scorer_context_match(self, sut) -> None:
        score = sut._scorers.context_match(
            entry=MagicMock(
                applicable_context=MagicMock(
                    task_types=["coding"], tech_stacks=["python", "fastapi"]
                )
            ),
            context=MagicMock(task_type="coding", tech_stack=["python"]),
        )
        assert 0 < score <= 1.0

    def test_TC_L106_L205_012_scorer_observed_count_saturated(self, sut) -> None:
        s1 = sut._scorers.observed_count(entry=MagicMock(observed_count=1))
        s15 = sut._scorers.observed_count(entry=MagicMock(observed_count=15))
        s100 = sut._scorers.observed_count(entry=MagicMock(observed_count=100))
        assert s1 < s15 <= s100

    def test_TC_L106_L205_013_scorer_recency_newer_higher(self, sut) -> None:
        s_new = sut._scorers.recency(
            entry=MagicMock(last_observed_at="2026-04-21T00:00:00Z"),
            now_iso="2026-04-22T00:00:00Z",
        )
        s_old = sut._scorers.recency(
            entry=MagicMock(last_observed_at="2024-01-01T00:00:00Z"),
            now_iso="2026-04-22T00:00:00Z",
        )
        assert s_new > s_old

    def test_TC_L106_L205_014_scorer_kind_priority_stage_dependent(
        self, sut
    ) -> None:
        p_anti = sut._scorers.kind_priority(
            entry=MagicMock(kind="anti_pattern"),
            context=MagicMock(current_stage="S3"),
        )
        p_pat = sut._scorers.kind_priority(
            entry=MagicMock(kind="pattern"),
            context=MagicMock(current_stage="S3"),
        )
        assert p_anti >= p_pat

    def test_TC_L106_L205_015_weights_sum_one(self, sut) -> None:
        total = sum(sut._config.weights.values())
        assert abs(total - 1.0) < 0.001
