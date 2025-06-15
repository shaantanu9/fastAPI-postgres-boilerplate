"""
WebSocket API routes for FastAPI.

- Endpoint: /ws/{room}
- Auth: JWT token required as query param (?token=...)
- Connection tracking: memory-leak safe, room-based
- Heartbeat: see manager.start_heartbeat() for dead connection cleanup
- Logging: connection, disconnection, errors
- Presence: /ws/presence/{room} (GET)
- Direct messaging: /ws/direct/{target_user} (WebSocket)
- Message history: /ws/history/{room} (GET)

Testing:
- Use FastAPI TestClient for automated tests
- Use Apidog/Postman or browser for manual tests
- Example: ws://localhost:8000/ws/testroom?token=JWT_TOKEN
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, Request
from app.websocket.manager import get_websocket_manager, WebSocketManager
import jwt
import os
import logging

router = APIRouter()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecret")
ALGORITHM = "HS256"

async def get_current_user(token: str = Query(...)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid token: missing user id")
        return user_id
    except Exception:
        return None

@router.websocket("/ws/{room}")
async def websocket_endpoint(
    websocket: WebSocket,
    room: str,
    token: str = Query(...),
    request: Request = None,
    manager: WebSocketManager = Depends(lambda request: get_websocket_manager(request)),
):
    user_id = await get_current_user(token)
    if not user_id:
        logging.warning(f"WebSocket rejected: invalid token {token}")
        await websocket.close(code=1008)  # Policy Violation
        return
    connection_id = f"{user_id}:{id(websocket)}"
    try:
        await manager.connect(websocket, connection_id, room=room, user_id=user_id)
        logging.info(f"WebSocket connected: user={user_id}, room={room}, id={connection_id}")
        # Send message history
        if manager.history:
            history = await manager.history.get_history(room)
            for msg in history:
                await websocket.send_text(msg)
        while True:
            data = await websocket.receive_text()
            if data.startswith("/dm ") and manager.user_connections:
                # Direct message: /dm target_user message
                try:
                    _, target_user, msg = data.split(" ", 2)
                    await direct_message(manager, user_id, target_user, msg)
                except Exception:
                    await websocket.send_text("Invalid direct message format. Use /dm target_user message")
            else:
                await manager.broadcast(f"{user_id}: {data}", room=room)
    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected: user={user_id}, room={room}, id={connection_id}")
    except Exception as e:
        logging.error(f"WebSocket error: user={user_id}, room={room}, id={connection_id}, error={e}")
        try:
            await websocket.send_text("Error: " + str(e))
        except Exception:
            pass
    finally:
        await manager.disconnect(websocket, room=room, user_id=user_id)

async def direct_message(manager: WebSocketManager, from_user: str, to_user: str, message: str):
    targets = manager.user_connections.get(to_user)
    if not targets:
        return
    for ws in list(targets):
        try:
            await ws.send_text(f"[DM] {from_user}: {message}")
        except Exception:
            pass

@router.get("/ws/presence/{room}")
async def get_presence(room: str, request: Request = None, manager: WebSocketManager = Depends(lambda request: get_websocket_manager(request))):
    if not manager.presence:
        raise HTTPException(status_code=501, detail="Presence not enabled")
    return {"room": room, "users": await manager.presence.get_online_users(room)}

@router.get("/ws/history/{room}")
async def get_history(room: str, request: Request = None, manager: WebSocketManager = Depends(lambda request: get_websocket_manager(request))):
    if not manager.history:
        raise HTTPException(status_code=501, detail="History not enabled")
    return {"room": room, "history": await manager.history.get_history(room)}

@router.websocket("/ws/direct/{target_user}")
async def direct_ws(
    websocket: WebSocket,
    target_user: str,
    token: str = Query(...),
    request: Request = None,
    manager: WebSocketManager = Depends(lambda request: get_websocket_manager(request)),
):
    user_id = await get_current_user(token)
    if not user_id:
        logging.warning(f"Direct WebSocket rejected: invalid token {token}")
        await websocket.close(code=1008)
        return
    connection_id = f"{user_id}:{id(websocket)}"
    try:
        await manager.connect(websocket, connection_id, user_id=user_id)
        while True:
            data = await websocket.receive_text()
            await direct_message(manager, user_id, target_user, data)
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket, user_id=user_id) 