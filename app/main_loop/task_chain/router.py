"""L1-01 L2-04 · Router · decision_type → L1 target + IC payload (WP05 简化).

对齐:
    - L2-04 §3 / §4 (本 L2 下游 IC 表)
    - Task 描述 4 路:
        state_transition → L1-02 IC-01 (stage_gate · Dev-δ)
        get_next_wp      → L1-03 IC-02 (l1_03 scheduler · Dev-ε)
        assign_wp        → L1-03 IC-03 (l1_03 scheduler · Dev-ε)
        invoke_skill     → L1-05 IC-04 (skill_dispatch · Dev-γ)

错误码:
    - E_CHAIN_NO_PROJECT_ID   · ctx.project_id 缺失 (PM-14)
    - E_CHAIN_CROSS_PROJECT   · ChosenAction.decision_params.project_id ≠ ctx.project_id
    - E_CHAIN_ACTION_UNSUPPORTED · decision_type 不在 ROUTABLE 白名单
    - E_CHAIN_DEF_INVALID     · 必填字段缺失 (如 state_transition 无 to_state)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.main_loop.decision_engine.schemas import ChosenAction

from .schemas import ROUTABLE_DECISION_TYPES, RouteDecision

# =========================================================
# RouteTarget · 路由结果的精简三元组 (target_l1 / ic_code / ic_builder)
# 仅内部使用 · 测试需访问时走 RouteDecision
# =========================================================


@dataclass(frozen=True)
class RouteTarget:
    """路由目标 · decision_type → target_l1 / ic_code 对照。"""

    target_l1: str
    ic_code: str


DECISION_TYPE_TO_TARGET: dict[str, RouteTarget] = {
    "state_transition": RouteTarget(target_l1="L1-02", ic_code="IC-01"),
    "get_next_wp":      RouteTarget(target_l1="L1-03", ic_code="IC-02"),
    "assign_wp":        RouteTarget(target_l1="L1-03", ic_code="IC-03"),
    "invoke_skill":     RouteTarget(target_l1="L1-05", ic_code="IC-04"),
}


# =========================================================
# 错误码 (字符串常量 · 供 TaskChainResult.rejection_reason 填充)
# =========================================================

E_CHAIN_NO_PROJECT_ID = "E_CHAIN_NO_PROJECT_ID"
E_CHAIN_CROSS_PROJECT = "E_CHAIN_CROSS_PROJECT"
E_CHAIN_ACTION_UNSUPPORTED = "E_CHAIN_ACTION_UNSUPPORTED"
E_CHAIN_DEF_INVALID = "E_CHAIN_DEF_INVALID"


class RouterError(ValueError):
    """Router 抛出的前置校验异常 · 携带 E_CHAIN_* 码."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


# =========================================================
# 主入口 · route_decision()
# =========================================================


def route_decision(
    action: ChosenAction,
    *,
    project_id: str,
    decision_id: str | None = None,
) -> RouteDecision:
    """将 WP03 产出的 ChosenAction 路由为 RouteDecision.

    Args:
        action: WP03 decide() 返回的 ChosenAction (frozen · 含 decision_type/params).
        project_id: ctx.project_id (PM-14 根;必填 · 不空).
        decision_id: 审计追溯 id · 可选 (空则后续由 spawner 生成).

    Returns:
        RouteDecision · 含 target_l1 / ic_code / 拼装好的 ic_payload.

    Raises:
        RouterError:
            - E_CHAIN_NO_PROJECT_ID   (project_id 空)
            - E_CHAIN_CROSS_PROJECT   (params.project_id ≠ project_id)
            - E_CHAIN_ACTION_UNSUPPORTED (decision_type 非 ROUTABLE)
            - E_CHAIN_DEF_INVALID     (必填 params 字段缺失)
    """
    # 1. project_id 必填
    if not project_id:
        raise RouterError(
            E_CHAIN_NO_PROJECT_ID,
            "project_id is empty (PM-14 root missing)",
        )

    # 2. decision_type 白名单
    dt = action.decision_type
    if dt not in ROUTABLE_DECISION_TYPES:
        raise RouterError(
            E_CHAIN_ACTION_UNSUPPORTED,
            f"decision_type={dt!r} not in ROUTABLE {sorted(ROUTABLE_DECISION_TYPES)}",
        )

    # 3. 跨 project 校验 (若 params 声明 project_id 必须匹配 ctx)
    params = action.decision_params or {}
    params_pid = params.get("project_id")
    if params_pid and params_pid != project_id:
        raise RouterError(
            E_CHAIN_CROSS_PROJECT,
            f"params.project_id={params_pid!r} != ctx.project_id={project_id!r}",
        )

    target = DECISION_TYPE_TO_TARGET[dt]

    # 4. 按 decision_type 拼 ic_payload + 提取 wp_id
    payload, wp_id = _build_payload_and_wp_id(dt, params, project_id)

    return RouteDecision(
        decision_type=dt,
        target_l1=target.target_l1,
        ic_code=target.ic_code,
        ic_payload=payload,
        project_id=project_id,
        wp_id=wp_id,
        decision_id=decision_id,
    )


