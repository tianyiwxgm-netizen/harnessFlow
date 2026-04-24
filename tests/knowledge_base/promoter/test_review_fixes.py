"""L1-06 L2-04 · Review fix tests · 2026-04-23 B-1 (HIGH).

Tests for the HIGH issue raised in
`docs/superpowers/reviews/2026-04-23-Dev-β-wp03-06-review.md`:

* **B-1 (HIGH)** — WRITE_TARGET_FAIL must NOT permanently blacklist an entry via
  `mark_rejected`. Transient storage errors should be retryable.

Additional MEDIUM fixes (A-2 ApprovalGate, D-3 batch manifest cache) are
implemented as follow-up commits in this branch; their TCs live in the same
file and are added incrementally.
"""
from __future__ import annotations

from app.knowledge_base.promoter.errors import PromoterErrorCode
from app.knowledge_base.promoter.promotion_executor import (
    InMemoryTargetStore,
    PromotionExecutor,
)
from app.knowledge_base.promoter.schemas import PromoteTarget


# ===========================================================================
# B-1 · WRITE_TARGET_FAIL transient storage error must NOT mark_rejected
# ===========================================================================


class _FlakyTargetStore(InMemoryTargetStore):
    """TargetStore that can be configured to raise on write_project/write_global."""

    def __init__(self, *, raise_on_write: type[Exception] | None = None) -> None:
        super().__init__()
        self._raise_on_write = raise_on_write
        self._write_attempts = 0

    def write_project(self, project_id, entry):
        self._write_attempts += 1
        if self._raise_on_write is not None:
            raise self._raise_on_write("simulated storage failure")
        super().write_project(project_id, entry)

    def write_global(self, entry):
        self._write_attempts += 1
        if self._raise_on_write is not None:
            raise self._raise_on_write("simulated storage failure")
        super().write_global(entry)


