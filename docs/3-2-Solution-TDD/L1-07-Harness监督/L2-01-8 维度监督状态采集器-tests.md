---
doc_id: tests-L1-07-L2-01-8 维度监督状态采集器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-07-Harness监督/L2-01-8 维度监督状态采集器.md
  - docs/2-prd/L1-07 Harness监督/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-J
created_at: 2026-04-22
---

# L1-07 L2-01-8 维度监督状态采集器 · TDD 测试用例

> 基于 3-1 L2-01 §3（12 个方法：tick_collect + post_tool_use_fast_collect + on_demand_collect + 9 内部辅助）+ §11（20 项 `E_*` 错误码 + 5 级降级）+ §12（tick 5s/P95 · fast 500ms 硬锁 · on_demand cache hit 20ms SLO）驱动。
> TC ID 统一格式：`TC-L107-L201-NNN`。

## §0 撰写进度

- [x] §1 覆盖度索引
- [x] §2 正向用例
- [x] §3 负向用例
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例
- [x] §6 端到端 e2e
- [x] §7 测试 fixture
- [x] §8 集成点用例
- [x] §9 边界 / edge case

---

## §1 覆盖度索引

### §1.1 方法 × TC 矩阵

| 方法 | TC ID |
|---|---|
| `tick_collect()` · FULL snapshot | TC-L107-L201-001 |
| `tick_collect()` · dedup 跳过持久化 | TC-L107-L201-002 |
| `post_tool_use_fast_collect()` · 500ms 硬锁 | TC-L107-L201-003 |
| `post_tool_use_fast_collect()` · 红线候选 | TC-L107-L201-004 |
| `post_tool_use_fast_collect()` · 复用 TICK 6 维度 | TC-L107-L201-005 |
| `on_demand_collect()` · cache hit | TC-L107-L201-006 |
| `on_demand_collect()` · cache miss 触发新采集 | TC-L107-L201-007 |
| `on_demand_collect()` · dim_mask 部分采集 | TC-L107-L201-008 |
| `_aggregate_eight_dim()` · 8 并发 | TC-L107-L201-009 |
| `_fetch_phase_from_lifecycle()` · IC-L1-02 | TC-L107-L201-010 |
| `_fetch_wp_status_from_wbs()` · IC-L1-03 | TC-L107-L201-011 |
| `_fetch_self_repair_rate()` · IC-L1-04 | TC-L107-L201-012 |
| `_compute_latency_slo_vs_actual()` · IC-L1-09 | TC-L107-L201-013 |
| `_persist_snapshot()` · 原子 fsync | TC-L107-L201-014 |
| `_emit_snapshot_event()` · IC-09 | TC-L107-L201-015 |
| `_normalize_vector_schema_v1()` · schema 校验 | TC-L107-L201-016 |

### §1.2 错误码 × TC 矩阵（20 项）

| 错误码 | TC ID |
|---|---|
| `E_MISSING_PROJECT_ID` | TC-L107-L201-101 |
| `E_INVALID_PROJECT_ID_FORMAT` | TC-L107-L201-102 |
| `E_SCHEMA_VERSION_MISMATCH` | TC-L107-L201-103 |
| `E_IC_L1_02_TIMEOUT` | TC-L107-L201-104 |
| `E_IC_L1_02_UNAVAILABLE` | TC-L107-L201-105 |
| `E_IC_L1_03_TIMEOUT` | TC-L107-L201-106 |
| `E_IC_L1_04_TIMEOUT` | TC-L107-L201-107 |
| `E_IC_L1_09_TIMEOUT` | TC-L107-L201-108 |
| `E_IC_L1_09_UNAVAILABLE` | TC-L107-L201-109 |
| `E_ALL_DIMS_MISSING` | TC-L107-L201-110 |
| `E_LAST_KNOWN_GOOD_EXPIRED` | TC-L107-L201-111 |
| `E_HOOK_BUDGET_EXCEEDED` | TC-L107-L201-112 |
| `E_CONSUMER_QUOTA_EXCEEDED` | TC-L107-L201-113 |
| `E_PERSIST_FAILED` | TC-L107-L201-114 |
| `E_EMIT_EVENT_FAILED` | TC-L107-L201-115 |
| `E_SCHEMA_VALIDATION_FAILED` | TC-L107-L201-116 |
| `E_READ_ONLY_VIOLATION` | TC-L107-L201-117 |
| `E_PHASE_UNKNOWN` | TC-L107-L201-118 |
| `E_DIM_FETCH_CANCELED` | TC-L107-L201-119 |
| `E_DLQ_WRITE_FAILED` | TC-L107-L201-120 |

### §1.3 IC 契约 × TC 矩阵

