"""L1-03 · WBS + WP 拓扑调度 · 5 L2 聚合。

L2-01 wbs_decomposer · L2-02 topology · L2-03 scheduler
L2-04 progress · L2-05 rollback

对外入口 IC-02（调度 · L2-03）+ IC-19（WBS 拆解 · L2-01）。
聚合根 `WBSTopologyManager` 持 DAG + 6 状态机。
"""

__all__ = [
    "topology",
    "scheduler",
    "wbs_decomposer",
    "progress",
    "rollback",
    "common",
]
