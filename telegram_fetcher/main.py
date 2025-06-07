import asyncio
import logging
import signal
from typing import List, Dict
import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
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
    allow_origins=["*"],  # Разрешаем все origins для тестов
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальные переменные
queue: asyncio.Queue = None
workers: List[TgClientWorker] = None
channel_status: Dict[str, str] = {}  # Статус подключения к каналам
background_tasks: List[asyncio.Task] = []  # Список фоновых задач

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_id = request.client.host
    if rate_limiter.is_rate_limited(client_id):
        raise HTTPException(status_code=429, detail="Too many requests")
    return await call_next(request)

@app.get("/api/channels")
async def get_channels():
    try:
        channels = db.get_channels()
        # Добавляем статус для каждого канала
        for channel in channels:
            channel["status"] = channel_status.get(channel["link"], "pending")
        return channels
    except Exception as e:
        logger.error(f"Error getting channels: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/add_channel")
async def add_channel(channel: ChannelIn):
    try:
        logger.info(f"Received request to add channel: {channel.link}")
        
        # Проверяем, существует ли канал
        channels = db.get_channels()
        if any(c["link"] == channel.link for c in channels):
            logger.info(f"Channel {channel.link} already exists")
            return {"ok": True, "status": "already_exists", "message": "Channel already exists"}
        
        # Добавляем канал
        logger.info(f"Adding channel to database: {channel.link}")
        db.add_channel(channel.dict())
        channel_status[channel.link] = "pending"
        logger.info(f"Channel {channel.link} added to database, status set to pending")
        
        # Запускаем задачу для проверки статуса подключения
        logger.info(f"Starting connection check task for channel: {channel.link}")
        check_task = asyncio.create_task(check_channel_connection(channel.link))
        background_tasks.append(check_task)
        
        logger.info(f"Successfully initiated channel addition process for: {channel.link}")
        return {
            "ok": True,
            "status": "pending",
            "message": "Channel added, connection in progress"
        }
    except Exception as e:
        logger.error(f"Error adding channel {channel.link}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/api/channels/{link}")
async def delete_channel(link: str):
    try:
        db.remove_channel(link)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error deleting channel: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def check_channel_connection(channel_link: str, timeout: int = 60):
    """Проверяет статус подключения к каналу."""
    logger.info(f"Starting connection check for channel: {channel_link}")
    start_time = asyncio.get_event_loop().time()
    
    while True:
        try:
            # Проверяем, подключен ли канал к любому из воркеров
            if workers:
                for worker in workers:
                    if channel_link in worker.my_links:
                        channel_status[channel_link] = "connected"
                        logger.info(f"Channel {channel_link} successfully connected by worker {worker.client.session.filename}")
                        return
            else:
                logger.warning("No workers available for channel connection check")
            
            # Проверяем таймаут
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > timeout:
                channel_status[channel_link] = "failed"
                logger.error(f"Failed to connect to channel {channel_link} after {timeout} seconds")
                return
            
            logger.debug(f"Waiting for channel {channel_link} connection... ({int(current_time - start_time)}s elapsed)")
            await asyncio.sleep(5)  # Проверяем каждые 5 секунд
            
        except Exception as e:
            logger.error(f"Error in connection check for channel {channel_link}: {e}", exc_info=True)
            channel_status[channel_link] = "failed"
            return

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint для отправки сообщений клиентам."""
    try:
        await websocket.accept()
        logger.info(f"WebSocket connection accepted from {websocket.client.host}")
        
        # Отправляем приветственное сообщение
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to Telegram Fetcher WebSocket"
        })
        
        while True:
            try:
                # Ждем сообщения из очереди
                msg = await queue.get()
                await websocket.send_json(msg)
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {websocket.client.host}")
                break
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                break
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info(f"WebSocket connection closed: {websocket.client.host}")

async def run_telegram_clients():
    """Запуск Telegram клиентов в фоновом режиме."""
    global workers
    try:
        workers = await run_pool(queue)
        logger.info(f"Started {len(workers)} Telegram clients")
        
        # Запускаем все клиенты в фоновом режиме
        for worker in workers:
            task = asyncio.create_task(worker.refresh_channels_loop())
            background_tasks.append(task)
            logger.info(f"Started background task for client {worker.client.session.filename}")
            
    except Exception as e:
        logger.error(f"Error starting Telegram clients: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """Запуск сервиса при старте."""
    global queue
    queue = asyncio.Queue()
    
    # Запускаем Telegram клиенты в фоновом режиме
    asyncio.create_task(run_telegram_clients())
    logger.info("Service started")

@app.on_event("shutdown")
async def shutdown_event():
    """Обработка завершения работы сервиса."""
    # Отменяем все фоновые задачи
    for task in background_tasks:
        task.cancel()
    
    # Ждем завершения всех задач
    if background_tasks:
        await asyncio.gather(*background_tasks, return_exceptions=True)
    
    # Останавливаем клиенты
    if workers:
        for w in workers:
            await w.stop()
    
    logger.info("Service shutdown complete")

def handle_sigterm(*_):
    """Обработка сигнала SIGTERM."""
    logger.info("Received SIGTERM")
    asyncio.create_task(shutdown_event())

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