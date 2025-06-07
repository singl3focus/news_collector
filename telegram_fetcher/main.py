import asyncio
import logging
import signal
from typing import List
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from jsondb import JsonDB
from jsondb_api import ChannelIn, db, rate_limiter
from tg_client_pool import TgClientWorker, run_pool

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация хранилища каналов
db = JsonDB()

# Создаем единое FastAPI приложение
app = FastAPI(title="Telegram Fetcher Service")

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене лучше ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_id = request.client.host
    if rate_limiter.is_rate_limited(client_id):
        raise HTTPException(status_code=429, detail="Too many requests")
    return await call_next(request)

@app.get("/api/channels")
async def get_channels():
    try:
        return db.get_channels()
    except Exception as e:
        logger.error(f"Error getting channels: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/channels")
async def add_channel(channel: ChannelIn):
    try:
        db.add_channel(channel.dict())
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error adding channel: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/api/channels/{link}")
async def delete_channel(link: str):
    try:
        db.remove_channel(link)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error deleting channel: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Глобальные переменные
queue: asyncio.Queue = None
workers: List[TgClientWorker] = None

@app.websocket("/ws")
async def websocket_endpoint(websocket):
    """WebSocket endpoint для отправки сообщений клиентам."""
    await websocket.accept()
    try:
        while True:
            msg = await queue.get()
            await websocket.send_json(msg)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

async def shutdown():
    """Корректное завершение работы сервиса."""
    logger.info("Shutting down...")
    if workers:
        for w in workers:
            await w.stop()
    logger.info("Shutdown complete")

@app.on_event("startup")
async def startup_event():
    """Запуск сервиса при старте."""
    global queue, workers
    queue = asyncio.Queue()
    workers = await run_pool(queue)
    logger.info("Service started")

@app.on_event("shutdown")
async def shutdown_event():
    """Обработка завершения работы сервиса."""
    await shutdown()

def handle_sigterm(*_):
    """Обработка сигнала SIGTERM."""
    logger.info("Received SIGTERM")
    asyncio.create_task(shutdown())

if __name__ == "__main__":
    # Регистрируем обработчик SIGTERM
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    # Запускаем сервер
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    ) 