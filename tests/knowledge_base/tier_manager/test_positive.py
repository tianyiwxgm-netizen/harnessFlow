"""L1-06 L2-01 · positive IC unit tests · 3-2 §2."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from app.knowledge_base.tier_manager.schemas import (
    ActivateEvent,
    ExpireScanTrigger,
    PromotionRequest,
    ScopeDecisionRequest,
    WriteSlotRequest,
)
from app.knowledge_base.tier_manager.tier_manager import TierManager


class TestL2_01_TierManager_Positive:
    """每个 public IC ≥ 1 正向用例。"""

    # ---- IC-L2-01 resolve_read_scope ----

    def test_TC_L106_L201_001_resolve_read_scope_session_only(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str
    ) -> None:
        sut._tier_repo.set_tier_ready(mock_project_id, project=False, global_=True)
        req = ScopeDecisionRequest(
            request_id="r-001",
            project_id=mock_project_id,
            session_id=mock_session_id,
            stage_hint="S2_split",
            requester_bc="BC-01",
        )
        resp = sut.resolve_read_scope(req)
        assert resp.verdict == "ALLOW"
        assert "session" in resp.allowed_scopes
        assert "project" not in resp.allowed_scopes
        assert resp.isolation_context is not None
        assert resp.isolation_context.accessor_pid == mock_project_id

    def test_TC_L106_L201_002_resolve_session_plus_project(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str
    ) -> None:
        sut._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
        req = ScopeDecisionRequest(
            request_id="r-002",
            project_id=mock_project_id,
            session_id=mock_session_id,
            stage_hint="S3_design",
            requester_bc="BC-01",
        )
        resp = sut.resolve_read_scope(req)
        assert resp.allowed_scopes == ["session", "project", "global"]
        assert resp.tier_paths is not None
        assert mock_project_id in resp.tier_paths.project
        assert "projects/" in resp.tier_paths.project

    def test_TC_L106_L201_003_resolve_all_three_tiers(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str
    ) -> None:
        sut._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
        resp = sut.resolve_read_scope(
            ScopeDecisionRequest(
                request_id="r-003",
                project_id=mock_project_id,
                session_id=mock_session_id,
                requester_bc="BC-07",
            )
        )
        assert resp.isolation_context is not None
        assert resp.isolation_context.global_layer == "no_owner"
        assert resp.tier_paths is not None
        assert resp.tier_paths.session.endswith(".kb.jsonl")
        assert "global_kb" in resp.tier_paths.global_

    def test_TC_L106_L201_004_resolve_kind_filter_subset(
        self, sut: TierManager, mock_project_id: str, mock_session_id: str
    ) -> None:
        sut._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
        resp = sut.resolve_read_scope(
            ScopeDecisionRequest(
                request_id="r-004",
                project_id=mock_project_id,
                session_id=mock_session_id,
                kind_filter=["pattern", "trap"],
                requester_bc="BC-01",
            )
        )
        assert resp.verdict == "ALLOW"
        assert "session" in resp.allowed_scopes

    def test_TC_L106_L201_005_resolve_expired_exclusion_ts(
        self,
        sut: TierManager,
        mock_project_id: str,
        mock_session_id: str,
        mock_clock: MagicMock,
    ) -> None:
        fixed = datetime(2026, 4, 22, 12, 0, tzinfo=UTC)
        mock_clock.now.return_value = fixed
        sut._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
        resp = sut.resolve_read_scope(
            ScopeDecisionRequest(
                request_id="r-005",
                project_id=mock_project_id,
                session_id=mock_session_id,
                requester_bc="BC-01",
            )
        )
        expected = (fixed - timedelta(days=7)).isoformat()
        assert resp.expired_exclusion_ts == expected

    # ---- IC-L2-02 allocate_session_write_slot ----

    def test_TC_L106_L201_006_allocate_new_entry(
        self,
        sut: TierManager,
        mock_project_id: str,
        mock_session_id: str,
        make_entry_candidate,
    ) -> None:
        cand = make_entry_candidate(kind="pattern", title="test-new")
        slot = sut.allocate_session_write_slot(
            WriteSlotRequest(
                request_id="w-001",
                project_id=mock_project_id,
                session_id=mock_session_id,
                entry_candidate=cand,
                requester_bc="BC-01",
            )
        )
        assert slot.verdict == "ALLOW"
        assert slot.deduplication_hint.merge_strategy == "new_entry"
        assert slot.write_path.endswith(".kb.jsonl")
        assert slot.schema_validation.passed is True
        assert slot.kind_validation.passed is True

    def test_TC_L106_L201_007_allocate_dedup_increment(
        self,
        sut: TierManager,
        mock_project_id: str,
        mock_session_id: str,
        make_entry_candidate,
    ) -> None:
        cand = make_entry_candidate(kind="pattern", title="dup-title")
        sut._session_idx.register(
            project_id=mock_project_id,
            session_id=mock_session_id,
            title=cand.title,
            kind=cand.kind,
            entry_id="ent-existing",
        )
        slot = sut.allocate_session_write_slot(
            WriteSlotRequest(
                request_id="w-002",
                project_id=mock_project_id,
                session_id=mock_session_id,
                entry_candidate=cand,
                requester_bc="BC-01",
            )
        )
        assert slot.deduplication_hint.existing_entry_id == "ent-existing"
        assert slot.deduplication_hint.merge_strategy == "increment_observed"

    def test_TC_L106_L201_008_allocate_schema_validates_8_kinds(
        self,
        sut: TierManager,
        mock_project_id: str,
        mock_session_id: str,
        make_entry_candidate,
    ) -> None:
        kinds = [
            "pattern",
            "trap",
            "recipe",
            "tool_combo",
            "anti_pattern",
            "project_context",
            "external_ref",
            "effective_combo",
        ]
        for k in kinds:
            cand = make_entry_candidate(kind=k, title=f"t-{k}")
            slot = sut.allocate_session_write_slot(
                WriteSlotRequest(
                    request_id=f"w-{k}",
                    project_id=mock_project_id,
                    session_id=mock_session_id,
                    entry_candidate=cand,
                    requester_bc="BC-01",
                )
            )
            assert slot.verdict == "ALLOW", f"kind={k} should pass"
            assert slot.kind_validation.passed is True

    # ---- IC-L2-03 check_promotion_rule ----

    def test_TC_L106_L201_009_promote_session_to_project_auto(
        self, sut: TierManager, mock_project_id: str
    ) -> None:
        resp = sut.check_promotion_rule(
            PromotionRequest(
                request_id="p-001",
                project_id=mock_project_id,
                entry_id="ent-100",
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
        assert resp.reason_code == "OK"
        assert resp.required_observed_count == 2
        assert mock_project_id in resp.expected_write_path

    def test_TC_L106_L201_010_promote_project_to_global_user_explicit(
        self, sut: TierManager, mock_project_id: str
    ) -> None:
        resp = sut.check_promotion_rule(
            PromotionRequest(
                request_id="p-002",
                project_id=mock_project_id,
                entry_id="ent-200",
                from_scope="project",
                to_scope="global",
                observed_count=3,
                approval={
                    "type": "user_explicit",
                    "approver": "user:alice",
                    "approved_at": "2026-04-22T11:00:00Z",
                },
                requester_bc="BC-07",
            )
        )
        assert resp.verdict == "ALLOW"
        assert resp.override_owner_project_id is None
        assert resp.required_observed_count == 3

    # ---- IC-L2-07 run_expire_scan ----

    def test_TC_L106_L201_011_expire_scan_all(
        self,
        sut: TierManager,
        mock_event_bus: MagicMock,
    ) -> None:
        sut._tier_repo.register_projects(["p-001", "p-002"])
        trig = ExpireScanTrigger(
            trigger_id="sc-001",
            trigger_at="2026-04-22T03:00:00Z",
            scan_mode="all",
            ttl_days=7,
        )
        summary = sut.run_expire_scan(trig)
        assert summary.scanned_project_count == 2
        emitted_types = _emitted_event_types(mock_event_bus)
        assert "L1-06:expire_scan_completed" in emitted_types

    def test_TC_L106_L201_012_expire_scan_single_project(
        self, sut: TierManager
    ) -> None:
        sut._tier_repo.register_projects(["p-001", "p-002"])
        trig = ExpireScanTrigger(
            trigger_id="sc-002",
            trigger_at="2026-04-22T03:00:00Z",
            scan_mode="single_project",
            target_project_id="p-001",
            ttl_days=7,
        )
        summary = sut.run_expire_scan(trig)
        assert summary.scanned_project_count == 1

    # ---- IC-L2-activate on_project_activated ----

    def test_TC_L106_L201_013_activate_new_project_emits_tier_ready(
        self, sut: TierManager, mock_event_bus: MagicMock
    ) -> None:
        evt = ActivateEvent(
            event_type="L1-02:project_created",
            project_id="p-NEW-001",
            project_name="Demo",
            stage="S0_gate",
            created_at="2026-04-22T10:00:00Z",
            resumed_from_snapshot=False,
        )
        sut.on_project_activated(evt)
        assert "L1-06:kb_tier_ready" in _emitted_event_types(mock_event_bus)

    def test_TC_L106_L201_014_activate_resumed_idempotent(
        self, sut: TierManager, mock_event_bus: MagicMock
    ) -> None:
        evt = ActivateEvent(
            event_type="L1-02:project_resumed",
            project_id="p-OLD-001",
            project_name="Old",
            stage="S3_design",
            created_at="2026-04-18T08:00:00Z",
            resumed_from_snapshot=True,
        )
        sut.on_project_activated(evt)
        sut.on_project_activated(evt)  # idempotent
        assert mock_event_bus.append.call_count >= 1

    # ---- Event emit payload checks ----

    def test_TC_L106_L201_015_emit_kb_tier_ready_payload(
        self, sut: TierManager, mock_event_bus: MagicMock
    ) -> None:
        sut._emit_kb_tier_ready(
            project_id="p-100",
            session_path="task-boards/p-100/",
            project_path="projects/p-100/kb/",
            global_path="global_kb/entries/",
            tier_ready_flag="projects/p-100/kb/.tier-ready.flag",
            activated_at="2026-04-22T10:00:00Z",
        )
        mock_event_bus.append.assert_called()
        payload = _last_payload(mock_event_bus)
        assert payload["project_id"] == "p-100"
        assert payload["tier_ready_flag"].endswith(".tier-ready.flag")

    def test_TC_L106_L201_016_emit_kb_entry_expired(
        self, sut: TierManager, mock_event_bus: MagicMock
    ) -> None:
        sut._emit_kb_entry_expired(
            project_id="p-100",
            entry_id="ent-EX-1",
            expired_at="2026-04-22T00:00:00Z",
        )
        mock_event_bus.append.assert_called()

    def test_TC_L106_L201_017_emit_cross_project_denied(
        self, sut: TierManager, mock_event_bus: MagicMock
    ) -> None:
        sut._emit_cross_project_denied(
            accessor_pid="p-100",
            owner_pid="p-200",
            request_id="r-XP-001",
        )
        payload = _last_payload(mock_event_bus)
        assert payload["accessor_pid"] == "p-100"
        assert payload["owner_pid"] == "p-200"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _emitted_event_types(bus: MagicMock) -> list[str]:
    out: list[str] = []
    for call in bus.append.call_args_list:
        et = call.kwargs.get("event_type")
        if et is None and call.args:
            et = call.args[0]
        if et is not None:
            out.append(et)
    return out


def _last_payload(bus: MagicMock) -> dict:
    call = bus.append.call_args
    payload = call.kwargs.get("payload")
    if payload is None:
        # payload is the last positional arg after event_type
        payload = call.args[-1] if call.args else {}
    return payload
