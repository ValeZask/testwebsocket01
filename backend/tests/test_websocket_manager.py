import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from backend.app.websocket_manager import ConnectionManager


@pytest.mark.asyncio
async def test_connect_adds_connection():
    manager = ConnectionManager()
    websocket = AsyncMock()
    username = "TestUser"

    await manager.connect(websocket, username)

    assert websocket in manager.active_connections
    assert manager.user_info[websocket] == username

@pytest.mark.asyncio
async def test_disconnect_removes_connection():
    manager = ConnectionManager()
    websocket = AsyncMock()
    username = "TestUser"

    await manager.connect(websocket, username)
    removed = manager.disconnect(websocket)

    assert websocket not in manager.active_connections
    assert websocket not in manager.user_info
    assert removed == username

@pytest.mark.asyncio
async def test_get_connected_users():
    manager = ConnectionManager()
    ws1, ws2 = AsyncMock(), AsyncMock()

    await manager.connect(ws1, "User1")
    await manager.connect(ws2, "User2")

    users = manager.get_connected_users()
    assert "User1" in users
    assert "User2" in users