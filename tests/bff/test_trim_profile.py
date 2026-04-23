"""BFF /api/config/profile endpoint tests (WP03 · L2-06)."""

import pytest
from httpx import AsyncClient, ASGITransport

from backend.bff.main import app
from backend.bff.routes.trim_profile import _reset_profile_state_for_tests


@pytest.fixture(autouse=True)
def _clear_profile_state():
    _reset_profile_state_for_tests()
    yield
    _reset_profile_state_for_tests()


@pytest.mark.asyncio
async def test_patch_profile_requires_pid():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.patch("/api/config/profile", json={"profile": "lean"})
    assert r.status_code == 422
    assert "PM-14" in r.json()["detail"]


@pytest.mark.asyncio
async def test_patch_profile_stores_and_returns_value():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.patch(
            "/api/config/profile",
            json={"profile": "lean"},
            headers={"X-Harness-Pid": "pj-a"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["profile"] == "lean"
    assert body["synced"] is True
    assert body["pid"] == "pj-a"
    assert body["note"] is None


@pytest.mark.asyncio
async def test_patch_profile_custom_returns_note():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.patch(
            "/api/config/profile",
            json={"profile": "custom"},
            headers={"X-Harness-Pid": "pj-b"},
        )
    assert r.status_code == 200
    assert r.json()["note"] is not None
    assert "checklist" in r.json()["note"]


@pytest.mark.asyncio
async def test_patch_profile_rejects_unknown_enum():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.patch(
            "/api/config/profile",
            json={"profile": "gigantic"},
            headers={"X-Harness-Pid": "pj-a"},
        )
    assert r.status_code == 422  # pydantic validation


@pytest.mark.asyncio
async def test_get_profile_returns_full_default():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.get(
            "/api/config/profile",
            headers={"X-Harness-Pid": "pj-new"},
        )
    assert r.status_code == 200
    assert r.json()["profile"] == "full"


@pytest.mark.asyncio
async def test_get_profile_returns_last_set_per_pid():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.patch(
            "/api/config/profile",
            json={"profile": "lean"},
            headers={"X-Harness-Pid": "pj-iso"},
        )
        r = await client.get(
            "/api/config/profile",
            headers={"X-Harness-Pid": "pj-iso"},
        )
    assert r.json()["profile"] == "lean"


@pytest.mark.asyncio
async def test_profiles_are_isolated_across_pids():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.patch(
            "/api/config/profile",
            json={"profile": "lean"},
            headers={"X-Harness-Pid": "pj-1"},
        )
        await client.patch(
            "/api/config/profile",
            json={"profile": "custom"},
            headers={"X-Harness-Pid": "pj-2"},
        )
        r1 = await client.get(
            "/api/config/profile",
            headers={"X-Harness-Pid": "pj-1"},
        )
        r2 = await client.get(
            "/api/config/profile",
            headers={"X-Harness-Pid": "pj-2"},
        )
    assert r1.json()["profile"] == "lean"
    assert r2.json()["profile"] == "custom"
