"""WebSocket connection management for realtime dashboard updates."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Track websocket clients by room and broadcast structured messages."""

    def __init__(self) -> None:
        self._active: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str = "dashboard") -> None:
        """Accept a websocket connection and register it in a room."""
        await websocket.accept()
        room_sockets = self._active.setdefault(room, [])
        room_sockets.append(websocket)
        logger.info(f"[WS] Client connected to room: {room}. Total in room: {len(room_sockets)}")

    def disconnect(self, websocket: WebSocket, room: str = "dashboard") -> None:
        """Remove a websocket connection from a room."""
        room_sockets = self._active.get(room, [])
        if websocket in room_sockets:
            room_sockets.remove(websocket)
        if not room_sockets and room in self._active:
            self._active.pop(room, None)
        logger.info(f"[WS] Client disconnected from room: {room}. Total in room: {len(room_sockets)}")

    async def broadcast(self, message: dict, room: str = "dashboard") -> None:
        """Broadcast a JSON message to all clients in a room."""
        payload = json.dumps(message)
        room_sockets = list(self._active.get(room, []))
        for websocket in room_sockets:
            try:
                await websocket.send_text(payload)
            except Exception:
                logger.exception(f"[WS] Broadcast failed for room: {room}")
                self.disconnect(websocket, room)

    async def broadcast_all(self, message: dict) -> None:
        """Broadcast a JSON message to every active room."""
        for room in list(self._active.keys()):
            await self.broadcast(message, room=room)

    async def send_personal(self, message: dict, websocket: WebSocket) -> None:
        """Send a JSON message to a single websocket client."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception:
            logger.exception("[WS] Personal send failed.")

    def get_connection_count(self, room: Optional[str] = None) -> dict[str, int]:
        """Return the active websocket counts by room."""
        if room is not None:
            return {room: len(self._active.get(room, []))}
        return {room_name: len(sockets) for room_name, sockets in self._active.items()}


class MessageType(str, Enum):
    """Enumerate the supported websocket message categories."""

    AGENT_UPDATE = "agent_update"
    HITL_REQUEST = "hitl_request"
    HITL_RESOLVED = "hitl_resolved"
    KPI_UPDATE = "kpi_update"
    AGENT_STEP = "agent_step"
    ERROR = "error"


def build_ws_message(msg_type: MessageType, data: dict, agent: Optional[str] = None) -> dict:
    """Build a standard websocket payload envelope."""
    return {
        "type": msg_type.value,
        "agent": agent,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }


ws_manager = ConnectionManager()
