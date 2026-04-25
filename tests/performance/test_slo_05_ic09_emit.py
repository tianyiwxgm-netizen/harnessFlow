"""SLO-05 · ic_09_emit_p99 ≤ 50ms · event-bus single sink 写延迟.

阈值: 50ms (IC-09 §7.1 prd SLO · IC-09 自身契约)
来源: EventBus.append (jsonl + hash chain + fsync)

度量定义:
- EventBus.append(event) sync 调 wall ms
- 实测 P99 ≈ 1.8ms · 50ms 阈值含 25x 余量

6 TC:
- T1 baseline · 1000 次 append · P99 ≤ 50ms
- T2 cold start · 首 50 次 P99 ≤ 50ms (首次含 jsonl 文件创建)
- T3 持续 5 个滑窗 (5000 次)
- T4 降级 · 大 payload (~3KB · 接近 4KB 限) · P99 仍 ≤ 50ms
- T5 多 actor 多 type 混合 · 5 种 type 轮询 · P99 ≤ 50ms
- T6 退化告警 · 75ms 样本必触发
"""
from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.perf_helpers import LatencySample, assert_p99_under

SLO_BUDGET_MS = 50.0


def _make_event(pid: str, idx: int, *, actor: str = "main_loop", evt_type: str = "L1-01:decision_made", payload: dict | None = None) -> Event:
    return Event(
        project_id=pid,
        type=evt_type,
        actor=actor,
        payload=payload or {"i": idx},
        timestamp=datetime.now(UTC),
    )


@pytest.mark.perf
class TestSLO05IC09Emit:
    """SLO-05: ic_09_emit_p99 ≤ 50ms · 6 TC."""

    def test_t1_baseline_p99_under_50ms(self, tmp_path: Path) -> None:
        """T1 · 1000 次 append · P99 ≤ 50ms · 含 50 次 warmup."""
        bus = EventBus(tmp_path / "bus_t1")
        pid = f"perf-slo05-{uuid.uuid4().hex[:8]}"
        # warmup
        for i in range(50):
            bus.append(_make_event(pid, i))
        samples: list[LatencySample] = []
        for i in range(1000):
            evt = _make_event(pid, i)
            t0 = time.perf_counter()
            bus.append(evt)
            samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
        stats = assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="ic09_baseline")
        # 健康度: P50 应 < 10ms
        assert stats.p50 < 10.0, f"ic09 emit P50 {stats.p50:.3f}ms 异常"

    def test_t2_cold_start_p99_under_50ms(self, tmp_path: Path) -> None:
        """T2 · 冷启动首 50 次 · 含 events.jsonl 文件创建 · P99 仍 ≤ 50ms."""
        bus = EventBus(tmp_path / "bus_t2")
        pid = f"perf-slo05-cold-{uuid.uuid4().hex[:8]}"
        samples: list[LatencySample] = []
        for i in range(50):
            evt = _make_event(pid, i)
            t0 = time.perf_counter()
            bus.append(evt)
            samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
        assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="ic09_cold")

    def test_t3_sustained_5_windows(self, tmp_path: Path) -> None:
        """T3 · 持续 5000 次 append · 5 个滑窗 P99 全 ≤ 50ms."""
        bus = EventBus(tmp_path / "bus_t3")
        pid = f"perf-slo05-sus-{uuid.uuid4().hex[:8]}"
        for i in range(50):
            bus.append(_make_event(pid, i))
        ms_list: list[float] = []
        for i in range(5000):
            evt = _make_event(pid, i)
            t0 = time.perf_counter()
            bus.append(evt)
            ms_list.append((time.perf_counter() - t0) * 1000.0)
        for window_idx in range(5):
            window = ms_list[window_idx * 1000 : (window_idx + 1) * 1000]
            samples = [LatencySample(elapsed_ms=v) for v in window]
            assert_p99_under(
                samples, budget_ms=SLO_BUDGET_MS,
                metric_name=f"ic09_window_{window_idx}",
            )

    def test_t4_large_payload_p99_under_50ms(self, tmp_path: Path) -> None:
        """T4 · 降级 · 大 payload (~3KB) · 接近 4KB 单行限 · P99 仍 ≤ 50ms.

        IC-09 LineTooLargeError 4096B · 我们用 3000B 控贴限.
        """
        bus = EventBus(tmp_path / "bus_t4")
        pid = f"perf-slo05-big-{uuid.uuid4().hex[:8]}"
        big_blob = "x" * 3000
        for i in range(20):
            bus.append(_make_event(
                pid, i,
                actor="executor",
                evt_type="L1-08:multimodal_artifact_registered",
                payload={"blob": big_blob, "size": 3000, "i": i},
            ))
        samples: list[LatencySample] = []
        for i in range(200):
            evt = _make_event(
                pid, i,
                actor="executor",
                evt_type="L1-08:multimodal_artifact_registered",
                payload={"blob": big_blob, "size": 3000, "i": i},
            )
            t0 = time.perf_counter()
            bus.append(evt)
            samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
        assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="ic09_large_payload")

    def test_t5_multi_type_actor_round_robin(self, tmp_path: Path) -> None:
        """T5 · 多 type x actor 轮询 · 5 种事件类型 · P99 ≤ 50ms."""
        bus = EventBus(tmp_path / "bus_t5")
        pid = f"perf-slo05-rr-{uuid.uuid4().hex[:8]}"
        rotations = [
            ("L1-01:decision_made", "main_loop"),
            ("L1-04:verifier_report_issued", "verifier"),
            ("L1-05:skill_invoked", "main_loop"),
            ("L1-06:knowledge_queried", "main_loop"),
            ("L1-09:meta_event_persisted", "audit_mirror"),
        ]
        for i in range(50):
            t, a = rotations[i % len(rotations)]
            bus.append(_make_event(pid, i, actor=a, evt_type=t))
        samples: list[LatencySample] = []
        for i in range(1000):
            t, a = rotations[i % len(rotations)]
            evt = _make_event(pid, i, actor=a, evt_type=t)
            t0 = time.perf_counter()
            bus.append(evt)
            samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
        assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="ic09_5types")

    def test_t6_degradation_detection(self) -> None:
        """T6 · 退化告警 · 75ms 样本必触发 · 反向验证."""
        samples = [LatencySample(elapsed_ms=75.0) for _ in range(100)]
        with pytest.raises(AssertionError, match="SLO p99 超标"):
            assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="ic09_degraded")
        boundary = [LatencySample(elapsed_ms=49.0) for _ in range(100)]
        stats = assert_p99_under(
            boundary, budget_ms=SLO_BUDGET_MS, metric_name="ic09_boundary",
        )
        assert stats.p99 == 49.0
