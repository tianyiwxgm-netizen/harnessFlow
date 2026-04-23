"""NetworkX DAG 封装 · 环检测 · 关键路径 · 拓扑分层。

选型 `architecture.md §5.1`：NetworkX 3.x · 零外部服务 · BSD-3 · O(V+E) 算法完备。
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import networkx as nx

from app.l1_03.common.errors import CycleError
from app.l1_03.topology.schemas import DAGEdge, WorkPackage


def build_digraph(
    wps: Sequence[WorkPackage],
    edges: Iterable[DAGEdge],
) -> nx.DiGraph:
    """根据 WP + edges 构 `networkx.DiGraph`。

    节点属性：`effort`（float · WP 自身工时）、`state`（str）、`project_id`（str）。
    边属性：`weight` = 终点节点的 `effort`（PERT 惯例 · 让 `dag_longest_path` 走最大工时路径）。
    同一 (from, to) 边重复加 NetworkX 会去重（DiGraph 语义）· 不 raise。
    """
    g: nx.DiGraph = nx.DiGraph()
    effort_by_id: dict[str, float] = {}
    for wp in wps:
        effort_by_id[wp.wp_id] = float(wp.effort_estimate)
        g.add_node(
            wp.wp_id,
            effort=float(wp.effort_estimate),
            state=str(wp.state),
            project_id=wp.project_id,
        )
    for e in edges:
        target_effort = effort_by_id.get(e.to_wp_id, 0.0)
        g.add_edge(e.from_wp_id, e.to_wp_id, weight=target_effort)
    return g


def assert_acyclic(g: nx.DiGraph) -> None:
    """不是 DAG → `CycleError(cycle=[(u,v), ...])` · 成本 O(V+E)。"""
    if not nx.is_directed_acyclic_graph(g):
        try:
            cycle_edges = list(nx.find_cycle(g, orientation="original"))
            # find_cycle 可能返 3/4-tuple 视版本 · 统一成 (u, v)
            cycle: list[tuple[str, str]] = [(edge[0], edge[1]) for edge in cycle_edges]
        except nx.NetworkXNoCycle:  # pragma: no cover — 按 is_directed_acyclic_graph 已判否，不应到达
            cycle = []
        raise CycleError(cycle=cycle)


def compute_critical_path(g: nx.DiGraph) -> list[str]:
    """关键路径 = `dag_longest_path` by edge `weight`（建图时设为终点 effort）。

    空图 / 无边图返 []（networkx 对无边图返回任一节点 · 这里对齐业务语义）。
    """
    if g.number_of_nodes() == 0:
        return []
    if g.number_of_edges() == 0:
        return []
    return list(nx.dag_longest_path(g, weight="weight", default_weight=0.0))


def topological_generations(g: nx.DiGraph) -> list[list[str]]:
    """分层拓扑排序 · 每层内 WP 可并行 · 顺序按 node id 稳定。"""
    return [sorted(layer) for layer in nx.topological_generations(g)]


def descendants(g: nx.DiGraph, wp_id: str) -> set[str]:
    """某 WP 的所有下游（差量拆解用 · `incremental_decompose`）。"""
    if wp_id not in g:
        return set()
    return set(nx.descendants(g, wp_id))
