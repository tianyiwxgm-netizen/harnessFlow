"""L1-06 L2-04 · Review fix tests · 2026-04-23 B-1 (HIGH) + A-2/D-3 (MEDIUM).

Tests for issues raised in
`docs/superpowers/reviews/2026-04-23-Dev-β-wp03-06-review.md`:

* **B-1 (HIGH)** — WRITE_TARGET_FAIL must NOT permanently blacklist an entry via
  `mark_rejected`. Transient storage errors should be retryable.
* **A-2 (MEDIUM)** — ``ApprovalGate`` is a Protocol; the executor accepts an
  injected gate so future real UI/service wiring does not need to modify core.
* **D-3 (MEDIUM)** — ``_promote_batch`` caches the candidate snapshot so
  per-entry lookups do not re-fetch — O(n²) snapshot reads → O(n).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.knowledge_base.promoter.errors import PromoterErrorCode
from app.knowledge_base.promoter.promotion_executor import (
    InMemoryTargetStore,
    PromotionExecutor,
)
from app.knowledge_base.promoter.schemas import (
    Approver,
    BatchScope,
    PromoteTarget,
)


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


# ===========================================================================
# A-2 · ApprovalGate Protocol — dependency injection for real UI integration
# ===========================================================================


class TestA2ApprovalGateInjection:
    """Verify ApprovalGate can be injected; default pass-through works."""

    def test_TC_L106_L204_A2_501_default_approval_gate_accepts_any_user_id(
        self,
        sut,
        mock_observer,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        """Default ApprovalGate = pass-through (accepts any non-empty user_id)."""
        src = make_source_entry(entry_id="kbe-a1", observed_count=1)
        mock_observer._entries_by_project[mock_project_id] = [src]
        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="kbe-a1",
                    from_scope="session",
                    to_scope="project",
                    reason="user_approved",
                    approver=Approver(user_id="human-1"),
                )
            )
        )
        assert resp.single_result.verdict == "promoted"

    def test_TC_L106_L204_A2_502_injected_approval_gate_denies(
        self,
        mock_observer,
        mock_event_bus,
        target_store,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        """A custom ApprovalGate can deny approval without modifying core."""
        src = make_source_entry(entry_id="kbe-a2", observed_count=1)
        mock_observer._entries_by_project[mock_project_id] = [src]

        class _DenyingGate:
            def approve(self, *, project_id, target, approver):
                return False, "approver not recognised"

        sut = PromotionExecutor(
            observer=mock_observer,
            event_bus=mock_event_bus,
            target_store=target_store,
            approval_gate=_DenyingGate(),
        )
        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="kbe-a2",
                    from_scope="session",
                    to_scope="project",
                    reason="user_approved",
                    approver=Approver(user_id="u-anon"),
                )
            )
        )
        assert resp.single_result.verdict == "rejected"
        assert (
            resp.single_result.reason_code
            == PromoterErrorCode.USER_APPROVAL_MISSING.value
        )

    def test_TC_L106_L204_A2_503_injected_approval_gate_approves(
        self,
        mock_observer,
        mock_event_bus,
        target_store,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        """A custom gate that approves allows the promotion to proceed."""
        src = make_source_entry(entry_id="kbe-a3", observed_count=1)
        mock_observer._entries_by_project[mock_project_id] = [src]

        class _AllowingGate:
            def approve(self, *, project_id, target, approver):
                # Always approve, even if user_id is empty
                return True, ""

        sut = PromotionExecutor(
            observer=mock_observer,
            event_bus=mock_event_bus,
            target_store=target_store,
            approval_gate=_AllowingGate(),
        )
        resp = sut.kb_promote(
            make_promote_request(
                target=PromoteTarget(
                    entry_id="kbe-a3",
                    from_scope="session",
                    to_scope="project",
                    reason="user_approved",
                    # Non-empty user_id still required to reach the gate
                    approver=Approver(user_id="custom-user"),
                )
            )
        )
        assert resp.single_result.verdict == "promoted"


# ===========================================================================
# D-3 · Batch manifest cache — O(n²) → O(n) snapshot reads
# ===========================================================================


class TestD3BatchManifestCache:
    """Verify `_promote_batch` caches manifest so `_lookup_source` does not re-fetch."""

    def test_TC_L106_L204_D3_601_batch_fetches_snapshot_once(
        self,
        mock_event_bus,
        target_store,
        make_source_entry,
        make_promote_request,
        mock_project_id,
    ) -> None:
        """With N candidates, provide_candidate_snapshot must be called exactly once."""
        # Build a mock observer that tracks call count
        observer = MagicMock()
        observer._entries_by_project = {
            mock_project_id: [
                make_source_entry(entry_id=f"e{i}", observed_count=2)
                for i in range(5)
            ]
        }
        call_count = {"n": 0}

        def _snapshot(*, project_id, min_observed_count=2, kind_filter=None, trace_id=""):
            call_count["n"] += 1
            entries = observer._entries_by_project.get(project_id, [])
            return SimpleNamespace(
                project_id=project_id,
                total_entries=len(entries),
                entries=list(entries),
                error_code=None,
                kind_filter=list(kind_filter or []),
                snapshot_id=f"snap-{project_id}-{call_count['n']}",
            )

        observer.provide_candidate_snapshot.side_effect = _snapshot

        sut = PromotionExecutor(
            observer=observer,
            event_bus=mock_event_bus,
            target_store=target_store,
        )
        resp = sut.kb_promote(
            make_promote_request(
                mode="batch",
                trigger="s7_batch",
                batch_scope=BatchScope(),
            )
        )
        assert resp.success is True
        assert len(resp.batch_result.promoted) == 5
        # The old O(n²) impl would call snapshot 1+N times (once for batch pull,
        # once per candidate in _lookup_source). With the cache it should be 1.
        assert call_count["n"] == 1, (
            f"expected exactly 1 snapshot call with manifest cache, got {call_count['n']}"
        )
