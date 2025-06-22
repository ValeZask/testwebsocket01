from typing import List, Dict
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_info: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.user_info[websocket] = username
        logger.info(f"User {username} connected. Total connections: {len(self.active_connections)}")
        await self.broadcast_system_message(f"{username} присоединился к чату")
        # Рассылаем обновлённое количество пользователей
        await self.broadcast_online_count()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            username = self.user_info.get(websocket, "Unknown")
            self.active_connections.remove(websocket)
            if websocket in self.user_info:
                del self.user_info[websocket]
            logger.info(f"User {username} disconnected. Total connections: {len(self.active_connections)}")
            return username
        return None

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast_message(self, message_data: dict):
        message = json.dumps(message_data, ensure_ascii=False)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to user: {e}")
                disconnected.append(connection)
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_system_message(self, content: str):
        system_message = {
            "type": "system",
            "content": content,
            "timestamp": None
        }
        await self.broadcast_message(system_message)

    async def broadcast_online_count(self):
        """Рассылает количество пользователей онлайн"""
        online_message = {
            "type": "online_count",
            "count": len(self.active_connections)
        }
        await self.broadcast_message(online_message)

    def get_connected_users(self) -> List[str]:
        return list(self.user_info.values())

manager = ConnectionManager()