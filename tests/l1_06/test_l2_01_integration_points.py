"""L1-06 L2-01 · integration with sibling L2s · 3-2 §8."""
from __future__ import annotations

from app.l1_06.l2_01.schemas import (
    PromotionRequest,
    ScopeDecisionRequest,
    WriteSlotRequest,
)
from app.l1_06.l2_01.tier_manager import TierManager


class TestL2_01_Integration:

    def test_TC_L106_L201_801_l2_02_reads_use_allowed_scopes(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str
    ) -> None:
        sut._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
        resp = sut.resolve_read_scope(
            ScopeDecisionRequest(
                request_id="i1",
                project_id=mock_project_id,
                session_id=mock_session_id,
                requester_bc="BC-01",
            )
        )
        assert set(resp.allowed_scopes).issubset({"session", "project", "global"})

    def test_TC_L106_L201_802_l2_03_writes_follow_slot_path(
        self,
        sut: TierManager,
        mock_project_id: str,
        mock_session_id: str,
        make_entry_candidate,
    ) -> None:
        cand = make_entry_candidate(kind="pattern", title="integr")
        slot = sut.allocate_session_write_slot(
            WriteSlotRequest(
                request_id="i2",
                project_id=mock_project_id,
                session_id=mock_session_id,
                entry_candidate=cand,
                requester_bc="BC-01",
            )
        )
        assert slot.write_path.startswith("task-boards/")
        assert mock_project_id in slot.write_path

    def test_TC_L106_L201_803_l2_04_promotion_respects_target_tier_ready(
        self, sut: TierManager, mock_project_id: str
    ) -> None:
        sut._tier_repo.set_tier_ready(mock_project_id, project=False, global_=False)
        resp = sut.check_promotion_rule(
            PromotionRequest(
                request_id="i3",
                project_id=mock_project_id,
                entry_id="ent-x",
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
        assert resp.target_tier_ready is False
        assert resp.verdict == "DENY"
