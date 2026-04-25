"""IC-07 · kb_write_session 集成测试 · 5 TC.

覆盖 (对齐 ic-contracts.md §3.7 + WP04 任务表):
    TC-1 写入 (fresh insert · INSERTED + observed_count=1)
    TC-2 晋升 (同 title 二次写 → MERGED + observed_count_after=2 · promotion_hint 在阈值)
    TC-3 拒绝 (kind 不在白名单 · REJECTED + error_code)
    TC-4 读后写 (idempotency_key 同值多次写 · entry_id 一致)
    TC-5 SLO P95 ≤ 100ms (§3.7 SLO)
"""
from __future__ import annotations

import time

from app.knowledge_base.observer.schemas import (
    PROMOTION_THRESHOLD_SESSION_TO_PROJECT,
)


class TestIC07Integration:
    """IC-07 集成 · ObserveAccumulator + InMemorySessionStore."""

    # ---- TC-1 · 写入 fresh INSERTED ----
    def test_fresh_insert_creates_entry(
        self, accumulator, make_request, project_id: str,
    ) -> None:
        resp = accumulator.kb_write_session(make_request())

        assert resp.success is True
        assert resp.action == "INSERTED"
        assert resp.observed_count_after == 1
        assert resp.first_observed_at == resp.last_observed_at
        assert resp.entry_id.startswith("kbe-")
        assert resp.project_id == project_id
        # IC-07 §3.7 dedup_key 透出 (review A-1a)
        assert resp.dedup_key != ""
        assert resp.error_code is None

    # ---- TC-2 · 晋升: 二次写同 title → MERGED + promotion_hint ----
    def test_second_write_merges_and_hints_promotion(
        self, accumulator, make_request,
    ) -> None:
        # 第 1 次 insert
        r1 = accumulator.kb_write_session(make_request(trace_id="t1"))
        # 第 2 次相同 (kind+title) → MERGED · 触发阈值 promotion_hint
        r2 = accumulator.kb_write_session(make_request(trace_id="t2"))

        assert r1.action == "INSERTED"
        assert r2.action == "MERGED"
        assert r2.entry_id == r1.entry_id  # 同 dedup_key
        assert r2.observed_count_after == 2
        # PROMOTION_THRESHOLD_SESSION_TO_PROJECT == 2 · 触发 hint
        assert r2.promotion_hint is not None
        assert r2.promotion_hint.session_to_project_eligible is True
        assert r2.promotion_hint.threshold == PROMOTION_THRESHOLD_SESSION_TO_PROJECT

    # ---- TC-3 · 拒绝: kind 不在白名单 → REJECTED ----
    def test_invalid_kind_rejected(
        self, accumulator, make_request, make_entry,
    ) -> None:
        bad_entry = make_entry(kind="not-in-whitelist")
        resp = accumulator.kb_write_session(make_request(entry=bad_entry))

        assert resp.success is False
        assert resp.action == "REJECTED"
        assert resp.error_code is not None
        # kind 错误码 · 来自 ObserverErrorCode (KIND_INVALID 等前缀)
        assert "KIND" in str(resp.error_code).upper()
        # 拒绝路径不写 dedup
        assert resp.entry_id == ""

    # ---- TC-4 · idempotency_key 同值多次 → 同 entry_id ----
    def test_idempotency_key_returns_same_entry_id(
        self, accumulator, make_request,
    ) -> None:
        idem_key = "idem-ic07-tc4-stable"
        r1 = accumulator.kb_write_session(
            make_request(trace_id="t1", idempotency_key=idem_key),
        )
        r2 = accumulator.kb_write_session(
            make_request(trace_id="t2", idempotency_key=idem_key),
        )
        # IC-07 §3.7 idempotent (同 dedup_key 返同 entry_id)
        assert r1.success is True
        assert r2.success is True
        assert r1.entry_id == r2.entry_id

    # ---- TC-5 · SLO P95 ≤ 100ms ----
    def test_slo_p95_within_100ms(
        self, accumulator, make_request, make_entry,
    ) -> None:
        latencies: list[float] = []
        for i in range(10):
            entry = make_entry(title=f"slo-title-{i}")
            t0 = time.perf_counter()
            resp = accumulator.kb_write_session(
                make_request(trace_id=f"trace-slo-{i}", entry=entry),
            )
            latencies.append((time.perf_counter() - t0) * 1000.0)
            assert resp.success is True

        latencies.sort()
        p95 = latencies[int(len(latencies) * 0.95)]
        # IC-07 SLO §3.7 · P95 ≤ 100ms · in-memory 远低
        assert p95 < 100.0, f"IC-07 P95 SLO 超时 {p95:.1f}ms"
