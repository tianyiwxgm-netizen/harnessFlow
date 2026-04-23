"""L1-06 L2-05 · integration points · 3-2 §8."""
from __future__ import annotations

from app.knowledge_base.retrieval.schemas import (
    RerankContext,
    RerankRequest,
    StageTransitionedEvent,
)


class TestL2_05_Integration:

    def test_TC_L106_L205_801_l2_02_driven_rerank_integration(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="i1",
                candidates=make_candidates(5),
                context=RerankContext(
                    current_stage="S3", task_type="c", tech_stack=["python"]
                ),
                top_k=3,
                trace_id="t",
            )
        )
        for e in resp.entries:
            assert e.entry_id.startswith("kbe-")

    def test_TC_L106_L205_802_strategy_table_drives_injection(
        self, sut, mock_strategy_repo, mock_project_id, mock_l2_02
    ) -> None:
        mock_strategy_repo.get.side_effect = lambda _s: {
            "injected_kinds": [],
            "recall_top_k": 0,
            "rerank_top_k": 0,
        }
        sut.on_stage_transitioned(
            StageTransitionedEvent(
                event_id="e",
                event_type="L1-02:stage_transitioned",
                project_id=mock_project_id,
                stage_from="S2",
                stage_to="S3",
                transition_reason="gate",
                transition_at="2026-04-22T10:00:00Z",
                trace_id="t",
            )
        )
        mock_l2_02.reverse_recall.assert_not_called()
