"""WBSFactory · L2-01 核心类 · `decompose_wbs()` 是 IC-19 主入口。

编排：
1. 校验 IC-19 入参（已由 pydantic 拦 · 此层只捕异常映射错误码）
2. 调 SkillInvoker 拿 raw WP list + edges
3. 对每 WP 二次校验 4 要素 + effort ≤ 5 天
4. 构建 WBSDraft
5. 发 IC-09 `L1-03:wbs_topology_ready` 事件（异步签 · 由 bus 负责分发到 L1-02 / S3 驱动）

关键错误码（IC-19 §3.19.4）：
- E_WBS_NO_PROJECT_ID
- E_WBS_4_PACK_INCOMPLETE
- E_WBS_ARCH_OUTPUT_MISSING
- E_WBS_DECOMPOSITION_FAIL
- E_WBS_TOPOLOGY_CORRUPT
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import ValidationError

from app.l1_03.common.errors import (
    IncompleteWPError,
    L103Error,
    OversizeError,
)
from app.l1_03.topology.schemas import EFFORT_LIMIT_DAYS, DAGEdge, WorkPackage
from app.l1_03.wbs_decomposer.schemas import (
    ArchitectureOutput,
    FourSetPlan,
    RequestWBSDecompositionCommand,
    RequestWBSDecompositionResult,
    TargetGranularity,
    WBSDraft,
)
from app.l1_03.wbs_decomposer.skill_invoker import SkillClientLike, SkillInvoker


class WBSError(L103Error):
    """IC-19 反馈语义的基础错误（E_WBS_xxx）· 不与 L2-02 的 E_L103_L202_xxx 冲突。"""

    code: str = "E_WBS_UNKNOWN"


class NoProjectIdError(WBSError):
    code = "E_WBS_NO_PROJECT_ID"

    def __init__(self) -> None:
        super().__init__("IC-19 入参缺 project_id")


class FourPackIncompleteError(WBSError):
    code = "E_WBS_4_PACK_INCOMPLETE"

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__("IC-19 artifacts_4_pack 不完整", missing=missing)


class ArchOutputMissingError(WBSError):
    code = "E_WBS_ARCH_OUTPUT_MISSING"

    def __init__(self) -> None:
        super().__init__("IC-19 architecture_output 缺失")


class DecompositionFailError(WBSError):
    code = "E_WBS_DECOMPOSITION_FAIL"

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__("skill 拆解失败", reason=reason)


class TopologyCorruptError(WBSError):
    code = "E_WBS_TOPOLOGY_CORRUPT"

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__("生成的 WBSDraft 拓扑损坏", reason=reason)


def _new_session_id() -> str:
    return f"decomp-{uuid.uuid4().hex[:12]}"


def _new_version() -> str:
    return f"topo-v-{uuid.uuid4().hex[:12]}"


class WBSFactory:
    """L2-01 主类。"""

    def __init__(
        self,
        skill_client: SkillClientLike,
        event_bus: Any | None = None,
    ) -> None:
        self._invoker = SkillInvoker(skill_client)
        self._event_bus = event_bus
        self._last_draft: WBSDraft | None = None
        self._last_session_id: str | None = None

    def handle_ic_19(
        self,
        command: RequestWBSDecompositionCommand,
    ) -> RequestWBSDecompositionResult:
        """IC-19 主入口 · 同步 accepted + 同步 or 异步拆解（本实现先同步）。

        单机 v1：本 stub 里拆解是同步的；真实 prod 可改异步 + IC-09 事件通知。
        """
        try:
            self._validate_command(command)
        except WBSError as exc:
            return RequestWBSDecompositionResult(
                command_id=command.command_id,
                accepted=False,
                reason=exc.args[0] if exc.args else "",
                error_code=exc.code,
            )

        session_id = _new_session_id()
        try:
            if command.mode == "full":
                wps, edges = self._invoker.decompose_full(
                    project_id=command.project_id,
                    four_set_plan=command.artifacts_4_pack.model_dump(),
                    architecture_output=command.architecture_output.model_dump(),
                    target_granularity=str(command.target_wp_granularity),
                )
            else:
                assert command.target_wp_id is not None  # pydantic 已拦
                wps, edges = self._invoker.decompose_incremental(
                    project_id=command.project_id,
                    target_wp_id=command.target_wp_id,
                    four_set_plan=command.artifacts_4_pack.model_dump(),
                    architecture_output=command.architecture_output.model_dump(),
                )
        except NotImplementedError as exc:
            raise DecompositionFailError(reason=f"skill 能力未接入：{exc}") from exc
        except (IncompleteWPError, OversizeError):
            # 业务语义错误：保留原类型让上层按 L1-03 错误码处理
            raise
        except ValidationError as exc:
            raise TopologyCorruptError(reason=f"skill 返回字段不合法：{exc}") from exc
        except ValueError as exc:
            # 例如 skill_invoker._parse 里的 "wp_list 为空"
            raise TopologyCorruptError(reason=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 — 其它异常降级为 skill 调用失败
            raise DecompositionFailError(reason=str(exc)) from exc

        # 4 要素 + effort 硬限 的二次 check（pydantic 层已拦，这里转 WBS 错误码）
        self._assert_wps_valid(wps)
        draft = self._build_draft(
            project_id=command.project_id,
            wps=wps,
            edges=edges,
        )

        self._emit_ready(session_id, command.project_id, draft)
        self._last_draft = draft
        self._last_session_id = session_id

        return RequestWBSDecompositionResult(
            command_id=command.command_id,
            accepted=True,
            decomposition_session_id=session_id,
        )

    @property
    def last_draft(self) -> WBSDraft | None:
        return self._last_draft

    @property
    def last_session_id(self) -> str | None:
        return self._last_session_id

    # ----- helpers -----

    @staticmethod
    def _validate_command(cmd: RequestWBSDecompositionCommand) -> None:
        if not cmd.project_id:
            raise NoProjectIdError()
        pack = cmd.artifacts_4_pack
        missing = [
            name
            for name in ("charter_path", "plan_path", "requirements_path", "risk_path")
            if not getattr(pack, name)
        ]
        if missing:
            raise FourPackIncompleteError(missing=missing)
        if not cmd.architecture_output.adr_path:
            raise ArchOutputMissingError()

    @staticmethod
    def _assert_wps_valid(wps: list[WorkPackage]) -> None:
        for wp in wps:
            if not (wp.goal and wp.dod_expr_ref):
                raise IncompleteWPError(
                    wp_id=wp.wp_id,
                    missing_fields=[
                        f for f in ("goal", "dod_expr_ref") if not getattr(wp, f)
                    ],
                )
            if wp.effort_estimate > EFFORT_LIMIT_DAYS:
                raise OversizeError(wp_id=wp.wp_id, effort=wp.effort_estimate)

    @staticmethod
    def _build_draft(
        project_id: str,
        wps: list[WorkPackage],
        edges: list[DAGEdge],
    ) -> WBSDraft:
        # PM-14：外层 wps 里任一 project_id 不对 → TopologyCorruptError
        bad = [w.wp_id for w in wps if w.project_id != project_id]
        if bad:
            raise TopologyCorruptError(
                reason=f"wps 跨 project：{bad} · expected_pid={project_id!r}"
            )
        return WBSDraft(
            project_id=project_id,
            topology_version=_new_version(),
            wp_list=wps,
            dag_edges=edges,
            critical_path_wp_ids=[],  # 由 L2-02 装图后回填
        )

    def _emit_ready(
        self,
        session_id: str,
        project_id: str,
        draft: WBSDraft,
    ) -> None:
        if self._event_bus is None:
            return
        self._event_bus.append(
            event_type="L1-03:wbs_topology_ready",
            content={
                "decomposition_session_id": session_id,
                "topology_version": draft.topology_version,
                "wp_count": draft.wp_count,
                "critical_path_wp_ids": list(draft.critical_path_wp_ids),
                "estimated_duration_h": draft.estimated_duration_h,
            },
            project_id=project_id,
        )


def decompose_wbs(
    four_set_plan: FourSetPlan | dict[str, str],
    architecture_output: ArchitectureOutput | dict[str, Any],
    *,
    project_id: str,
    skill_client: SkillClientLike,
    event_bus: Any | None = None,
    target_granularity: TargetGranularity | str = TargetGranularity.MEDIUM,
    mode: str = "full",
    target_wp_id: str | None = None,
    command_id: str | None = None,
) -> WBSDraft:
    """便捷函数 · 构 IC-19 cmd + 走 WBSFactory · 返回 WBSDraft（不是 result 包）。

    场景：组内部直接拿 WBSDraft 去 L2-02 装图（非 IC-19 远端 call）。
    """
    if isinstance(four_set_plan, dict):
        four_set_plan = FourSetPlan(**four_set_plan)
    if isinstance(architecture_output, dict):
        architecture_output = ArchitectureOutput(**architecture_output)
    if isinstance(target_granularity, str):
        target_granularity = TargetGranularity(target_granularity)

    cmd = RequestWBSDecompositionCommand(
        command_id=command_id or f"wbs-req-{uuid.uuid4().hex[:12]}",
        project_id=project_id,
        artifacts_4_pack=four_set_plan,
        architecture_output=architecture_output,
        target_wp_granularity=target_granularity,
        mode=mode,  # type: ignore[arg-type]
        target_wp_id=target_wp_id,
    )
    factory = WBSFactory(skill_client=skill_client, event_bus=event_bus)
    result = factory.handle_ic_19(cmd)
    if not result.accepted:
        # 外层便捷函数抛异常更自然
        raise WBSError(f"IC-19 被拒：{result.reason}", error_code=result.error_code)
    draft = factory.last_draft
    if draft is None:
        # 理论上 accepted=True 必有 draft，防御性 assertion
        raise RuntimeError("factory accepted 但未记录 last_draft")
    return draft
