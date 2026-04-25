"""IC-02 · 负向 / PM-14 / SLO · 5 TC.

覆盖:
    TC-1 · 非法跃迁(READY → DONE 跨度) → IllegalTransition · 不 emit
    TC-2 · stale state(实际 != from_state) → StaleStateError · 不 emit
    TC-3 · wp_id 不存在 → WPNotFoundError · 不 emit
    TC-4 · 跨 pid: WBSTopologyManager 跨 pid 不接受 wp(load 时拒)
    TC-5 · SLO: transition_state P99 ≤ 200ms(20 次采样)
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.l1_03.common.errors import (
    IllegalTransition,
    PM14MismatchError,
    StaleStateError,
    WPNotFoundError,
)
from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.state_machine import State
from tests.shared.ic_assertions import assert_ic_09_emitted, list_events


class TestIC02Negative:
    """非法跃迁 / stale / wp_id / 跨 pid · 4 TC."""

    # ---- TC-1 · 非法跃迁 READY → DONE(跨度) ----
    def test_illegal_transition_raises(
        self,
        manager: WBSTopologyManager,
        linear_wbs,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        wps, edges = linear_wbs
        manager.load_topology(wps, edges)

        # 装图 emit 一条 wbs_decomposed · 记录基线
        before = len(list_events(
            event_bus_root, project_id,
            type_exact="L1-03:wp_state_changed",
        ))

        with pytest.raises(IllegalTransition):
            manager.transition_state("wp-001", State.READY, State.DONE)

        # 不应再 emit 任何 wp_state_changed
        after = list_events(
            event_bus_root, project_id,
            type_exact="L1-03:wp_state_changed",
        )
        assert len(after) == before, (
            f"非法跃迁不应 emit · 期望={before} 实际={len(after)}"
        )
        # WP 状态保持 READY
        assert manager.find_wp("wp-001").state == State.READY

    # ---- TC-2 · stale state ----
    def test_stale_state_raises(
        self,
        manager: WBSTopologyManager,
        linear_wbs,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        wps, edges = linear_wbs
        manager.load_topology(wps, edges)

        # 当前是 READY · 但传 from_state=RUNNING(stale)
        with pytest.raises(StaleStateError):
            manager.transition_state("wp-001", State.RUNNING, State.DONE)

        # 不 emit
        events = list_events(
            event_bus_root, project_id,
            type_exact="L1-03:wp_state_changed",
        )
        assert len(events) == 0

    # ---- TC-3 · wp_id 不存在 ----
    def test_unknown_wp_id_raises(
        self,
        manager: WBSTopologyManager,
        linear_wbs,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        wps, edges = linear_wbs
        manager.load_topology(wps, edges)

        with pytest.raises(WPNotFoundError):
            manager.transition_state("wp-NONEXIST", State.READY, State.RUNNING)

        events = list_events(
            event_bus_root, project_id,
            type_exact="L1-03:wp_state_changed",
        )
        assert len(events) == 0

    # ---- TC-4 · 跨 pid load 拒(PM14MismatchError) ----
    def test_cross_pid_wp_rejected_at_load(
        self,
        manager: WBSTopologyManager,
        make_wp,
        other_project_id: str,
    ) -> None:
        # 构造一个属于其他 pid 的 WP
        bad_wp = make_wp("wp-bad", proj=other_project_id)
        with pytest.raises(PM14MismatchError):
            manager.load_topology([bad_wp])


class TestIC02SLO:
    """IC-02 SLO · transition_state 单次延迟 ≤ 200ms · 20 次采样."""

    def test_transition_state_p99_under_200ms(
        self,
        manager: WBSTopologyManager,
        make_wp,
    ) -> None:
        # 装单个 WP · 反复 READY ⇄ RUNNING 切换不可(state_machine 7 边只单向)
        # 改为 20 次独立 manager + 一次 READY → RUNNING
        latencies: list[float] = []
        for i in range(20):
            mgr = WBSTopologyManager(project_id="proj-ic02-slo", event_bus=None)
            wp = make_wp(f"wp-{i}", proj="proj-ic02-slo")
            mgr.load_topology([wp])
            t0 = time.perf_counter()
            mgr.transition_state(f"wp-{i}", State.READY, State.RUNNING)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)

        latencies.sort()
        p99_idx = max(0, int(len(latencies) * 0.99) - 1)
        p99 = latencies[p99_idx]
        assert p99 < 200.0, (
            f"IC-02 transition_state SLO 违规 P99={p99:.2f}ms 期望<200ms · "
            f"全部样本(ms)={[f'{x:.2f}' for x in latencies]}"
        )
