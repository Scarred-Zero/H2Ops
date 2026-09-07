import asyncio
import json
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger("websocket_manager")


class ConnectionManager:
    """
    Manages live WebSocket connections grouped into "rooms" — one room per
    facility_id — so a broadcast for Facility A never reaches a client only
    watching Facility B. Safe for concurrent connect/disconnect/broadcast
    from multiple asyncio tasks (MQTT subscriber, REST handlers, etc.).
    """

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, facility_id: str) -> None:
        await websocket.accept()
        async with self._lock:
            self._rooms[facility_id].add(websocket)
        logger.info(f"Client connected to facility room {facility_id}")

    async def disconnect(self, websocket: WebSocket, facility_id: str) -> None:
        async with self._lock:
            room = self._rooms.get(facility_id)
            if room and websocket in room:
                room.remove(websocket)
                if not room:
                    del self._rooms[facility_id]
        logger.info(f"Client disconnected from facility room {facility_id}")

    async def broadcast_to_facility(self, facility_id: str, payload: dict) -> None:
        """Send a JSON payload to every socket subscribed to this facility."""
        async with self._lock:
            room = list(self._rooms.get(facility_id, ()))

        if not room:
            return

        message = json.dumps(payload, default=str)
        stale: list[WebSocket] = []

        for socket in room:
            try:
                await socket.send_text(message)
            except Exception as exc:
                logger.warning(f"Dropping dead socket in {facility_id}: {exc}")
                stale.append(socket)

        if stale:
            async with self._lock:
                for socket in stale:
                    self._rooms.get(facility_id, set()).discard(socket)

    async def broadcast_to_all(self, payload: dict) -> None:
        """Useful for system-wide alerts (e.g. broker disconnect notices)."""
        async with self._lock:
            facility_ids = list(self._rooms.keys())
        for facility_id in facility_ids:
            await self.broadcast_to_facility(facility_id, payload)

    def room_size(self, facility_id: str) -> int:
        return len(self._rooms.get(facility_id, ()))


# Singleton instance imported by ws routes and the MQTT subscriber worker
connection_manager = ConnectionManager()
