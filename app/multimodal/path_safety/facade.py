"""PathSafetyFacade · L2-04 唯一入口 · IC-11 handle_process_content."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Callable

from app.multimodal.common.errors import L108Error
from app.multimodal.common.event_bus_stub import EventBusStub
from app.multimodal.common.pid_guard import assert_same_project
from app.multimodal.path_safety.auditor import ContentAuditor
from app.multimodal.path_safety.halted_state import HaltedState
from app.multimodal.path_safety.lock_keeper import ConcurrencyLockKeeper
from app.multimodal.path_safety.router import DegradationRouter, RouteInput
from app.multimodal.path_safety.schemas import (
    ErrorBody,
    ProcessContentCommand,
    ProcessContentResult,
    RouteDecision,
    ValidationResult,
)
from app.multimodal.path_safety.symlink_detector import SymlinkCycleDetector
from app.multimodal.path_safety.whitelist import PathWhitelistValidator


# Stub dispatcher signature — WP-05 will replace with real L2-01/02/03 router
DispatchFn = Callable[[ProcessContentCommand, ValidationResult, RouteDecision], dict[str, Any]]


_BINARY_SNIFF_BYTES = 512


def _looks_binary(realpath: Path) -> bool:
    """Quick binary detection: any NUL byte in first 512 bytes ⇒ treat as binary."""
    try:
        with open(realpath, "rb") as f:
            sample = f.read(_BINARY_SNIFF_BYTES)
    except OSError:
        return False
    return b"\x00" in sample


class PathSafetyFacade:
    """L2-04 主门面 · 所有 I/O 必须经此入口。"""

    def __init__(
        self,
        project_root: Path,
        project_id: str,
        allowlist: list[str],
        bus: EventBusStub,
        dispatch_fn: DispatchFn,
    ) -> None:
        self.project_id = project_id
        self.whitelist = PathWhitelistValidator(project_root, project_id, allowlist)
        self.symlink = SymlinkCycleDetector()
        self.router = DegradationRouter()
        self.locks = ConcurrencyLockKeeper()
        self.auditor = ContentAuditor(bus=bus)
        self.dispatch_fn = dispatch_fn

    def handle_process_content(self, cmd: ProcessContentCommand) -> ProcessContentResult:
        """Sync entry point · returns ProcessContentResult (never raises for caller)."""
        started = time.perf_counter()
        try:
            # --- PM-14 cross-project guard ---
            assert_same_project(self.project_id, cmd.project_id)

            # --- L1-07 HALTED guard ---
            if HaltedState.is_halted():
                raise L108Error("halted_denied", "L1-07 global halt active")

            # --- whitelist + symlink ---
            validation = self.whitelist.validate(cmd.target_path, action="read")
            assert validation.realpath is not None  # invariant: ok=True ⇒ realpath set
            real = Path(validation.realpath)
            self.symlink.check(real)

            # --- os.stat guard: not_found / permission_denied / not_a_file ---
            try:
                st = os.stat(real)
            except FileNotFoundError:
                raise L108Error("not_found", str(real))
            except PermissionError:
                raise L108Error("permission_denied", str(real))

            import stat as _stat
            if _stat.S_ISDIR(st.st_mode):
                raise L108Error("not_a_file", str(real))

            # --- binary guard for md content ---
            if cmd.content_type.value == "md" and _looks_binary(real):
                raise L108Error("binary_unsupported", str(real))

            # --- route decision (stub stats since we don't parse here) ---
            route = self._decide_route(cmd, real, st.st_size)

            # --- dispatch to L2-01/02/03 via stub ---
            structured = self.dispatch_fn(cmd, validation, route)

            # --- audit success ---
            self.auditor.emit(
                "content_read",
                {"path": str(real), "route": route.value, "pid": self.project_id},
            )

            duration_ms = int((time.perf_counter() - started) * 1000)
            return ProcessContentResult(
                command_id=cmd.command_id,
                success=True,
                structured_output=structured,
                duration_ms=duration_ms,
            )

        except L108Error as e:
            # map L2-04 code → IC-11 code per contract §3.11.4 where applicable
            ic11_code = _map_to_ic11(e.code)
            self.auditor.emit(
                "path_rejected",
                {"code": e.code, "detail": e.detail, "pid": cmd.project_id},
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            return ProcessContentResult(
                command_id=cmd.command_id,
                success=False,
                error=ErrorBody(code=ic11_code, message=str(e)),
                duration_ms=duration_ms,
            )

    def _decide_route(self, cmd: ProcessContentCommand, real: Path, size: int) -> RouteDecision:
        ct = cmd.content_type.value
        if ct == "md":
            # Count lines cheaply (we're pre-paging, not reading the content into memory for use).
            with open(real, "rb") as f:
                line_count = sum(1 for _ in f)
            return self.router.route_md(RouteInput(realpath=real, line_count=line_count))
        if ct == "code":
            # For code, we scan the target_path as a file or directory LoC estimate.
            line_count = _estimate_loc(real)
            return self.router.route_code(RouteInput(realpath=real, line_count=line_count))
        if ct == "image":
            ext = real.suffix.lower().lstrip(".")
            return self.router.route_image(RouteInput(realpath=real, ext=ext, size_bytes=size))
        # pdf / markdown_batch treated as DIRECT for now (WP-02 will refine)
        return RouteDecision.DIRECT


def _estimate_loc(path: Path) -> int:
    """Rough LoC estimator · counts newlines in a single file; 1 for a directory stub in WP-01."""
    if path.is_dir():
        # WP-01: we don't walk. Return 0 so small repos go DIRECT. WP-03 will replace.
        return 0
    with open(path, "rb") as f:
        return sum(1 for _ in f)


# --- L2-04 error code → IC-11 error code mapping (per contract §3.11.4) ---

_L2_04_TO_IC_11: dict[str, str] = {
    "invalid_project_id": "E_PC_NO_PROJECT_ID",
    "path_escape": "E_PC_PATH_OUT_OF_PROJECT",
    "cross_project": "E_PC_PATH_OUT_OF_PROJECT",
    "path_forbidden": "E_PC_PATH_OUT_OF_PROJECT",
    "not_found": "E_PC_PATH_NOT_FOUND",
    "type_mismatch": "E_PC_TYPE_TASK_MISMATCH",
}


def _map_to_ic11(l2_04_code: str) -> str:
    """Map internal L2-04 code to outward-facing IC-11 code · fallback returns original."""
    return _L2_04_TO_IC_11.get(l2_04_code, l2_04_code)
