"""L2-01 · WBS 拆解器 · IC-19 入口。

职责（`architecture.md §2.2`）：
- `decompose_wbs(four_set_plan, architecture_output, target_granularity) -> WBSDraft`
- `diff_merge(old_topology, new_wbs) -> WBSDraft`（保留 RUNNING/DONE）
- 调 L1-05 `wbs-decomposer` skill（IC-04）做实际 LLM 拆解 · 本 L2 编排。

对外 IC：
- 接收 IC-19 · `request_wbs_decomposition_command` · 同步 accepted + 异步事件 `L1-03:wbs_topology_ready`。
- 发起 IC-04（调 L1-05 skill）· 同步。
"""

from app.l1_03.wbs_decomposer.diff_merge import diff_merge
from app.l1_03.wbs_decomposer.factory import WBSFactory, decompose_wbs
from app.l1_03.wbs_decomposer.schemas import (
    ArchitectureOutput,
    DecompositionSession,
    FourSetPlan,
    RequestWBSDecompositionCommand,
    RequestWBSDecompositionResult,
    TargetGranularity,
    WBSDraft,
)
from app.l1_03.wbs_decomposer.skill_invoker import SkillInvoker

__all__ = [
    "FourSetPlan",
    "ArchitectureOutput",
    "TargetGranularity",
    "WBSDraft",
    "RequestWBSDecompositionCommand",
    "RequestWBSDecompositionResult",
    "DecompositionSession",
    "WBSFactory",
    "decompose_wbs",
    "diff_merge",
    "SkillInvoker",
]
