# backend/api/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Any

_clients: list[WebSocket] = []


async def ws_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    _clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in _clients:
            _clients.remove(websocket)


async def broadcast(data: Any) -> None:
    dead = []
    for client in _clients:
        try:
            await client.send_json(data)
        except Exception:
            dead.append(client)
    for c in dead:
        _clients.remove(c)
