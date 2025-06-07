import websockets
import json
import re
from dataclasses import dataclass
from datetime import datetime
from collections import deque
from simhash import Simhash, SimhashIndex
import logging
from .pubsub import *

logger = logging.getLogger(__name__)

# Конфигурация дедубликации
DEDUP_WINDOW_SIZE = 100
SIMHASH_DISTANCE = 10


"""
{
    "timestamp": "2024-03-14T12:00:00Z",
    "channel_id": 123456789,
    "channel_title": "Channel Name",
    "text": "Message content"
}
"""


@dataclass
class NewsPost:
    text: str
    raw_timestamp: str
    channel_id: str
    channel_title: str
    timestamp: int = 0
    simhash: int = 0

    def __post_init__(self):
        try:
            dt = datetime.fromisoformat(self.raw_timestamp.replace("Z", "+00:00"))
            self.timestamp = int(dt.timestamp())
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid timestamp: {self.raw_timestamp} - {e}")

        try:
            self.channel_id = int(self.channel_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid channel_id: {self.channel_id}")

        self.simhash = self.calculate_simhash()

    def calculate_simhash(self):
        text = self.preprocess_text(self.text)
        return Simhash(text, f=64).value

    @staticmethod
    def preprocess_text(text) -> str:
        text = re.sub(r'[^\w\s]', '', text.lower())
        stopwords = {'и', 'в', 'с', 'на', 'о', 'по', 'для', 'не', 'что', 'как', 'это', 'из', 'от'}
        return ' '.join(word for word in text.split() if word not in stopwords)


class Deduplicator:
    def __init__(self, window_size=DEDUP_WINDOW_SIZE, distance=SIMHASH_DISTANCE):
        self.window_size = window_size
        self.distance = distance
        self.known_hashes = deque(maxlen=window_size)
        self.index = SimhashIndex([], f=64, k=distance)

    def is_duplicate(self, post: NewsPost) -> bool:
        if post.simhash in self.known_hashes:
            return True

        simhash_obj = Simhash(value=post.simhash, f=self.index.f)
        if self.index.get_near_dups(simhash_obj):
            return True

        self.add_post(post)
        return False

    def add_post(self, post: NewsPost) -> None:
        self.known_hashes.append(post.simhash)
        self.index.add(str(post.simhash), Simhash(value=post.simhash, f=self.index.f))


async def receive_posts(uri: str, pubsub: PubSub):
    deduplicator = Deduplicator()

    async with websockets.connect(uri) as websocket:
        logger.info(f"Connected to {uri}")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)

                    logger.info(f"Received: {data}")

                    # Фильтрация служебных сообщений
                    if data.get("type") in ["connection_established", "ping"]:
                        logger.debug(f"Ignoring system message: {data.get('type')}")
                        continue

                    # Проверка обязательных полей
                    required = ["text", "timestamp", "channel_id"]
                    if not all(k in data for k in required):
                        logger.warning(f"Missing fields in: {message[:100]}...")
                        continue


                    post = NewsPost(
                        text=data["text"],
                        raw_timestamp=data["timestamp"],
                        channel_id=data["channel_id"],
                        channel_title=data.get("channel_title", "Unknown")
                    )

                    logger.info(f"Received: {post.channel_title} - {post.timestamp}")

                    if deduplicator.is_duplicate(post):
                        logger.info(f"Duplicate: {post.channel_title} - {post.timestamp}")
                        continue

                    try:
                        pubsub.publish(EVENT_NEW_POST, post)
                    except Exception as e:
                        logger.error(f"Publish error: {e}")

                except json.JSONDecodeError:
                    logger.error(f"JSON error: {message[:100]}...")
                except Exception as e:
                    logger.exception(f"Processing error: {e}")

        except websockets.ConnectionClosed:
            logger.warning("Connection closed")
        except Exception as e:
            logger.exception(f"Critical error: {e}")