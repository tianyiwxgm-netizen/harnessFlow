"""L1-06 L2-03 · positive path tests for IC-07 kb_write_session."""
from __future__ import annotations

from app.knowledge_base.observer.schemas import (
    KIND_WHITELIST,
    PROMOTION_THRESHOLD_SESSION_TO_PROJECT,
)


class TestPositiveIC07:
    def test_TC_L106_L203_101_fresh_insert(self, sut, make_request) -> None:
        resp = sut.kb_write_session(make_request())
        assert resp.success is True
        assert resp.action == "INSERTED"
        assert resp.observed_count_after == 1
        assert resp.first_observed_at == resp.last_observed_at
        assert resp.entry_id.startswith("kbe-")
        assert resp.promotion_hint is not None
        assert resp.promotion_hint.session_to_project_eligible is False

    def test_TC_L106_L203_102_second_write_same_title_merges(
        self, sut, make_request
    ) -> None:
        r1 = sut.kb_write_session(make_request(trace_id="t1"))
        r2 = sut.kb_write_session(make_request(trace_id="t2"))
        assert r2.action == "MERGED"
        assert r2.entry_id == r1.entry_id
        assert r2.observed_count_after == 2

    def test_TC_L106_L203_103_title_normalised_whitespace(
        self, sut, make_request, make_entry
    ) -> None:
        e1 = make_entry(title="OAuth Redirect Loop")
        e2 = make_entry(title="  oauth   redirect    loop  ")
        r1 = sut.kb_write_session(make_request(trace_id="t1", entry=e1))
        r2 = sut.kb_write_session(make_request(trace_id="t2", entry=e2))
        assert r1.action == "INSERTED"
        assert r2.action == "MERGED"
        assert r2.was_normalized is True

    def test_TC_L106_L203_104_promotion_hint_at_threshold(
        self, sut, make_request
    ) -> None:
        for i in range(PROMOTION_THRESHOLD_SESSION_TO_PROJECT):
            resp = sut.kb_write_session(make_request(trace_id=f"t{i}"))
        assert resp.promotion_hint.session_to_project_eligible is True
        assert resp.promotion_hint.threshold == (
            PROMOTION_THRESHOLD_SESSION_TO_PROJECT
        )

    def test_TC_L106_L203_105_different_kind_same_title_not_merged(
        self, sut, make_request, make_entry
    ) -> None:
        r1 = sut.kb_write_session(
            make_request(trace_id="t1", entry=make_entry(kind="trap"))
        )
        r2 = sut.kb_write_session(
            make_request(trace_id="t2", entry=make_entry(kind="pattern"))
        )
        assert r1.entry_id != r2.entry_id
        assert r2.action == "INSERTED"

    def test_TC_L106_L203_106_source_links_union(
        self, sut, make_request, make_entry
    ) -> None:
        r1 = sut.kb_write_session(
            make_request(
                entry=make_entry(source_links=["decision:a", "verdict:b"])
            )
        )
        sut.kb_write_session(
            make_request(
                trace_id="t2",
                entry=make_entry(source_links=["decision:a", "verdict:c"]),
            )
        )
        stored = sut._repo.list_by_project_and_kind(r1.project_id, ["trap"])[0]
        assert set(stored.source_links) == {
            "decision:a",
            "verdict:b",
            "verdict:c",
        }

    def test_TC_L106_L203_107_last_observed_at_updated_on_merge(
        self, sut, make_request
    ) -> None:
        r1 = sut.kb_write_session(make_request(trace_id="t1"))
        r2 = sut.kb_write_session(make_request(trace_id="t2"))
        assert r2.last_observed_at >= r1.last_observed_at
        assert r2.first_observed_at == r1.first_observed_at

    def test_TC_L106_L203_108_all_eight_kinds_accepted(
        self, sut, make_request, make_entry
    ) -> None:
        assert KIND_WHITELIST == {
            "pattern",
            "trap",
            "recipe",
            "tool_combo",
            "anti_pattern",
            "project_context",
            "external_ref",
            "effective_combo",
        }
        for i, k in enumerate(sorted(KIND_WHITELIST)):
            resp = sut.kb_write_session(
                make_request(
                    trace_id=f"t{i}",
                    entry=make_entry(kind=k, title=f"entry-{i}"),
                )
            )
            assert resp.success is True, k

    def test_TC_L106_L203_109_trace_id_echoed(
        self, sut, make_request
    ) -> None:
        resp = sut.kb_write_session(make_request(trace_id="trace-abc"))
        assert resp.trace_id == "trace-abc"

    def test_TC_L106_L203_110_idempotency_replay_returns_cached(
        self, sut, make_request
    ) -> None:
        r1 = sut.kb_write_session(
            make_request(trace_id="t1", idempotency_key="idem-123")
        )
        r2 = sut.kb_write_session(
            make_request(trace_id="t1", idempotency_key="idem-123")
        )
        # Replay returns cached response — observed_count stays at 1.
        assert r2.entry_id == r1.entry_id
        assert r2.observed_count_after == 1
