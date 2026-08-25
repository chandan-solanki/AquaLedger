from httpx import AsyncClient


async def test_health_returns_healthy_status(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert "x-request-id" in response.headers


async def test_readiness_returns_ready_when_the_database_is_reachable(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
