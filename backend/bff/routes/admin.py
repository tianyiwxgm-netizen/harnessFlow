"""/api/admin/* BFF endpoints (WP04 · L2-07).

WP04 scope: stub health endpoint is implemented end-to-end; other 7 subtabs
(users / permissions / audit / backup / config / metrics / red_line_alerts)
return 501 with a marker pointing to the responsible future WP. Real
implementations are produced by later WPs that consume Dev-α L1-09 events and
Dev-δ L2-07 permissions.
"""

import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.bff.config import settings
from backend.bff.deps import get_active_pid

router = APIRouter()

_BOOT_TS = time.time()


class AdminHealthResponse(BaseModel):
    status: str
    bff_version: str
    uptime_seconds: float
    services: dict[str, str]


@router.get(
    "/admin/health",
    response_model=AdminHealthResponse,
    tags=["admin"],
)
async def admin_health() -> AdminHealthResponse:
    return AdminHealthResponse(
        status="ok",
        bff_version=settings.bff_version,
        uptime_seconds=round(time.time() - _BOOT_TS, 3),
        services={
            "bff": "ok",
            "l1_09_event_bus": "unknown",
            "l1_06_kb": "unknown",
            "l1_02_lifecycle": "unknown",
        },
    )


def _not_implemented_yet(subtab: str, owner: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"/admin/{subtab} not implemented in WP04 — delegated to {owner}",
    )


@router.get("/admin/users", tags=["admin"])
async def admin_users():
    raise _not_implemented_yet("users", "future auth WP")


@router.get("/admin/permissions", tags=["admin"])
async def admin_permissions():
    raise _not_implemented_yet("permissions", "future auth WP")


@router.get("/admin/audit", tags=["admin"])
async def admin_audit(
    pid: Annotated[str | None, Depends(get_active_pid)],
):
    if pid is None:
        raise HTTPException(status_code=422, detail="PM-14: X-Harness-Pid required for audit")
    raise _not_implemented_yet("audit", "Dev-α L1-09 L2-03 IC-18")


@router.get("/admin/backup", tags=["admin"])
async def admin_backup():
    raise _not_implemented_yet("backup", "Dev-α L1-09 L2-04")


@router.get("/admin/config", tags=["admin"])
async def admin_config():
    raise _not_implemented_yet("config", "future config WP")


@router.get("/admin/metrics", tags=["admin"])
async def admin_metrics():
    raise _not_implemented_yet("metrics", "future observability WP")


@router.get("/admin/red_line_alerts", tags=["admin"])
async def admin_red_line_alerts(
    pid: Annotated[str | None, Depends(get_active_pid)],
):
    if pid is None:
        raise HTTPException(status_code=422, detail="PM-14: X-Harness-Pid required")
    raise _not_implemented_yet("red_line_alerts", "Dev-ζ L1-07 subscription")
