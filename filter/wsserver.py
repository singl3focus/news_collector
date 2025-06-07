import asyncio
import json
import uuid
import websockets
import threading
from pubsub import PubSub
from filter import NewsPost


class WSServer:
    def __init__(self, pubsub: PubSub, redis_client, host: str, port: int):
        self.pubsub = pubsub
        self.redis = redis_client
        self.clients = set()
        self.host = host
        self.port = port
        self.server = None
        self.loop = asyncio.new_event_loop()  # Создаем отдельный event loop

    async def handler(self, websocket):
        self.clients.add(websocket)
        try:
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

    def start(self):
        # Запуск сервера в отдельном потоке с собственным event loop
        def run_server():
            asyncio.set_event_loop(self.loop)
            self.server = self.loop.run_until_complete(
                websockets.serve(self.handler, self.host, self.port)
            )
            self.loop.run_forever()

        threading.Thread(target=run_server, daemon=True).start()
