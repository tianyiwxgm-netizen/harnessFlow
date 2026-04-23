"""L2-02 activate_project_id · 对齐 tech §3.5 + §6.2 + §1.4 PM-14 硬约束。

硬规则：
  1. caller_l2 必为 "L2-01"（PM-14 越权 E_PM14_OWNERSHIP_VIOLATION）
  2. user_confirmed 必为 True（E_USER_NOT_CONFIRMED · Gate 未通过不允许激活）
  3. 当前 state 必为 DRAFT（E_STATE_NOT_DRAFT · 非幂等 · 已激活拒重复）
  4. anchor_hash 复算 vs 入参 · 不符 E_ANCHOR_HASH_MISMATCH（章程被外部改动检测）
  5. 状态转换 DRAFT → INITIALIZED · 写 state.json · 写 meta/created.json（标活化时刻）
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.project_lifecycle.kickoff.anchor_hash import compute_anchor_hash
from app.project_lifecycle.kickoff.errors import (
    E_ANCHOR_HASH_MISMATCH,
    E_PM14_OWNERSHIP_VIOLATION,
    E_STATE_NOT_DRAFT,
    E_USER_NOT_CONFIRMED,
    KickoffError,
)
from app.project_lifecycle.kickoff.schemas import ActivateRequest, ActivateResponse

_PM14_AUTHORIZED_CALLER = "L2-01"


def activate_project_id(
    req: ActivateRequest,
    *,
    project_root: str,
) -> ActivateResponse:
    # 1. PM-14 越权检查
    if req.caller_l2 != _PM14_AUTHORIZED_CALLER:
        raise KickoffError(
            error_code=E_PM14_OWNERSHIP_VIOLATION,
            message=(
                f"only L2-01 may activate · got caller_l2={req.caller_l2!r}"
            ),
            caller_l2=req.caller_l2,
            project_id=req.project_id,
        )

    # 2. user_confirmed
    if not req.user_confirmed:
        raise KickoffError(
            error_code=E_USER_NOT_CONFIRMED,
            message="activate requires user_confirmed=True (S1 Gate approve)",
            caller_l2=req.caller_l2,
            project_id=req.project_id,
        )

    # 3. state 检查
    root = Path(project_root).absolute()
    state_path = root / "projects" / req.project_id / "meta" / "state.json"
    if not state_path.exists():
        raise KickoffError(
            error_code=E_STATE_NOT_DRAFT,
            message=f"project {req.project_id} has no state.json (not produced?)",
            project_id=req.project_id,
        )
    state_data = json.loads(state_path.read_text(encoding="utf-8"))
    if state_data.get("state") != "DRAFT":
        raise KickoffError(
            error_code=E_STATE_NOT_DRAFT,
            message=f"project {req.project_id} state={state_data.get('state')!r}, expected DRAFT",
            project_id=req.project_id,
        )

    # 4. anchor_hash 复核
    expected_prefixed = req.goal_anchor_hash
    expected = expected_prefixed.removeprefix("sha256:")
    recomputed = compute_anchor_hash(req.project_id, root_dir=str(root))
    if recomputed != expected:
        raise KickoffError(
            error_code=E_ANCHOR_HASH_MISMATCH,
            message=(
                f"anchor_hash mismatch · expected={expected[:12]}... "
                f"actual={recomputed[:12]}..."
            ),
            caller_l2=req.caller_l2,
            project_id=req.project_id,
            context={"expected_hash": expected, "actual_hash": recomputed},
        )

    # 5. 状态转换 + 写 created.json
    activated_at = datetime.now(UTC).isoformat()
    state_data["state"] = "INITIALIZED"
    state_data["activated_at"] = activated_at
    state_path.write_text(json.dumps(state_data), encoding="utf-8")

    created_path = root / "projects" / req.project_id / "meta" / "created.json"
    created_path.write_text(
        json.dumps({
            "project_id": req.project_id,
            "activated_at": activated_at,
            "goal_anchor_hash": expected_prefixed,
            "charter_path": req.charter_path,
            "stakeholders_path": req.stakeholders_path,
        }, sort_keys=True),
        encoding="utf-8",
    )

    return ActivateResponse(
        project_id=req.project_id,
        state="INITIALIZED",
        activated_at=activated_at,
        meta_path=str(created_path),
    )
