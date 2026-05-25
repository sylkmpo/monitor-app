from typing import Any, Dict, List

from fastapi import WebSocket
from loguru import logger


class EventNotificationService:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        stale_connections: List[WebSocket] = []
        for websocket in self.active_connections:
            try:
                await websocket.send_json(payload)
            except Exception as exc:
                logger.warning(f"WebSocket event push failed: {exc}")
                stale_connections.append(websocket)

        for websocket in stale_connections:
            self.disconnect(websocket)
