"""
Tests for the /packages endpoints.

Uses an in-memory SQLite database via SQLAlchemy so no real
PostgreSQL or Docker is needed to run the test suite.
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture(autouse=True)
def _setup_db():
    """Create tables before each test, drop after."""
    import asyncio

    async def _init():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _teardown():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.get_event_loop().run_until_complete(_init())
    yield
    asyncio.get_event_loop().run_until_complete(_teardown())


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


SAMPLE_PAYLOAD = {
    "sender": "Logistic Plus LLC",
    "recipient": "John Doe",
    "contents": "UTP Cat.6 Cable, 10m",
    "weight_kg": 2.3,
    "destination": "Central Warehouse",
    "routing_zone": "A-12",
}

class TestCreatePackage:
    def test_returns_201_with_sku(self, client):
        response = client.post("/api/v1/packages", json=SAMPLE_PAYLOAD)
        assert response.status_code == 201
        body = response.json()
        assert body["sku"].startswith("WH-")
        assert body["sender"] == SAMPLE_PAYLOAD["sender"]
        assert body["weight_kg"] == SAMPLE_PAYLOAD["weight_kg"]

    def test_missing_required_field_returns_422(self, client):
        response = client.post("/api/v1/packages", json={"sender": "Test"})
        assert response.status_code == 422


class TestGetPackage:
    def test_get_existing_package(self, client):
        sku = client.post("/api/v1/packages", json=SAMPLE_PAYLOAD).json()["sku"]
        response = client.get(f"/api/v1/packages/{sku}")
        assert response.status_code == 200
        assert response.json()["sku"] == sku

    def test_get_nonexistent_returns_404(self, client):
        response = client.get("/api/v1/packages/WH-DEADBEEF")
        assert response.status_code == 404


class TestListPackages:
    def test_list_returns_created_packages(self, client):
        client.post("/api/v1/packages", json=SAMPLE_PAYLOAD)
        client.post("/api/v1/packages", json=SAMPLE_PAYLOAD)
        response = client.get("/api/v1/packages")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_pagination(self, client):
        for _ in range(5):
            client.post("/api/v1/packages", json=SAMPLE_PAYLOAD)
        response = client.get("/api/v1/packages?limit=2")
        assert len(response.json()) == 2


class TestDeletePackage:
    def test_delete_existing(self, client):
        sku = client.post("/api/v1/packages", json=SAMPLE_PAYLOAD).json()["sku"]
        assert client.delete(f"/api/v1/packages/{sku}").status_code == 204
        assert client.get(f"/api/v1/packages/{sku}").status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        assert client.delete("/api/v1/packages/WH-DEADBEEF").status_code == 404


class TestUpdatePackage:
    def test_update_existing(self, client):
        sku = client.post("/api/v1/packages", json=SAMPLE_PAYLOAD).json()["sku"]
        response = client.patch(
            f"/api/v1/packages/{sku}",
            json={"status": "IN_TRANSIT", "weight_kg": 5.5}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "IN_TRANSIT"
        assert body["weight_kg"] == 5.5
        # Ensure other fields remain untouched
        assert body["sender"] == SAMPLE_PAYLOAD["sender"]

    def test_update_nonexistent_returns_404(self, client):
        response = client.patch("/api/v1/packages/WH-DEADBEEF", json={"status": "DELIVERED"})
        assert response.status_code == 404


class TestGetLabel:
    def test_returns_png(self, client):
        sku = client.post("/api/v1/packages", json=SAMPLE_PAYLOAD).json()["sku"]
        response = client.get(f"/api/v1/packages/{sku}/label")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        # PNG magic bytes
        assert response.content[:4] == b"\x89PNG"

    def test_label_for_nonexistent_returns_404(self, client):
        assert client.get("/api/v1/packages/WH-DEADBEEF/label").status_code == 404
