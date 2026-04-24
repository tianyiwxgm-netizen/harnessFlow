"""L1-06 L2-03 · Review fix tests · 2026-04-23 MEDIUMS.

Tests for MEDIUM issues raised in
`docs/superpowers/reviews/2026-04-23-Dev-β-wp03-06-review.md`:

* **A-1a (MEDIUM)** — `WriteSessionResponse.dedup_key` must be surfaced so L2-04
  can correlate merge events by dedup key (IC-07 §3.7).
* **A-1b (MEDIUM)** — `_payload_matches_cache` must detect content divergence
  on the same idempotency key → IDEMPOTENCY_KEY_CONFLICT (§6.1 Step 5).
"""
from __future__ import annotations

from app.knowledge_base.observer.errors import ObserverErrorCode


# ===========================================================================
# A-1a · WriteSessionResponse.dedup_key surfaced
# ===========================================================================


class TestA1aDedupKeySurfaced:
    def test_TC_L106_L203_A1a_401_response_has_dedup_key_field(
        self, sut, make_request
    ) -> None:
        """§3.7 WriteResult has a `dedup_key` field — must be present on the VO."""
        resp = sut.kb_write_session(make_request())
        # Field must exist on the dataclass
        assert hasattr(resp, "dedup_key"), (
            "WriteSessionResponse must expose `dedup_key` per IC-07 §3.7"
        )

    def test_TC_L106_L203_A1a_402_dedup_key_matches_title_hash(
        self, sut, make_request, mock_project_id
    ) -> None:
        """dedup_key must equal the internal title_hash so L2-04 can correlate."""
        resp = sut.kb_write_session(make_request())
        assert resp.success is True
        assert resp.dedup_key  # non-empty for successful inserts
        # Trigger a merge on the same title → same dedup_key
        resp2 = sut.kb_write_session(make_request(trace_id="t-2"))
        assert resp2.success is True
        assert resp2.action == "MERGED"
        assert resp2.dedup_key == resp.dedup_key, (
            "merged entry must carry the same dedup_key as the initial insert"
        )

    def test_TC_L106_L203_A1a_403_dedup_key_differs_for_different_titles(
        self, sut, make_request, make_entry
    ) -> None:
        r1 = sut.kb_write_session(make_request(entry=make_entry(title="First title")))
        r2 = sut.kb_write_session(
            make_request(entry=make_entry(title="Totally different title"))
        )
        assert r1.dedup_key != r2.dedup_key

    def test_TC_L106_L203_A1a_404_dedup_key_empty_on_rejected_response(
        self, sut, make_request, make_entry
    ) -> None:
        """Rejected responses carry an empty dedup_key (no stored entry)."""
        resp = sut.kb_write_session(make_request(entry=make_entry(kind="xxx")))
        assert resp.success is False
        assert resp.dedup_key == ""


# ===========================================================================
# A-1b · Idempotency conflict detection via content hash
# ===========================================================================


class TestA1bIdempotencyConflict:
    def test_TC_L106_L203_A1b_501_same_key_same_payload_is_replay(
        self, sut, make_request
    ) -> None:
        """Identical payload + same idem key → replay (returns the cached resp)."""
        req1 = make_request(idempotency_key="same-key-1", trace_id="t1")
        req2 = make_request(idempotency_key="same-key-1", trace_id="t1")
        r1 = sut.kb_write_session(req1)
        r2 = sut.kb_write_session(req2)
        assert r1.success is True
        assert r2.success is True
        # Same cached response echoed
        assert r1.entry_id == r2.entry_id
        assert r1.audit_event_id == r2.audit_event_id

    def test_TC_L106_L203_A1b_502_same_key_different_payload_is_conflict(
        self, sut, make_request, make_entry
    ) -> None:
        """Same idem key + different content → IDEMPOTENCY_KEY_CONFLICT."""
        r1 = sut.kb_write_session(
            make_request(
                idempotency_key="dup-key-A",
                entry=make_entry(title="Original title", content={"v": 1}),
            )
        )
        assert r1.success is True

        # Same idem key, different title
        r2 = sut.kb_write_session(
            make_request(
                idempotency_key="dup-key-A",
                entry=make_entry(title="Different title", content={"v": 1}),
            )
        )
        assert r2.success is False
        assert (
            r2.error_code
            == ObserverErrorCode.IDEMPOTENCY_KEY_CONFLICT.value
        ), (
            "per §6.1 D5, same idempotency_key with different payload MUST "
            "produce IDEMPOTENCY_KEY_CONFLICT — current stub silently returns replay"
        )

    def test_TC_L106_L203_A1b_503_same_key_same_title_different_content_conflict(
        self, sut, make_request, make_entry
    ) -> None:
        """Content divergence alone (same title) → conflict."""
        sut.kb_write_session(
            make_request(
                idempotency_key="dup-key-B",
                entry=make_entry(title="T", content={"v": 1}),
            )
        )
        r2 = sut.kb_write_session(
            make_request(
                idempotency_key="dup-key-B",
                entry=make_entry(title="T", content={"v": 2}),
            )
        )
        assert r2.success is False
        assert (
            r2.error_code
            == ObserverErrorCode.IDEMPOTENCY_KEY_CONFLICT.value
        )

    def test_TC_L106_L203_A1b_504_same_key_same_kind_different_kind_conflict(
        self, sut, make_request, make_entry
    ) -> None:
        sut.kb_write_session(
            make_request(
                idempotency_key="dup-key-C",
                entry=make_entry(title="same", kind="trap"),
            )
        )
        r2 = sut.kb_write_session(
            make_request(
                idempotency_key="dup-key-C",
                entry=make_entry(title="same", kind="pattern"),
            )
        )
        assert r2.success is False
        assert (
            r2.error_code
            == ObserverErrorCode.IDEMPOTENCY_KEY_CONFLICT.value
        )
