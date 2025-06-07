import redis
import time
import logging

logger = logging.getLogger(__name__)


def setup_redis(host: str, port: int) -> redis.Redis:
    r = redis.Redis(
        host=host,
        port=port,
        decode_responses=True,
        health_check_interval=30
    )
    while True:
        try:
            if r.ping():
                logger.info("Redis has been connected")
                return r
        except redis.ConnectionError:
            logger.info("Waiting Redis...")
            time.sleep(1)
