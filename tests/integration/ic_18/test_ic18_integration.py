"""IC-18 · audit_query (query_audit_trail) 集成测试 · 5 TC.

(WP04 任务表 IC-18 = L1-09 AuditQuery.query_audit_trail · L1-10 → L1-09)

覆盖:
    TC-1 按 pid: PROJECT_ID anchor → 全部 event_layer 命中
    TC-2 按 type: filter.event_type 命中预期 type
    TC-3 按时间窗: filter.time_range_start/end 收窄
    TC-4 hash-chain 校验: 物理 events.jsonl sequence 连续 · 无 gap
    TC-5 SLO P95 ≤ 500ms (§3.18)
"""
from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import pytest

from app.l1_09.audit import AnchorType, AuditProjectRequired, QueryFilter


class TestIC18Integration:
    """IC-18 集成 · AuditQuery.query_audit_trail."""

    # ---- TC-1 · 按 pid: PROJECT_ID anchor → 全部 event_layer 命中 ----
    def test_anchor_project_id_returns_all_events(
        self, audit_query, seed_events, make_anchor, project_id: str,
    ) -> None:
        seed_events(n=5, event_type="L1-05:task_done")

        anchor = make_anchor()  # 默认 PROJECT_ID
        trail = audit_query.query_audit_trail(anchor)

        assert trail.project_id == project_id
        assert trail.event_layer.count == 5
        assert trail.total_entries >= 5

    # ---- TC-2 · 按 type: filter.event_type 命中 ----
    def test_filter_by_event_type(
        self, audit_query, seed_events, make_anchor,
    ) -> None:
        seed_events(n=3, event_type="L1-05:task_done")
        seed_events(n=2, event_type="L1-05:decision_made")

        anchor = make_anchor()
        f = QueryFilter(event_type="L1-05:decision_made")
        trail = audit_query.query_audit_trail(anchor, f)

        # 只命中 decision_made 2 条
        assert trail.event_layer.count == 2

    # ---- TC-3 · 按时间窗: filter.time_range_start 收窄 ----
    def test_filter_by_time_range(
        self, audit_query, seed_events, make_anchor,
    ) -> None:
        # 写 5 条 (默认 now)
        seed_events(n=5, event_type="L1-05:task_done")

        # 时间窗设置在 1 小时之前 · 应排除全部
        future_start = datetime.now(UTC) + timedelta(hours=1)
        f = QueryFilter(time_range_start=future_start)
        trail = audit_query.query_audit_trail(make_anchor(), f)

        # 时间窗收窄到 1h 之后 · 全部 event 都早 → 命中 0
        assert trail.event_layer.count == 0

    # ---- TC-4 · hash-chain 完整校验 ----
    def test_hash_chain_continuous_no_gap(
        self,
        audit_query,
        real_event_bus,
        seed_events,
        make_anchor,
        project_id: str,
        event_bus_root,
    ) -> None:
        seed_events(n=5, event_type="L1-05:task_done")

        # 通过物理 events.jsonl 校验 sequence 连续
        events_path = (
            event_bus_root / "projects" / project_id / "events.jsonl"
        )
        assert events_path.exists()
        import json

        seqs = []
        prev_hashes = []
        for raw in events_path.read_bytes().splitlines():
            if raw.strip():
                evt = json.loads(raw.decode("utf-8"))
                seqs.append(evt["sequence"])
                prev_hashes.append(evt.get("prev_hash"))

        # IC-18 §3.18 hash-chain 完整性: sequence 1..N 连续
        assert seqs == list(range(1, 6))
        # AuditQuery 不应报告 gap
        anchor = make_anchor()
        trail = audit_query.query_audit_trail(anchor)
        assert trail.hash_chain_gap == []

    # ---- TC-5 · SLO P95 ≤ 500ms ----
    def test_slo_p95_within_500ms(
        self, audit_query, seed_events, make_anchor,
    ) -> None:
        seed_events(n=20, event_type="L1-05:task_done")

        latencies: list[float] = []
        for _ in range(10):
            anchor = make_anchor()
            t0 = time.perf_counter()
            trail = audit_query.query_audit_trail(anchor)
            latencies.append((time.perf_counter() - t0) * 1000.0)
            assert trail.total_entries >= 20

        latencies.sort()
        p95 = latencies[int(len(latencies) * 0.95)]
        assert p95 < 500.0, f"IC-18 P95 SLO 超时 {p95:.1f}ms"
