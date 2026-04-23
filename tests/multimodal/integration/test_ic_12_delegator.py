"""WP-η-05 IC-12 delegator contract tests."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.multimodal.common.errors import L108Error
from app.multimodal.ic_12_delegator import (
    DispatchResult,
    delegate_codebase_onboarding,
)


class _MockL1_05:
    def __init__(self, *, session_id: str = "sub-0001") -> None:
        self.session_id = session_id
        self.calls: list[dict[str, Any]] = []

    async def dispatch_codebase_onboarding(self, cmd: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(cmd)
        await asyncio.sleep(0.005)
        return {"dispatched": True, "subagent_session_id": self.session_id}


async def test_ic_12_happy_dispatch_under_200ms() -> None:
    client = _MockL1_05()
    result = await delegate_codebase_onboarding(
        project_id="p-001", repo_path="large/", client=client,
    )
    assert isinstance(result, DispatchResult)
    assert result.dispatched is True
    assert result.subagent_session_id == "sub-0001"
    assert result.delegation_id.startswith("ob-")
    assert result.dispatch_ms < 200, f"IC-12 dispatch must be < 200ms, got {result.dispatch_ms}ms"
    assert client.calls[0]["project_id"] == "p-001"
    assert client.calls[0]["repo_path"] == "large/"


async def test_ic_12_rejects_missing_project_id() -> None:
    client = _MockL1_05()
    with pytest.raises(L108Error) as ei:
        await delegate_codebase_onboarding(project_id="", repo_path="large/", client=client)
    assert ei.value.code == "E_PC_NO_PROJECT_ID"


async def test_ic_12_rejects_missing_repo_path() -> None:
    client = _MockL1_05()
    with pytest.raises(L108Error) as ei:
        await delegate_codebase_onboarding(project_id="p-001", repo_path="", client=client)
    assert ei.value.code == "invalid_path"
