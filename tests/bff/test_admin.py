"""BFF /api/admin/* tests (WP04 · L2-07)."""

import pytest
from httpx import AsyncClient, ASGITransport

from backend.bff.main import app


@pytest.mark.asyncio
async def test_admin_health_returns_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.get("/api/admin/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["bff_version"] == "0.1.0"
    assert "bff" in body["services"]
    assert body["services"]["bff"] == "ok"
    assert body["uptime_seconds"] >= 0


@pytest.mark.asyncio
async def test_admin_users_not_implemented():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.get("/api/admin/users")
    assert r.status_code == 501
    assert "not implemented" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_permissions_not_implemented():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.get("/api/admin/permissions")
    assert r.status_code == 501


@pytest.mark.asyncio
async def test_admin_audit_requires_pid():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.get("/api/admin/audit")
    assert r.status_code == 422
    assert "PM-14" in r.json()["detail"]


@pytest.mark.asyncio
async def test_admin_audit_with_pid_is_501_pending_l1_09():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.get(
            "/api/admin/audit",
            headers={"X-Harness-Pid": "pj-x"},
        )
    assert r.status_code == 501
    assert "L1-09" in r.json()["detail"]


@pytest.mark.asyncio
async def test_admin_backup_not_implemented():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.get("/api/admin/backup")
    assert r.status_code == 501


@pytest.mark.asyncio
async def test_admin_config_not_implemented():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.get("/api/admin/config")
    assert r.status_code == 501


@pytest.mark.asyncio
async def test_admin_metrics_not_implemented():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.get("/api/admin/metrics")
    assert r.status_code == 501


@pytest.mark.asyncio
async def test_admin_red_line_alerts_requires_pid():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.get("/api/admin/red_line_alerts")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_admin_red_line_alerts_with_pid_is_501_pending_l1_07():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.get(
            "/api/admin/red_line_alerts",
            headers={"X-Harness-Pid": "pj-x"},
        )
    assert r.status_code == 501
    assert "L1-07" in r.json()["detail"]
