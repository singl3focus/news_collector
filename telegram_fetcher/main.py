import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from jsondb_api import app as rest_app, db
from ws_server import app as ws_app, websocket_endpoint
from tg_client_pool import TgClientWorker, run_pool

# Объединяем REST API и WebSocket в один FastAPI приложение
app = FastAPI(title="Telegram Fetcher Service")

# Добавляем CORS middleware для REST API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем запросы с любого origin (в продакшене лучше ограничить)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Монтируем REST API приложение по пути /api
app.mount("/api", rest_app)

# Монтируем WebSocket endpoint
app.websocket("/ws")(websocket_endpoint)

# Глобальная очередь сообщений
queue = asyncio.Queue()

# Конфигурация Telegram клиентов
# TODO: Замените на свои значения API_ID, API_HASH и SESSION_NAMES
API_ID_LIST = [123456, 789012]  # Пример
API_HASH_LIST = ["your_api_hash_1", "your_api_hash_2"]  # Пример
SESSION_NAMES = ["client1", "client2"]  # Пример

async def start_telegram_clients():
    """Запускает пул Telegram клиентов."""
    global queue
    await run_pool(queue)

@app.on_event("startup")
async def startup_event():
    """Запускает Telegram клиентов при старте сервера."""
    asyncio.create_task(start_telegram_clients())

async def main():
    queue = asyncio.Queue()
    # Подставляем очередь в ws_server
    import ws_server
    ws_server.queue = queue
    await run_pool(queue)
    uvicorn.run(ws_app, host="0.0.0.0", port=8002)

if __name__ == "__main__":
    # jsondb_api поднимаем отдельно: uvicorn telegram_fetcher.jsondb_api:app --host 0.0.0.0 --port 8001
    # а main.py — как основной воркер Telegram и WS
    asyncio.run(main()) 