"""L2-02 · 拓扑图管理器 · WBSTopology 聚合根。

对外暴露：
- State（6 状态 · enum）
- LEGAL_TRANSITIONS（7 条合法跃迁 · frozenset · 单点定义）
- WorkPackage / DAGEdge / CriticalPath / WBSTopology（schemas）
- TopologySnapshot（只读视图 VO）
- WBSTopologyManager（聚合根实现）
"""

from app.l1_03.topology.dag import (
    assert_acyclic,
    build_digraph,
    compute_critical_path,
    topological_generations,
)
from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.schemas import (
    CriticalPath,
    DAGEdge,
    WBSTopology,
    WorkPackage,
)
from app.l1_03.topology.snapshot import TopologySnapshot, read_snapshot
from app.l1_03.topology.state_machine import (
    LEGAL_TRANSITIONS,
    State,
    assert_transition,
    is_legal,
)

__all__ = [
    "State",
    "LEGAL_TRANSITIONS",
    "assert_transition",
    "is_legal",
    "WorkPackage",
    "DAGEdge",
    "CriticalPath",
    "WBSTopology",
    "TopologySnapshot",
    "read_snapshot",
    "build_digraph",
    "assert_acyclic",
    "compute_critical_path",
    "topological_generations",
    "WBSTopologyManager",
]
