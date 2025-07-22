import asyncio

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.main import app
from db.db import Base
from db.db_depends import get_db


@pytest.fixture(scope="session")
async def test_db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture
async def async_client(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        app.dependency_overrides[get_db] = lambda: AsyncSession(test_db)
        yield client
        app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_get_main(async_client):
    response = await async_client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_login(async_client):
    response = await async_client.get("/user/login")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_register(async_client):
    response = await async_client.get("/user/register")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_post_register(async_client):
    import uuid
    username = f"user_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    response = await async_client.post(
        "/user/register",
        json={
            "username": username,
            "name": "Alex",
            "email": email,
            "password": "12345678"
        }
    )
    assert response.status_code == 303
