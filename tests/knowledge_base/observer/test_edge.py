"""L1-06 L2-03 · edge cases + PM-14 cross-project isolation."""
from __future__ import annotations

from app.knowledge_base.observer.accumulator import (
    ObserveAccumulator,
    _InMemorySessionStore,
)


class TestEdgeCases:
    def test_TC_L106_L203_401_pm14_two_projects_isolated(
        self, mock_event_bus, make_request, make_entry
    ) -> None:
        """Two concurrent projects writing the same title stay isolated."""
        repo = _InMemorySessionStore()
        sut = ObserveAccumulator(
            tier_manager=None, event_bus=mock_event_bus, repo=repo
        )
        rA = sut.kb_write_session(
            make_request(project_id="pA", trace_id="tA")
        )
        rB = sut.kb_write_session(
            make_request(project_id="pB", trace_id="tB")
        )
        assert rA.entry_id != rB.entry_id
        assert rA.project_id == "pA"
        assert rB.project_id == "pB"
        assert repo.count_by_project("pA") == 1
        assert repo.count_by_project("pB") == 1

    def test_TC_L106_L203_402_case_and_whitespace_normalised_to_same_entry(
        self, sut, make_request, make_entry
    ) -> None:
        r1 = sut.kb_write_session(
            make_request(entry=make_entry(title="Hello World"))
        )
        r2 = sut.kb_write_session(
            make_request(
                trace_id="t2",
                entry=make_entry(title="HELLO   world"),
            )
        )
        assert r1.entry_id == r2.entry_id

    def test_TC_L106_L203_403_similar_but_not_identical_stays_distinct(
        self, sut, make_request, make_entry
    ) -> None:
        r1 = sut.kb_write_session(
            make_request(entry=make_entry(title="Hello World"))
        )
        r2 = sut.kb_write_session(
            make_request(
                trace_id="t2",
                entry=make_entry(title="Hello World 2"),
            )
        )
        assert r1.entry_id != r2.entry_id

    def test_TC_L106_L203_404_seed_from_storage_counts(
        self, sut, make_request
    ) -> None:
        sut.kb_write_session(make_request(trace_id="t1"))
        sut.kb_write_session(
            make_request(
                trace_id="t2",
                entry=make_request().entry,
            )
        )
        n = sut.seed_from_storage(sut.kb_write_session(make_request(trace_id="t3")).project_id)
        assert n >= 1

    def test_TC_L106_L203_405_title_exactly_200_chars_allowed(
        self, sut, make_request, make_entry
    ) -> None:
        title = "x" * 200
        resp = sut.kb_write_session(
            make_request(entry=make_entry(title=title))
        )
        assert resp.success is True

    def test_TC_L106_L203_406_audit_event_bus_failure_does_not_block_write(
        self, mock_event_bus, repo, make_request
    ) -> None:
        mock_event_bus.append.side_effect = RuntimeError("bus dead")
        sut = ObserveAccumulator(
            tier_manager=None, event_bus=mock_event_bus, repo=repo
        )
        resp = sut.kb_write_session(make_request())
        assert resp.success is True
        assert resp.action == "INSERTED"

    def test_TC_L106_L203_407_no_tier_manager_still_writes(
        self, mock_event_bus, repo, make_request
    ) -> None:
        sut = ObserveAccumulator(
            tier_manager=None, event_bus=mock_event_bus, repo=repo
        )
        resp = sut.kb_write_session(make_request())
        assert resp.success is True

    def test_TC_L106_L203_408_promotion_hint_reflects_latest_count(
        self, sut, make_request
    ) -> None:
        r1 = sut.kb_write_session(make_request(trace_id="t1"))
        assert r1.promotion_hint.session_to_project_eligible is False
        r2 = sut.kb_write_session(make_request(trace_id="t2"))
        assert r2.promotion_hint.session_to_project_eligible is True

    def test_TC_L106_L203_409_audit_emitted_on_write(
        self, sut, make_request, mock_event_bus
    ) -> None:
        sut.kb_write_session(make_request(trace_id="t-audit"))
        assert mock_event_bus.append.called
        # At least one call with event_type=kb_entry_written
        events = [
            c.kwargs.get("event_type") or c.args[0]
            for c in mock_event_bus.append.call_args_list
        ]
        assert "kb_entry_written" in events

    def test_TC_L106_L203_410_dedup_merge_does_not_create_duplicates_in_repo(
        self, sut, make_request, mock_project_id, repo
    ) -> None:
        sut.kb_write_session(make_request(trace_id="t1"))
        sut.kb_write_session(make_request(trace_id="t2"))
        sut.kb_write_session(make_request(trace_id="t3"))
        assert repo.count_by_project(mock_project_id) == 1
