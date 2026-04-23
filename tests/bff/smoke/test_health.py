import pytest
from httpx import AsyncClient, ASGITransport

from backend.bff.main import app


@pytest.mark.asyncio
async def test_health_returns_200_and_status_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
    assert body["pid"] is None


@pytest.mark.asyncio
async def test_health_echoes_pid_header_when_present():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/health", headers={"X-Harness-Pid": "pj-abc"})
    assert response.status_code == 200
    assert response.json()["pid"] == "pj-abc"


@pytest.mark.asyncio
async def test_cors_allows_vite_dev_origin():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
