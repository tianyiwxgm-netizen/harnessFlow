"""PATCH /api/config/profile — apply trim profile (L2-06 runtime switch).

WP03 scope: store in-process (module-level dict keyed by pid) and echo back.
Real persistence (projects/<pid>/compliance/profile.yaml) is L1-02 territory and
is out of scope for the BFF during the Dev-θ phase; the dict is a mock pending
Dev-δ's L1-02 integration.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.bff.deps import get_active_pid

router = APIRouter()

TrimProfile = Literal["full", "lean", "custom"]

# Mock in-process store (Dev-θ WP03 placeholder; Dev-δ L1-02 replaces this).
_PROFILE_STATE: dict[str, TrimProfile] = {}


class ProfilePatchBody(BaseModel):
    profile: TrimProfile = Field(..., description="Trim profile enum (full/lean/custom)")


class ProfilePatchResponse(BaseModel):
    profile: TrimProfile
    synced: bool
    pid: str | None
    note: str | None = None


@router.patch(
    "/config/profile",
    response_model=ProfilePatchResponse,
    tags=["trim-profile"],
)
async def patch_config_profile(
    body: ProfilePatchBody,
    pid: Annotated[str | None, Depends(get_active_pid)],
) -> ProfilePatchResponse:
    if pid is None:
        # PM-14: write-class endpoint rejects when no active project.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="PM-14: X-Harness-Pid header is required for write operations",
        )

    _PROFILE_STATE[pid] = body.profile
    note = (
        "custom profile active — checklist 未完成（WP03 占位 · 待 L2-06 modal 完成）"
        if body.profile == "custom"
        else None
    )
    return ProfilePatchResponse(
        profile=body.profile,
        synced=True,
        pid=pid,
        note=note,
    )


@router.get(
    "/config/profile",
    response_model=ProfilePatchResponse,
    tags=["trim-profile"],
)
async def get_config_profile(
    pid: Annotated[str | None, Depends(get_active_pid)],
) -> ProfilePatchResponse:
    if pid is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="PM-14: X-Harness-Pid header is required",
        )
    current: TrimProfile = _PROFILE_STATE.get(pid, "full")
    return ProfilePatchResponse(profile=current, synced=True, pid=pid)


def _reset_profile_state_for_tests() -> None:
    """Test-only helper. Not part of the public API."""
    _PROFILE_STATE.clear()
