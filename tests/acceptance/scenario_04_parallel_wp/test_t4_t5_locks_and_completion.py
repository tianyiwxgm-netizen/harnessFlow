"""Scenario 04 · T4-T5 · 锁互斥 (IC-10/11) + 5 WP 全完成.

T4: parallelism cap 守护 · 第 6 个 WP 起会被拒 (IC-10 lock)
T5: 5 WP 全 RUNNING → DONE · all-done 判定
"""
from __future__ import annotations

import pytest

from app.l1_03.common.errors import ParallelismCapError
from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.schemas import WorkPackage
from app.l1_03.topology.state_machine import State
from tests.shared.gwt_helpers import GWT


def test_t4_parallelism_cap_blocks_sixth_wp(
    project_id: str,
    make_wp,
    gwt: GWT,
) -> None:
    """T4 · parallelism_limit=5 · 第 6 个 WP READY→RUNNING 拒 (IC-10 锁互斥)."""
    with gwt("T4 · parallelism cap 守护 (IC-10/11 锁互斥)"):
        gwt.given("6 WP 加载 · parallelism_limit=5")
        manager = WBSTopologyManager(project_id=project_id, parallelism_limit=5)
        wps = [make_wp(f"wp-{i}") for i in range(1, 7)]
        manager.load_topology(wps, [])

        gwt.when("先起 5 个 WP RUNNING")
        for i in range(1, 6):
            manager.transition_state(f"wp-{i}", State.READY, State.RUNNING)
        snap = manager.read_snapshot()
        running_count = sum(1 for s in snap.wp_states.values() if s == State.RUNNING)
        assert running_count == 5

        gwt.then("第 6 个 WP READY→RUNNING 应被 ParallelismCapError 拒")
        with pytest.raises(ParallelismCapError):
            manager.transition_state("wp-6", State.READY, State.RUNNING)

        gwt.then("第 6 个 WP 仍 READY (并发上限保护)")
        snap = manager.read_snapshot()
        assert snap.wp_states["wp-6"] == State.READY


def test_t5_five_wps_all_complete(
    project_id: str,
    loaded_topo: WBSTopologyManager,
    gwt: GWT,
) -> None:
    """T5 · 5 WP READY→RUNNING→DONE 全完成 · all-done 判定."""
    with gwt("T5 · 5 WP 全完成 · all-done"):
        gwt.given("5 WP 全 READY")
        for i in range(1, 6):
            loaded_topo.transition_state(f"wp-{i}", State.READY, State.RUNNING)

        gwt.when("依次推 RUNNING → DONE 全 5 个")
        for i in range(1, 6):
            loaded_topo.transition_state(f"wp-{i}", State.RUNNING, State.DONE)

        gwt.then("5 WP 全 DONE · all-done 触发")
        snap = loaded_topo.read_snapshot()
        done = [w for w, s in snap.wp_states.items() if s == State.DONE]
        assert len(done) == 5
        assert all(s == State.DONE for s in snap.wp_states.values())
