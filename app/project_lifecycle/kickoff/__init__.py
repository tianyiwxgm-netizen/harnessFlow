"""L2-02 启动阶段产出器 · PM-14 pid 创建唯一入口。

public API:
  - StartupProducer(brainstorm, template, event_bus, project_root)
  - kickoff_create_project(KickoffRequest) → KickoffResponse
  - activate_project_id(ActivateRequest, project_root) → ActivateResponse  (L2-01 调)
  - recover_draft(pid, root_dir, event_bus) → RecoveryResult  (L1-09 崩溃恢复调)
"""
from app.project_lifecycle.kickoff.activator import activate_project_id
from app.project_lifecycle.kickoff.errors import KickoffError
from app.project_lifecycle.kickoff.producer import StartupProducer
from app.project_lifecycle.kickoff.recovery import recover_draft
from app.project_lifecycle.kickoff.schemas import (
    ActivateRequest,
    ActivateResponse,
    KickoffErr,
    KickoffRequest,
    KickoffResponse,
    KickoffSuccess,
    RecoveryResult,
)

__all__ = [
    "StartupProducer",
    "activate_project_id",
    "recover_draft",
    "KickoffError",
    "KickoffRequest",
    "KickoffResponse",
    "KickoffSuccess",
    "KickoffErr",
    "ActivateRequest",
    "ActivateResponse",
    "RecoveryResult",
]
