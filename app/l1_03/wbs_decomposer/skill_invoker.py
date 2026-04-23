"""L2-01 → L1-05 skill 调用的薄层。

IC-04 `invoke_skill(capability, params) -> dict` · 同步。
本层把 L2-01 内部 domain 对象（FourSetPlan / ArchitectureOutput）序列化为 skill params，
再把 skill 返回的 raw dict 反序列化为 `WorkPackage` + `DAGEdge`。

真实 L1-05 客户端到位后，只需把 SkillClientStub 换成真实 client 即可，不改本模块。
"""

from __future__ import annotations

from typing import Any, Protocol

from app.l1_03.topology.schemas import DAGEdge, WorkPackage


class SkillClientLike(Protocol):
    """Duck-type：任何有 `invoke_skill(capability, params) -> dict` 的对象都可注入。"""

    def invoke_skill(self, capability: str, params: dict[str, Any]) -> dict[str, Any]:
        ...


class SkillInvoker:
    """封装 `wbs.decompose` / `wbs.decompose_incremental` 两类 skill 调用。"""

    CAPABILITY_FULL = "wbs.decompose"
    CAPABILITY_INCREMENTAL = "wbs.decompose_incremental"

    def __init__(self, client: SkillClientLike) -> None:
        self._client = client

    def decompose_full(
        self,
        project_id: str,
        four_set_plan: dict[str, str],
        architecture_output: dict[str, Any],
        target_granularity: str,
    ) -> tuple[list[WorkPackage], list[DAGEdge]]:
        params = {
            "project_id": project_id,
            "four_set_plan": four_set_plan,
            "architecture_output": architecture_output,
            "target_granularity": target_granularity,
        }
        raw = self._client.invoke_skill(self.CAPABILITY_FULL, params)
        return self._parse(raw)

    def decompose_incremental(
        self,
        project_id: str,
        target_wp_id: str,
        four_set_plan: dict[str, str],
        architecture_output: dict[str, Any],
    ) -> tuple[list[WorkPackage], list[DAGEdge]]:
        params = {
            "project_id": project_id,
            "target_wp_id": target_wp_id,
            "four_set_plan": four_set_plan,
            "architecture_output": architecture_output,
        }
        raw = self._client.invoke_skill(self.CAPABILITY_INCREMENTAL, params)
        return self._parse(raw)

    @staticmethod
    def _parse(
        raw: dict[str, Any],
    ) -> tuple[list[WorkPackage], list[DAGEdge]]:
        wp_list_raw = raw.get("wp_list")
        edges_raw = raw.get("edges", [])
        if not isinstance(wp_list_raw, list) or not wp_list_raw:
            raise ValueError(
                "skill 返回缺 wp_list 或为空 · 无法构建 WBSDraft"
            )
        wps = [WorkPackage.model_validate(w) for w in wp_list_raw]
        edges = [DAGEdge.model_validate(e) for e in edges_raw]
        return wps, edges
