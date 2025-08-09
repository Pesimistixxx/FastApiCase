import asyncio

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from db.base import Base
from db.db_depends import get_db


@pytest.fixture(scope="module")
async def test_db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_db):
    async_session = async_sessionmaker(
        test_db, class_=AsyncSession, expire_on_commit=False
    )
    session = async_session()

    try:
        yield session
    finally:
        await session.close()


@pytest.fixture
async def async_client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app),
                           base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
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
