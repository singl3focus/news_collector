import pytest
import asyncio
import logging
from typing import AsyncGenerator

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def event_loop():
    """Создаем event loop для всех тестов."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
async def setup_teardown():
    """Фикстура для настройки и очистки перед/после каждого теста."""
    logger.info("Setting up test...")
    yield
    logger.info("Tearing down test...")