def _build_payload_and_wp_id(
    decision_type: str,
    params: dict[str, Any],
    project_id: str,
) -> tuple[dict[str, Any], str | None]:
    """按 decision_type 拼装 IC payload 并抽取 wp_id.

    约定:
        - state_transition: 需 from_state / to_state / reason;wp_id 可选.
        - get_next_wp:      仅需 requester_tick;wp_id 无 (返回值才是 wp).
        - assign_wp:        需 wp_id · 必填.
        - invoke_skill:     需 capability · 必填;wp_id 可选 (若该 skill 服务某 wp).
    """
    payload: dict[str, Any] = {"project_id": project_id}
    wp_id: str | None = None

    if decision_type == "state_transition":
        to_state = params.get("to_state")
        if not to_state:
            raise RouterError(
                E_CHAIN_DEF_INVALID,
                "state_transition: missing required field 'to_state'",
            )
        payload.update({
            "from_state": params.get("from_state"),  # 允许 None (首次 S0)
            "to_state": to_state,
            "reason": params.get("reason", ""),
            "trigger_tick": params.get("trigger_tick"),
            "evidence_refs": tuple(params.get("evidence_refs") or ()),
            "gate_id": params.get("gate_id"),
        })
        # state_transition 可能附带 wp_id (某 wp 完成触发 state_transition)
        wp_id = params.get("wp_id")

    elif decision_type == "get_next_wp":
        payload.update({
            "query_id": params.get("query_id"),
            "requester_tick": params.get("requester_tick"),
            "topology_id": params.get("topology_id"),
        })
        # get_next_wp 不携带 wp_id (wp 是查询结果)

    elif decision_type == "assign_wp":
        wp_id = params.get("wp_id")
        if not wp_id:
            raise RouterError(
                E_CHAIN_DEF_INVALID,
                "assign_wp: missing required field 'wp_id'",
            )
        payload.update({
            "wp_id": wp_id,
            "assignee": params.get("assignee"),
            "assigner_tick": params.get("assigner_tick"),
        })

    elif decision_type == "invoke_skill":
        capability = params.get("capability")
        if not capability:
            raise RouterError(
                E_CHAIN_DEF_INVALID,
                "invoke_skill: missing required field 'capability'",
            )
        payload.update({
            "invocation_id": params.get("invocation_id"),
            "capability": capability,
            "params": params.get("params") or {},
            "caller_l1": params.get("caller_l1", "L1-01"),
            "context": params.get("context") or {"project_id": project_id},
            "timeout_ms": params.get("timeout_ms", 30000),
            "allow_fallback": params.get("allow_fallback", True),
        })
        wp_id = params.get("wp_id")

    return payload, wp_id


__all__ = [
    "DECISION_TYPE_TO_TARGET",
    "E_CHAIN_ACTION_UNSUPPORTED",
    "E_CHAIN_CROSS_PROJECT",
    "E_CHAIN_DEF_INVALID",
    "E_CHAIN_NO_PROJECT_ID",
    "RouteTarget",
    "RouterError",
    "route_decision",
]