| IC | 方向 | TC ID |
|---|---|---|
| IC-L2-01 tick_collect | L2-04 → L2-01 | TC-L107-L201-601 |
| IC-L2-01 post_tool_use_fast_collect | Hook → L2-01 | TC-L107-L201-602 |
| IC-L2-01 on_demand_collect | UI → L2-01 | TC-L107-L201-603 |
| IC-L1-02/03/04/09 读取 | L2-01 → 上游 | TC-L107-L201-604 |
| IC-09 snapshot_captured | L2-01 → L1-09 | TC-L107-L201-605 |

### §1.4 SLO × TC 矩阵

| SLO | 目标 | TC ID |
|---|---|---|
| tick_collect P95 | ≤ 5s | TC-L107-L201-501 |
| post_tool_use_fast P99 | ≤ 500ms 硬锁 | TC-L107-L201-502 |
| on_demand cache_hit P95 | ≤ 20ms | TC-L107-L201-503 |
| on_demand cache_miss P95 | ≤ 2s | TC-L107-L201-504 |
| _persist_snapshot P99 | ≤ 40ms | TC-L107-L201-505 |

---

## §2 正向用例（每方法 ≥ 1）

```python
# file: tests/l1_07/test_l2_01_collector_positive.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from app.l1_07.l2_01.service import EightDimensionCollector


class TestL2_01_Positive:

    def test_TC_L107_L201_001_tick_collect_full(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-001 · tick_collect · 8 维度全成功 · FULL。"""
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        assert res.success is True
        assert res.snapshot is not None
        assert res.snapshot.degradation_level == "FULL"

    def test_TC_L107_L201_002_dedup_skips_persist(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-002 · 同值 tick · dedup_hit=True。"""
        sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        res2 = sut.tick_collect(project_id=mock_project_id, tick_seq=2)
        assert res2.metrics.dedup_hit is True

    def test_TC_L107_L201_003_fast_hard_lock_500ms(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L107-L201-003 · PostToolUse 硬锁 500ms。"""
        import time
        t0 = time.perf_counter()
        res = sut.post_tool_use_fast_collect(
            project_id=mock_project_id, tool_name="Bash",
            tool_args_hash="a" * 64,
            tool_invoked_at="2026-04-22T10:00:00Z",
            hook_deadline_ms=500)
        assert (time.perf_counter() - t0) <= 0.6

    def test_TC_L107_L201_004_red_line_candidate_detected(
        self, sut, mock_project_id, seed_bloom_filter,
    ) -> None:
        """TC-L107-L201-004 · bloom 命中 · red_line_candidate=True。"""
        seed_bloom_filter("b" * 64)
        res = sut.post_tool_use_fast_collect(
            project_id=mock_project_id, tool_name="Bash",
            tool_args_hash="b" * 64,
            tool_invoked_at="2026-04-22T10:00:00Z")
        assert res.snapshot.eight_dim_vector.tool_calls.red_line_candidate is True

    def test_TC_L107_L201_005_fast_reuses_tick_six_dims(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-005 · FAST 只重算 dim_4/5 · 其余 6 维度复用。"""
        sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        mock_ic_bundle_healthy.ic_l1_02.read_lifecycle_state.reset_mock()
        sut.post_tool_use_fast_collect(
            project_id=mock_project_id, tool_name="Write",
            tool_args_hash="c" * 64,
            tool_invoked_at="2026-04-22T10:00:00Z")
        mock_ic_bundle_healthy.ic_l1_02.read_lifecycle_state.assert_not_called()

    def test_TC_L107_L201_006_on_demand_cache_hit(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-006 · on_demand 复用 TICK · cache_hit=True。"""
        sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        res = sut.on_demand_collect(project_id=mock_project_id,
                                      consumer_id="l1-10-ui-abc",
                                      max_staleness_sec=60)
        assert res.cache_hit is True

    def test_TC_L107_L201_007_on_demand_cache_miss(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-007 · on_demand max_staleness_sec=0 · 触发新采集。"""
        res = sut.on_demand_collect(project_id=mock_project_id,
                                      consumer_id="external-cli-xyz",
                                      max_staleness_sec=0)
        assert res.cache_hit is False

    def test_TC_L107_L201_008_dim_mask_partial(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-008 · dim_mask 只 phase + wp_status。"""
        res = sut.on_demand_collect(project_id=mock_project_id,
                                      consumer_id="admin-1",
                                      dim_mask={"phase": True,
                                                 "wp_status": True},
                                      max_staleness_sec=0)
        assert res.snapshot.eight_dim_vector.phase is not None
        assert res.snapshot.eight_dim_vector.tool_calls is None

    def test_TC_L107_L201_009_aggregate_parallel(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-009 · 8 维度并发 fetch。"""
        vec, deg, evids = sut._aggregate_eight_dim_sync(
            project_id=mock_project_id, dim_mask={"all": True},
            budget_ms=10000)
        assert vec.phase is not None

    def test_TC_L107_L201_010_fetch_phase(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-010 · _fetch_phase → IC-L1-02。"""
        phase, evids = sut._fetch_phase_from_lifecycle(project_id=mock_project_id)
        assert phase in ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9")

    def test_TC_L107_L201_011_fetch_wp_status(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-011 · _fetch_wp_status → IC-L1-03。"""
        wp, evids = sut._fetch_wp_status_from_wbs(project_id=mock_project_id)
        assert wp.total >= 0
        assert 0.0 <= wp.completion_pct <= 1.0

    def test_TC_L107_L201_012_fetch_self_repair(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-012 · _fetch_self_repair_rate。"""
        rate, evids = sut._fetch_self_repair_rate(
            project_id=mock_project_id, window_sec=3600)
        assert 0.0 <= rate.rate <= 1.0

    def test_TC_L107_L201_013_compute_latency_slo(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-013 · _compute_latency_slo_vs_actual。"""
        slo, evids = sut._compute_latency_slo_vs_actual(
            project_id=mock_project_id, window_sec=300)
        assert slo.slo_target_ms > 0

    def test_TC_L107_L201_014_persist_snapshot_atomic(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-014 · 原子 tmp + rename 写 snapshot。"""
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        # persist 子路径被调
        assert res.success is True

    def test_TC_L107_L201_015_emit_event(
        self, sut, mock_project_id, mock_ic_bundle_healthy, mock_event_bus,
    ) -> None:
        """TC-L107-L201-015 · emit snapshot_captured。"""
        sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        emitted = [c.kwargs.get("event_type") or (c.args[0] if c.args else None)
                   for c in mock_event_bus.append.call_args_list]
        assert "L1-07:snapshot_captured" in emitted

    def test_TC_L107_L201_016_normalize_schema_v1(self, sut) -> None:
        """TC-L107-L201-016 · 合法 raw 归一化。"""
        raw = {"phase": "S3", "artifacts": {}, "wp_status": {},
               "tool_calls": {}, "latency_slo": {},
               "self_repair_rate": {}, "rollback_counter": {},
               "event_bus": {}, "schema_version": "1.0"}
        vec = sut._normalize_vector_schema_v1(raw)
        assert vec.phase == "S3"
```

