"""WP-η-05 IC-12 delegator contract tests."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

import pytest

from app.multimodal import ic_12_delegator
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


# --- P1-01 regression : ts must be dynamic UTC now, not hardcoded -----------

_ISO_UTC_Z = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)


async def test_ic_12_ts_is_dynamic_utc_now_not_hardcoded() -> None:
    """P1-01: ts must reflect current UTC wall-clock, not a fixed literal."""
    client = _MockL1_05()
    before = datetime.now(timezone.utc)
    await delegate_codebase_onboarding(
        project_id="p-001", repo_path="repo/", client=client,
    )
    after = datetime.now(timezone.utc)

    ts_str = client.calls[0]["ts"]
    # Contract §3.12.2 says ts is ISO-8601 string; we additionally demand Z-suffix UTC.
    assert isinstance(ts_str, str)
    assert _ISO_UTC_Z.match(ts_str), f"ts not ISO-8601 Z: {ts_str!r}"
    assert not ts_str.startswith("2026-04-23T00:00:00"), (
        "P1-01 regression: ts looks like the previously hardcoded literal"
    )
    parsed = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    assert before <= parsed <= after, (
        f"ts {parsed.isoformat()} outside call window "
        f"[{before.isoformat()}, {after.isoformat()}]"
    )


async def test_ic_12_ts_differs_across_consecutive_calls() -> None:
    """P1-01 regression: two consecutive calls must produce distinct ts values."""
    client = _MockL1_05()
    await delegate_codebase_onboarding(
        project_id="p-001", repo_path="repo/", client=client,
    )
    # sleep > clock resolution; microseconds in ISO output give us plenty of headroom
    await asyncio.sleep(0.002)
    await delegate_codebase_onboarding(
        project_id="p-001", repo_path="repo/", client=client,
    )
    ts1 = client.calls[0]["ts"]
    ts2 = client.calls[1]["ts"]
    assert ts1 != ts2, f"ts must advance between calls: {ts1} == {ts2}"


async def test_ic_12_ts_uses_injected_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clock is factored into _utc_now_iso so tests can pin it deterministically."""
    fixed = "2030-01-02T03:04:05.000000Z"
    monkeypatch.setattr(ic_12_delegator, "_utc_now_iso", lambda: fixed)
    client = _MockL1_05()
    await delegate_codebase_onboarding(
        project_id="p-001", repo_path="repo/", client=client,
    )
    assert client.calls[0]["ts"] == fixed
