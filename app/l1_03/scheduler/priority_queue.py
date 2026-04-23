"""候选 WP 排序 · 关键路径优先 · 稳定顺序（wp_id asc）。

规则（`architecture.md §6.1` 调度四件套 · 步骤 3）：
    排序键 = (0 if wp_id in critical_set else 1, topo_level, -effort, wp_id)

- critical_path 节点优先（key 第一位）
- 相同类别内按拓扑层级（topo_level）升序 · 浅层先
- 同层按 effort desc（大工时先调度）
- 最后按 wp_id asc 稳定收束
"""

from __future__ import annotations

from collections.abc import Sequence

from app.l1_03.topology.snapshot import TopologySnapshot


def prioritize_candidates(
    wp_ids: Sequence[str],
    snapshot: TopologySnapshot,
    topo_layers: list[list[str]] | None = None,
    prefer_critical_path: bool = True,
) -> list[str]:
    """按调度四件套规则对候选 wp_id 排序。"""
    critical_set = frozenset(snapshot.critical_path) if prefer_critical_path else frozenset()
    layer_idx: dict[str, int] = {}
    if topo_layers:
        for idx, layer in enumerate(topo_layers):
            for wid in layer:
                layer_idx[wid] = idx

    def _sort_key(wp_id: str) -> tuple[int, int, float, str]:
        is_crit = 0 if wp_id in critical_set else 1
        level = layer_idx.get(wp_id, 0)
        effort = snapshot.wp_effort.get(wp_id, 0.0)
        return (is_crit, level, -effort, wp_id)

    return sorted(wp_ids, key=_sort_key)
