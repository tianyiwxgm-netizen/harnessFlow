"""L1-06 L2-03 · IC-07 + IC-L2-06 field-level contract tests.

Verifies that WriteSessionResponse carries the full set of §3.1 output
fields and that PM-14 is enforced on every entry point.
"""
from __future__ import annotations

from app.knowledge_base.observer.accumulator import ObserveAccumulator
from app.knowledge_base.observer.schemas import (
    CandidateSnapshotRequest,
    PROMOTION_THRESHOLD_SESSION_TO_PROJECT,
)


class TestIC07Schema:
    def test_TC_L106_L203_301_response_has_all_success_fields(
        self, sut, make_request
    ) -> None:
        resp = sut.kb_write_session(make_request())
        # 3-1 §3.1 success payload keys
        required = [
            "success",
            "action",
            "entry_id",
            "project_id",
            "observed_count_after",
            "first_observed_at",
            "last_observed_at",
            "was_normalized",
            "promotion_hint",
            "trace_id",
            "audit_event_id",
        ]
        d = resp.__dict__
        for key in required:
            assert key in d, f"missing {key}"
        assert resp.success is True

    def test_TC_L106_L203_302_rejected_response_carries_error_code(
        self, sut, make_request, make_entry
    ) -> None:
        resp = sut.kb_write_session(
            make_request(entry=make_entry(kind="xxx"))
        )
        assert resp.success is False
        assert resp.action == "REJECTED"
        assert resp.error_code is not None
        assert resp.error_message

    def test_TC_L106_L203_303_project_id_always_echoed(
        self, sut, make_request, mock_project_id
    ) -> None:
        resp = sut.kb_write_session(make_request())
        assert resp.project_id == mock_project_id

    def test_TC_L106_L203_304_promotion_hint_object_shape(
        self, sut, make_request
    ) -> None:
        # Trigger 2 writes so hint becomes eligible.
        for i in range(PROMOTION_THRESHOLD_SESSION_TO_PROJECT):
            resp = sut.kb_write_session(make_request(trace_id=f"t{i}"))
        assert resp.promotion_hint is not None
        assert hasattr(resp.promotion_hint, "session_to_project_eligible")
        assert hasattr(resp.promotion_hint, "threshold")


class TestICL206Schema:
    def test_TC_L106_L203_305_snapshot_happy_path_fields(
        self, sut, make_request, mock_project_id
    ) -> None:
        # Seed 3 writes across 2 kinds
        for i, kind in enumerate(["trap", "pattern", "pattern"]):
            from app.knowledge_base.observer.schemas import (
                ApplicableContext,
                KBEntryRequest,
            )

            req = make_request(
                trace_id=f"t{i}",
                entry=KBEntryRequest(
                    kind=kind,
                    title=f"title-{i}",
                    content={"x": i},
                    applicable_context=ApplicableContext(
                        stage=["S3"], task_type=["coding"], tech_stack=[]
                    ),
                    source_links=[f"d{i}"],
                ),
            )
            sut.kb_write_session(req)
        # Ensure merge count reaches threshold on kind=pattern
        from app.knowledge_base.observer.schemas import (
            ApplicableContext,
            KBEntryRequest,
        )

        sut.kb_write_session(
            make_request(
                trace_id="merge-1",
                entry=KBEntryRequest(
                    kind="pattern",
                    title="title-1",
                    content={"x": 1},
                    applicable_context=ApplicableContext(
                        stage=["S3"], task_type=["coding"], tech_stack=[]
                    ),
                    source_links=["d1"],
                ),
            )
        )
        manifest = sut.provide_candidate_snapshot(project_id=mock_project_id)
        assert manifest.project_id == mock_project_id
        assert manifest.snapshot_id.startswith("snap-")
        assert manifest.total_entries >= 1
        assert all(
            e.promotion_hint is not None
            and e.promotion_hint.session_to_project_eligible is True
            for e in manifest.entries
        )

    def test_TC_L106_L203_306_snapshot_filters_by_kind(
        self, sut, make_request, mock_project_id
    ) -> None:
        # 2 traps observed twice each + 1 pattern observed twice
        from app.knowledge_base.observer.schemas import (
            ApplicableContext,
            KBEntryRequest,
        )

        def write(kind, title, tr):
            return sut.kb_write_session(
                make_request(
                    trace_id=tr,
                    entry=KBEntryRequest(
                        kind=kind,
                        title=title,
                        content={"x": 1},
                        applicable_context=ApplicableContext(),
                        source_links=["d"],
                    ),
                )
            )

        for k, t in [("trap", "trap-a"), ("trap", "trap-a"), ("pattern", "p-1"), ("pattern", "p-1")]:
            write(k, t, "x")
        manifest = sut.provide_candidate_snapshot(
            project_id=mock_project_id, kind_filter=["trap"]
        )
        assert all(e.kind == "trap" for e in manifest.entries)

    def test_TC_L106_L203_307_snapshot_empty_kind_filter_error(
        self, sut, mock_project_id
    ) -> None:
        manifest = sut.provide_candidate_snapshot(
            project_id=mock_project_id, kind_filter=[]
        )
        assert manifest.error_code is not None
        assert "SNAPSHOT_KIND_EMPTY" in manifest.error_code

    def test_TC_L106_L203_308_snapshot_missing_project_id(
        self, sut
    ) -> None:
        manifest = sut.provide_candidate_snapshot(project_id="")
        assert manifest.error_code is not None
        assert "PM14" in manifest.error_code

    def test_TC_L106_L203_309_snapshot_default_all_kinds_when_none(
        self, sut, make_request, mock_project_id
    ) -> None:
        """kind_filter=None (default) → all kinds returned."""
        sut.kb_write_session(make_request(trace_id="t1"))
        sut.kb_write_session(make_request(trace_id="t2"))
        manifest = sut.provide_candidate_snapshot(project_id=mock_project_id)
        assert manifest.kind_filter == []  # None → no filter
        assert manifest.total_entries >= 1