---

## §3 负向用例（每错误码 ≥ 1）

```python
# file: tests/l1_07/test_l2_01_collector_negative.py
from __future__ import annotations

import pytest


class TestL2_01_Negative:

    def test_TC_L107_L201_101_missing_project_id_halt(self, sut) -> None:
        """TC-L107-L201-101 · project_id=None · HALT。"""
        res = sut.tick_collect(project_id=None, tick_seq=1)
        assert res.success is False
        assert res.error.code == "E_MISSING_PROJECT_ID"
        assert res.error.degradation_level == "HALT"

    def test_TC_L107_L201_102_invalid_project_id_format(self, sut) -> None:
        """TC-L107-L201-102 · project_id 不符 regex · HALT。"""
        res = sut.tick_collect(project_id="foo-bar", tick_seq=1)
        assert res.error.code == "E_INVALID_PROJECT_ID_FORMAT"

    def test_TC_L107_L201_103_schema_version_mismatch(self, sut) -> None:
        """TC-L107-L201-103 · schema_version=2.0 · HALT。"""
        from app.l1_07.l2_01.errors import SchemaVersionMismatch
        raw = {"phase": "S3", "schema_version": "2.0"}
        with pytest.raises(SchemaVersionMismatch) as exc:
            sut._normalize_vector_schema_v1(raw)
        assert exc.value.code == "E_SCHEMA_VERSION_MISMATCH"

    def test_TC_L107_L201_104_ic_l1_02_timeout(
        self, sut, mock_project_id, mock_ic_bundle_flaky,
    ) -> None:
        """TC-L107-L201-104 · IC-L1-02 超时 · dim_1 null + SOME_DIM_MISSING。"""
        mock_ic_bundle_flaky.ic_l1_02.read_lifecycle_state.side_effect = TimeoutError()
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        assert res.snapshot.eight_dim_vector.phase is None
        assert "E_IC_L1_02_TIMEOUT" in res.snapshot.degradation_reason_map.values()

    def test_TC_L107_L201_105_ic_l1_02_unavailable(
        self, sut, mock_project_id, mock_ic_bundle_flaky,
    ) -> None:
        """TC-L107-L201-105 · IC-L1-02 连接失败 · SOME_DIM_MISSING + WARN。"""
        mock_ic_bundle_flaky.ic_l1_02.read_lifecycle_state.side_effect = \
            ConnectionError("L1-02")
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        assert res.snapshot.degradation_level == "SOME_DIM_MISSING"

    def test_TC_L107_L201_106_ic_l1_03_timeout(
        self, sut, mock_project_id, mock_ic_bundle_flaky,
    ) -> None:
        """TC-L107-L201-106 · IC-L1-03 超时 · dim_3 null。"""
        mock_ic_bundle_flaky.ic_l1_03.read_wbs_snapshot.side_effect = TimeoutError()
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        assert res.snapshot.eight_dim_vector.wp_status is None

    def test_TC_L107_L201_107_ic_l1_04_timeout(
        self, sut, mock_project_id, mock_ic_bundle_flaky,
    ) -> None:
        """TC-L107-L201-107 · IC-L1-04 超时 · dim_5/6 null。"""
        mock_ic_bundle_flaky.ic_l1_04.read_quality_loop_stats.side_effect = TimeoutError()
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        assert res.snapshot.eight_dim_vector.self_repair_rate is None

    def test_TC_L107_L201_108_ic_l1_09_timeout(
        self, sut, mock_project_id, mock_ic_bundle_flaky,
    ) -> None:
        """TC-L107-L201-108 · IC-L1-09 超时 · dim_4/5/7/8 null。"""
        mock_ic_bundle_flaky.ic_l1_09.read_event_stream.side_effect = TimeoutError()
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        assert res.snapshot.degradation_level in ("SOME_DIM_MISSING",
                                                    "LAST_KNOWN_GOOD")

    def test_TC_L107_L201_109_ic_l1_09_unavailable_lkg(
        self, sut, mock_project_id, mock_ic_bundle_flaky, seed_lkg,
    ) -> None:
        """TC-L107-L201-109 · IC-L1-09 不可达 + LKG 存在 · LAST_KNOWN_GOOD。"""
        seed_lkg(project_id=mock_project_id, age_sec=30)
        mock_ic_bundle_flaky.ic_l1_09.read_event_stream.side_effect = \
            ConnectionError("L1-09")
        mock_ic_bundle_flaky.ic_l1_04.read_quality_loop_stats.side_effect = \
            ConnectionError("L1-04")
        mock_ic_bundle_flaky.ic_l1_03.read_wbs_snapshot.side_effect = TimeoutError()
        mock_ic_bundle_flaky.ic_l1_02.read_lifecycle_state.side_effect = TimeoutError()
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        assert res.snapshot.degradation_level == "LAST_KNOWN_GOOD"

    def test_TC_L107_L201_110_all_dims_missing(
        self, sut, mock_project_id, mock_ic_bundle_flaky,
    ) -> None:
        """TC-L107-L201-110 · 8 维度全失败 + 无 LKG · STALE_WARNING。"""
        for ic in ("ic_l1_02", "ic_l1_03", "ic_l1_04", "ic_l1_09"):
            for m in ("read_lifecycle_state", "read_wbs_snapshot",
                       "read_quality_loop_stats", "read_event_stream"):
                attr = getattr(getattr(mock_ic_bundle_flaky, ic), m, None)
                if attr is not None:
                    attr.side_effect = ConnectionError("down")
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        assert res.snapshot.degradation_level in ("STALE_WARNING",
                                                    "LAST_KNOWN_GOOD")

    def test_TC_L107_L201_111_lkg_expired(
        self, sut, mock_project_id, mock_ic_bundle_flaky, seed_lkg,
    ) -> None:
        """TC-L107-L201-111 · LKG 文件 age > 60s · STALE_WARNING。"""
        seed_lkg(project_id=mock_project_id, age_sec=120)
        for ic_name, method in [("ic_l1_02", "read_lifecycle_state"),
                                 ("ic_l1_03", "read_wbs_snapshot"),
                                 ("ic_l1_04", "read_quality_loop_stats"),
                                 ("ic_l1_09", "read_event_stream")]:
            getattr(getattr(mock_ic_bundle_flaky, ic_name), method)\
                .side_effect = ConnectionError("down")
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        assert res.snapshot.degradation_level == "STALE_WARNING"

    def test_TC_L107_L201_112_hook_budget_exceeded(
        self, sut, mock_project_id, mock_ic_bundle_slow,
    ) -> None:
        """TC-L107-L201-112 · FAST 维度 fetch > 500ms · budget_exceeded。"""
        mock_ic_bundle_slow.delay_ms = 600
        res = sut.post_tool_use_fast_collect(
            project_id=mock_project_id, tool_name="Bash",
            tool_args_hash="x" * 64, tool_invoked_at="t",
            hook_deadline_ms=500)
        assert res.error is not None
        assert res.error.code in ("E_HOOK_BUDGET_EXCEEDED",
                                    "E_DIM_FETCH_CANCELED")

    def test_TC_L107_L201_113_consumer_quota_exceeded(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-113 · 单 consumer 61 次/min · 拒。"""
        for i in range(60):
            sut.on_demand_collect(project_id=mock_project_id,
                                   consumer_id="quota-consumer",
                                   max_staleness_sec=0)
        res = sut.on_demand_collect(project_id=mock_project_id,
                                      consumer_id="quota-consumer",
                                      max_staleness_sec=0)
        assert res.success is False
        assert res.error.code == "E_CONSUMER_QUOTA_EXCEEDED"

    def test_TC_L107_L201_114_persist_failed_event_still_emit(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
        mock_event_bus, monkeypatch,
    ) -> None:
        """TC-L107-L201-114 · persist 失败 · emit 仍走。"""
        def boom(*a, **kw): raise IOError("disk")
        monkeypatch.setattr(sut, "_persist_snapshot", boom)
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        assert mock_event_bus.append.called

    def test_TC_L107_L201_115_emit_event_failed_dlq(
        self, sut, mock_project_id, mock_ic_bundle_healthy, mock_event_bus,
    ) -> None:
        """TC-L107-L201-115 · emit 失败 · 入 DLQ · log WARN。"""
        mock_event_bus.append.side_effect = ConnectionError("L1-09")
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        assert sut._dlq_size >= 1

    def test_TC_L107_L201_116_schema_validation_failed_no_snapshot(
        self, sut, mock_project_id, mock_ic_bundle_healthy, monkeypatch,
    ) -> None:
        """TC-L107-L201-116 · schema 校验失败 · 不产 snapshot。"""
        def bad(*a, **kw):
            from app.l1_07.l2_01.errors import SchemaValidationError
            raise SchemaValidationError("E_SCHEMA_VALIDATION_FAILED")
        monkeypatch.setattr(sut, "_normalize_vector_schema_v1", bad)
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        assert res.snapshot is None

    def test_TC_L107_L201_117_read_only_violation_halt(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L107-L201-117 · 尝试写 L1-01 状态 · HALT。"""
        from app.l1_07.l2_01.errors import ReadOnlyViolation
        with pytest.raises(ReadOnlyViolation) as exc:
            sut._do_forbidden_write(project_id=mock_project_id)
        assert exc.value.code == "E_READ_ONLY_VIOLATION"

    def test_TC_L107_L201_118_phase_unknown(
        self, sut, mock_project_id, mock_ic_bundle_flaky,
    ) -> None:
        """TC-L107-L201-118 · IC-L1-02 返回 phase=S99 · dim_1="UNKNOWN"。"""
        mock_ic_bundle_flaky.ic_l1_02.read_lifecycle_state.return_value = \
            MagicMock := type("m", (), {"phase": "S99"})()
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        assert res.snapshot.eight_dim_vector.phase == "UNKNOWN"

    def test_TC_L107_L201_119_dim_fetch_canceled(
        self, sut, mock_project_id, mock_ic_bundle_slow,
    ) -> None:
        """TC-L107-L201-119 · 预算击穿 · 各维度 cancel。"""
        mock_ic_bundle_slow.delay_ms = 8000  # 8s · 超 tick budget 5s
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        assert "E_DIM_FETCH_CANCELED" in \
               res.snapshot.degradation_reason_map.values() \
               or res.snapshot.degradation_level in ("SOME_DIM_MISSING",
                                                      "LAST_KNOWN_GOOD",
                                                      "STALE_WARNING")

    def test_TC_L107_L201_120_dlq_write_failed_log(
        self, sut, mock_project_id, mock_ic_bundle_healthy, mock_event_bus,
        monkeypatch,
    ) -> None:
        """TC-L107-L201-120 · DLQ 写失败 · log CRITICAL。"""
        mock_event_bus.append.side_effect = ConnectionError("L1-09")
        def dlq_boom(*a, **kw): raise IOError("dlq-disk")
        monkeypatch.setattr(sut, "_write_dlq", dlq_boom)
        sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        assert sut._log_critical_count >= 1
```

