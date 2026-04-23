"""L1-06 L2-01 · IC contract integration tests · 3-2 §4."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.l1_06.l2_01.schemas import (
    ActivateEvent,
    ExpireScanTrigger,
    PromotionRequest,
    ScopeDecisionRequest,
    WriteSlotRequest,
)
from app.l1_06.l2_01.tier_manager import TierManager


def _emitted_event_types(bus: MagicMock) -> list[str]:
    out: list[str] = []
    for call in bus.append.call_args_list:
        et = call.kwargs.get("event_type")
        if et is None and call.args:
            et = call.args[0]
        if et is not None:
            out.append(et)
    return out


class TestL2_01_IC_Contracts:

    def test_TC_L106_L201_601_ic_l2_01_consumed_by_l2_02(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str
    ) -> None:
        req = ScopeDecisionRequest(
            request_id="r-ic1",
            project_id=mock_project_id,
            session_id=mock_session_id,
            kind_filter=["pattern"],
            requester_bc="BC-01",
        )
        resp = sut.resolve_read_scope(req)
        for f in (
            "request_id",
            "verdict",
            "allowed_scopes",
            "isolation_context",
            "tier_paths",
            "expired_exclusion_ts",
            "emitted_at",
        ):
            assert hasattr(resp, f), f"contract missing field {f}"
        assert resp.request_id == req.request_id

    def test_TC_L106_L201_602_ic_l2_02_consumed_by_l2_03(
        self,
        sut: TierManager,
        mock_project_id: str,
        mock_session_id: str,
        make_entry_candidate,
    ) -> None:
        cand = make_entry_candidate(kind="pattern", title="ic-602")
        slot = sut.allocate_session_write_slot(
            WriteSlotRequest(
                request_id="w-ic2",
                project_id=mock_project_id,
                session_id=mock_session_id,
                entry_candidate=cand,
                requester_bc="BC-01",
            )
        )
        assert slot.deduplication_hint is not None
        assert slot.schema_validation is not None
        assert slot.kind_validation is not None

    def test_TC_L106_L201_603_ic_l2_03_consumed_by_l2_04(
        self, sut: TierManager, mock_project_id: str
    ) -> None:
        resp = sut.check_promotion_rule(
            PromotionRequest(
                request_id="p-ic3",
                project_id=mock_project_id,
                entry_id="ent-ic3",
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
        assert resp.expected_write_path == f"projects/{mock_project_id}/kb/entries/"

    def test_TC_L106_L201_604_ic_l2_07_bg_scheduler_invocation(
        self, sut: TierManager, mock_event_bus: MagicMock
    ) -> None:
        sut._tier_repo.register_projects(["p-001"])
        trig = ExpireScanTrigger(
            trigger_id="sc-ic4",
            trigger_at="2026-04-22T03:00:00Z",
            scan_mode="all",
            ttl_days=7,
        )
        sut.run_expire_scan(trig)
        assert "L1-06:expire_scan_completed" in _emitted_event_types(mock_event_bus)

    def test_TC_L106_L201_605_ic_l2_activate_subscribed_from_bc_02(
        self, sut: TierManager, mock_event_bus: MagicMock
    ) -> None:
        evt = ActivateEvent(
            event_type="L1-02:project_created",
            project_id="p-ic5",
            project_name="IC",
            stage="S0_gate",
            created_at="2026-04-22T10:00:00Z",
            resumed_from_snapshot=False,
        )
        sut.on_project_activated(evt)
        assert "L1-06:kb_tier_ready" in _emitted_event_types(mock_event_bus)

    def test_TC_L106_L201_606_ic_09_append_event_sink(
        self, sut: TierManager, mock_event_bus: MagicMock
    ) -> None:
        sut._emit_kb_tier_ready(
            project_id="p-006",
            session_path="x",
            project_path="y",
            global_path="z",
            tier_ready_flag="f",
            activated_at="t",
        )
        assert mock_event_bus.append.called
