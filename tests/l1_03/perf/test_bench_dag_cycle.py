"""ε-WP06 · DAG 环检测性能 bench · `architecture.md §10.1`：V ≤ 10 时 < 1ms。"""

from __future__ import annotations

import random

import pytest

from app.l1_03.topology.dag import assert_acyclic, build_digraph
from app.l1_03.topology.schemas import DAGEdge, WorkPackage

pytestmark = pytest.mark.perf


def _mk_wps(project_id: str, n: int) -> list[WorkPackage]:
    return [
        WorkPackage(
            wp_id=f"wp-{i:02d}", project_id=project_id,
            goal=f"g{i}", dod_expr_ref=f"dod{i}",
            deps=[], effort_estimate=1.0,
        )
        for i in range(n)
    ]


def _mk_random_dag_edges(n: int, density: float = 0.3) -> list[DAGEdge]:
    rng = random.Random(42)
    edges: list[DAGEdge] = []
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() < density:
                edges.append(DAGEdge(from_wp_id=f"wp-{i:02d}", to_wp_id=f"wp-{j:02d}"))
    return edges


def test_bench_dag_acyclic_check_v10(benchmark, project_id: str) -> None:
    """V=10 随机 DAG 环检测 · P95 < 1ms（architecture §10.1）。"""
    wps = _mk_wps(project_id, 10)
    edges = _mk_random_dag_edges(10)
    g = build_digraph(wps, edges)

    def _run() -> None:
        assert_acyclic(g)

    benchmark(_run)
    # pytest-benchmark 默认会打印统计 · 我们断言平均 < 1ms（1e-3s）
    assert benchmark.stats.stats.mean < 1e-3


def test_bench_dag_build_v10(benchmark, project_id: str) -> None:
    """V=10 装图 · < 5ms（含 node+edge 构建）。"""
    wps = _mk_wps(project_id, 10)
    edges = _mk_random_dag_edges(10)

    def _run() -> None:
        build_digraph(wps, edges)

    benchmark(_run)
    assert benchmark.stats.stats.mean < 5e-3
