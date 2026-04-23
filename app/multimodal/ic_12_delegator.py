"""IC-12 delegate_codebase_onboarding · async dispatch to L1-05 子 Agent."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from app.multimodal.common.errors import L108Error


def _utc_now_iso() -> str:
    """Return current UTC time in ISO-8601 Z-suffixed format (RFC 3339).

    Factored out for deterministic mocking in tests (monkeypatch this symbol).
    """
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class L1_05_Client(Protocol):
    """Protocol L1-05 (Dev-γ) will implement · tests provide a mock."""
    async def dispatch_codebase_onboarding(self, cmd: dict[str, Any]) -> dict[str, Any]: ...


@dataclass
class DispatchResult:
    delegation_id: str
    dispatched: bool
    subagent_session_id: str | None
    reason: str | None = None
    dispatch_ms: int = 0


async def delegate_codebase_onboarding(
    *,
    project_id: str,
    repo_path: str,
    client: L1_05_Client,
    timeout_s: int = 600,
    focus_interfaces: list[str] | None = None,
    kb_write_back: bool = True,
) -> DispatchResult:
    """Dispatch IC-12 · returns DispatchResult · enforces contract §3.12.4 validation."""
    if not project_id or not project_id.strip():
        raise L108Error("E_PC_NO_PROJECT_ID", "project_id missing")
    if not repo_path or not repo_path.strip():
        raise L108Error("invalid_path", "repo_path missing or empty")

    delegation_id = f"ob-{uuid.uuid4()}"
    cmd: dict[str, Any] = {
        "delegation_id": delegation_id,
        "project_id": project_id,
        "repo_path": repo_path,
        "kb_write_back": kb_write_back,
        "timeout_s": timeout_s,
        "ts": _utc_now_iso(),
    }
    if focus_interfaces:
        cmd["focus"] = {"interfaces": focus_interfaces}

    t0 = time.perf_counter()
    dispatch = await asyncio.wait_for(
        client.dispatch_codebase_onboarding(cmd), timeout=2.0
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return DispatchResult(
        delegation_id=delegation_id,
        dispatched=bool(dispatch.get("dispatched", False)),
        subagent_session_id=dispatch.get("subagent_session_id"),
        reason=dispatch.get("reason"),
        dispatch_ms=elapsed_ms,
    )
