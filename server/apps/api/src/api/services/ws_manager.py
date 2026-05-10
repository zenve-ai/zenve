from __future__ import annotations

import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, org_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(org_id, []).append(ws)
        logger.info("WS connected: org=%s total=%d", org_id, len(self._connections[org_id]))

    def disconnect(self, org_id: str, ws: WebSocket) -> None:
        conns = self._connections.get(org_id, [])
        if ws in conns:
            conns.remove(ws)
        logger.info("WS disconnected: org=%s remaining=%d", org_id, len(conns))

    async def broadcast(self, org_id: str, message: dict) -> None:
        conns = self._connections.get(org_id, [])
        if not conns:
            return
        stale: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(org_id, ws)
