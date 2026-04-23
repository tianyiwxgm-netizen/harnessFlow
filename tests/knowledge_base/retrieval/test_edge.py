"""L1-06 L2-05 · edge cases · 3-2 §9."""
from __future__ import annotations

import threading

from app.knowledge_base.retrieval.schemas import RerankContext, RerankRequest


class TestL2_05_Edge:

    def test_TC_L106_L205_901_single_candidate(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r",
                candidates=make_candidates(1),
                context=RerankContext(
                    current_stage="S3", task_type="c", tech_stack=["python"]
                ),
                top_k=5,
                trace_id="t",
            )
        )
        assert len(resp.entries) == 1

    def test_TC_L106_L205_902_top_k_equals_candidate_count(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r",
                candidates=make_candidates(5),
                context=RerankContext(
                    current_stage="S3", task_type="c", tech_stack=["python"]
                ),
                top_k=5,
                trace_id="t",
            )
        )
        assert len(resp.entries) == 5

    def test_TC_L106_L205_903_all_same_score_stable_sort(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        cands = make_candidates(10)
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r",
                candidates=cands,
                context=RerankContext(
                    current_stage="S3", task_type="c", tech_stack=["python"]
                ),
                top_k=10,
                trace_id="t",
            )
        )
        resp2 = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r-2",
                candidates=cands,
                context=RerankContext(
                    current_stage="S3", task_type="c", tech_stack=["python"]
                ),
                top_k=10,
                trace_id="t",
            )
        )
        assert [e.entry_id for e in resp.entries] == [
            e.entry_id for e in resp2.entries
        ]

    def test_TC_L106_L205_904_very_large_1k_candidates(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        resp = sut.rerank(
            RerankRequest(
                project_id=mock_project_id,
                rerank_id="r",
                candidates=make_candidates(1000),
                context=RerankContext(
                    current_stage="S3", task_type="c", tech_stack=["python"]
                ),
                top_k=10,
                trace_id="t",
            )
        )
        assert resp.status == "success"
        assert len(resp.entries) == 10

    def test_TC_L106_L205_905_concurrent_rerank_50(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        cands = make_candidates(20)
        ctx = RerankContext(
            current_stage="S3", task_type="c", tech_stack=["python"]
        )
        errs: list[Exception] = []

        def _run(i: int) -> None:
            try:
                sut.rerank(
                    RerankRequest(
                        project_id=mock_project_id,
                        rerank_id=f"c-{i}",
                        candidates=cands,
                        context=ctx,
                        top_k=5,
                        trace_id="t",
                    )
                )
            except Exception as e:
                errs.append(e)

        ts = [threading.Thread(target=_run, args=(i,)) for i in range(50)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        assert not errs
