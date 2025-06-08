import asyncio
from datetime import time
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

    async def broadcast_to_subscribers(self, post):
        """Отправка поста с отслеживанием просмотров"""
        with self.clients_lock:
            if not self.clients:
                return

            tasks = []
            for websocket, client_info in self.clients.items():
                if post.channel_id in client_info["channels"]:
                    try:
                        message = json.dumps(post.__dict__)
                        task = asyncio.create_task(websocket.send(message))
                        # Прикрепляем информацию для отслеживания
                        task.client_info = client_info
                        task.post_id = post.id
                        task.websocket = websocket
                        tasks.append(task)
                    except Exception as e:
                        logger.error(f"Send error: {e}")
                        del self.clients[websocket]
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    task = tasks[i]
                    if not isinstance(result, Exception):
                        # Успешная отправка = просмотр
                        await self.add_viewed_post(
                            task.client_info["user_id"],
                            task.post_id
                        )
                    else:
                        # Обработка ошибок отправки
                        with self.clients_lock:
                            if task.websocket in self.clients:
                                del self.clients[task.websocket]

    async def add_viewed_post(self, user_id: str, post_id: str):
        """Добавление просмотра в Redis (асинхронно)"""
        loop = asyncio.get_running_loop()
        def _add():
            key = f"user:viewed:{user_id}"
            timestamp = time.time()
            with self.redis.pipeline() as pipe:
                # Добавляем пост с временной меткой
                pipe.zadd(key, {post_id: timestamp})
                # Устанавливаем TTL 48 часов для ключа
                pipe.expire(key, 48 * 3600)
                pipe.execute()
        await loop.run_in_executor(None, _add)

    def process_event(self, post):
        """Обработка нового поста (вызывается из основного потока)"""
        # Сохранение с использованием ID поста
        self.redis.setex(
            f"post:{post.id}",
            86400,  # 24 часа TTL
            json.dumps(post.__dict__)
        )
        
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
