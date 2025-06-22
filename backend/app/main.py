from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import json
import logging
import os
from datetime import datetime

from .database import engine, get_db
from .models import Base, Message
from .websocket_manager import manager

# Создаем таблицы
Base.metadata.create_all(bind=engine)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GroupChat WebSocket API", version="1.0.0")

# Добавляем CORS для Railway
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене лучше указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def get(request):
    """Простая HTML страница для тестирования чата"""
    # Определяем WebSocket URL в зависимости от окружения
    host = request.headers.get("host", "localhost:8000")
    is_https = request.headers.get("x-forwarded-proto") == "https" or request.url.scheme == "https"
    ws_protocol = "wss" if is_https else "ws"
    ws_url = f"{ws_protocol}://{host}"

    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
<head>
    <title>Group Chat Test</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        #messages {{ border: 1px solid #ccc; height: 300px; overflow-y: scroll; padding: 10px; margin: 10px 0; }}
        #messageInput {{ width: 300px; padding: 5px; }}
        #sendButton, #connectButton {{ padding: 5px 10px; margin: 5px; }}
        .message {{ margin: 5px 0; }}
        .system {{ color: #666; font-style: italic; }}
        .user {{ color: #000; }}
        .timestamp {{ color: #999; font-size: 0.8em; }}
    </style>
</head>
<body>
    <h1>Group Chat Test</h1>

    <div>
        <input type="text" id="usernameInput" placeholder="Введите ваше имя" />
        <button id="connectButton" onclick="connect()">Подключиться</button>
        <button id="disconnectButton" onclick="disconnect()" disabled>Отключиться</button>
    </div>

    <div id="messages"></div>

    <div>
        <input type="text" id="messageInput" placeholder="Введите сообщение" disabled />
        <button id="sendButton" onclick="sendMessage()" disabled>Отправить</button>
    </div>

    <div>
        <p>Статус: <span id="status">Отключен</span></p>
        <p>Онлайн: <span id="onlineCount">0</span></p>
    </div>

    <script>
        let ws = null;
        let username = null;

        function connect() {{
            username = document.getElementById('usernameInput').value.trim();
            if (!username) {{
                alert('Введите имя пользователя');
                return;
            }}

            ws = new WebSocket(`{ws_url}/ws/${{username}}`);

            ws.onopen = function(event) {{
                document.getElementById('status').innerText = 'Подключен';
                document.getElementById('connectButton').disabled = true;
                document.getElementById('disconnectButton').disabled = false;
                document.getElementById('messageInput').disabled = false;
                document.getElementById('sendButton').disabled = false;
                document.getElementById('usernameInput').disabled = true;
            }};

            ws.onmessage = function(event) {{
                const data = JSON.parse(event.data);
                displayMessage(data);
            }};

            ws.onclose = function(event) {{
                document.getElementById('status').innerText = 'Отключен';
                document.getElementById('connectButton').disabled = false;
                document.getElementById('disconnectButton').disabled = true;
                document.getElementById('messageInput').disabled = true;
                document.getElementById('sendButton').disabled = true;
                document.getElementById('usernameInput').disabled = false;
            }};

            ws.onerror = function(error) {{
                console.error('WebSocket error:', error);
            }};
        }}

        function disconnect() {{
            if (ws) {{
                ws.close();
            }}
        }}

        function sendMessage() {{
            const messageInput = document.getElementById('messageInput');
            const message = messageInput.value.trim();

            if (message && ws) {{
                ws.send(JSON.stringify({{
                    type: 'message',
                    content: message
                }}));
                messageInput.value = '';
            }}
        }}

        function displayMessage(data) {{
            const messages = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message';

            if (data.type === 'system') {{
                messageDiv.className += ' system';
                messageDiv.innerHTML = data.content;
            }} else if (data.type === 'history') {{
                // Отображаем историю сообщений
                data.messages.forEach(msg => {{
                    const historyDiv = document.createElement('div');
                    historyDiv.className = 'message user';
                    historyDiv.innerHTML = `
                        <strong>${{msg.username}}:</strong> ${{msg.content}}
                        <span class="timestamp">(${{new Date(msg.created_at).toLocaleString()}})</span>
                    `;
                    messages.appendChild(historyDiv);
                }});
                messages.scrollTop = messages.scrollHeight;
                return;
            }} else {{
                messageDiv.className += ' user';
                const timestamp = data.timestamp ? new Date(data.timestamp).toLocaleString() : '';
                messageDiv.innerHTML = `
                    <strong>${{data.username}}:</strong> ${{data.content}}
                    <span class="timestamp">(${{timestamp}})</span>
                `;
            }}

            messages.appendChild(messageDiv);
            messages.scrollTop = messages.scrollHeight;
        }}

        // Отправка сообщения по Enter
        document.getElementById('messageInput').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') {{
                sendMessage();
            }}
        }});
    </script>
</body>
</html>
    """)


@app.websocket("/ws/{{username}}")
async def websocket_endpoint(websocket: WebSocket, username: str, db: Session = Depends(get_db)):
    """WebSocket эндпоинт для чата"""

    # Подключаем пользователя
    await manager.connect(websocket, username)

    try:
        # Отправляем историю сообщений новому пользователю
        recent_messages = db.query(Message).order_by(Message.created_at.desc()).limit(50).all()
        recent_messages.reverse()  # Меняем порядок на хронологический

        if recent_messages:
            history_data = {{
                "type": "history",
                "messages": [msg.to_dict() for msg in recent_messages]
            }}
            await manager.send_personal_message(json.dumps(history_data, ensure_ascii=False), websocket)

        # Основной цикл обработки сообщений
        while True:
            # Получаем сообщение от клиента
            data = await websocket.receive_text()
            message_data = json.loads(data)

            if message_data.get("type") == "message":
                content = message_data.get("content", "").strip()

                if content:
                    # Сохраняем сообщение в базу данных
                    db_message = Message(username=username, content=content)
                    db.add(db_message)
                    db.commit()
                    db.refresh(db_message)

                    # Отправляем сообщение всем подключенным пользователям
                    broadcast_data = {{
                        "type": "message",
                        "username": username,
                        "content": content,
                        "timestamp": db_message.created_at.isoformat() if db_message.created_at else None
                    }}

                    await manager.broadcast_message(broadcast_data)
                    logger.info(f"Message from {{username}}: {{content}}")

    except WebSocketDisconnect:
        # Пользователь отключился
        disconnected_user = manager.disconnect(websocket)
        if disconnected_user:
            await manager.broadcast_system_message(f"{{disconnected_user}} покинул чат")

    except Exception as e:
        logger.error(f"Error in websocket connection: {{e}}")
        manager.disconnect(websocket)


@app.get("/api/messages", response_model=List[dict])
async def get_messages(limit: int = 50, db: Session = Depends(get_db)):
    """API для получения последних сообщений"""
    messages = db.query(Message).order_by(Message.created_at.desc()).limit(limit).all()
    messages.reverse()
    return [msg.to_dict() for msg in messages]


@app.get("/api/online")
async def get_online_users():
    """API для получения списка онлайн пользователей"""
    return {{
        "users": manager.get_connected_users(),
        "count": len(manager.active_connections)
    }}


@app.get("/health")
async def health_check():
    """Health check для Railway"""
    return {{"status": "healthy"}}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)