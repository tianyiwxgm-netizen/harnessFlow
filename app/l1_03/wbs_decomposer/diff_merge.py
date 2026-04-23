"""L2-01 差量合并 · change_request / 失败回退后重新拆解时用。

策略（`architecture.md §5.3`）：
1. 保留旧 topology 里 `state in {RUNNING, DONE}` 的 WP（身份不变）。
2. 新 WBS 中若丢弃了某 RUNNING WP → 拒绝（`RunningWPCannotBeDropped`）。
3. 合并：preserved + new_wps → 新 WBSDraft；重建 edges。
4. 差量装图性能 ≤ 全量 1/4（`architecture.md §10.1`）。
"""

from __future__ import annotations

from app.l1_03.common.errors import RunningWPCannotBeDropped
from app.l1_03.topology.schemas import DAGEdge, WBSTopology, WorkPackage
from app.l1_03.topology.state_machine import State
from app.l1_03.wbs_decomposer.schemas import WBSDraft


def diff_merge(
    old_topology: WBSTopology,
    new_wps: list[WorkPackage],
    new_edges: list[DAGEdge],
    new_topology_version: str,
    critical_path_wp_ids: list[str] | None = None,
) -> WBSDraft:
    """把新 wp_list 与旧 topology 中 RUNNING/DONE 的 WP 合并。

    - 旧 RUNNING/DONE WP 原样保留（身份不变 / state 不变）· 即使新 WBS 同 wp_id 也以旧为准。
    - 旧 RUNNING WP 若新 WBS 未提 → 拒绝（RunningWPCannotBeDropped）。
    - 新旧同 wp_id 但旧是 READY/FAILED/BLOCKED/STUCK：以新为准（允许 L2-05 回退改造）。
    - edges 以新为准（旧 edges 可能因差量而失效）。
    """
    new_ids = {w.wp_id for w in new_wps}
    preserved: list[WorkPackage] = []
    new_idx = {w.wp_id: w for w in new_wps}

    for old_wp in old_topology.wp_list:
        if old_wp.state in (State.RUNNING, State.DONE):
            # running/done 不可丢
            if old_wp.wp_id not in new_ids:
                # 允许 DONE WP 被 drop（项目已完成那段）· RUNNING 绝对禁止
                if old_wp.state == State.RUNNING:
                    raise RunningWPCannotBeDropped(wp_id=old_wp.wp_id)
                continue
            preserved.append(old_wp.model_copy())
            new_idx.pop(old_wp.wp_id, None)  # 用旧替新

    merged: list[WorkPackage] = preserved + list(new_idx.values())

    return WBSDraft(
        project_id=old_topology.project_id,
        topology_version=new_topology_version,
        wp_list=merged,
        dag_edges=new_edges,
        critical_path_wp_ids=critical_path_wp_ids or [],
    )
