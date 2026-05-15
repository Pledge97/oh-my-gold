# backend/api/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Any

_clients: list[WebSocket] = []
_last_message: Any = None  # 缓存最近一次推送，新连接立即发送


async def ws_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    _clients.append(websocket)
    # 新连接立即推送最近一次数据，不等下一个调度周期
    if _last_message is not None:
        try:
            await websocket.send_json(_last_message)
        except Exception:
            pass
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in _clients:
            _clients.remove(websocket)


async def broadcast(data: Any) -> None:
    global _last_message
    _last_message = data
    dead = []
    for client in _clients:
        try:
            await client.send_json(data)
        except Exception:
            dead.append(client)
    for c in dead:
        _clients.remove(c)