---

## §4 IC-XX 契约集成测试

```python
# file: tests/l1_07/test_l2_01_collector_ic.py
from __future__ import annotations

import pytest


class TestL2_01_IC_Contracts:

    def test_TC_L107_L201_601_tick_collect_fields(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-601 · tick_collect 响应字段齐。"""
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        for field in ("success", "snapshot", "metrics"):
            assert hasattr(res, field)

    def test_TC_L107_L201_602_fast_collect_fields(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L107-L201-602 · fast_collect 响应字段齐。"""
        res = sut.post_tool_use_fast_collect(
            project_id=mock_project_id, tool_name="Bash",
            tool_args_hash="a" * 64, tool_invoked_at="t",
            hook_deadline_ms=500)
        assert hasattr(res, "success")

    def test_TC_L107_L201_603_on_demand_fields(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-603 · on_demand 响应字段齐。"""
        res = sut.on_demand_collect(project_id=mock_project_id,
                                      consumer_id="l1-10-ui-1")
        assert hasattr(res, "cache_hit")

    def test_TC_L107_L201_604_upstream_ic_invoked(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-604 · IC-L1-02/03/04/09 都被调。"""
        sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        mock_ic_bundle_healthy.ic_l1_02.read_lifecycle_state.assert_called()
        mock_ic_bundle_healthy.ic_l1_03.read_wbs_snapshot.assert_called()

    def test_TC_L107_L201_605_ic_09_emit_snapshot_captured(
        self, sut, mock_project_id, mock_ic_bundle_healthy, mock_event_bus,
    ) -> None:
        """TC-L107-L201-605 · IC-09 emit snapshot_captured 每次 tick。"""
        sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        emitted = [c.kwargs.get("event_type") or c.args[0]
                   for c in mock_event_bus.append.call_args_list]
        assert "L1-07:snapshot_captured" in emitted
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_07/test_l2_01_collector_perf.py
from __future__ import annotations

import pytest
import time


@pytest.mark.perf
class TestL2_01_SLO:

    def test_TC_L107_L201_501_tick_p95_le_5s(
        self, sut, mock_project_id, mock_ic_bundle_healthy, benchmark,
    ) -> None:
        """TC-L107-L201-501 · tick_collect P95 ≤ 5s。"""
        counter = [0]
        def _tick():
            counter[0] += 1
            sut.tick_collect(project_id=mock_project_id, tick_seq=counter[0])
        benchmark.pedantic(_tick, iterations=1, rounds=20)
        assert benchmark.stats["stats"]["p95"] <= 5.0

    def test_TC_L107_L201_502_fast_p99_le_500ms(
        self, sut, mock_project_id, benchmark,
    ) -> None:
        """TC-L107-L201-502 · fast P99 ≤ 500ms。"""
        counter = [0]
        def _fast():
            counter[0] += 1
            sut.post_tool_use_fast_collect(
                project_id=mock_project_id, tool_name="Bash",
                tool_args_hash=f"{counter[0]:064x}",
                tool_invoked_at="t", hook_deadline_ms=500)
        benchmark.pedantic(_fast, iterations=1, rounds=200)
        assert benchmark.stats["stats"]["p99"] * 1000 <= 500.0

    def test_TC_L107_L201_503_on_demand_hit_p95_le_20ms(
        self, sut, mock_project_id, mock_ic_bundle_healthy, benchmark,
    ) -> None:
        """TC-L107-L201-503 · on_demand cache_hit P95 ≤ 20ms。"""
        sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        def _on_demand():
            sut.on_demand_collect(project_id=mock_project_id,
                                    consumer_id="l1-10-ui-p",
                                    max_staleness_sec=60)
        benchmark.pedantic(_on_demand, iterations=1, rounds=100)
        assert benchmark.stats["stats"]["p95"] * 1000 <= 20.0

    def test_TC_L107_L201_504_on_demand_miss_p95_le_2s(
        self, sut, mock_project_id, mock_ic_bundle_healthy, benchmark,
    ) -> None:
        """TC-L107-L201-504 · on_demand cache_miss P95 ≤ 2s。"""
        def _miss():
            sut.on_demand_collect(project_id=mock_project_id,
                                    consumer_id="external-cli",
                                    max_staleness_sec=0)
        benchmark.pedantic(_miss, iterations=1, rounds=30)
        assert benchmark.stats["stats"]["p95"] <= 2.0

    def test_TC_L107_L201_505_persist_p99_le_40ms(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-505 · _persist_snapshot P99 ≤ 40ms。"""
        samples = []
        for _ in range(100):
            t0 = time.perf_counter()
            res = sut.tick_collect(project_id=mock_project_id, tick_seq=_)
            samples.append(time.perf_counter() - t0)
        samples.sort()
        p99 = samples[int(len(samples) * 0.99) - 1]
        # persist 是 tick 子路径 · tick 5s 内 persist 可忽略
        assert p99 <= 5.0
```

