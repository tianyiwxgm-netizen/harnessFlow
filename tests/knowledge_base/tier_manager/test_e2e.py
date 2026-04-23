"""L1-06 L2-01 · e2e · 3-2 §6."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.knowledge_base.tier_manager.schemas import (
    ActivateEvent,
    ExpireScanTrigger,
    PromotionRequest,
    ScopeDecisionRequest,
    WriteSlotRequest,
)
from app.knowledge_base.tier_manager.tier_manager import TierManager


def _emitted(bus: MagicMock) -> list[str]:
    out: list[str] = []
    for call in bus.append.call_args_list:
        et = call.kwargs.get("event_type")
        if et is None and call.args:
            et = call.args[0]
        if et is not None:
            out.append(et)
    return out


@pytest.mark.e2e
class TestL2_01_E2E:

    def test_TC_L106_L201_701_activate_then_read_then_write(
        self, sut: TierManager
    ) -> None:
        sut.on_project_activated(
            ActivateEvent(
                event_type="L1-02:project_created",
                project_id="p-e2e",
                project_name="E2E",
                stage="S0_gate",
                created_at="2026-04-22T10:00:00Z",
                resumed_from_snapshot=False,
            )
        )
        sut._session_idx.register_session("p-e2e", "s-1")
        scope = sut.resolve_read_scope(
            ScopeDecisionRequest(
                request_id="r",
                project_id="p-e2e",
                session_id="s-1",
                requester_bc="BC-01",
            )
        )
        assert scope.verdict == "ALLOW"
        assert "project" in scope.allowed_scopes

    def test_TC_L106_L201_702_session_write_then_promote_to_project(
        self, sut: TierManager, make_entry_candidate
    ) -> None:
        sut.on_project_activated(
            ActivateEvent(
                event_type="L1-02:project_created",
                project_id="p-prom",
                project_name="P",
                stage="S0_gate",
                created_at="2026-04-22T10:00:00Z",
                resumed_from_snapshot=False,
            )
        )
        sut._session_idx.register_session("p-prom", "s-1")
        cand = make_entry_candidate(kind="pattern", title="recurring")
        sut.allocate_session_write_slot(
            WriteSlotRequest(
                request_id="w1",
                project_id="p-prom",
                session_id="s-1",
                entry_candidate=cand,
                requester_bc="BC-01",
            )
        )
        slot2 = sut.allocate_session_write_slot(
            WriteSlotRequest(
                request_id="w2",
                project_id="p-prom",
                session_id="s-1",
                entry_candidate=cand,
                requester_bc="BC-01",
            )
        )
        assert slot2.deduplication_hint.merge_strategy == "increment_observed"
        resp = sut.check_promotion_rule(
            PromotionRequest(
                request_id="p",
                project_id="p-prom",
                entry_id=slot2.deduplication_hint.existing_entry_id or "x",
                from_scope="session",
                to_scope="project",
                observed_count=2,
                approval={
                    "type": "auto",
                    "approver": "system",
                    "approved_at": "2026-04-22T10:00:00Z",
                },
                requester_bc="BC-07",
            )
        )
        assert resp.verdict == "ALLOW"

    def test_TC_L106_L201_703_expire_scan_end_to_end_with_emit(
        self, sut: TierManager, mock_event_bus: MagicMock, fake_fs_with_entries
    ) -> None:
        fake_fs_with_entries(
            project_count=2, entries_per_project=5, expired_count=2
        )
        sut._tier_repo.register_projects(["p-seed-000", "p-seed-001"])
        sut.run_expire_scan(
            ExpireScanTrigger(
                trigger_id="sc-e2e",
                trigger_at="2026-04-22T03:00:00Z",
                scan_mode="all",
                ttl_days=7,
            )
        )
        emitted = _emitted(mock_event_bus)
        assert "L1-06:expire_scan_completed" in emitted
        assert emitted.count("L1-06:kb_entry_expired") >= 2
