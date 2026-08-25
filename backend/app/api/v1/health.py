from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness only - the process is up and serving requests. Never
    touches the database, so a slow/unreachable Postgres can never make
    an otherwise-healthy container look unhealthy and get restarted for
    the wrong reason."""
    return {"status": "healthy"}


@router.get("/health/ready")
async def readiness(session: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Readiness - the process is up AND can reach Postgres. What a
    deployment healthcheck (Docker Compose `depends_on: condition:
    service_healthy`, a reverse proxy, an orchestrator) should probe
    before routing real traffic to this container or starting a
    dependent service, distinct from plain liveness above."""
    await session.execute(text("SELECT 1"))
    return {"status": "ready"}
