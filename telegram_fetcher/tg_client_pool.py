import asyncio
from telethon import TelegramClient, events
import aiohttp
import logging
from typing import List
from tg_config import API_ID_LIST, API_HASH_LIST, SESSION_NAMES, JSONDB_API_URL
from telethon.tl.functions.channels import JoinChannelRequest
import random
from telethon.errors import UserNotParticipantError, ChannelPrivateError

logger = logging.getLogger(__name__)

class TgClientWorker:
    def __init__(self, api_id: int, api_hash: str, session_name: str, queue: asyncio.Queue, worker_index: int, total_workers: int):
        """
        Инициализация воркера Telegram клиента.
        
        Args:
            api_id: Telegram API ID
            api_hash: Telegram API Hash
            session_name: имя сессии
            queue: очередь для отправки сообщений
            worker_index: индекс воркера
            total_workers: общее количество воркеров
        """
        session_path = f"sessions/{session_name}"
        self.client = TelegramClient(session_path, api_id, api_hash)
        self.queue = queue
        self.worker_index = worker_index
        self.total_workers = total_workers
        self.my_links = set()
        self.session = None  # aiohttp session

    async def start(self):
        """Запуск клиента и инициализация aiohttp сессии."""
        await self.client.start()
        self.client.add_event_handler(self.on_message, events.NewMessage)
        self.session = aiohttp.ClientSession()
        logger.info(f"[{self.client.session.filename}] started")
        asyncio.create_task(self.refresh_channels_loop())

    async def stop(self):
        """Корректное завершение работы клиента."""
        if self.session:
            await self.session.close()
        await self.client.disconnect()
        logger.info(f"[{self.client.session.filename}] stopped")

    async def refresh_channels_loop(self):
        """Периодическое обновление списка каналов."""
        retry_delay = 1
        max_retry_delay = 30
        while True:
            try:
                async with self.session.get(JSONDB_API_URL) as response:
                    if response.status == 200:
                        channels = await response.json()
                        part = [c for i, c in enumerate(channels) if i % self.total_workers == self.worker_index]
                        for ch in part:
                            if ch["link"] not in self.my_links:
                                try:
                                    username = ch["link"].split("/")[-1]
                                    # Проверяем, находимся ли мы уже в канале
                                    try:
                                        channel = await self.client.get_entity(username)
                                        # Пробуем получить информацию о канале
                                        # Если мы не участник, это вызовет ChannelPrivateError
                                        await self.client.get_permissions(channel)
                                        logger.info(f"Already a member of {ch['link']}")
                                    except ChannelPrivateError:
                                        # Если мы не участник, присоединяемся
                                        delay = random.uniform(5, 15)
                                        logger.info(f"Waiting {delay:.1f} seconds before joining {ch['link']}")
                                        await asyncio.sleep(delay)
                                        await self.client(JoinChannelRequest(channel=username))
                                        logger.info(f"Joined {ch['link']}")
                                    except Exception as e:
                                        logger.error(f"Error checking/joining {ch['link']}: {e}")
                                        continue
                                    self.my_links.add(ch["link"])
                                except Exception as e:
                                    logger.error(f"Error processing {ch['link']}: {e}")
                        retry_delay = 1
                    else:
                        logger.error(f"Failed to fetch channels: {response.status}")
                        await asyncio.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, max_retry_delay)
                        continue
            except Exception as e:
                logger.error(f"Error in refresh_channels_loop: {e}")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)
                continue

            await asyncio.sleep(30)

    async def on_message(self, event):
        """Обработка новых сообщений."""
        try:
            ch = await event.get_chat()
            if getattr(ch, "username", None) in self.my_links or f"https://t.me/{getattr(ch, 'username', '')}" in self.my_links:
                msg = {
                    "timestamp": event.date.isoformat(),
                    "channel_id": ch.id,
                    "channel_title": getattr(ch, "title", ""),
                    "text": event.text,
                }
                await self.queue.put(msg)
        except Exception as e:
            logger.error(f"Error processing message: {e}")

async def run_pool(queue: asyncio.Queue) -> List[TgClientWorker]:
    """
    Запуск пула Telegram клиентов.
    
    Args:
        queue: очередь для отправки сообщений
        
    Returns:
        List[TgClientWorker]: список запущенных воркеров
    """
    workers = []
    N = len(SESSION_NAMES)
    for i, (api_id, api_hash, session) in enumerate(zip(API_ID_LIST, API_HASH_LIST, SESSION_NAMES)):
        w = TgClientWorker(api_id, api_hash, session, queue, i, N)
        await w.start()
        workers.append(w)
    return workers 