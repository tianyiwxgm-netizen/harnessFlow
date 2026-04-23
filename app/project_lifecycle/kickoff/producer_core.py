"""L2-02 produce_kickoff 算法 · 对齐 tech §6.1 + dispatch §3.2 8 步。

主循环：
  1. 生成 pid (p_{uuid}) · 冲突重试 1 次
  2. 建目录 projects/<pid>/{chart,meta,stage-gates}/
  3. 写 state.json: DRAFT
  4. brainstorming 澄清（mock · ≤ 3 轮）
  5. L2-07 render kickoff.goal / kickoff.scope
  6. atomic_write 2 份章程
  7. compute_anchor_hash
  8. 写 meta/project_manifest.yaml + 发 4 IC-09 事件（顺序：project_created / charter_ready / stakeholders_ready / goal_anchor_hash_locked）

依赖注入：brainstorm / template / event_bus · 便于单元 mock。
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import yaml

from app.project_lifecycle.kickoff.anchor_hash import compute_anchor_hash
from app.project_lifecycle.kickoff.atomic_writer import atomic_write_chart
from app.project_lifecycle.kickoff.errors import (
    E_BRAINSTORM_SUBAGENT_FAILED,
    E_PID_DUPLICATE,
    KickoffError,
)
from app.project_lifecycle.kickoff.pid_gen import generate_pid
from app.project_lifecycle.kickoff.schemas import KickoffSuccess, TrimLevel


class BrainstormClient(Protocol):
    def invoke(
        self, user_utterance: str, *, prior_context: str | None = None,
    ) -> dict[str, Any]: ...


class EventSink(Protocol):
    def append_event(
        self, *, project_id: str, event_type: str, payload: dict[str, Any],
    ) -> None: ...


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mkdir_project(root: Path, pid: str) -> dict[str, Path]:
    base = root / "projects" / pid
    dirs = {
        "base": base,
        "chart": base / "chart",
        "meta": base / "meta",
        "stage_gates": base / "stage-gates",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def _goal_slots(user_utterance: str, slots: dict[str, Any]) -> dict[str, Any]:
    goals = slots.get("goals") or slots.get("success_criteria") or ["待用户确认"]
    if not isinstance(goals, list) or not goals:
        goals = ["待用户确认"]
    return {
        "user_utterance": user_utterance,
        "goals": goals,
        "deadline": str(slots.get("deadline") or "TBD"),
    }


def _scope_slots(slots: dict[str, Any]) -> dict[str, Any]:
    in_scope = slots.get("in_scope") or slots.get("scope_items") or ["待澄清"]
    return {
        "scope_items": in_scope if isinstance(in_scope, list) else [str(in_scope)],
        "out_of_scope": slots.get("out_of_scope") or [],
        "constraints": slots.get("constraints") or [],
    }


def _render_body(render_result: Any) -> str:
    """统一 RenderedOutput / dict / str · 返 markdown 正文（含 frontmatter）。"""
    if hasattr(render_result, "output"):
        return str(render_result.output)
    if isinstance(render_result, dict):
        return str(render_result.get("template_body") or render_result.get("output") or "")
    return str(render_result)


def _sha_of_file(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def produce_kickoff(
    user_utterance: str,
    *,
    brainstorm: BrainstormClient,
    template: Any,
    event_bus: EventSink,
    project_root: str = ".",
    trim_level: TrimLevel = "full",
    prior_context: str | None = None,
) -> KickoffSuccess:
    root = Path(project_root).absolute()
    root.mkdir(parents=True, exist_ok=True)

    # Step 1 · pid 生成（冲突重试 1 次）
    pid: str | None = None
    for _ in range(2):
        candidate = generate_pid()
        if not (root / "projects" / candidate).exists():
            pid = candidate
            break
    if pid is None:
        raise KickoffError(
            error_code=E_PID_DUPLICATE,
            message="pid collision persisted after retry",
        )

    # Step 2 · 建目录
    dirs = _mkdir_project(root, pid)

    # Step 3 · 写 state.json DRAFT
    (dirs["meta"] / "state.json").write_text(
        json.dumps({
            "state": "DRAFT",
            "project_id": pid,
            "created_at": _iso_now(),
        }),
        encoding="utf-8",
    )

    # Step 4 · brainstorming
    try:
        bs_result = brainstorm.invoke(user_utterance, prior_context=prior_context)
    except Exception as exc:  # noqa: BLE001
        raise KickoffError(
            error_code=E_BRAINSTORM_SUBAGENT_FAILED,
            message=f"brainstorm subagent failed: {exc}",
            project_id=pid,
        ) from exc

    rounds = int(bs_result.get("rounds", 1))
    is_confirmed = bool(bs_result.get("is_confirmed", True))
    bs_slots = dict(bs_result.get("slots", {}))
    clarification_incomplete = (rounds > 3) or (not is_confirmed)

    # Step 5 · render 两份模板
    goal_render = template.render_template(
        request_id=f"kickoff-{pid}-goal",
        project_id=pid,
        kind="kickoff.goal",
        slots=_goal_slots(user_utterance, bs_slots),
        caller_l2="L2-02",
    )
    scope_render = template.render_template(
        request_id=f"kickoff-{pid}-scope",
        project_id=pid,
        kind="kickoff.scope",
        slots=_scope_slots(bs_slots),
        caller_l2="L2-02",
    )

    # Step 6 · atomic_write 章程
    goal_path = dirs["chart"] / "HarnessFlowGoal.md"
    scope_path = dirs["chart"] / "HarnessFlowPrdScope.md"
    atomic_write_chart(str(goal_path), _render_body(goal_render))
    atomic_write_chart(str(scope_path), _render_body(scope_render))

    # Step 7 · anchor hash
    anchor = compute_anchor_hash(pid, root_dir=str(root))
    anchor_prefixed = f"sha256:{anchor}"

    # Step 8 · manifest + 4 事件（顺序：project_created / charter_ready / stakeholders_ready / goal_anchor_hash_locked）
    manifest = {
        "project_id": pid,
        "state": "DRAFT",
        "created_at": _iso_now(),
        "goal_anchor_hash": anchor_prefixed,
        "trim_level": trim_level,
        "clarification_rounds": rounds,
        "clarification_incomplete": clarification_incomplete,
        "charter_path": str(goal_path),
        "stakeholders_path": str(scope_path),
    }
    manifest_path = dirs["meta"] / "project_manifest.yaml"
    atomic_write_chart(
        str(manifest_path),
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
    )

    event_bus.append_event(
        project_id=pid,
        event_type="project_created",
        payload={"state": "DRAFT", "created_at": manifest["created_at"]},
    )
    event_bus.append_event(
        project_id=pid,
        event_type="charter_ready",
        payload={"path": str(goal_path), "sha256": _sha_of_file(goal_path)},
    )
    event_bus.append_event(
        project_id=pid,
        event_type="stakeholders_ready",
        payload={"path": str(scope_path), "sha256": _sha_of_file(scope_path)},
    )
    event_bus.append_event(
        project_id=pid,
        event_type="goal_anchor_hash_locked",
        payload={"goal_anchor_hash": anchor_prefixed},
    )

    return KickoffSuccess(
        project_id=pid,
        charter_path=str(goal_path),
        stakeholders_path=str(scope_path),
        manifest_path=str(manifest_path),
        goal_anchor_hash=anchor_prefixed,
        clarification_rounds=min(rounds, 3),
        clarification_incomplete=clarification_incomplete,
        events_published=(
            "project_created",
            "charter_ready",
            "stakeholders_ready",
            "goal_anchor_hash_locked",
        ),
        trim_level_applied=trim_level,
    )
