from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WsManager:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._connections: dict[str, set[WebSocket]] = {}

    def connect(self, workspace_id: str, ws: WebSocket) -> None:
        self._connections.setdefault(workspace_id, set()).add(ws)

    def disconnect(self, workspace_id: str, ws: WebSocket) -> None:
        conns = self._connections.get(workspace_id)
        if conns:
            conns.discard(ws)

    def broadcast(self, workspace_id: str, msg: dict) -> None:
        if not self._loop.is_running():
            return
        asyncio.run_coroutine_threadsafe(self._send_all(workspace_id, msg), self._loop)

    async def _send_all(self, workspace_id: str, msg: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._connections.get(workspace_id, set())):
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(workspace_id, ws)
