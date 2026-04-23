"""L1-06 L2-02 · e2e (3 TC) · 3-2 §6."""
from __future__ import annotations

import pytest

from app.knowledge_base.reader.schemas import ApplicableContext, ReadRequest
from app.knowledge_base.reader.service import KBReadService


@pytest.mark.e2e
class TestL2_02_E2E:

    def test_TC_L106_L202_701_l1_01_to_l2_02_to_l2_05_full(
        self, sut: KBReadService, mock_l2_01, mock_l2_05, fake_repo,
        mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed(session=2, project=3, global_=5)
        req = ReadRequest(
            trace_id="e2e-1",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(route="S4"),
            top_k=5,
        )
        res = sut.read(req)
        assert res.error_hint is None
        assert len(res.entries) == 5
        mock_l2_01.scope_check.assert_called_once()
        mock_l2_05.rerank.assert_called_once()

    def test_TC_L106_L202_702_reverse_recall_stage_changed_trigger(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed_for_stage("S3", ["pattern", "trap"], count=3)
        res = sut.reverse_recall(
            project_id=mock_project_id,
            session_id=mock_session_id,
            stage="S3",
            kinds=["pattern", "trap"],
            caller_identity="L2-05",
        )
        assert len(res) >= 3

    def test_TC_L106_L202_703_degraded_path_returns_empty_not_halt(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.fail_all_layers(OSError("all layers down"))
        req = ReadRequest(
            trace_id="e2e-3",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=5,
        )
        res = sut.read(req)
        assert res.entries == []
        assert res.error_hint == "kb_degraded"
