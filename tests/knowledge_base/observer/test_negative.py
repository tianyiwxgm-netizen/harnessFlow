"""L1-06 L2-03 · negative path tests · every error code exercised."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.knowledge_base.observer.accumulator import (
    ObserveAccumulator,
    _InMemorySessionStore,
)
from app.knowledge_base.observer.errors import ObserverErrorCode
from app.knowledge_base.observer.schemas import (
    HARD_CAP_PER_PROJECT,
    SOFT_CAP_PER_PROJECT,
    StoredEntry,
)


class TestNegativeIC07:
    def test_TC_L106_L203_201_missing_project_id(
        self, sut, make_request
    ) -> None:
        resp = sut.kb_write_session(make_request(project_id=""))
        assert resp.success is False
        assert resp.error_code == ObserverErrorCode.PM14_PROJECT_ID_MISSING.value

    def test_TC_L106_L203_202_pm14_mismatch(
        self, sut, make_request, make_entry, mock_project_id_other
    ) -> None:
        entry = make_entry()
        entry.project_id = mock_project_id_other  # differs from req.project_id
        resp = sut.kb_write_session(make_request(entry=entry))
        assert resp.error_code == ObserverErrorCode.PM14_PROJECT_ID_MISMATCH.value

    def test_TC_L106_L203_203_cross_layer_denied_project_scope(
        self, sut, make_request, make_entry
    ) -> None:
        entry = make_entry()
        entry.scope = "project"
        resp = sut.kb_write_session(make_request(entry=entry))
        assert resp.error_code == ObserverErrorCode.CROSS_LAYER_DENIED.value

    def test_TC_L106_L203_204_cross_layer_denied_global_scope(
        self, sut, make_request, make_entry
    ) -> None:
        entry = make_entry()
        entry.scope = "global"
        resp = sut.kb_write_session(make_request(entry=entry))
        assert resp.error_code == ObserverErrorCode.CROSS_LAYER_DENIED.value

    def test_TC_L106_L203_205_kind_not_whitelisted(
        self, sut, make_request, make_entry
    ) -> None:
        resp = sut.kb_write_session(
            make_request(entry=make_entry(kind="not_a_kind"))
        )
        assert resp.error_code == ObserverErrorCode.KIND_NOT_WHITELISTED.value

    def test_TC_L106_L203_206_title_empty(
        self, sut, make_request, make_entry
    ) -> None:
        resp = sut.kb_write_session(make_request(entry=make_entry(title="")))
        assert resp.error_code == ObserverErrorCode.TITLE_EMPTY_OR_TOO_LONG.value

    def test_TC_L106_L203_207_title_too_long(
        self, sut, make_request, make_entry
    ) -> None:
        resp = sut.kb_write_session(
            make_request(entry=make_entry(title="X" * 201))
        )
        assert resp.error_code == ObserverErrorCode.TITLE_EMPTY_OR_TOO_LONG.value

    def test_TC_L106_L203_208_source_links_empty(
        self, sut, make_request, make_entry
    ) -> None:
        resp = sut.kb_write_session(
            make_request(entry=make_entry(source_links=[]))
        )
        assert resp.error_code == ObserverErrorCode.SOURCE_LINKS_EMPTY.value

    def test_TC_L106_L203_209_raw_text_content_denied(
        self, sut, make_request, make_entry
    ) -> None:
        entry = make_entry()
        entry.content = "this is a free-form string, not a dict"  # type: ignore[assignment]
        resp = sut.kb_write_session(make_request(entry=entry))
        assert resp.error_code == ObserverErrorCode.RAW_TEXT_DENIED.value

    def test_TC_L106_L203_210_observed_count_override_ignored_but_allowed(
        self, sut, make_request, make_entry, mock_event_bus
    ) -> None:
        """Caller-supplied observed_count must be stripped (not rejected)."""
        resp = sut.kb_write_session(
            make_request(entry=make_entry(observed_count=999))
        )
        assert resp.success is True
        assert resp.observed_count_after == 1
        # Audit log must record the override as soft-rejection.
        codes = [
            rec["payload"].get("reason") or rec["payload"].get("error_code")
            for rec in sut._audit_log
            if rec["event_type"] == "kb_entry_write_rejected"
        ]
        assert ObserverErrorCode.COUNT_OVERRIDE_IGNORED.value in codes

    def test_TC_L106_L203_211_idempotency_conflict_different_project(
        self, mock_event_bus, repo, make_request
    ) -> None:
        """Same idempotency_key under different project_id stays isolated."""
        sut = ObserveAccumulator(
            tier_manager=None, event_bus=mock_event_bus, repo=repo
        )
        r1 = sut.kb_write_session(
            make_request(
                project_id="pA",
                trace_id="t",
                idempotency_key="idem-x",
            )
        )
        r2 = sut.kb_write_session(
            make_request(
                project_id="pB",
                trace_id="t",
                idempotency_key="idem-x",
            )
        )
        # Different projects → cache key differs → separate inserts.
        assert r1.entry_id != r2.entry_id
        assert r1.project_id == "pA"
        assert r2.project_id == "pB"

    def test_TC_L106_L203_212_hard_cap_rejected_on_insert(
        self, mock_event_bus, make_request, make_entry
    ) -> None:
        """Use a tiny hard cap so we don't need 10k seeds to exercise branch."""
        repo = _InMemorySessionStore()
        for i in range(3):
            repo.append_entry(
                "pcap",
                StoredEntry(
                    entry_id=f"seed-{i}",
                    project_id="pcap",
                    kind="trap",
                    title=f"t-{i}",
                    title_hash=f"{i:032x}",
                    content={"x": 1},
                ),
            )
        sut = ObserveAccumulator(
            tier_manager=None,
            event_bus=mock_event_bus,
            repo=repo,
            soft_cap=2,
            hard_cap=3,
        )
        resp = sut.kb_write_session(
            make_request(
                project_id="pcap",
                entry=make_entry(
                    title="brand new title that doesn't collide"
                ),
            )
        )
        assert resp.error_code == ObserverErrorCode.CAPACITY_HARD_REJECTED.value

    def test_TC_L106_L203_213_soft_cap_warns_but_accepts(
        self, mock_event_bus, make_request, make_entry
    ) -> None:
        """Use a small soft/hard cap so the warning branch fires without 10k seeds."""
        repo = _InMemorySessionStore()
        for i in range(2):
            repo.append_entry(
                "psoft",
                StoredEntry(
                    entry_id=f"seed-{i}",
                    project_id="psoft",
                    kind="trap",
                    title=f"t-{i}",
                    title_hash=f"{i:032x}",
                    content={"x": 1},
                ),
            )
        sut = ObserveAccumulator(
            tier_manager=None,
            event_bus=mock_event_bus,
            repo=repo,
            soft_cap=2,
            hard_cap=100,
        )
        resp = sut.kb_write_session(
            make_request(
                project_id="psoft",
                entry=make_entry(title="fresh"),
            )
        )
        assert resp.success is True
        warnings = [
            rec
            for rec in sut._audit_log
            if rec["event_type"] == "kb_session_capacity_warning"
        ]
        assert warnings

    def test_TC_L106_L203_214_tier_manager_rejects_schema(
        self, mock_event_bus, repo, make_request
    ) -> None:
        tm = MagicMock()
        tm.write_slot_request.return_value = MagicMock(
            schema_valid=False, slot_granted=False, existing_entry_id=None
        )
        sut = ObserveAccumulator(
            tier_manager=tm, event_bus=mock_event_bus, repo=repo
        )
        resp = sut.kb_write_session(make_request())
        assert resp.error_code == ObserverErrorCode.L201_SCHEMA_INVALID.value

    def test_TC_L106_L203_215_tier_manager_unavailable_degrades(
        self, mock_event_bus, repo, make_request
    ) -> None:
        """L2-01 raising should not block the write (degraded path)."""
        tm = MagicMock()
        tm.write_slot_request.side_effect = RuntimeError("L201 dead")
        sut = ObserveAccumulator(
            tier_manager=tm, event_bus=mock_event_bus, repo=repo
        )
        resp = sut.kb_write_session(make_request())
        # Proceeds with best-effort write (degraded semantics).
        assert resp.success is True
        assert resp.action == "INSERTED"
