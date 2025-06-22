from typing import List, Dict
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Список активных соединений
        self.active_connections: List[WebSocket] = []
        # Словарь для хранения информации о пользователях
        self.user_info: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, username: str):
        """Подключение нового пользователя"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.user_info[websocket] = username

        logger.info(f"User {username} connected. Total connections: {len(self.active_connections)}")

        # Уведомляем всех о новом пользователе
        await self.broadcast_system_message(f"{username} присоединился к чату")

    def disconnect(self, websocket: WebSocket):
        """Отключение пользователя"""
        if websocket in self.active_connections:
            username = self.user_info.get(websocket, "Unknown")
            self.active_connections.remove(websocket)
            if websocket in self.user_info:
                del self.user_info[websocket]

            logger.info(f"User {username} disconnected. Total connections: {len(self.active_connections)}")
            return username
        return None

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Отправка личного сообщения"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast_message(self, message_data: dict):
        """Рассылка сообщения всем подключенным пользователям"""
        message = json.dumps(message_data, ensure_ascii=False)
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to user: {e}")
                disconnected.append(connection)

        # Удаляем отключенные соединения
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_system_message(self, content: str):
        """Рассылка системного сообщения"""
        system_message = {
            "type": "system",
            "content": content,
            "timestamp": None
        }
        await self.broadcast_message(system_message)

    def get_connected_users(self) -> List[str]:
        """Получить список подключенных пользователей"""
        return list(self.user_info.values())


# Глобальный экземпляр менеджера соединений
manager = ConnectionManager()
