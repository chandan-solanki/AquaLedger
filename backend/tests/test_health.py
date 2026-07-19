from httpx import AsyncClient


async def test_health_returns_healthy_status(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert "x-request-id" in response.headers
