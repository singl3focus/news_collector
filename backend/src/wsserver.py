import asyncio
import json
import uuid
import websockets
import threading
from .pubsub import PubSub
from .filter import NewsPost


class WSServer:
    def __init__(self, pubsub: PubSub, redis_client, host: str, port: int):
        self.pubsub = pubsub
        self.redis = redis_client
        self.clients = {}  # websocket: {"user_id": "...", "channels": set()}
        self.host = host
        self.port = port
        self.server = None

    async def handler(self, websocket):
        try:
            # Первое сообщение - аутентификация
            auth = await websocket.recv()
            token = json.loads(auth)["token"]
            
            # Проверка токена
            user_id = self.redis.get(f"auth:token:{token}")
            if not user_id:
                await websocket.close(code=4001)
                return
                
            # Загружаем подписки пользователя
            channels = self.redis.smembers(f"user:channels:{user_id}")
            self.clients[websocket] = {
                "user_id": user_id,
                "channels": set(map(int, channels))
            }

            async for _ in websocket:
                pass
        finally:
            self.clients.remove(websocket)

    async def broadcast(self, data):
        if self.clients:
            message = json.dumps(data.__dict__)
            await asyncio.gather(*[client.send(message) for client in self.clients])

    def process_event(self, post: NewsPost):
        # Сохранение в Redis
        self.redis.setex(f"post:{uuid.uuid4()}", 86400, json.dumps(post.__dict__))

        # Запуск broadcast в отдельном event loop
        asyncio.run_coroutine_threadsafe(self.broadcast(post), self.loop)

    # Запуск WebSocket сервера в отдельном потоке с собственным event loop
    def start(self):
        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def start():
                server = await websockets.serve(
                    self.handler, 
                    self.host, 
                    self.port
                )
                await asyncio.Future()  # Бесконечное ожидание
            
            loop.run_until_complete(start())
        
        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()
