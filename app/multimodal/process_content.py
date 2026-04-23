"""IC-11 process_content · L1-08 唯一对外入口 · 包 PathSafetyFacade + ContentRouter + IC-12."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.multimodal.common.errors import L108Error
from app.multimodal.common.event_bus_stub import EventBusStub
from app.multimodal.ic_12_delegator import L1_05_Client, delegate_codebase_onboarding
from app.multimodal.path_safety.facade import PathSafetyFacade
from app.multimodal.path_safety.schemas import (
    ErrorBody,
    ProcessContentCommand,
    ProcessContentResult,
)
from app.multimodal.router import ContentRouter, MultimodalDeps, check_type_task_compatibility


@dataclass
class ProcessContentDeps:
    facade_project_root: Path
    facade_project_id: str
    facade_allowlist: list[str]
    multimodal_deps: MultimodalDeps
    bus: EventBusStub
    l1_05_client: L1_05_Client | None = None


def process_content(
    cmd: ProcessContentCommand,
    deps: ProcessContentDeps,
) -> ProcessContentResult:
    """IC-11 single entry · returns ProcessContentResult · never raises to caller."""
    # Pre-validate task × content_type matrix BEFORE any I/O (fast-fail IC-11 E_PC_TYPE_TASK_MISMATCH)
    try:
        check_type_task_compatibility(cmd.content_type.value, cmd.task.value)
    except L108Error as e:
        return ProcessContentResult(
            command_id=cmd.command_id,
            success=False,
            error=ErrorBody(code="E_PC_TYPE_TASK_MISMATCH", message=str(e)),
            duration_ms=0,
        )

    router = ContentRouter(deps.multimodal_deps)
    facade = PathSafetyFacade(
        project_root=deps.facade_project_root,
        project_id=deps.facade_project_id,
        allowlist=deps.facade_allowlist,
        bus=deps.bus,
        dispatch_fn=lambda c, v, r: router.route(c, v, r),
    )

    result = facade.handle_process_content(cmd)

    # If the facade routed DELEGATE (code > 100k LOC), replace structured_output with async_task_id via IC-12.
    if result.success and result.structured_output and result.structured_output.get("route") == "DELEGATE":
        if deps.l1_05_client is None:
            return ProcessContentResult(
                command_id=cmd.command_id,
                success=False,
                error=ErrorBody(code="E_PC_LARGE_CODE_BASE", message="large code but no L1-05 client configured"),
                duration_ms=result.duration_ms,
            )
        t0 = time.perf_counter()
        try:
            dispatch = asyncio.run(delegate_codebase_onboarding(
                project_id=cmd.project_id,
                repo_path=cmd.target_path,
                client=deps.l1_05_client,
            ))
            # Use uuid4().hex (no hyphens) to satisfy ^async-[0-9a-zA-Z]+$ validator
            async_id = f"async-{uuid.uuid4().hex}"
            return ProcessContentResult(
                command_id=cmd.command_id,
                success=True,
                async_task_id=async_id,
                structured_output={"delegation_id": dispatch.delegation_id, "dispatched": dispatch.dispatched},
                duration_ms=int((time.perf_counter() - t0) * 1000) + result.duration_ms,
            )
        except L108Error as e:
            return ProcessContentResult(
                command_id=cmd.command_id,
                success=False,
                error=ErrorBody(code="E_PC_LARGE_CODE_BASE", message=str(e)),
                duration_ms=result.duration_ms,
            )

    return result
