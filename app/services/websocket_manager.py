from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Map user_id to their active WebSocket connection
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                print(f"Error sending message to user {user_id}: {e}")
                # Maybe disconnect if broken?
                pass

    async def broadcast(self, message: dict, user_ids: List[int]):
        """Broadcast message to a list of user_ids if they are connected."""
        for user_id in user_ids:
            await self.send_personal_message(message, user_id)

manager = ConnectionManager()
