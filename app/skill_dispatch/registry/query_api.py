"""L2-01 读接口 · 绑定 snapshot · 双 buffer swap() 供热更新原子替换.

4 个查询方法:
  query_candidates(capability) -> list[SkillSpec]       # 候选链 · builtin_fallback 末尾
  query_subagent(name) -> SubagentEntry                 # 子 Agent 角色注册
  query_tool(tool_name) -> ToolEntry                    # 原子/组合工具
  query_schema_pointer(capability) -> str               # 回传 schema 指针

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-01-Skill 注册表.md §3.2-3.5
  - docs/superpowers/plans/Dev-γ-impl.md §3 Task 01.3
"""
from __future__ import annotations

from .schemas import RegistrySnapshot, SkillSpec, SubagentEntry, ToolEntry


class CapabilityNotFoundError(KeyError):
    """E_REG_MISSING_CAPABILITY."""


class NoAvailableCapabilityError(CapabilityNotFoundError):
    """E_INTENT_NO_AVAILABLE · 候选存在但全部被 Constraints 过滤（availability/cost/timeout）.

    继承自 `CapabilityNotFoundError` · 使 SkillExecutor Phase 1 原有
    `except CapabilityNotFoundError` 捕获路径直接覆盖"无候选可选"场景 · 落 success=false
    · 不向调用方 raise（契约红线：IC-04 全链失败不 raise）.
    """


class SubagentNotFoundError(KeyError):
    """E_REG_MISSING_SUBAGENT."""


class ToolNotFoundError(KeyError):
    """E_REG_MISSING_TOOL."""


class RegistryQueryAPI:
    """绑定 snapshot · 读取四类注册信息.

    热更新时 · fs_watcher 生成新 snapshot · 调 swap() 原子替换（单赋值 Python 原子）.
    """

    def __init__(self, snapshot: RegistrySnapshot) -> None:
        self._snap = snapshot

    @property
    def snapshot(self) -> RegistrySnapshot:
        return self._snap

    def swap(self, new_snapshot: RegistrySnapshot) -> None:
        """原子替换 snapshot · 由热更新路径驱动（Task 01.5 fs_watcher）."""
        self._snap = new_snapshot

    def query_candidates(self, capability: str) -> list[SkillSpec]:
        cp = self._snap.capability_points.get(capability)
        if cp is None:
            raise CapabilityNotFoundError(f"E_REG_MISSING_CAPABILITY: {capability!r}")
        # 内建兜底始终排在末尾（排序稳定 · 不丢原顺序）
        non_fb = [c for c in cp.candidates if not c.is_builtin_fallback]
        fb = [c for c in cp.candidates if c.is_builtin_fallback]
        return non_fb + fb

    def query_subagent(self, name: str) -> SubagentEntry:
        se = self._snap.subagents.get(name)
        if se is None:
            raise SubagentNotFoundError(f"E_REG_MISSING_SUBAGENT: {name!r}")
        return se

    def query_tool(self, tool_name: str) -> ToolEntry:
        te = self._snap.tools.get(tool_name)
        if te is None:
            raise ToolNotFoundError(f"E_REG_MISSING_TOOL: {tool_name!r}")
        return te

    def query_schema_pointer(self, capability: str) -> str:
        cp = self._snap.capability_points.get(capability)
        if cp is None:
            raise CapabilityNotFoundError(f"E_REG_MISSING_CAPABILITY: {capability!r}")
        return cp.schema_pointer
