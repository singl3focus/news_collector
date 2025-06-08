import logging
import config

CONFIG_FILE = "config.yaml"


def define_log_level(level: str) -> int:
    level = level.lower().strip()

    if level == "debug":
        return logging.DEBUG
    elif level == "info":
        return logging.INFO
    elif level == "warn" or level == "warning":
        return logging.WARN
    elif level == "error":
        return logging.ERROR
    else:
        return logging.INFO


def setup_logging() -> None:
    cfg = config.parse_config(CONFIG_FILE)

    root_logger = logging.getLogger()
    root_logger.setLevel(define_log_level(cfg.logger.log_level))

    # Форматтер для всех обработчиков
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Файловый обработчик
    file_handler = logging.FileHandler(cfg.logger.log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)

    # Консольный обработчик с обработкой ошибок
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.encoder = lambda s: s.encode('utf-8', 'replace')  # Добавлено

    # Очистка старых обработчиков
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Добавление новых обработчиков
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


setup_logging()

logger = logging.getLogger(__name__)

import asyncio
import threading 
import uvicorn 
from src import redis_init
from src import filter
from src import wsserver
from src import restserver
from src.ranking import ranking_news
from src.pubsub import *


def run_rest(collector_http, host: str = "0.0.0.0", port: int = 9080, redis_host: str = "localhost", redis_port: int = 6379):
    app = restserver.create_app(collector_http, redis_host=redis_host, redis_port=redis_port)
    uvicorn.run(app, host=host, port=port)


async def main_async():
    cfg = config.parse_config(CONFIG_FILE)
    r = redis_init.setup_redis(cfg.database.host, cfg.database.port)
    event_bus = PubSub()
    
    # Регистрация подписок ДО запуска обработки сообщений
    event_bus.subscribe(EVENT_NEW_POST, lambda data: tonal_callback(data, event_bus))
    event_bus.subscribe(EVENT_FILTERED_POST, lambda data: rank_callback(data, event_bus))

    # Создание и запуск WebSocket сервера
    ws_server = wsserver.WSServer(
        event_bus,
        r,
        host=cfg.network.wsserver.host,
        port=cfg.network.wsserver.port
    )
    event_bus.subscribe(EVENT_FULL_POST, ws_server.process_event)
    ws_server.start()

    # Запуск REST API в отдельном потоке
    threading.Thread(target=run_rest, daemon=True, args=(cfg.network.collector_http,)).start()

    # Запуск обработки сообщений как асинхронной задачи
    asyncio.create_task(filter.receive_posts(cfg.network.collector_uri, event_bus))

    # Бесконечный цикл для поддержания работы приложения
    while True:
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            logger.info("Application shutting down")
            break
        except Exception as e:
            logger.exception("Unexpected error in main loop")


def main():
    try:
        asyncio.run(main_async())
    except Exception as e:
        logger.exception("Application crashed")
        return 1
    return 0


def tonal_callback(data: filter.NewsPost, pubsub: PubSub) -> None:
    logger.info(f"[tonal] Get post: {data}")

    good, new_data = ranking_news.is_good_news(data)
    logger.info(f"[tonal] New is good: {good}")

    if good and new_data is not None:
        pubsub.publish(EVENT_FILTERED_POST, new_data)


def rank_callback(data: ranking_news.Post, pubsub: PubSub) -> None:
    logger.info(f"[rank] Get post: {data}")

    new_data = data
    pubsub.publish(EVENT_FULL_POST, new_data)


if __name__ == "__main__":
    main()
