"""L1-06 L2-01 · negative tests · 12 error codes (3-2 §3)."""
from __future__ import annotations

import pytest

from app.l1_06.l2_01.errors import TierError
from app.l1_06.l2_01.schemas import (
    PromotionRequest,
    ScopeDecisionRequest,
    WriteSlotRequest,
)
from app.l1_06.l2_01.tier_manager import TierManager


class TestL2_01_Negative:

    def test_TC_L106_L201_101_tier_not_activated(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str
    ) -> None:
        """E-TIER-001 · no .tier-ready.flag → DENY."""
        sut._tier_repo.set_tier_ready(mock_project_id, project=False, global_=False)
        req = ScopeDecisionRequest(
            request_id="r",
            project_id=mock_project_id,
            session_id=mock_session_id,
            requester_bc="BC-01",
        )
        resp = sut.resolve_read_scope(req)
        assert resp.verdict == "DENY"
        assert resp.error_code == "E-TIER-001"

    def test_TC_L106_L201_102_cross_project_read_denied(
        self, sut: TierManager
    ) -> None:
        """E-TIER-002 · accessor ≠ owner on Project tier."""
        sut._tier_repo.set_tier_ready("p-B", project=True, global_=True)
        sut._session_idx.register_session("p-A", "s-a")
        sut._tier_repo.set_tier_ready("p-A", project=True, global_=True)
        # force the isolation enforcer to see accessor=p-A, target_owner=p-B
        sut._isolation.force_cross_project("p-A", "p-B")
        req = ScopeDecisionRequest(
            request_id="r",
            project_id="p-A",
            session_id="s-a",
            requester_bc="BC-01",
        )
        resp = sut.resolve_read_scope(req)
        assert resp.verdict == "DENY"
        assert resp.error_code == "E-TIER-002"

    def test_TC_L106_L201_103_invalid_kind(
        self,
        sut: TierManager,
        mock_project_id: str,
        mock_session_id: str,
        make_entry_candidate,
    ) -> None:
        """E-TIER-003 · kind='hotfix' not in whitelist."""
        cand = make_entry_candidate(kind="hotfix", title="invalid")
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
        assert slot.error_code == "E-TIER-003"
        assert slot.kind_validation.passed is False

    def test_TC_L106_L201_104_schema_violation(
        self,
        sut: TierManager,
        mock_project_id: str,
        mock_session_id: str,
        make_entry_candidate,
    ) -> None:
        """E-TIER-004 · empty content fails schema."""
        cand = make_entry_candidate(kind="pattern", title="t", content="")
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
        assert slot.schema_validation.passed is False
        assert any(v.field == "content" for v in slot.schema_validation.violations)

    def test_TC_L106_L201_105_wrong_scope_for_write(
        self,
        sut: TierManager,
        mock_project_id: str,
        mock_session_id: str,
        make_entry_candidate,
    ) -> None:
        """E-TIER-005 · entry_candidate.scope=project → DENY."""
        cand = make_entry_candidate(kind="pattern", title="direct-write", scope="project")
        slot = sut.allocate_session_write_slot(
            WriteSlotRequest(
                request_id="w",
                project_id=mock_project_id,
                session_id=mock_session_id,
                entry_candidate=cand,
                requester_bc="BC-01",
            )
        )
        assert slot.error_code == "E-TIER-005"

    def test_TC_L106_L201_106_promotion_skip_level(
        self, sut: TierManager, mock_project_id: str
    ) -> None:
        """E-TIER-006 · session → global DENY."""
        resp = sut.check_promotion_rule(
            PromotionRequest(
                request_id="p",
                project_id=mock_project_id,
                entry_id="ent-1",
                from_scope="session",
                to_scope="global",
                observed_count=5,
                approval={
                    "type": "user_explicit",
                    "approver": "user:alice",
                    "approved_at": "2026-04-22T10:00:00Z",
                },
                requester_bc="BC-07",
            )
        )
        assert resp.verdict == "DENY"
        assert resp.reason_code == "SKIP_LEVEL"
        assert resp.error_code == "E-TIER-006"

    def test_TC_L106_L201_107_promotion_below_threshold(
        self, sut: TierManager, mock_project_id: str
    ) -> None:
        """E-TIER-007 · observed_count=1 < 2."""
        resp = sut.check_promotion_rule(
            PromotionRequest(
                request_id="p",
                project_id=mock_project_id,
                entry_id="ent-2",
                from_scope="session",
                to_scope="project",
                observed_count=1,
                approval={
                    "type": "auto",
                    "approver": "system",
                    "approved_at": "2026-04-22T10:00:00Z",
                },
                requester_bc="BC-07",
            )
        )
        assert resp.reason_code == "BELOW_THRESHOLD"
        assert resp.error_code == "E-TIER-007"

    def test_TC_L106_L201_108_promotion_missing_approval(
        self, sut: TierManager, mock_project_id: str
    ) -> None:
        """E-TIER-008 · project → global without user_explicit."""
        resp = sut.check_promotion_rule(
            PromotionRequest(
                request_id="p",
                project_id=mock_project_id,
                entry_id="ent-3",
                from_scope="project",
                to_scope="global",
                observed_count=5,
                approval={
                    "type": "auto",
                    "approver": "system",
                    "approved_at": "2026-04-22T10:00:00Z",
                },
                requester_bc="BC-07",
            )
        )
        assert resp.reason_code == "MISSING_APPROVAL"
        assert resp.error_code == "E-TIER-008"

    def test_TC_L106_L201_109_expired_entry_access(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str
    ) -> None:
        """E-TIER-009 · old last_observed_at landed in post-filter audit log."""
        sut._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
        old_ts = "2026-04-10T00:00:00+00:00"
        sut._session_idx.add_entry(
            project_id=mock_project_id,
            session_id=mock_session_id,
            entry_id="ent-expired",
            last_observed_at=old_ts,
        )
        sut.resolve_read_scope(
            ScopeDecisionRequest(
                request_id="r",
                project_id=mock_project_id,
                session_id=mock_session_id,
                requester_bc="BC-01",
            )
        )
        assert "ent-expired" in sut._audit.expired_post_filter_log

    def test_TC_L106_L201_110_path_resolution_fail(
        self, sut: TierManager
    ) -> None:
        """E-TIER-010 · illegal project_id (path traversal attempt)."""
        resp = sut.resolve_read_scope(
            ScopeDecisionRequest(
                request_id="r",
                project_id="p/../etc",
                session_id="s-1",
                requester_bc="BC-01",
            )
        )
        assert resp.verdict == "DENY"
        assert resp.error_code == "E-TIER-010"

    def test_TC_L106_L201_111_tier_registry_corrupt(
        self, sut: TierManager, corrupt_yaml
    ) -> None:
        """E-TIER-011 · tier-layout.yaml parse error → lockdown."""
        corrupt_yaml("configs/tier-layout.yaml")
        with pytest.raises(TierError) as exc:
            sut._tier_repo.reload()
        assert exc.value.code == "E-TIER-011"
        assert sut._degradation_level == "EMERGENCY_LOCKDOWN"

    def test_TC_L106_L201_112_session_id_not_found(
        self, sut: TierManager, mock_project_id: str
    ) -> None:
        """E-TIER-012 · session_id not registered to project."""
        sut._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
        resp = sut.resolve_read_scope(
            ScopeDecisionRequest(
                request_id="r",
                project_id=mock_project_id,
                session_id="s-UNKNOWN-999",
                requester_bc="BC-01",
            )
        )
        assert resp.error_code == "E-TIER-012"
