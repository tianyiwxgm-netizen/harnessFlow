"""L1-06 L2-02 · integration (2 TC) · 3-2 §8."""
from __future__ import annotations

from app.knowledge_base.reader.schemas import ApplicableContext, ReadRequest
from app.knowledge_base.reader.service import KBReadService


class TestL2_02_Integration:

    def test_TC_L106_L202_801_l1_01_decision_loop_injection(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed(session=3, project=3, global_=3)
        req = ReadRequest(
            trace_id="tick-1",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(route="S4"),
            top_k=3,
            cache_enabled=True,
        )
        sut.read(req)
        r2 = sut.read(req)
        r3 = sut.read(req)
        assert r2.meta.cache_hit
        assert r3.meta.cache_hit

    def test_TC_L106_L202_802_with_l2_03_session_writes_visible_next_read(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        req = ReadRequest(
            trace_id="next",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=5,
            cache_enabled=True,
        )
        fake_repo.seed(session=1)
        r1 = sut.read(req)
        fake_repo.seed(session=2)
        sut._tick_cache.invalidate_on_write()
        r2 = sut.read(req)
        assert len(r2.entries) >= len(r1.entries)
