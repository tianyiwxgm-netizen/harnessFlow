"""L2-02 recover_draft · 对齐 tech §6.5 崩溃恢复。

规则：
  - 无 meta/state.json → action="no_op"（根本未启动）
  - goal.md + scope.md + manifest.yaml 全齐 → action="resumed" · 重放 s1_ready
  - 半成品（缺任一核心文件）→ action="rolled_back" · rmtree · 发 kickoff_rolled_back
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Protocol

from app.project_lifecycle.kickoff.schemas import RecoveryResult


class EventSink(Protocol):
    def append_event(
        self, *, project_id: str, event_type: str, payload: dict[str, Any],
    ) -> None: ...


def recover_draft(
    project_id: str,
    *,
    root_dir: str,
    event_bus: EventSink,
) -> RecoveryResult:
    root = Path(root_dir).absolute()
    base = root / "projects" / project_id
    state_path = base / "meta" / "state.json"

    if not state_path.exists():
        return RecoveryResult(
            action="no_op",
            project_id=project_id,
            reason="no state.json",
        )

    goal_path = base / "chart" / "HarnessFlowGoal.md"
    scope_path = base / "chart" / "HarnessFlowPrdScope.md"
    manifest_path = base / "meta" / "project_manifest.yaml"

    all_ready = goal_path.exists() and scope_path.exists() and manifest_path.exists()

    if all_ready:
        event_bus.append_event(
            project_id=project_id,
            event_type="s1_ready",
            payload={"recovered": True},
        )
        return RecoveryResult(
            action="resumed",
            project_id=project_id,
            reason="all core files present",
        )

    # 半成品 · rmtree
    shutil.rmtree(base, ignore_errors=True)
    event_bus.append_event(
        project_id=project_id,
        event_type="kickoff_rolled_back",
        payload={"reason": "partial_draft_found"},
    )
    return RecoveryResult(
        action="rolled_back",
        project_id=project_id,
        reason="partial_draft_found",
    )
