"""L1-06 L2-04 · negative path tests · all key error codes."""
from __future__ import annotations

from app.knowledge_base.promoter.errors import PromoterErrorCode
from app.knowledge_base.promoter.schemas import (
    Approver,
    BatchScope,
    PromoteTarget,
)


class TestNegativeIC08:
    def test_TC_L106_L204_301_missing_project_id(
        self, sut, make_promote_request
    ) -> None:
        req = make_promote_request(
            project_id="",
            target=PromoteTarget(
                entry_id="kbe-1",
                from_scope="session",
                to_scope="project",
                reason="auto_threshold",
            ),
        )
        resp = sut.kb_promote(req)
        assert resp.success is False
        assert resp.error_code == PromoterErrorCode.PROJECT_ID_MISSING.value

    def test_TC_L106_L204_302_skip_layer_denied_session_to_global(
        self,
        sut,
        mock_observer,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        src = make_source_entry(entry_id="e1", observed_count=5)
        mock_observer._entries_by_project[mock_project_id] = [src]
        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="e1",
                    from_scope="session",
                    to_scope="global",
                    reason="user_approved",
                    approver=Approver(user_id="u1"),
                )
            )
        )
        assert resp.single_result.verdict == "rejected"
        assert resp.single_result.reason_code == PromoterErrorCode.SKIP_LAYER_DENIED.value

    def test_TC_L106_L204_303_user_approved_missing_user_id(
        self, sut, make_promote_request
    ) -> None:
        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="e1",
                    from_scope="session",
                    to_scope="project",
                    reason="user_approved",
                    approver=None,
                )
            )
        )
        assert resp.single_result.verdict == "rejected"
        assert (
            resp.single_result.reason_code
            == PromoterErrorCode.USER_APPROVAL_MISSING.value
        )

    def test_TC_L106_L204_304_invalid_reason(
        self, sut, make_promote_request
    ) -> None:
        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="e1",
                    from_scope="session",
                    to_scope="project",
                    reason="invalid_reason",
                )
            )
        )
        assert resp.single_result.verdict == "rejected"
        assert resp.single_result.reason_code == PromoterErrorCode.INVALID_FROM_TO.value

    def test_TC_L106_L204_305_invalid_from_scope(
        self, sut, make_promote_request
    ) -> None:
        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="e1",
                    from_scope="global",
                    to_scope="project",
                    reason="auto_threshold",
                )
            )
        )
        assert resp.single_result.reason_code == PromoterErrorCode.INVALID_FROM_TO.value

    def test_TC_L106_L204_306_source_not_found(
        self, sut, mock_observer, make_promote_request, mock_project_id
    ) -> None:
        mock_observer._entries_by_project[mock_project_id] = []  # empty
        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="does-not-exist",
                    from_scope="session",
                    to_scope="project",
                    reason="auto_threshold",
                )
            )
        )
        assert resp.single_result.reason_code == PromoterErrorCode.SOURCE_NOT_FOUND.value

    def test_TC_L106_L204_307_project_threshold_unmet(
        self,
        sut,
        mock_observer,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        src = make_source_entry(entry_id="e1", observed_count=1)
        mock_observer._entries_by_project[mock_project_id] = [src]
        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="e1",
                    from_scope="session",
                    to_scope="project",
                    reason="auto_threshold",
                )
            )
        )
        assert resp.single_result.verdict == "kept"
        assert (
            resp.single_result.reason_code
            == PromoterErrorCode.PROJECT_THRESHOLD_UNMET.value
        )

    def test_TC_L106_L204_308_global_threshold_unmet(
        self,
        sut,
        mock_observer,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        src = make_source_entry(entry_id="e2", observed_count=2)
        mock_observer._entries_by_project[mock_project_id] = [src]
        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="e2",
                    from_scope="project",
                    to_scope="global",
                    reason="auto_threshold",
                )
            )
        )
        assert resp.single_result.verdict == "kept"
        assert (
            resp.single_result.reason_code
            == PromoterErrorCode.GLOBAL_THRESHOLD_UNMET.value
        )

    def test_TC_L106_L204_309_rejected_cannot_undo(
        self,
        sut,
        mock_observer,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        src = make_source_entry(entry_id="e-rej", observed_count=2)
        mock_observer._entries_by_project[mock_project_id] = [src]
        # First: invalid reason → get REJECTED (auto-marks rejected)
        sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="e-rej",
                    from_scope="session",
                    to_scope="project",
                    reason="invalid_reason",
                )
            )
        )
        # Second: even a valid re-promote is blocked
        r2 = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="e-rej",
                    from_scope="session",
                    to_scope="project",
                    reason="auto_threshold",
                )
            )
        )
        assert r2.single_result.verdict == "rejected"
        assert (
            r2.single_result.reason_code
            == PromoterErrorCode.REJECTED_CANNOT_UNDO.value
        )

    def test_TC_L106_L204_310_pm14_entry_project_mismatch(
        self,
        sut,
        mock_observer,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        # entry belongs to another project
        src = make_source_entry(
            entry_id="e-x", observed_count=2, project_id="other-proj"
        )
        # snapshot fixture uses req.project_id, so put src under the requested pid
        mock_observer._entries_by_project[mock_project_id] = [src]
        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="e-x",
                    from_scope="session",
                    to_scope="project",
                    reason="auto_threshold",
                )
            )
        )
        assert resp.single_result.reason_code == PromoterErrorCode.PROJECT_ID_MISMATCH.value

    def test_TC_L106_L204_311_batch_pull_fail(
        self, sut, mock_observer, make_promote_request, mock_project_id
    ) -> None:
        mock_observer.provide_candidate_snapshot.side_effect = RuntimeError(
            "snapshot dead"
        )
        resp = sut.kb_promote(
            make_promote_request(mode="batch", batch_scope=BatchScope())
        )
        assert resp.success is False
        assert resp.error_code == PromoterErrorCode.CANDIDATE_PULL_FAIL.value

    def test_TC_L106_L204_312_batch_ceremony_lock(
        self,
        sut,
        mock_observer,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        # Simulate concurrent ceremony by manually pushing lock before call.
        sut._running_ceremonies.add(mock_project_id)
        try:
            resp = sut.kb_promote(
                make_promote_request(mode="batch", batch_scope=BatchScope())
            )
            assert resp.error_code == PromoterErrorCode.CEREMONY_ALREADY_RUNNING.value
        finally:
            sut._running_ceremonies.discard(mock_project_id)

    def test_TC_L106_L204_313_unknown_mode(
        self, sut, make_promote_request
    ) -> None:
        req = make_promote_request(mode="dance_party")
        resp = sut.kb_promote(req)
        assert resp.error_code == PromoterErrorCode.INVALID_FROM_TO.value

    def test_TC_L106_L204_314_single_missing_target(
        self, sut, make_promote_request
    ) -> None:
        resp = sut.kb_promote(make_promote_request(target=None))
        assert resp.error_code == PromoterErrorCode.INVALID_FROM_TO.value

    def test_TC_L106_L204_315_no_observer_batch_fails(
        self, mock_event_bus, target_store, make_promote_request
    ) -> None:
        """Batch without observer → candidate pull fails cleanly."""
        from app.knowledge_base.promoter.promotion_executor import (
            PromotionExecutor,
        )

        sut = PromotionExecutor(
            observer=None,
            event_bus=mock_event_bus,
            target_store=target_store,
        )
        resp = sut.kb_promote(
            make_promote_request(mode="batch", batch_scope=BatchScope())
        )
        assert resp.error_code == PromoterErrorCode.CANDIDATE_PULL_FAIL.value
