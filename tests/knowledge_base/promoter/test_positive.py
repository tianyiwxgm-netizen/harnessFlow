"""L1-06 L2-04 · positive path tests for IC-08 kb_promote."""
from __future__ import annotations

from app.knowledge_base.promoter.schemas import (
    Approver,
    BatchScope,
    PromoteTarget,
)


class TestPositiveSingle:
    def test_TC_L106_L204_101_session_to_project_auto(
        self,
        sut,
        mock_observer,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        src = make_source_entry(entry_id="kbe-1", observed_count=2)
        mock_observer._entries_by_project[mock_project_id] = [src]
        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="kbe-1",
                    from_scope="session",
                    to_scope="project",
                    reason="auto_threshold",
                )
            )
        )
        assert resp.success is True
        assert resp.single_result.verdict == "promoted"
        assert resp.single_result.final_scope == "project"
        assert resp.single_result.promotion_id is not None

    def test_TC_L106_L204_102_project_to_global_auto(
        self,
        sut,
        mock_observer,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        src = make_source_entry(entry_id="kbe-2", observed_count=3)
        mock_observer._entries_by_project[mock_project_id] = [src]
        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="kbe-2",
                    from_scope="project",
                    to_scope="global",
                    reason="auto_threshold",
                )
            )
        )
        assert resp.single_result.verdict == "promoted"
        assert resp.single_result.final_scope == "global"

    def test_TC_L106_L204_103_user_approved_under_threshold(
        self,
        sut,
        mock_observer,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        src = make_source_entry(entry_id="kbe-3", observed_count=1)
        mock_observer._entries_by_project[mock_project_id] = [src]
        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="kbe-3",
                    from_scope="session",
                    to_scope="project",
                    reason="user_approved",
                    approver=Approver(user_id="u1"),
                )
            )
        )
        assert resp.single_result.verdict == "promoted"

    def test_TC_L106_L204_104_idempotency_same_source_same_scope(
        self,
        sut,
        mock_observer,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        src = make_source_entry(entry_id="kbe-4", observed_count=2)
        mock_observer._entries_by_project[mock_project_id] = [src]
        r1 = sut.kb_promote(
            make_promote_request(
                request_id="r1",
                target=PromoteTarget(
                    entry_id="kbe-4",
                    from_scope="session",
                    to_scope="project",
                    reason="auto_threshold",
                ),
            )
        )
        r2 = sut.kb_promote(
            make_promote_request(
                request_id="r2",
                target=PromoteTarget(
                    entry_id="kbe-4",
                    from_scope="session",
                    to_scope="project",
                    reason="auto_threshold",
                ),
            )
        )
        assert r1.single_result.promotion_id == r2.single_result.promotion_id
        assert r2.single_result.reason_code == "idempotent_replay"

    def test_TC_L106_L204_105_promoted_entry_stored(
        self,
        sut,
        target_store,
        mock_observer,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        src = make_source_entry(entry_id="kbe-5", observed_count=2, kind="trap")
        mock_observer._entries_by_project[mock_project_id] = [src]
        sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="kbe-5",
                    from_scope="session",
                    to_scope="project",
                    reason="auto_threshold",
                )
            )
        )
        project_entries = target_store.list_project(mock_project_id)
        assert len(project_entries) == 1
        assert project_entries[0].source_entry_id == "kbe-5"
        assert project_entries[0].kind == "trap"
        assert project_entries[0].scope == "project"


class TestPositiveBatch:
    def test_TC_L106_L204_201_batch_ceremony_promotes_all(
        self,
        sut,
        mock_observer,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        mock_observer._entries_by_project[mock_project_id] = [
            make_source_entry(entry_id="e1", observed_count=2),
            make_source_entry(entry_id="e2", observed_count=5),
        ]
        resp = sut.kb_promote(
            make_promote_request(
                mode="batch",
                trigger="s7_batch",
                batch_scope=BatchScope(),
            )
        )
        assert resp.success is True
        assert resp.batch_result is not None
        assert set(resp.batch_result.promoted) == {"e1", "e2"}
        assert resp.batch_result.candidates_total == 2
        assert resp.batch_result.ceremony_id.startswith("cer-")

    def test_TC_L106_L204_202_batch_kept_when_under_threshold(
        self,
        sut,
        mock_observer,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        # Under-threshold entries are filtered by snapshot min_observed_count=2,
        # so they don't appear in candidates and stay kept in session.
        mock_observer._entries_by_project[mock_project_id] = [
            make_source_entry(entry_id="e_low", observed_count=1),
            make_source_entry(entry_id="e_ok", observed_count=2),
        ]
        resp = sut.kb_promote(
            make_promote_request(mode="batch", batch_scope=BatchScope())
        )
        assert "e_ok" in resp.batch_result.promoted
        # e_low was filtered out by the snapshot → not in any bucket
        assert "e_low" not in resp.batch_result.promoted
        assert "e_low" not in resp.batch_result.kept

    def test_TC_L106_L204_203_batch_duration_recorded(
        self,
        sut,
        mock_observer,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        mock_observer._entries_by_project[mock_project_id] = [
            make_source_entry(entry_id="e1", observed_count=2)
        ]
        resp = sut.kb_promote(
            make_promote_request(mode="batch", batch_scope=BatchScope())
        )
        assert resp.batch_result.duration_ms >= 0