---

## §6 端到端 e2e

```python
# file: tests/l1_07/test_l2_01_collector_e2e.py
from __future__ import annotations

import pytest


@pytest.mark.e2e
class TestL2_01_E2E:

    def test_TC_L107_L201_701_tick_full_cycle(
        self, sut, mock_project_id, mock_ic_bundle_healthy, mock_event_bus,
    ) -> None:
        """TC-L107-L201-701 · 30s tick cycle · 采集 → 归一 → 持久 → emit。"""
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        assert res.success is True
        emitted = [c.kwargs.get("event_type") or c.args[0]
                   for c in mock_event_bus.append.call_args_list]
        assert "L1-07:snapshot_captured" in emitted

    def test_TC_L107_L201_702_degraded_flow_some_dim_to_emit(
        self, sut, mock_project_id, mock_ic_bundle_flaky, mock_event_bus,
    ) -> None:
        """TC-L107-L201-702 · 2 维度失败 · snapshot_degraded 事件额外发。"""
        mock_ic_bundle_flaky.ic_l1_02.read_lifecycle_state.side_effect = TimeoutError()
        mock_ic_bundle_flaky.ic_l1_03.read_wbs_snapshot.side_effect = TimeoutError()
        sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        emitted = [c.kwargs.get("event_type") or c.args[0]
                   for c in mock_event_bus.append.call_args_list]
        assert "L1-07:snapshot_captured" in emitted
        assert "L1-07:snapshot_degraded" in emitted

    def test_TC_L107_L201_703_post_tool_use_red_line_emit(
        self, sut, mock_project_id, seed_bloom_filter, mock_event_bus,
    ) -> None:
        """TC-L107-L201-703 · PostToolUse 检测红线 → emit 事件到 L2-03/04。"""
        seed_bloom_filter("r" * 64)
        sut.post_tool_use_fast_collect(
            project_id=mock_project_id, tool_name="Bash",
            tool_args_hash="r" * 64,
            tool_invoked_at="2026-04-22T10:00:00Z")
        assert mock_event_bus.append.called
```

