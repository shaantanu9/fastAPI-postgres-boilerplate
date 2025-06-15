"""
Test WebSocket endpoint (/ws/{room}) for connection, messaging, authentication, presence, direct messaging, and history.
"""
import pytest
import asyncio
import httpx_ws
from httpx import AsyncClient
from typing import AsyncGenerator, Generator
from datetime import datetime

pytestmark = pytest.mark.anyio

@pytest.fixture
async def ws_client(client: AsyncClient, make_token) -> AsyncGenerator[tuple[AsyncClient, str], None]:
    """Create a WebSocket client with authentication token."""
    token = make_token()
    yield client, token

@pytest.fixture
async def ws_connection(ws_client) -> AsyncGenerator[httpx_ws.WebSocketSession, None]:
    """Create a WebSocket connection."""
    client, token = ws_client
    ws_url = f"ws://test/ws/testroom?token={token}"
    async with httpx_ws.connect_ws(ws_url, client=client) as ws:
        yield ws

async def test_websocket_connection(ws_connection):
    """Test WebSocket connection and basic messaging."""
    ws = ws_connection
    await ws.send_text("Hello, Server!")
    response = await ws.receive_text()
    assert "Hello" in response

async def test_websocket_room_messaging(ws_client):
    """Test WebSocket room messaging."""
    client, token = ws_client
    room = "test_room"
    
    ws_url1 = f"ws://test/ws/{room}?token={token}"
    ws_url2 = f"ws://test/ws/{room}?token={token}"
    
    async with httpx_ws.connect_ws(ws_url1, client=client) as ws1:
        async with httpx_ws.connect_ws(ws_url2, client=client) as ws2:
            await ws1.send_text("Hello from client 1")
            response = await ws2.receive_text()
            assert "Hello from client 1" in response

async def test_websocket_authentication(ws_client):
    """Test WebSocket authentication."""
    client, _ = ws_client
    
    # Try to connect without token
    with pytest.raises(httpx_ws.WebSocketUpgradeError):
        async with httpx_ws.connect_ws("ws://test/ws/testroom", client=client) as _:
            pass

async def test_websocket_presence(ws_client):
    """Test WebSocket presence notifications."""
    client, token = ws_client
    room = "presence_test"
    
    ws_url1 = f"ws://test/ws/{room}?token={token}"
    ws_url2 = f"ws://test/ws/{room}?token={token}"
    
    async with httpx_ws.connect_ws(ws_url1, client=client) as ws1:
        # Should receive presence notification for first client
        presence_msg = await ws1.receive_text()
        assert "joined" in presence_msg.lower()
        
        async with httpx_ws.connect_ws(ws_url2, client=client) as ws2:
            # Should receive presence notification for second client
            presence_msg = await ws1.receive_text()
            assert "joined" in presence_msg.lower()
            
        # Should receive disconnect notification
        disconnect_msg = await ws1.receive_text()
        assert "left" in disconnect_msg.lower()

async def test_websocket_direct_messaging(ws_client):
    """Test WebSocket direct messaging."""
    client, token = ws_client
    
    ws_url1 = f"ws://test/ws/room1?token={token}"
    ws_url2 = f"ws://test/ws/room2?token={token}"
    
    async with httpx_ws.connect_ws(ws_url1, client=client) as ws1:
        async with httpx_ws.connect_ws(ws_url2, client=client) as ws2:
            # Send direct message
            await ws1.send_json({
                "type": "direct",
                "target": "user2",
                "message": "Private message"
            })
            
            # Receive direct message
            response = await ws2.receive_json()
            assert response["type"] == "direct"
            assert response["message"] == "Private message"

async def test_websocket_connect_and_message(ws_client: tuple[AsyncClient, str]):
    """Test basic WebSocket connection and messaging."""
    client, token = ws_client
    async with httpx_ws.connect(f"ws://test/ws/testroom?token={token}", client=client) as ws:
        await ws.send_text("hello")
        assert await wait_for_message(ws, "testuser: hello")

async def test_websocket_auth_failure(client: AsyncClient):
    """Test WebSocket connection with invalid token."""
    with pytest.raises(Exception):
        async with httpx_ws.connect("ws://test/ws/testroom", client=client) as _:
            pass

async def test_presence_tracking(ws_client: tuple[AsyncClient, str]):
    """Test user presence tracking in rooms."""
    client, token = ws_client
    room = "presence_test_room"
    
    async with httpx_ws.connect(f"ws://test/ws/{room}?token={token}", client=client) as ws:
        # Wait for presence to update
        await asyncio.sleep(0.1)
        
        # Check presence via REST API
        resp = await client.get(f"/ws/presence/{room}")
        assert resp.status_code == 200
        presence_data = resp.json()
        assert "users" in presence_data
        assert "testuser" in presence_data["users"]

async def test_message_history(ws_client: tuple[AsyncClient, str]):
    """Test message history functionality."""
    client, token = ws_client
    room = "history_test_room"
    test_message = f"test message {datetime.utcnow().isoformat()}"
    
    async with httpx_ws.connect(f"ws://test/ws/{room}?token={token}", client=client) as ws:
        await ws.send_text(test_message)
        assert await wait_for_message(ws, f"testuser: {test_message}")
        
        # Check history via REST API
        resp = await client.get(f"/ws/history/{room}")
        assert resp.status_code == 200
        history_data = resp.json()
        assert "history" in history_data
        assert any(test_message in msg for msg in history_data["history"])

async def test_direct_messaging(client: AsyncClient, make_token):
    """Test direct messaging between users."""
    token1 = make_token("alice")
    token2 = make_token("bob")
    room = "dm_test_room"
    
    async with httpx_ws.connect(f"ws://test/ws/{room}?token={token1}", client=client) as ws1:
        async with httpx_ws.connect(f"ws://test/ws/{room}?token={token2}", client=client) as ws2:
            # Send DM from alice to bob
            dm_message = "private message"
            await ws1.send_text(f"/dm bob {dm_message}")
            
            # Bob should receive the DM
            assert await wait_for_message(ws2, f"[DM] alice: {dm_message}")
            
            # Alice should get confirmation
            assert await wait_for_message(ws1, "Message sent to bob")

async def test_multiple_room_handling(client: AsyncClient, make_token):
    """Test handling multiple rooms simultaneously."""
    token = make_token("multiroom_user")
    room1, room2 = "room1", "room2"
    
    async with httpx_ws.connect(f"ws://test/ws/{room1}?token={token}", client=client) as ws1:
        async with httpx_ws.connect(f"ws://test/ws/{room2}?token={token}", client=client) as ws2:
            # Send messages to both rooms
            msg1, msg2 = "message to room1", "message to room2"
            
            await ws1.send_text(msg1)
            await ws2.send_text(msg2)
            
            # Verify messages in respective rooms
            assert await wait_for_message(ws1, f"multiroom_user: {msg1}")
            assert await wait_for_message(ws2, f"multiroom_user: {msg2}")

async def test_connection_cleanup(ws_client: tuple[AsyncClient, str]):
    """Test proper cleanup of WebSocket connections."""
    client, token = ws_client
    room = "cleanup_test_room"
    
    # Connect and immediately disconnect
    ws = await httpx_ws.connect(f"ws://test/ws/{room}?token={token}", client=client)
    await ws.close()
    
    # Check presence after disconnect
    await asyncio.sleep(0.1)  # Wait for cleanup
    resp = await client.get(f"/ws/presence/{room}")
    assert resp.status_code == 200
    assert "testuser" not in resp.json()["users"] 