class TestB1WriteTargetFailDoesNotMarkRejected:
    """B-1 · infra failure must be retryable, not permanently blacklisted."""

    def test_TC_L106_L204_B1_401_oserror_on_write_does_not_mark_rejected(
        self,
        mock_observer,
        mock_event_bus,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        """OSError (transient disk full / IO error) MUST NOT mark_rejected."""
        src = make_source_entry(entry_id="kbe-w1", observed_count=2)
        mock_observer._entries_by_project[mock_project_id] = [src]

        store = _FlakyTargetStore(raise_on_write=OSError)
        sut = PromotionExecutor(
            observer=mock_observer,
            event_bus=mock_event_bus,
            target_store=store,
        )

        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="kbe-w1",
                    from_scope="session",
                    to_scope="project",
                    reason="auto_threshold",
                )
            )
        )

        # The ceremony completed with an error verdict — no hard blacklist
        assert resp.single_result is not None
        assert resp.single_result.verdict == "error", (
            "WRITE_TARGET_FAIL on infra error must yield verdict='error', "
            "not 'rejected' (REJECTED_CANNOT_UNDO is irreversible)"
        )
        assert (
            resp.single_result.reason_code
            == PromoterErrorCode.WRITE_TARGET_FAIL.value
        )
        # Entry must not be in the rejected-cannot-undo set
        assert not store.is_rejected(mock_project_id, "kbe-w1"), (
            "transient infra failure MUST NOT populate the rejected blacklist"
        )

    def test_TC_L106_L204_B1_402_ioerror_on_write_does_not_mark_rejected(
        self,
        mock_observer,
        mock_event_bus,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        """IOError is an alias for OSError → must be treated as infra failure."""
        src = make_source_entry(entry_id="kbe-w2", observed_count=2)
        mock_observer._entries_by_project[mock_project_id] = [src]

        store = _FlakyTargetStore(raise_on_write=IOError)
        sut = PromotionExecutor(
            observer=mock_observer,
            event_bus=mock_event_bus,
            target_store=store,
        )

        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="kbe-w2",
                    from_scope="session",
                    to_scope="project",
                    reason="auto_threshold",
                )
            )
        )
        assert resp.single_result.verdict == "error"
        assert not store.is_rejected(mock_project_id, "kbe-w2")

    def test_TC_L106_L204_B1_403_timeouterror_on_write_does_not_mark_rejected(
        self,
        mock_observer,
        mock_event_bus,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        """TimeoutError on storage write is infra failure → retryable."""
        src = make_source_entry(entry_id="kbe-w3", observed_count=2)
        mock_observer._entries_by_project[mock_project_id] = [src]

        store = _FlakyTargetStore(raise_on_write=TimeoutError)
        sut = PromotionExecutor(
            observer=mock_observer,
            event_bus=mock_event_bus,
            target_store=store,
        )

        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="kbe-w3",
                    from_scope="session",
                    to_scope="project",
                    reason="auto_threshold",
                )
            )
        )
        assert resp.single_result.verdict == "error"
        assert not store.is_rejected(mock_project_id, "kbe-w3")

    def test_TC_L106_L204_B1_404_retry_after_transient_failure_succeeds(
        self,
        mock_observer,
        mock_event_bus,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        """After a transient write failure, a retry must succeed.

        This is the core production-correctness property: a flaky disk or
        a briefly-unreachable storage backend must not permanently block
        the entry from being promoted on retry.
        """
        src = make_source_entry(entry_id="kbe-w4", observed_count=2)
        mock_observer._entries_by_project[mock_project_id] = [src]

        # First attempt raises OSError
        store = _FlakyTargetStore(raise_on_write=OSError)
        sut = PromotionExecutor(
            observer=mock_observer,
            event_bus=mock_event_bus,
            target_store=store,
        )
        r1 = sut.kb_promote(
            make_promote_request(
                request_id="retry-attempt-1",
                target=PromoteTarget(
                    entry_id="kbe-w4",
                    from_scope="session",
                    to_scope="project",
                    reason="auto_threshold",
                ),
            )
        )
        assert r1.single_result.verdict == "error"

        # Now storage recovers → a retry must succeed
        store._raise_on_write = None
        r2 = sut.kb_promote(
            make_promote_request(
                request_id="retry-attempt-2",
                target=PromoteTarget(
                    entry_id="kbe-w4",
                    from_scope="session",
                    to_scope="project",
                    reason="auto_threshold",
                ),
            )
        )
        assert r2.single_result.verdict == "promoted", (
            "retry after infra recovery MUST promote successfully; "
            "current bug permanently blacklists via mark_rejected"
        )
        assert r2.single_result.promotion_id is not None
        # And the entry was actually written
        assert len(store.list_project(mock_project_id)) == 1

    def test_TC_L106_L204_B1_405_content_rejection_still_marks_rejected(
        self,
        sut,
        target_store,
        mock_observer,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        """Content rejections (invalid reason, skip-layer, ...) MUST still
        populate the rejected-cannot-undo blacklist per §11.4.
        """
        src = make_source_entry(entry_id="kbe-reject-content", observed_count=2)
        mock_observer._entries_by_project[mock_project_id] = [src]

        # Use invalid_reason → triggers INVALID_FROM_TO content rejection
        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="kbe-reject-content",
                    from_scope="session",
                    to_scope="project",
                    reason="invalid_reason",
                )
            )
        )
        assert resp.single_result.verdict == "rejected"
        # Content rejection DOES populate blacklist (undo-proof per design)
        assert target_store.is_rejected(mock_project_id, "kbe-reject-content")

        # A retry with valid params must STILL be blocked
        r2 = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="kbe-reject-content",
                    from_scope="session",
                    to_scope="project",
                    reason="auto_threshold",
                )
            )
        )
        assert (
            r2.single_result.reason_code
            == PromoterErrorCode.REJECTED_CANNOT_UNDO.value
        )

    def test_TC_L106_L204_B1_406_write_global_infra_failure_retryable(
        self,
        mock_observer,
        mock_event_bus,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        """write_global path must also be retryable on infra failure."""
        src = make_source_entry(entry_id="kbe-g1", observed_count=3)
        mock_observer._entries_by_project[mock_project_id] = [src]

        store = _FlakyTargetStore(raise_on_write=OSError)
        sut = PromotionExecutor(
            observer=mock_observer,
            event_bus=mock_event_bus,
            target_store=store,
        )

        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="kbe-g1",
                    from_scope="project",
                    to_scope="global",
                    reason="auto_threshold",
                )
            )
        )
        assert resp.single_result.verdict == "error"
        assert not store.is_rejected(mock_project_id, "kbe-g1")
