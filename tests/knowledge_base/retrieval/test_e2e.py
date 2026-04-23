"""L1-06 L2-05 · e2e · 3-2 §6."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.knowledge_base.retrieval.schemas import (
    RerankContext,
    RerankRequest,
    StageTransitionedEvent,
)


@pytest.mark.e2e
class TestL2_05_E2E:

    def test_TC_L106_L205_701_l2_02_rerank_to_l1_01_inject_full(
        self, sut, mock_project_id, mock_l2_02, mock_l1_01
    ) -> None:
        def _summary(i: int) -> MagicMock:
            es = MagicMock()
            es.title = f"t-{i}"
            ac = MagicMock()
            ac.stages = ["S3"]
            ac.task_types = ["coding"]
            ac.tech_stacks = ["python"]
            es.applicable_context = ac
            es.observed_count = 10
            es.last_observed_at = "2026-04-20T00:00:00Z"
            return es

        mock_l2_02.reverse_recall.return_value = MagicMock(
            candidates=[
                {
                    "entry_id": f"c-{i}",
                    "scope": "project",
                    "kind": "anti_pattern",
                    "entry_summary": _summary(i),
                }
                for i in range(10)
            ],
            recalled_count=10,
            scope_layers_hit=["project"],
            duration_ms=40,
        )
        sut.on_stage_transitioned(
            StageTransitionedEvent(
                event_id="e2e-1",
                event_type="L1-02:stage_transitioned",
                project_id=mock_project_id,
                stage_from="S2",
                stage_to="S3",
                transition_reason="gate_approved",
                transition_at="2026-04-22T10:00:00Z",
                trace_id="t",
            )
        )
        mock_l1_01.push_context.assert_called_once()

    def test_TC_L106_L205_702_s7_reverse_collect_then_promote_candidates(
        self, sut, mock_project_id, mock_l2_03
    ) -> None:
        sut.on_stage_transitioned(
            StageTransitionedEvent(
                event_id="e2e-2",
                event_type="L1-02:stage_transitioned",
                project_id=mock_project_id,
                stage_from="S6",
                stage_to="S7",
                transition_reason="gate",
                transition_at="2026-04-22T10:00:00Z",
                trace_id="t",
            )
        )
        mock_l2_03.provide_candidate_snapshot.assert_called()

    def test_TC_L106_L205_703_rerank_idem_cache_across_tick(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        ctx = RerankContext(
            current_stage="S3", task_type="c", tech_stack=["python"]
        )
        cands = make_candidates(count=10)
        r1 = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="idem-e2e",
                candidates=cands,
                context=ctx,
                top_k=5,
                trace_id="t",
            )
        )
        r2 = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="idem-e2e",
                candidates=cands,
                context=ctx,
                top_k=5,
                trace_id="t",
            )
        )
        assert r1.entries[0].entry_id == r2.entries[0].entry_id
