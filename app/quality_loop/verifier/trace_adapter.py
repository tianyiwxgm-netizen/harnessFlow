"""L1-04 · L2-06 · trace_adapter · 适配 L2-05 S4 ExecutionTrace → VerificationRequest.

**职责**：把 L2-05 (WP05 · main-2 并行) 产出的 S4 ExecutionTrace 翻译成本 L2 的入参 VO。

**并发协议**（Exe-plan §3 WP06）：
- WP05 (main-2) 并发进行中 · 尚未合 main
- 本模块定义 `ExecutionTrace` 的 **最小字段 Protocol 接口** · 不引 WP05 实现
- 当 WP05 merged 后 · 可无缝替换为 WP05 的真实类型
- mock 场景下可直接传 dict / 任意对象，只要 duck-type 匹配

**最小契约字段**：
- `project_id`   · PM-14（必有）
- `wp_id`        · 本 WP（必有）
- `git_head`     · S4 结束时的 commit sha（必有）
- `artifact_refs` · S4 产物路径清单（必有 · 可空列表）
- `test_report`  · 测试报告 dict（可选 · None = 尚无）
- `blueprint_slice` · TDD 蓝图切片（WP02 蓝图器产 · WP05 传透）
- `acceptance_criteria` · quality_gates 子集（WP04 产）
- `main_session_id` · 主 session id（PM-03 用于前缀校验）
- `ts`           · ISO8601 时间戳

**锚点**：
- L2-06 §2.3 VerifierWorkPackage schema
- IC-20 §3.20.2 入参 delegate_verifier_command
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from app.quality_loop.verifier.schemas import VerificationRequest, VerifierError


class TraceAdapterError(VerifierError):
    """trace_adapter 适配失败（缺字段 / schema 违反）.

    错误码对齐 L2-06 §3.12：
    - `E06 missing_blueprint_artifact` · blueprint_slice 缺失
    - `E10 s4_snapshot_invalid`        · S4 快照 schema 违反
    """


@runtime_checkable
class ExecutionTraceLike(Protocol):
    """S4 ExecutionTrace 鸭子类型协议（Dev-ζ WP05 产 · 本 WP 只读）.

    任何提供以下只读属性的对象都可以作为 trace 传入 `adapt_from_s4`。

    **PM-14**：`project_id` 必为非空字符串。
    """

    project_id: str
    wp_id: str
    git_head: str
    artifact_refs: tuple[str, ...] | list[str]
    test_report: dict[str, Any] | None
    blueprint_slice: dict[str, Any]
    acceptance_criteria: dict[str, Any]
    main_session_id: str
    ts: str


@dataclass(frozen=True)
class MockExecutionTrace:
    """WP05 尚未 merged 前的 mock trace 类型.

    **用途**：
    - 本 WP06 TC 里直接构造 · 避免等 WP05
    - trace_adapter 演示/集成测试 · 提供最小字段
    - 生产环境 WP05 merged 后应替换为真实类型（Protocol 保证兼容）
    """

    project_id: str
    wp_id: str
    git_head: str
    blueprint_slice: dict[str, Any]
    main_session_id: str
    ts: str
    artifact_refs: tuple[str, ...] = ()
    test_report: dict[str, Any] | None = None
    acceptance_criteria: dict[str, Any] = field(default_factory=dict)


def adapt_from_s4(
    trace: ExecutionTraceLike,
    *,
    timeout_s: int = 1200,
    delegation_id: str | None = None,
) -> VerificationRequest:
    """把 S4 ExecutionTrace → VerificationRequest.

    Args:
        trace: ExecutionTraceLike · WP05 产的 S4 执行轨迹（或 mock 对象）
        timeout_s: verifier 超时秒数（默认 1200 秒 = 20 min · §3.20.2）
        delegation_id: 幂等 key；None 则自动生成 `ver-{uuid-v7-hex}`

    Returns:
        VerificationRequest · frozen VO

    Raises:
        TraceAdapterError: trace 缺字段 / schema 违反
    """
    # 1. 基础字段校验（PM-14 + 必要性）
    if not trace.project_id or not trace.project_id.strip():
        raise TraceAdapterError("E_VER_NO_PROJECT_ID: trace.project_id is empty")
    if not trace.wp_id or not trace.wp_id.strip():
        raise TraceAdapterError("E10_s4_snapshot_invalid: trace.wp_id is empty")
    if not trace.git_head:
        raise TraceAdapterError("E10_s4_snapshot_invalid: trace.git_head is empty")
    if not trace.main_session_id:
        raise TraceAdapterError("E07_main_session_id_collision: trace.main_session_id missing")

    # 2. blueprint_slice 必有（E06）
    if not trace.blueprint_slice:
        raise TraceAdapterError(
            "E06_missing_blueprint_artifact: trace.blueprint_slice is empty",
        )

    # 3. 组 s4_snapshot dict（IC-20 §3.20.2 字段）
    artifact_refs_list = list(trace.artifact_refs) if trace.artifact_refs else []
    s4_snapshot: dict[str, Any] = {
        "artifact_refs": artifact_refs_list,
        "git_head": trace.git_head,
    }
    if trace.test_report is not None:
        s4_snapshot["test_report"] = dict(trace.test_report)

    # 4. delegation_id 幂等 key（按 (wp_id, git_head) 决定；可外部指定）
    if delegation_id is None:
        delegation_id = _gen_delegation_id(trace.wp_id, trace.git_head)

    # 5. 构造 VerificationRequest
    return VerificationRequest(
        project_id=trace.project_id,
        wp_id=trace.wp_id,
        blueprint_slice=dict(trace.blueprint_slice),
        s4_snapshot=s4_snapshot,
        acceptance_criteria=dict(trace.acceptance_criteria or {}),
        main_session_id=trace.main_session_id,
        delegation_id=delegation_id,
        timeout_s=timeout_s,
        ts=trace.ts,
    )


def _gen_delegation_id(wp_id: str, git_head: str) -> str:
    """幂等 delegation_id 生成（`ver-{uuid4-hex-12}`）.

    **幂等规则**：本函数无法做到跨会话幂等（需外部存储 (wp_id, git_head) → delegation_id
    映射才真幂等）· 本 WP 仅提供格式合法的 uuid-hex 字符串。

    上游 L2-06 应在自己的 repo 层做 (wp_id, git_head) 查重 · 命中则复用历史 delegation_id。
    """
    _ = (wp_id, git_head)  # 保留参数以备未来 deterministic hash 算法
    return f"ver-{uuid.uuid4().hex[:12]}"
