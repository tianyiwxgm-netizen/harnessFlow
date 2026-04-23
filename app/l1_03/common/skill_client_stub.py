"""IC-04 `invoke_skill` 的 stub（仅 wbs-decomposer 相关 capability）。

真实实现由 L1-05（Dev-γ）`app/l1_05/l2_03_skill/` 提供 · 契约：
- `invoke_skill(capability: str, params: dict) -> dict`
- 同步返回 · 长任务由 L1-05 内部异步（本 stub 不模拟异步）

本 stub 支持：
- `capability="wbs.decompose"`：按 `params["target_granularity"]` 返固定 fixture WBS
- `capability="wbs.decompose_incremental"`：返 subtree 替换 fixture
- 其他 capability → NotImplementedError
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class SkillClientStub:
    """L1-05 skill 调用 stub。

    `register(capability, handler)` 可以让测试覆盖默认 handler；
    `invoke_skill` 按 capability 路由到 handler，不存在 → NotImplementedError。
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "wbs.decompose": self._default_decompose,
            "wbs.decompose_incremental": self._default_decompose_incremental,
        }
        self.invocations: list[tuple[str, dict[str, Any]]] = []

    def invoke_skill(
        self,
        capability: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        self.invocations.append((capability, dict(params)))
        if capability not in self._handlers:
            raise NotImplementedError(
                f"SkillClientStub 未注册 capability={capability!r}"
            )
        return self._handlers[capability](params)

    def register(
        self,
        capability: str,
        handler: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        self._handlers[capability] = handler

    def reset(self) -> None:
        self.invocations.clear()

    # --- 默认 handler ---

    @staticmethod
    def _default_decompose(params: dict[str, Any]) -> dict[str, Any]:
        pid = params.get("project_id", "pid-stub")
        return {
            "wp_list": [
                {
                    "wp_id": "wp-a", "project_id": pid, "goal": "stub-a",
                    "dod_expr_ref": "dod-a", "deps": [], "effort_estimate": 2.0,
                    "recommended_skills": [],
                },
                {
                    "wp_id": "wp-b", "project_id": pid, "goal": "stub-b",
                    "dod_expr_ref": "dod-b", "deps": ["wp-a"], "effort_estimate": 1.5,
                    "recommended_skills": [],
                },
                {
                    "wp_id": "wp-c", "project_id": pid, "goal": "stub-c",
                    "dod_expr_ref": "dod-c", "deps": ["wp-a"], "effort_estimate": 3.0,
                    "recommended_skills": [],
                },
            ],
            "edges": [
                {"from_wp_id": "wp-a", "to_wp_id": "wp-b"},
                {"from_wp_id": "wp-a", "to_wp_id": "wp-c"},
            ],
        }

    @staticmethod
    def _default_decompose_incremental(params: dict[str, Any]) -> dict[str, Any]:
        target = params.get("target_wp_id", "wp-x")
        pid = params.get("project_id", "pid-stub")
        return {
            "wp_list": [
                {
                    "wp_id": f"{target}-sub1", "project_id": pid,
                    "goal": "subtree1", "dod_expr_ref": "dod-sub1",
                    "deps": [], "effort_estimate": 1.0,
                    "recommended_skills": [],
                },
                {
                    "wp_id": f"{target}-sub2", "project_id": pid,
                    "goal": "subtree2", "dod_expr_ref": "dod-sub2",
                    "deps": [f"{target}-sub1"], "effort_estimate": 1.5,
                    "recommended_skills": [],
                },
            ],
            "edges": [
                {
                    "from_wp_id": f"{target}-sub1",
                    "to_wp_id": f"{target}-sub2",
                },
            ],
        }
