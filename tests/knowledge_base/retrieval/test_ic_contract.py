"""L1-06 L2-05 · IC contract · 3-2 §4."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.knowledge_base.retrieval.schemas import (
    RerankContext,
    RerankRequest,
    ReverseRecallRequest,
)


class TestL2_05_IC_Contracts:

    def test_TC_L106_L205_601_ic_l2_04_fields(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r",
                candidates=make_candidates(3),
                context=RerankContext(
                    current_stage="S3", task_type="c", tech_stack=["python"]
                ),
                top_k=2,
                trace_id="t",
            )
        )
        for field in (
            "project_id",
            "rerank_id",
            "status",
            "entries",
            "weights_applied",
            "duration_ms",
        ):
            assert hasattr(resp, field)

    def test_TC_L106_L205_602_ic_l2_05_forwards_to_l2_02(
        self, sut, mock_l2_02, mock_project_id
    ) -> None:
        mock_l2_02.reverse_recall.return_value = MagicMock(
            candidates=[], recalled_count=0, scope_layers_hit=[], duration_ms=1
        )
        sut.reverse_recall(
            ReverseRecallRequest(
                project_id=mock_project_id,
                injection_id="i",
                stage_to="S3",
                kinds=["anti_pattern"],
                scope_priority=["session"],
                recall_top_k=5,
                trace_id="t",
            )
        )
        mock_l2_02.reverse_recall.assert_called_once()

    def test_TC_L106_L205_603_stage_event_subscription(
        self, sut, mock_project_id
    ) -> None:
        assert "L1-02:stage_transitioned" in sut._subscribed_event_types

    def test_TC_L106_L205_604_ic_09_audit_on_rerank(
        self, sut, mock_project_id, mock_audit, make_candidates
    ) -> None:
        sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r",
                candidates=make_candidates(3),
                context=RerankContext(
                    current_stage="S3", task_type="c", tech_stack=["python"]
                ),
                top_k=2,
                trace_id="t",
            )
        )
        assert mock_audit.append.called

    def test_TC_L106_L205_605_push_to_l101_fields(
        self, sut, mock_l1_01, mock_project_id
    ) -> None:
        sut._push_to_l101(
            project_id=mock_project_id,
            injection_id="i",
            stage="S3",
            entries=[{"entry_id": "e"}],
            trace_id="t",
        )
        call_args = mock_l1_01.push_context.call_args[0][0]
        for field in (
            "project_id",
            "injection_id",
            "stage",
            "entries",
            "context_type",
        ):
            assert hasattr(call_args, field) or field in call_args
