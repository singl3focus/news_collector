import asyncio
import json
import uuid
import websockets
import threading
import logging
from threading import Lock
from .pubsub import PubSub
from .filter import NewsPost

logger = logging.getLogger(__name__)

class WSServer:
    def __init__(self, pubsub: PubSub, redis_client, host: str, port: int):
        self.pubsub = pubsub
        self.redis = redis_client
        self.clients = {}  # websocket: {"user_id": "...", "channels": set()}
        self.host = host
        self.port = port
        self.server = None
        self.loop = None
        self.clients_lock = Lock()  # Блокировка для потокобезопасности

    async def handler(self, websocket):
        try:
            # Аутентификация
            auth = await websocket.recv()
            try:
                token = json.loads(auth)["token"]
            except (json.JSONDecodeError, KeyError):
                await websocket.close(code=4001)
                return

            # Проверка токена
            user_id = self.redis.get(f"auth:token:{token}")
            if not user_id:
                await websocket.close(code=4001)
                return

            # Загрузка подписок
            channels = self.redis.smembers(f"user:channels:{user_id}")
            with self.clients_lock:
                self.clients[websocket] = {
                    "user_id": user_id,
                    "channels": set(map(int, channels))
                }

            # Ожидание сообщений (TODO: можно добавить обработку команд)
            async for message in websocket:
                pass
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            with self.clients_lock:
                if websocket in self.clients:
                    del self.clients[websocket]

    async def broadcast_to_subscribers(self, post: NewsPost):
        """Отправка только подписанным клиентам"""
        with self.clients_lock:
            if not self.clients:
                return

            tasks = []
            for websocket, client_info in self.clients.items():
                # Проверка подписки на канал
                if post.channel_id in client_info["channels"]:
                    try:
                        message = json.dumps(post.__dict__)
                        tasks.append(websocket.send(message))
                    except Exception as e:
                        logger.error(f"Send error: {e}")
                        # Удаляем отключенного клиента
                        del self.clients[websocket]
            
            if tasks:
                await asyncio.gather(*tasks)

    def process_event(self, post: NewsPost):
        """Обработка нового поста (вызывается из основного потока)"""
        # Сохранение в Redis
        self.redis.setex(f"post:{uuid.uuid4()}", 86400, json.dumps(post.__dict__))
        
        # Отправка подписчикам
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.broadcast_to_subscribers(post), 
                self.loop
            )

    def start(self):
        """Запуск сервера в отдельном потоке"""
        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.loop = loop  # Сохраняем ссылку на event loop
            
            async def start_server():
                self.server = await websockets.serve(
                    self.handler,
                    self.host,
                    self.port
                )
                logger.info(f"WS server started on {self.host}:{self.port}")
                await self.server.wait_closed()
                
            loop.run_until_complete(start_server())
        
        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()
