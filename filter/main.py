import logging
import config


def define_log_level(level: str) -> int:
    level = level.upper().strip()

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
    """Настройка логирования при запуске приложения"""

    cfg = config.parse_config("config.yaml")

    root_logger = logging.getLogger()
    root_logger.setLevel(define_log_level(cfg.logger.log_level))

    # Форматтер для всех обработчиков
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Файловый обработчик
    file_handler = logging.FileHandler(cfg.logger.log_file)
    file_handler.setFormatter(formatter)

    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Очистка старых обработчиков
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Добавление новых обработчиков
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


setup_logging()

logger = logging.getLogger(__name__)

import redis_init
import filter
from pubsub import *
import wsserver
import threading
import asyncio


"""
TODO:
- создание pub/sub (общение между этапами через него).
- пайплайн (этапы): получение постов (посты приходят по одному) > Тональность > Ранжирование > WS сервер.
- в Main происходит запуск вебсокет сервера в отдельном потоке, который отправляет посты клиентам.
Также после отправки добавляется пост добавляется в кэш (redis) с TTL в 1 день.

После сделать работу с юзерами в БД (redis). CRON, который в 19 по МСК собирает инфу по юзерам и скидывает их
"""

CONFIG_FILE = "config.yaml"


async def main_async():
    """Асинхронная главная функция приложения"""
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
        host=cfg.network.server_host,
        port=cfg.network.server_port
    )
    event_bus.subscribe(EVENT_FULL_POST, ws_server.process_event)
    threading.Thread(target=ws_server.start, daemon=True).start()

    # Запуск обработки сообщений как асинхронной задачи
    asyncio.create_task(filter.receive_posts(cfg.network.collector_uri, event_bus))

    # Бесконечный цикл для поддержания работы приложения
    while True:
        await asyncio.sleep(3600)  # Не блокирующее ожидание


def main():
    """Точка входа в приложение"""
    asyncio.run(main_async())


# TODO: Тональность
def tonal_callback(data: filter.NewsPost, pubsub: PubSub) -> None:
    logger.info(f"[tonal] Получен пост: {data}")
    print(f"[tonal] Получен пост: {data}")

    new_data = data  # Вычиление тональности
    pubsub.publish(EVENT_FILTERED_POST, new_data)


# TODO: Ранжирование
def rank_callback(data, pubsub: PubSub) -> None:
    logger.info(f"[ранжирование] Получен пост: {data}")
    print(f"[ранжирование] Получен пост: {data}")

    new_data = data  # Дополнение поста
    pubsub.publish(EVENT_FULL_POST, new_data)


if __name__ == "__main__":
    main()
