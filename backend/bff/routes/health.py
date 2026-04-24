from typing import Annotated

from fastapi import APIRouter, Depends

from backend.bff.config import settings
from backend.bff.deps import get_active_pid

router = APIRouter()


@router.get("/health", tags=["system"])
async def health(
    pid: Annotated[str | None, Depends(get_active_pid)],
) -> dict[str, str | None]:
    return {
        "status": "ok",
        "version": settings.bff_version,
        "pid": pid,
    }
