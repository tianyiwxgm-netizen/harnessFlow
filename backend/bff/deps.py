from typing import Annotated

from fastapi import Header

from backend.bff.config import settings


def get_active_pid(
    x_harness_pid: Annotated[str | None, Header(alias=settings.pid_header_name)] = None,
) -> str | None:
    """PM-14 · Read active project id from X-Harness-Pid request header.

    WP01 allows None (no active project). Write-type endpoints in later WPs
    will promote None to HTTP 422 to enforce PM-14 at the write boundary.
    """
    return x_harness_pid
