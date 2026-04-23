"""L1-06 L2-05 · negative · 3-2 §3 · 20 error codes."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from app.knowledge_base.retrieval.errors import WeightsSumError
from app.knowledge_base.retrieval.schemas import (
    RerankContext,
    RerankRequest,
    ReverseRecallRequest,
    StageTransitionedEvent,
)


class TestL2_05_Negative:

    def test_TC_L106_L205_101_empty_candidates(self, sut, mock_project_id) -> None:
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r",
                candidates=[],
                context=RerankContext(
                    current_stage="S3", task_type="c", tech_stack=[]
                ),
                top_k=5,
                trace_id="t",
            )
        )
        assert resp.entries == []

    def test_TC_L106_L205_102_invalid_top_k(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r",
                candidates=make_candidates(5),
                context=RerankContext(
                    current_stage="S3", task_type="c", tech_stack=[]
                ),
                top_k=-1,
                trace_id="t",
            )
        )
        assert (
            "E_L205_IC04_INVALID_TOP_K" in (resp.warnings or [])
            or resp.top_k_capped is True
        )

    def test_TC_L106_L205_103_project_id_missing(
        self, sut, make_candidates
    ) -> None:
        resp = sut.rerank(
            RerankRequest(
                project_id=None,
                rerank_id="r",
                candidates=make_candidates(5),
                context=RerankContext(
                    current_stage="S3", task_type="c", tech_stack=[]
                ),
                top_k=5,
                trace_id="t",
            )
        )
        assert resp.status == "rejected"
        assert resp.error_code == "E_L205_IC04_PROJECT_ID_MISSING"

    def test_TC_L106_L205_104_context_invalid(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r",
                candidates=make_candidates(5),
                context=RerankContext(
                    current_stage=None, task_type="c", tech_stack=[]
                ),
                top_k=5,
                trace_id="t",
            )
        )
        assert resp.error_code == "E_L205_IC04_CONTEXT_INVALID"

    def test_TC_L106_L205_105_scorer_fail_skip_signal(
        self, sut, mock_project_id, make_candidates, monkeypatch
    ) -> None:
        def boom(*_a, **_kw):
            raise ValueError("scorer bug")

        monkeypatch.setattr(sut._scorers, "stage_match", boom)
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r",
                candidates=make_candidates(5),
                context=RerankContext(
                    current_stage="S3", task_type="c", tech_stack=["python"]
                ),
                top_k=3,
                trace_id="t",
            )
        )
        assert "stage_match" in resp.signals_skipped

    def test_TC_L106_L205_106_all_scorers_fail_fallback_raw(
        self, sut, mock_project_id, make_candidates, monkeypatch
    ) -> None:
        def boom(*_a, **_kw):
            raise ValueError("all bug")

        for s in (
            "stage_match",
            "context_match",
            "observed_count",
            "recency",
            "kind_priority",
        ):
            monkeypatch.setattr(sut._scorers, s, boom)
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r",
                candidates=make_candidates(5),
                context=RerankContext(
                    current_stage="S3", task_type="c", tech_stack=["python"]
                ),
                top_k=3,
                trace_id="t",
            )
        )
        assert resp.degraded is True
        assert resp.fallback_mode == "FALLBACK_RAW"

    def test_TC_L106_L205_107_weights_sum_invalid(self, sut) -> None:
        sut._config.weights = {
            "context_match": 0.2,
            "stage_match": 0.2,
            "observed_count": 0.1,
            "recency": 0.2,
            "kind_priority": 0.1,
        }  # sum = 0.8
        with pytest.raises(WeightsSumError) as exc:
            sut._validate_weights()
        assert exc.value.code == "E_L205_IC04_WEIGHTS_SUM_INVALID"

    def test_TC_L106_L205_108_top_k_capped(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r",
                candidates=make_candidates(50),
                context=RerankContext(
                    current_stage="S3", task_type="c", tech_stack=["python"]
                ),
                top_k=10000,
                trace_id="t",
            )
        )
        assert resp.top_k_capped is True

    def test_TC_L106_L205_109_isolation_violation(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        cands = make_candidates(5, project_override="p-WRONG")
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r",
                candidates=cands,
                context=RerankContext(
                    current_stage="S3", task_type="c", tech_stack=["python"]
                ),
                top_k=3,
                trace_id="t",
            )
        )
        assert resp.status == "rejected"
        assert resp.error_code == "E_L205_IC04_ISOLATION_VIOLATION"

    def test_TC_L106_L205_110_rerank_timeout(
        self, sut, mock_project_id, make_candidates, monkeypatch
    ) -> None:
        def slow(*_a, **_kw):
            time.sleep(0.15)
            return 0.5

        monkeypatch.setattr(sut._scorers, "stage_match", slow)
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r",
                candidates=make_candidates(10),
                context=RerankContext(
                    current_stage="S3", task_type="c", tech_stack=["python"]
                ),
                top_k=3,
                trace_id="t",
                timeout_ms=100,
            )
        )
        assert resp.degraded is True
        assert (
            resp.error_code == "E_L205_IC04_TIMEOUT"
            or "E_L205_IC04_TIMEOUT" in (resp.signals_skipped or [])
        )

    def test_TC_L106_L205_111_trace_cache_fail_non_blocking(
        self, sut, mock_project_id, make_candidates, monkeypatch
    ) -> None:
        def boom(*_a, **_kw):
            raise OSError("fs")

        monkeypatch.setattr(sut._trace_cache, "write", boom)
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r",
                candidates=make_candidates(5),
                context=RerankContext(
                    current_stage="S3", task_type="c", tech_stack=["python"]
                ),
                top_k=3,
                include_trace=True,
                trace_id="t",
            )
        )
        assert resp.status == "success"

    def test_TC_L106_L205_112_entry_field_tampered(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        cands = make_candidates(5)
        cands[0].entry_summary.title = "TAMPERED"
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r",
                candidates=cands,
                context=RerankContext(
                    current_stage="S3", task_type="c", tech_stack=["python"]
                ),
                top_k=3,
                trace_id="t",
            )
        )
        assert resp.error_code == "E_L205_IC04_ENTRY_FIELD_TAMPERED"

    def test_TC_L106_L205_113_l2_02_unavailable_empty_injection(
        self, sut, mock_project_id, mock_l2_02, mock_l1_01
    ) -> None:
        mock_l2_02.reverse_recall.side_effect = TimeoutError("down")
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
        mock_l1_01.push_context.assert_not_called()

    def test_TC_L106_L205_114_reverse_recall_empty(
        self, sut, mock_project_id, mock_l2_02
    ) -> None:
        mock_l2_02.reverse_recall.return_value = MagicMock(
            candidates=[], recalled_count=0, scope_layers_hit=[], duration_ms=5
        )
        resp = sut.reverse_recall(
            ReverseRecallRequest(
                project_id=mock_project_id,
                injection_id="i",
                stage_to="S3",
                kinds=["anti_pattern"],
                scope_priority=["session", "project"],
                recall_top_k=20,
                trace_id="t",
            )
        )
        assert resp.recalled_count == 0

    def test_TC_L106_L205_115_reverse_recall_timeout(
        self, sut, mock_project_id, mock_l2_02
    ) -> None:
        def slow(*_a, **_kw):
            time.sleep(1.5)

        mock_l2_02.reverse_recall.side_effect = slow
        resp = sut.reverse_recall(
            ReverseRecallRequest(
                project_id=mock_project_id,
                injection_id="i",
                stage_to="S3",
                kinds=["anti_pattern"],
                scope_priority=["session", "project"],
                recall_top_k=20,
                trace_id="t",
                timeout_ms=1000,
            )
        )
        assert resp.error_code == "E_L205_IC05_TIMEOUT"

    def test_TC_L106_L205_116_stage_unknown(self, sut, mock_project_id) -> None:
        sut.on_stage_transitioned(
            StageTransitionedEvent(
                event_id="e",
                event_type="L1-02:stage_transitioned",
                project_id=mock_project_id,
                stage_from="S2",
                stage_to="S99",
                transition_reason="gate",
                transition_at="2026-04-22T10:00:00Z",
                trace_id="t",
            )
        )
        assert (
            any("E_L205_STAGE_UNKNOWN" in str(e) for e in sut._audit_log)
            or sut._last_error_code == "E_L205_STAGE_UNKNOWN"
        )

    def test_TC_L106_L205_117_strategy_not_found_fallback(
        self, sut, mock_project_id, mock_strategy_repo
    ) -> None:
        mock_strategy_repo.get.side_effect = KeyError("no strategy")
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
        assert sut._fallback_no_injection_count >= 1

    def test_TC_L106_L205_118_stage_inject_timeout(
        self, sut, mock_project_id, mock_l2_02
    ) -> None:
        def slow(*_a, **_kw):
            time.sleep(2.5)

        mock_l2_02.reverse_recall.side_effect = slow
        t0 = time.perf_counter()
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
            ),
            e2e_timeout_s=2.0,
        )
        assert (time.perf_counter() - t0) < 3.0

    def test_TC_L106_L205_119_l101_push_fail_retry(
        self, sut, mock_project_id, mock_l1_01
    ) -> None:
        call = [0]

        def _flaky(*_a, **_kw):
            call[0] += 1
            if call[0] == 1:
                raise TimeoutError("L1-01")
            return MagicMock(accepted=True, context_id="c", rejection_reason=None)

        mock_l1_01.push_context.side_effect = _flaky
        resp = sut._push_to_l101(
            project_id=mock_project_id,
            injection_id="i",
            stage="S3",
            entries=[],
            trace_id="t",
        )
        assert resp.accepted is True
        assert call[0] == 2

    def test_TC_L106_L205_120_duplicate_event_idempotent(
        self, sut, mock_project_id
    ) -> None:
        evt = StageTransitionedEvent(
            event_id="same-evt",
            event_type="L1-02:stage_transitioned",
            project_id=mock_project_id,
            stage_from="S2",
            stage_to="S3",
            transition_reason="gate",
            transition_at="2026-04-22T10:00:00Z",
            trace_id="t",
        )
        sut.on_stage_transitioned(evt)
        sut.on_stage_transitioned(evt)
        assert sut._duplicate_event_skipped_count >= 1
