from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core import database as db_module
from app.core.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DB_URL, future=True)
    async with eng.begin() as conn:
        # SQLite needs FK enforcement enabled explicitly for ON DELETE CASCADE.
        from sqlalchemy import text

        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


@pytest_asyncio.fixture
async def session(session_factory) -> AsyncIterator[AsyncSession]:
    async with session_factory() as s:
        # SQLite needs PRAGMA per-connection; ensure FK on for this session.
        from sqlalchemy import text

        await s.execute(text("PRAGMA foreign_keys=ON"))
        yield s


@pytest_asyncio.fixture
async def client(engine, session_factory) -> AsyncIterator[AsyncClient]:
    """Override get_db + lifespan for the test app."""

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as s:
            from sqlalchemy import text

            await s.execute(text("PRAGMA foreign_keys=ON"))
            yield s

    # Also point the global session factory at our test factory so background
    # tasks (which open their own session) hit the in-memory DB.
    original_factory = db_module._session_factory
    original_engine = db_module._engine
    db_module._engine = engine
    db_module._session_factory = session_factory

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    db_module._session_factory = original_factory
    db_module._engine = original_engine


@pytest.fixture
def consent_payload() -> dict:
    return {
        "gameplay": True,
        "interaction_patterns": True,
        "self_report": True,
        "retain_profile_7d": True,
        "research_aggregate": False,
    }
