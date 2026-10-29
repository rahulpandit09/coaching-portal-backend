from typing import Dict, List, Any
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Map client_id / username to list of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)

    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            if websocket in self.active_connections[client_id]:
                self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]

    async def send_personal_message(self, client_id: str, message: Any):
        if client_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[client_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.debug(f"Failed to send websocket message to {client_id}: {e}")
                    dead_connections.append(connection)
            for dead in dead_connections:
                self.disconnect(dead, client_id)

    async def broadcast(self, message: Any):
        for client_id, connections in list(self.active_connections.items()):
            dead_connections = []
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.debug(f"Failed to broadcast message to {client_id}: {e}")
                    dead_connections.append(connection)
            for dead in dead_connections:
                self.disconnect(dead, client_id)


manager = ConnectionManager()
