import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "acoustic-livestock-health-backend"
    assert "version" in data
    assert "disclaimer" in data


@pytest.mark.asyncio
async def test_api_v1_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data
