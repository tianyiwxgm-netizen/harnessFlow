"""L2-01 IC-16 push_stage_gate_card · L1-10 UI 接入前的 stub。

真实 L1-10 UI bridge 接入前 · 本 stub 负责：
  1. 构造 §3.16.2 合规的 push_stage_gate_card_command payload
  2. 若 ui_bridge 注入 · delegate 给真实接收方
  3. 否则降级为 IC-09 事件（审计可追溯）

对齐 docs/3-1-Solution-Technical/integration/ic-contracts.md §3.16。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Protocol


# §3.16.2 artifact_type 合法枚举
_ARTIFACT_TYPE_BY_STAGE: dict[str, tuple[str, ...]] = {
    "S1": ("charter",),
    "S2": ("charter", "plan", "wbs", "togaf_doc"),
    "S3": ("tdd_blueprint",),
    "S5": ("verifier_report", "code"),
    "S7": ("verifier_report",),
}


class UIBridge(Protocol):
    """L1-10 UI bridge 接收方 protocol · 真实 L1-10 L2-02 Gate 卡片实装时对齐。"""

    def push_stage_gate_card_to_ui(self, *, command: dict[str, Any]) -> dict[str, Any]: ...


def build_push_stage_gate_card_command(
    *,
    gate_id: str,
    project_id: str,
    stage_name: str,
    artifacts_bundle: list[dict[str, Any]] | None = None,
    trim_level: str = "standard",
    allowed_decisions: tuple[str, ...] = ("approve", "reject", "request_change"),
    blocks_progress: bool = True,
) -> dict[str, Any]:
    """构造 §3.16.2 push_stage_gate_card_command · 必填 6 字段全覆盖。

    - card_id: 生成 "card-{uuid-v7}" 格式（本地 uuid4 近似 · L1-10 接入后可换 v7）
    - artifacts_bundle 单项 schema: {artifact_type, path, summary, page_count?}
    - ts: ISO-8601 utc with Z
    """
    if not gate_id:
        msg = "§3.16.5 E_CARD_GATE_ID_MISMATCH · gate_id required"
        raise ValueError(msg)
    if not project_id:
        msg = "§3.16.5 E_CARD_NO_PROJECT_ID · project_id required"
        raise ValueError(msg)

    if artifacts_bundle is None:
        artifacts_bundle = _default_artifacts_bundle(
            stage_name=stage_name, project_id=project_id, gate_id=gate_id,
        )
    if not artifacts_bundle or len(artifacts_bundle) < 1:
        msg = "§3.16.5 E_CARD_BUNDLE_EMPTY · artifacts_bundle must have >=1 items"
        raise ValueError(msg)

    if trim_level not in ("minimal", "standard", "full"):
        msg = f"§3.16.5 E_CARD_TRIM_UNSUPPORTED · trim_level={trim_level!r}"
        raise ValueError(msg)

    ts = (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )
    return {
        "card_id": f"card-{uuid.uuid4()}",
        "project_id": project_id,
        "gate_id": gate_id,
        "stage_name": stage_name,
        "artifacts_bundle": list(artifacts_bundle),
        "trim_level": trim_level,
        "allowed_decisions": list(allowed_decisions),
        "blocks_progress": blocks_progress,
        "ts": ts,
    }


def _default_artifacts_bundle(
    *,
    stage_name: str,
    project_id: str,
    gate_id: str,
) -> list[dict[str, Any]]:
    """stage 默认 artifact 集 · L1-10 真实接入前兜底 · artifacts_bundle ≥ 1。"""
    types = _ARTIFACT_TYPE_BY_STAGE.get(stage_name, ("charter",))
    pid_short = project_id[:8] if project_id else "unknown"
    return [
        {
            "artifact_type": t,
            "path": f"projects/{project_id}/{t}/{gate_id}.md",
            "summary": f"stub-{stage_name}-{t} · pid={pid_short}",
        }
        for t in types
    ]


__all__ = [
    "UIBridge",
    "build_push_stage_gate_card_command",
]
