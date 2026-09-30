import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_ml_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "acoustic-livestock-ml-service"
