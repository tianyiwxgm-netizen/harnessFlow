"""L1-06 L2-01 · edge cases · 3-2 §9."""
from __future__ import annotations

import contextlib
import threading

from app.knowledge_base.tier_manager.schemas import (
    ActivateEvent,
    ScopeDecisionRequest,
    WriteSlotRequest,
)
from app.knowledge_base.tier_manager.tier_manager import TierManager


class TestL2_01_EdgeCases:

    def test_TC_L106_L201_901_empty_kind_filter_means_all(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str
    ) -> None:
        sut._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
        resp = sut.resolve_read_scope(
            ScopeDecisionRequest(
                request_id="r",
                project_id=mock_project_id,
                session_id=mock_session_id,
                kind_filter=[],
                requester_bc="BC-01",
            )
        )
        assert resp.verdict == "ALLOW"

    def test_TC_L106_L201_902_extra_large_content_10mb_schema_rejects(
        self,
        sut: TierManager,
        mock_project_id: str,
        mock_session_id: str,
        make_entry_candidate,
    ) -> None:
        cand = make_entry_candidate(
            kind="pattern", title="big", content="x" * (10 * 1024 * 1024)
        )
        slot = sut.allocate_session_write_slot(
            WriteSlotRequest(
                request_id="w",
                project_id=mock_project_id,
                session_id=mock_session_id,
                entry_candidate=cand,
                requester_bc="BC-01",
            )
        )
        assert slot.verdict == "DENY"
        assert slot.error_code == "E-TIER-004"

    def test_TC_L106_L201_903_concurrent_activate_idempotent_flag_write(
        self, sut: TierManager
    ) -> None:
        evt = ActivateEvent(
            event_type="L1-02:project_created",
            project_id="p-concurrent",
            project_name="C",
            stage="S0_gate",
            created_at="2026-04-22T10:00:00Z",
            resumed_from_snapshot=False,
        )
        errs: list[Exception] = []

        def _run() -> None:
            try:
                sut.on_project_activated(evt)
            except Exception as e:  # pragma: no cover - only on failure
                errs.append(e)

        threads = [threading.Thread(target=_run) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errs, f"concurrent activate raised: {errs}"

    def test_TC_L106_L201_904_eventbus_timeout_degrades_to_read_only_isolation(
        self, sut: TierManager, mock_event_bus
    ) -> None:
        mock_event_bus.append.side_effect = TimeoutError("bus slow")
        evt = ActivateEvent(
            event_type="L1-02:project_created",
            project_id="p-to",
            project_name="T",
            stage="S0_gate",
            created_at="2026-04-22T10:00:00Z",
            resumed_from_snapshot=False,
        )
        for _ in range(6):
            with contextlib.suppress(TimeoutError):
                sut.on_project_activated(evt)
        assert sut._degradation_level in ("READ_ONLY_ISOLATION", "L1")
        buf = sut._fs_root / "projects" / "p-to" / "kb" / ".l201-emit-buffer.jsonl"
        assert buf.exists() or sut._buffer_in_mem

    def test_TC_L106_L201_905_session_id_null_rejected(
        self, sut: TierManager, mock_project_id: str
    ) -> None:
        resp = sut.resolve_read_scope(
            ScopeDecisionRequest(
                request_id="r",
                project_id=mock_project_id,
                session_id="",
                requester_bc="BC-01",
            )
        )
        assert resp.error_code == "E-TIER-012"