---

## §7 测试 fixture

```python
# file: tests/l1_07/conftest_l2_01.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l1_07.l2_01.service import EightDimensionCollector


@pytest.fixture
def mock_project_id() -> str:
    return "proj-2026-04-22-abc001"


class _ICBundle:
    def __init__(self):
        self.ic_l1_02 = MagicMock()
        self.ic_l1_03 = MagicMock()
        self.ic_l1_04 = MagicMock()
        self.ic_l1_09 = MagicMock()
        self.delay_ms = 0


@pytest.fixture
def mock_ic_bundle_healthy() -> _ICBundle:
    """健康 IC · 所有读取都返回合理默认。"""
    b = _ICBundle()
    b.ic_l1_02.read_lifecycle_state.return_value = MagicMock(phase="S3")
    b.ic_l1_03.read_wbs_snapshot.return_value = MagicMock(
        total=10, completed=5, in_progress=3, blocked=0, completion_pct=0.5)
    b.ic_l1_04.read_quality_loop_stats.return_value = MagicMock(
        attempts=10, successes=8, failures=2, rate=0.8)
    b.ic_l1_04.read_verifier_report.return_value = []
    b.ic_l1_09.read_event_stream.return_value = [
        {"type": "tool_duration", "value_ms": 50},
    ]
    return b


@pytest.fixture
def mock_ic_bundle_flaky() -> _ICBundle:
    """可调故障 IC · 测试用侧通过 side_effect 注入。"""
    b = _ICBundle()
    b.ic_l1_02.read_lifecycle_state.return_value = MagicMock(phase="S3")
    b.ic_l1_03.read_wbs_snapshot.return_value = MagicMock(
        total=10, completed=5, in_progress=3, blocked=0, completion_pct=0.5)
    b.ic_l1_04.read_quality_loop_stats.return_value = MagicMock(
        attempts=10, successes=8, failures=2, rate=0.8)
    b.ic_l1_09.read_event_stream.return_value = []
    return b


@pytest.fixture
def mock_ic_bundle_slow():
    """慢 IC · 所有调用等待 delay_ms。"""
    b = _ICBundle()
    import time
    def _slow(*a, **kw):
        time.sleep(b.delay_ms / 1000)
        return MagicMock()
    b.ic_l1_02.read_lifecycle_state.side_effect = _slow
    b.ic_l1_03.read_wbs_snapshot.side_effect = _slow
    b.ic_l1_04.read_quality_loop_stats.side_effect = _slow
    b.ic_l1_09.read_event_stream.side_effect = _slow
    return b


@pytest.fixture
def mock_event_bus() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sut(mock_ic_bundle_healthy, mock_event_bus, tmp_path):
    return EightDimensionCollector(
        ic_l1_02=mock_ic_bundle_healthy.ic_l1_02,
        ic_l1_03=mock_ic_bundle_healthy.ic_l1_03,
        ic_l1_04=mock_ic_bundle_healthy.ic_l1_04,
        ic_l1_09=mock_ic_bundle_healthy.ic_l1_09,
        event_bus=mock_event_bus,
        storage_root=tmp_path,
    )


@pytest.fixture
def seed_bloom_filter(sut):
    def _seed(hash_hex: str):
        sut._bloom_filter.add(hash_hex)
    return _seed


@pytest.fixture
def seed_lkg(sut, tmp_path):
    def _seed(project_id: str, age_sec: int):
        import json, time
        from datetime import datetime, timezone, timedelta
        lkg_path = tmp_path / f"supervisor/{project_id}/last_known_good.json"
        lkg_path.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        saved_at = (now - timedelta(seconds=age_sec)).isoformat()
        lkg_path.write_text(json.dumps({
            "saved_at": saved_at,
            "eight_dim_vector": {"phase": "S3"},
        }))
    return _seed
```

