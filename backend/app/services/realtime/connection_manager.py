import asyncio
from typing import Dict, List
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Map of facility_id -> list of active WebSocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, facility_id: int):
        await websocket.accept()
        async with self.lock:
            if facility_id not in self.active_connections:
                self.active_connections[facility_id] = []
            self.active_connections[facility_id].append(websocket)
            logger.info(f"Client connected to facility {facility_id}. Total: {len(self.active_connections[facility_id])}")

    async def disconnect(self, websocket: WebSocket, facility_id: int):
        async with self.lock:
            if facility_id in self.active_connections:
                if websocket in self.active_connections[facility_id]:
                    self.active_connections[facility_id].remove(websocket)
                    if not self.active_connections[facility_id]:
                        del self.active_connections[facility_id]
                    logger.info(f"Client disconnected from facility {facility_id}")

    async def broadcast_to_facility(self, facility_id: int, message: str):
        # We take a copy of the list to safely iterate while items might be removed
        async with self.lock:
            connections = self.active_connections.get(facility_id, []).copy()
        
        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Error sending message to client on facility {facility_id}: {e}")
                await self.disconnect(connection, facility_id)

manager = ConnectionManager()
