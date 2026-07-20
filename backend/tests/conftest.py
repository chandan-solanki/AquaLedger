from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import engine, get_db
from app.main import app
from app.modules.auth.security import login_rate_limiter


@pytest.fixture(autouse=True)
def _reset_login_rate_limiter() -> None:
    """The rate limiter is a process-wide in-memory singleton (Phase 3);
    reset it between tests so one test's attempts can't trip another's."""
    login_rate_limiter._hits.clear()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """A session bound to a connection-level transaction that is always
    rolled back, so tests can freely exercise real endpoints (including the
    seeded super admin) against the real database without leaving traces.

    session.commit() only closes a SAVEPOINT here, it never touches the
    outer transaction - that's what join_transaction_mode achieves.
    """
    async with engine.connect() as connection:
        await connection.begin()
        session_factory = async_sessionmaker(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        async with session_factory() as session:
            yield session
        await connection.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()