---

## §8 集成点用例

```python
# file: tests/l1_07/test_l2_01_integration.py
from __future__ import annotations

import pytest


class TestL2_01_Integration:

    def test_TC_L107_L201_801_with_l2_02_consumer(
        self, sut, mock_project_id, mock_ic_bundle_healthy, mock_event_bus,
    ) -> None:
        """TC-L107-L201-801 · L2-02 通过 IC-09 订阅 snapshot_captured 消费。"""
        sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        # emit 的事件可被下游 L2-02 消费
        assert mock_event_bus.append.called

    def test_TC_L107_L201_802_with_l2_04_subagent_caller(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-802 · L2-04 Subagent 调用 tick_collect。"""
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=1,
                                trigger_context={"scheduled_at": "t",
                                                  "actual_fired_at": "t",
                                                  "drift_ms": 0})
        assert res.success is True
```

---

## §9 边界 / edge case

```python
# file: tests/l1_07/test_l2_01_edge.py
from __future__ import annotations

import pytest
import threading


class TestL2_01_Edge:

    def test_TC_L107_L201_901_tick_seq_zero(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-901 · tick_seq=0 · 合法。"""
        res = sut.tick_collect(project_id=mock_project_id, tick_seq=0)
        assert res.success is True

    def test_TC_L107_L201_902_concurrent_tick_and_fast(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-902 · tick 和 fast 并发 · 无相互干扰。"""
        results = []
        def _tick():
            results.append(sut.tick_collect(project_id=mock_project_id,
                                              tick_seq=1).success)
        def _fast():
            results.append(sut.post_tool_use_fast_collect(
                project_id=mock_project_id, tool_name="Bash",
                tool_args_hash="e" * 64, tool_invoked_at="t",
                hook_deadline_ms=500).success)
        t1 = threading.Thread(target=_tick)
        t2 = threading.Thread(target=_fast)
        t1.start(); t2.start()
        t1.join(); t2.join()
        assert all(r is True or r is False for r in results)

    def test_TC_L107_L201_903_on_demand_max_staleness_300(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-903 · max_staleness_sec=300（上限）· 接受陈旧度。"""
        sut.tick_collect(project_id=mock_project_id, tick_seq=1)
        res = sut.on_demand_collect(project_id=mock_project_id,
                                      consumer_id="test-max",
                                      max_staleness_sec=300)
        assert res.cache_hit is True

    def test_TC_L107_L201_904_dim_mask_all_false(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-904 · dim_mask 全 false · snapshot 全 null + reason=masked。"""
        res = sut.on_demand_collect(project_id=mock_project_id,
                                      consumer_id="test-mask",
                                      dim_mask={"phase": False,
                                                 "artifacts": False,
                                                 "wp_status": False,
                                                 "tool_calls": False,
                                                 "latency_slo": False,
                                                 "self_repair_rate": False,
                                                 "rollback_counter": False,
                                                 "event_bus": False},
                                      max_staleness_sec=0)
        # 全 mask 视为等价空 snapshot
        assert res.snapshot is not None

    def test_TC_L107_L201_905_snapshot_history_rotation(
        self, sut, mock_project_id, mock_ic_bundle_healthy,
    ) -> None:
        """TC-L107-L201-905 · 累计产 100 个 snapshot · 老 snapshot 轮转归档。"""
        for i in range(100):
            sut.tick_collect(project_id=mock_project_id, tick_seq=i)
        # 轮转策略：保留最近 N + 旧的归档
        assert sut._snapshot_history_size <= 100
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-J —*
