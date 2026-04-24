from __future__ import annotations

import os
from collections.abc import AsyncIterator

os.environ.setdefault("ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from campaign.db import session as db_session
from campaign.db.models import Base
from campaign.main import app


@pytest_asyncio.fixture(autouse=True)
async def _setup_db() -> AsyncIterator[None]:
    async with db_session.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with db_session.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
