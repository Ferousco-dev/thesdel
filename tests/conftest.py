import os

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest
from fakeredis import aioredis as fake_aioredis
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app import main as main_module
from app.shared import db as db_module
from app.shared import redis_client as redis_module


@pytest.fixture(autouse=True)
def _isolated_infra(monkeypatch):
    """Every test gets a fresh in-memory Mongo + Redis — no live services
    required, and no state leaks between tests."""
    mock_client = AsyncMongoMockClient()
    monkeypatch.setattr(db_module, "_client", mock_client)
    monkeypatch.setattr(db_module, "get_client", lambda: mock_client)

    fake_redis = fake_aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_module, "_redis", fake_redis)
    monkeypatch.setattr(redis_module, "get_redis", lambda: fake_redis)

    yield


@pytest.fixture
async def client():
    app = main_module.create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
