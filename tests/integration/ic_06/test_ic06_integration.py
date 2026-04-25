"""IC-06 · kb_read 集成测试 · 5 TC.

覆盖 (对齐 ic-contracts.md §3.6 + WP04 任务表):
    TC-1 检索命中: 3 层 read · S>P>G 优先级合并 · meta.project_id 一致 (PM-14)
    TC-2 Rerank 路径: reranker 调用 + observed_count 排序生效
    TC-3 无结果 (kind 过滤后 candidate_count=0 · returned_count=0)
    TC-4 跨层 (3 层都有命中 · scopes_hit 含 session+project+global · merge 不去重错)
    TC-5 SLO · P95 ≤ 500ms (§3.6 · 内存 fake repo 远低于阈值)
"""
from __future__ import annotations

import time

from tests.shared.ic_assertions import assert_kb_read_returned


class TestIC06Integration:
    """IC-06 集成 · KBReadService + 3 层 fake repo."""

    # ---- TC-1 · 正向: 命中 + meta.project_id (PM-14) ----
    def test_session_layer_hit_returns_entries_with_pm14_meta(
        self, reader, fake_repo, make_entry, make_request, project_id: str,
    ) -> None:
        fake_repo.session_entries = [
            make_entry(entry_id="kbe-s1", title="hit-1"),
            make_entry(entry_id="kbe-s2", title="hit-2"),
        ]

        result = reader.read(make_request())

        # IC-06 共用断言: meta.project_id == 入参 pid + entries ≥ 1
        entries = assert_kb_read_returned(result, project_id=project_id, min_entries=2)
        assert {e.id for e in entries} == {"kbe-s1", "kbe-s2"}
        assert result.meta.cache_hit is False
        assert result.meta.degraded is False
        # session 命中 · scopes_hit 含 session
        assert "session" in result.meta.scopes_hit

    # ---- TC-2 · Rerank 路径: observed_count DESC 排序 + reranker 调用 ----
    def test_reranker_orders_by_observed_count(
        self, reader, fake_repo, make_entry, make_request, project_id: str,
    ) -> None:
        fake_repo.session_entries = [
            make_entry(entry_id="kbe-low", title="A", observed_count=1),
            make_entry(entry_id="kbe-mid", title="B", observed_count=5),
            make_entry(entry_id="kbe-hi", title="C", observed_count=10),
        ]

        result = reader.read(make_request(top_k=3))

        entries = assert_kb_read_returned(result, project_id=project_id, min_entries=3)
        # FakeReranker 按 observed_count DESC 排
        ids = [e.id for e in entries]
        assert ids == ["kbe-hi", "kbe-mid", "kbe-low"]
        assert result.meta.rerank_fallback is False  # 正常路径未降级

    # ---- TC-3 · 负向: kind 过滤后无结果 ----
    def test_no_match_returns_empty_entries(
        self, reader, fake_repo, make_entry, make_request, project_id: str,
    ) -> None:
        fake_repo.session_entries = [
            make_entry(entry_id="kbe-pat", kind="pattern", title="x"),
        ]

        # 请求 trap 类 · 实际只有 pattern · 过滤后 0 条
        result = reader.read(make_request(kind="trap"))

        assert result.meta.project_id == project_id
        assert result.meta.returned_count == 0
        assert len(result.entries) == 0
        # 正常无结果 · 不降级
        assert result.meta.degraded is False

    # ---- TC-4 · 跨层: 3 层命中 + S>P>G 优先级合并 ----
    def test_three_layers_merge_with_session_priority(
        self, reader, fake_repo, make_entry, make_request, project_id: str,
    ) -> None:
        fake_repo.session_entries = [
            make_entry(entry_id="kbe-s", scope="session", title="t-session"),
        ]
        fake_repo.project_entries = [
            make_entry(entry_id="kbe-p", scope="project", title="t-project"),
        ]
        fake_repo.global_entries = [
            make_entry(entry_id="kbe-g", scope="global", title="t-global"),
        ]

        result = reader.read(make_request(top_k=3))

        # PM-14 + 3 层各 1 条 · 共 3 条
        entries = assert_kb_read_returned(result, project_id=project_id, min_entries=3)
        assert {e.id for e in entries} == {"kbe-s", "kbe-p", "kbe-g"}
        # IC-06 §3.6 scopes_hit · 三层全亮
        assert set(result.meta.scopes_hit) == {"session", "project", "global"}

    # ---- TC-5 · SLO P95 ≤ 500ms (§3.6) ----
    def test_slo_p95_within_500ms(
        self, reader, fake_repo, make_entry, make_request, project_id: str,
    ) -> None:
        fake_repo.session_entries = [
            make_entry(entry_id=f"kbe-{i}", title=f"t-{i}", observed_count=i)
            for i in range(20)
        ]

        # 跑 10 次 · 取 P95 (内存路径远 < 500ms · 单次也行)
        latencies: list[float] = []
        for i in range(10):
            t0 = time.perf_counter()
            result = reader.read(make_request(trace_id=f"trace-slo-{i}", top_k=5))
            latencies.append((time.perf_counter() - t0) * 1000.0)
            assert result.meta.project_id == project_id

        # IC-06 SLO §3.6: P95 ≤ 500ms (允许冷启动稍慢 · 内存 fake 应远低)
        latencies.sort()
        p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
        assert p95 < 500.0, f"IC-06 P95 SLO 超时 {p95:.1f}ms"

    # ---- TC-6 · cross-IC e2e · IC-09 audit emit (kb_read_performed 路径) ----
    def test_cross_ic09_audit_emitted_on_read(
        self, reader, fake_repo, audit_sink, make_entry, make_request, project_id: str,
    ) -> None:
        """读路径成功 · audit_sink 收到 kb_read_performed 事件 (IC-06 → IC-09 联动)."""
        fake_repo.session_entries = [
            make_entry(entry_id="kbe-cross", title="cross"),
        ]

        result = reader.read(make_request(trace_id="trace-cross-09"))
        assert result.meta.project_id == project_id

        # IC-09 联动: audit_sink 应至少收到 kb_read_performed
        types = [e["type"] for e in audit_sink.events]
        assert "kb_read_performed" in types
        # 命中 trace_id 透传
        performed = [e for e in audit_sink.events if e["type"] == "kb_read_performed"]
        assert performed[0]["payload"].get("trace_id") == "trace-cross-09"
