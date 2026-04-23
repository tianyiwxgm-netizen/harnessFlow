"""ε-WP06 · IC-02 get_next_wp 性能 bench · `architecture.md §10.1`：P95 ≤ 200ms。"""

from __future__ import annotations

import pytest

from app.l1_03.common.event_bus_stub import EventBusStub
from app.l1_03.scheduler import GetNextWPQuery, WPDispatcher
from app.l1_03.topology.manager import WBSTopologyManager

pytestmark = pytest.mark.perf


def test_bench_ic_02_get_next_wp(benchmark, project_id: str, make_wp) -> None:
    """IC-02 冷路径单次 < 200ms（V=10 WP 场景）· 每次 setup 全新 manager 避免 state 累积。"""

    def _setup() -> tuple[tuple[WPDispatcher, GetNextWPQuery], dict]:
        event_bus = EventBusStub()
        manager = WBSTopologyManager(project_id=project_id, event_bus=event_bus)
        wps = [make_wp(f"wp-{i:02d}") for i in range(10)]
        manager.load_topology(wps, [])
        dispatcher = WPDispatcher(manager, event_bus)
        q = GetNextWPQuery(
            query_id="q", project_id=project_id, requester_tick="t",
        )
        return (dispatcher, q), {}

    def _run(dispatcher: WPDispatcher, q: GetNextWPQuery) -> None:
        dispatcher.get_next_wp(q)

    benchmark.pedantic(_run, setup=_setup, rounds=30, iterations=1)
    # 单次调用（含 snapshot + 排序 + transition）应远低于 200ms · P95 ≤ 200ms
    assert benchmark.stats.stats.mean < 0.2
