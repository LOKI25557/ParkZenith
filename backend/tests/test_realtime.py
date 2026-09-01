import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
import asyncio

from backend.app.main import app
from backend.app.database.session import get_async_session
from backend.app.models.base import Base
from backend.app.core.dependencies import get_admin_user, get_current_user
from backend.app.models.user import User

DATABASE_URL_TEST = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(
    DATABASE_URL_TEST,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

AsyncSessionLocalTest = async_sessionmaker(
    bind=engine_test,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def override_get_async_session():
    async with AsyncSessionLocalTest() as session:
        yield session

async def override_get_current_user():
    return User(id=1, email="user@test.com", is_superuser=False)

async def override_get_admin_user():
    return User(id=2, email="admin@test.com", is_superuser=True)

# We use the sync TestClient because it supports WebSockets natively in FastAPI
client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    # Setup DB
    async def init_db():
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(init_db())
    
    app.dependency_overrides[get_async_session] = override_get_async_session
    app.dependency_overrides[get_admin_user] = override_get_admin_user
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    yield
    
    # Teardown DB
    async def drop_db():
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine_test.dispose()
    asyncio.run(drop_db())
    app.dependency_overrides.clear()


def test_realtime_websocket_flow():
    # 1. Create a facility via REST
    res = client.post("/api/v1/facilities", json={"name": "WS Facility", "address": "WS Addr", "total_slots": 10})
    if res.status_code == 404:
        res = client.post("/facilities", json={"name": "WS Facility", "address": "WS Addr", "total_slots": 10})
    assert res.status_code == 201
    facility_id = res.json()["id"]

    # 2. Create a zone
    res = client.post(f"/facilities/{facility_id}/zones", json={"name": "WS Zone"})
    assert res.status_code == 201
    zone_id = res.json()["id"]

    # 3. Create a slot
    res = client.post(f"/zones/{zone_id}/slots", json={"slot_number": "WS1"})
    assert res.status_code == 201
    slot_id = res.json()["id"]

    # 4. Connect via WebSocket and check initial snapshot
    with client.websocket_connect(f"/ws/parking/{facility_id}") as websocket:
        data = websocket.receive_json()
        assert data["event"] == "parking_snapshot"
        assert data["facility_id"] == facility_id
        assert data["data"]["total_slots"] == 1
        assert len(data["data"]["slots"]) == 1
        assert data["data"]["slots"][0]["slot_number"] == "WS1"
        assert data["data"]["slots"][0]["status"] == "available"

        # 5. Update slot status in REST while WS is connected
        # Since we are using synchronous TestClient, we might need a background task or 
        # since FastAPI TestClient blocks, we can just patch it and then receive the events.
        # Oh wait, if we are inside the `with` block, we can't make another client call easily if it blocks on the same thread for SQLite locks.
        # But aiosqlite + StaticPool should allow concurrent connections.
        res = client.patch(f"/slots/{slot_id}/status", json={"status": "occupied"})
        assert res.status_code == 200

        # 6. Receive status change event
        status_data = websocket.receive_json()
        assert status_data["event"] == "slot_status_changed"
        assert status_data["slot_id"] == slot_id
        assert status_data["new_status"] == "occupied"

        # 7. Receive occupancy update event
        occ_data = websocket.receive_json()
        assert occ_data["event"] == "occupancy_updated"
        assert occ_data["data"]["occupied_slots"] == 1
        assert occ_data["data"]["available_slots"] == 0

def test_websocket_invalid_facility():
    from starlette.websockets import WebSocketDisconnect
    try:
        with client.websocket_connect("/ws/parking/9999") as websocket:
            websocket.receive_json()
        assert False, "Should have disconnected"
    except WebSocketDisconnect as e:
        assert e.code == 4004
