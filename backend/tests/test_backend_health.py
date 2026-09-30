import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_response():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "acoustic-livestock-health-backend",
        "version": "0.1.0",
    }


@pytest.mark.asyncio
async def test_edge_routes_are_registered(async_client):
    response = await async_client.get("/openapi.json")

    assert response.status_code == 200
    assert {
        "/api/v1/edge/ingest",
        "/api/v1/edge/sync-batch",
        "/api/v1/edge/heartbeat",
    }.issubset(response.json()["paths"])
