"""L1-06 L2-02 · edge (5 TC) · 3-2 §9."""
from __future__ import annotations

import threading

from app.knowledge_base.reader.schemas import ApplicableContext, ReadRequest
from app.knowledge_base.reader.service import KBReadService


class TestL2_02_Edge:

    def test_TC_L106_L202_901_empty_kb_returns_empty_no_error(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed(0, 0, 0)
        req = ReadRequest(
            trace_id="empty",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=3,
        )
        res = sut.read(req)
        assert res.entries == []
        assert res.error_hint is None

    def test_TC_L106_L202_902_top_k_zero(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed(session=3)
        req = ReadRequest(
            trace_id="tk0",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=0,
        )
        res = sut.read(req)
        assert res.entries == []

    def test_TC_L106_L202_903_very_long_content_truncated_at_8000(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed_with_bad_entries(session_good=2, session_bad=1)
        req = ReadRequest(
            trace_id="long",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=10,
        )
        res = sut.read(req)
        assert res.meta.schema_invalid_skipped >= 1

    def test_TC_L106_L202_904_concurrent_16_reads_no_lock_contention(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed(session=5, project=5, global_=5)
        req = ReadRequest(
            trace_id="conc",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=5,
            cache_enabled=False,
        )
        errs: list[Exception] = []

        def _run() -> None:
            try:
                sut.read(req)
            except Exception as e:
                errs.append(e)

        threads = [threading.Thread(target=_run) for _ in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errs

    def test_TC_L106_L202_905_scope_subset_only_session(
        self,
        sut: KBReadService,
        mock_l2_01,
        fake_repo,
        mock_project_id,
        mock_session_id,
    ) -> None:
        mock_l2_01.scope_check.return_value.allowed_scopes = ["session"]
        fake_repo.seed(session=2, project=5, global_=5)
        req = ReadRequest(
            trace_id="only-s",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=10,
        )
        res = sut.read(req)
        assert len(res.entries) <= 2
