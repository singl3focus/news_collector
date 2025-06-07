import asyncio
from telethon import TelegramClient, events
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_ID_LIST = [int(os.getenv("API_ID_1")), int(os.getenv("API_ID_2"))]
API_HASH_LIST = [os.getenv("API_HASH_1"), os.getenv("API_HASH_2")]
SESSION_NAMES = [os.getenv("SESSION_NAME_1"), os.getenv("SESSION_NAME_2")]
JSONDB_API_URL = os.getenv("JSONDB_API_URL", "http://localhost:8001/channels")

class TgClientWorker:
    def __init__(self, api_id, api_hash, session_name, queue, worker_index, total_workers):
        self.client = TelegramClient(session_name, api_id, api_hash)
        self.queue = queue
        self.worker_index = worker_index
        self.total_workers = total_workers
        self.my_links = set()

    async def start(self):
        await self.client.start()
        self.client.add_event_handler(self.on_message, events.NewMessage)
        print(f"[{self.client.session.filename}] started")
        asyncio.create_task(self.refresh_channels_loop())

    async def refresh_channels_loop(self):
        while True:
            channels = requests.get(JSONDB_API_URL).json()
            part = [c for i, c in enumerate(channels) if i % self.total_workers == self.worker_index]
            for ch in part:
                if ch["link"] not in self.my_links:
                    try:
                        await self.client.join_chat(ch["link"])
                        self.my_links.add(ch["link"])
                        print(f"Joined {ch['link']}")
                    except Exception as e:
                        print(f"Error join {ch['link']}: {e}")
            await asyncio.sleep(30)

    async def on_message(self, event):
        ch = await event.get_chat()
        if getattr(ch, "username", None) in self.my_links or f"https://t.me/{getattr(ch, 'username', '')}" in self.my_links:
            msg = {
                "timestamp": event.date.isoformat(),
                "channel_id": ch.id,
                "channel_title": getattr(ch, "title", ""),
                "text": event.text,
            }
            await self.queue.put(msg)

async def run_pool(queue):
    workers = []
    N = len(SESSION_NAMES)
    for i, (api_id, api_hash, session) in enumerate(zip(API_ID_LIST, API_HASH_LIST, SESSION_NAMES)):
        w = TgClientWorker(api_id, api_hash, session, queue, i, N)
        await w.start()
        workers.append(w)
    return workers 