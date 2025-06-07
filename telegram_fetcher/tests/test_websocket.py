import asyncio
import pytest
import websockets
import json
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import AsyncIterator

# Настройка логирования для тестов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация тестов
TEST_CHANNEL = {
    "link": "https://t.me/durov",
    "title": "Test Channel"
}
WS_URL = "ws://172.20.10.6:8001/ws"
API_URL = "http://172.20.10.6:8001/api/channels"

@pytest.fixture(scope="session")
def event_loop():
    """Создаем event loop для всех тестов."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def api_client():
    """Фикстура для HTTP клиента."""
    logger.info("Creating API client...")
    async with aiohttp.ClientSession() as session:
        yield session
    logger.info("API client closed")

@pytest.fixture
async def setup_channel(api_client):
    """Фикстура для настройки тестового канала."""
    logger.info("Setting up test channel...")
    try:
        # Добавляем тестовый канал
        async with api_client.post(API_URL, json=TEST_CHANNEL) as response:
            assert response.status == 200
            logger.info("Test channel added successfully")
        yield
    finally:
        # Удаляем тестовый канал после тестов
        try:
            async with api_client.delete(f"{API_URL}/{TEST_CHANNEL['link']}") as response:
                assert response.status == 200
                logger.info("Test channel removed successfully")
        except Exception as e:
            logger.error(f"Error removing test channel: {e}")

@pytest.fixture
async def websocket_client():
    """Фикстура для WebSocket клиента."""
    logger.info("Creating WebSocket client...")
    try:
        async with websockets.connect(
            WS_URL,
            extra_headers={
                "Origin": "http://localhost:8001",
                "User-Agent": "pytest-websocket-client"
            }
        ) as websocket:
            logger.info("WebSocket connected, waiting for welcome message...")
            # Ждем приветственное сообщение
            welcome_msg = await websocket.recv()
            welcome_data = json.loads(welcome_msg)
            assert welcome_data["type"] == "connection_established"
            logger.info("Received welcome message")
            yield websocket
    except Exception as e:
        logger.error(f"Error in websocket_client fixture: {e}")
        raise
    logger.info("WebSocket client closed")

@pytest.mark.asyncio
class TestWebSocket:
    async def test_websocket_connection(self, websocket_client):
        """Тест базового подключения к WebSocket."""
        logger.info("Testing basic WebSocket connection...")
        assert websocket_client.open
        # Проверяем, что можем отправить и получить сообщение
        await websocket_client.send(json.dumps({"type": "ping"}))
        logger.info("Sent ping message")
        response = await websocket_client.recv()
        assert response is not None
        logger.info("Received response")

    async def test_receive_messages(self, setup_channel, websocket_client):
        """Тест получения сообщений через WebSocket."""
        logger.info("Testing message reception...")
        try:
            message = await asyncio.wait_for(websocket_client.recv(), timeout=60.0)
            data = json.loads(message)
            
            # Проверяем структуру сообщения
            assert "timestamp" in data
            assert "channel_id" in data
            assert "channel_title" in data
            assert "text" in data
            
            # Проверяем формат timestamp
            timestamp = datetime.fromisoformat(data["timestamp"])
            assert timestamp > datetime.now() - timedelta(minutes=5)
            
            logger.info(f"Received message: {data}")
            
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for message")
            pytest.fail("Timeout waiting for message")
        except Exception as e:
            logger.error(f"Error in test_receive_messages: {e}")
            raise

    async def test_multiple_connections(self, setup_channel, api_client):
        """Тест множественных подключений к WebSocket."""
        logger.info("Testing multiple connections...")
        connections = []
        try:
            # Создаем несколько подключений
            for i in range(3):
                logger.info(f"Creating connection {i+1}/3...")
                ws = await websockets.connect(
                    WS_URL,
                    extra_headers={
                        "Origin": "http://localhost:8001",
                        "User-Agent": "pytest-websocket-client"
                    }
                )
                # Ждем приветственное сообщение
                welcome_msg = await ws.recv()
                welcome_data = json.loads(welcome_msg)
                assert welcome_data["type"] == "connection_established"
                logger.info(f"Connection {i+1} established")
                connections.append(ws)
            
            # Проверяем, что все соединения активны
            for i, ws in enumerate(connections):
                assert ws.open
                logger.info(f"Connection {i+1} is open")
            
            # Ждем сообщения на всех соединениях
            tasks = []
            for i, ws in enumerate(connections):
                task = asyncio.create_task(ws.recv())
                tasks.append(task)
                logger.info(f"Created receive task for connection {i+1}")
            
            # Ждем первое сообщение на любом из соединений
            logger.info("Waiting for first message...")
            done, pending = await asyncio.wait(
                tasks,
                timeout=30.0,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Отменяем оставшиеся задачи
            for task in pending:
                task.cancel()
            
            assert len(done) > 0, "No messages received on any connection"
            
            # Проверяем полученное сообщение
            message = json.loads(done.pop().result())
            assert "text" in message
            logger.info("Received message on one of the connections")
            
        except Exception as e:
            logger.error(f"Error in test_multiple_connections: {e}")
            raise
        finally:
            # Закрываем все соединения
            for i, ws in enumerate(connections):
                try:
                    await ws.close()
                    logger.info(f"Closed connection {i+1}")
                except Exception as e:
                    logger.error(f"Error closing connection {i+1}: {e}")

    async def test_connection_recovery(self):
        """Тест восстановления соединения после разрыва."""
        logger.info("Testing connection recovery...")
        try:
            async with websockets.connect(
                WS_URL,
                extra_headers={
                    "Origin": "http://localhost:8001",
                    "User-Agent": "pytest-websocket-client"
                }
            ) as websocket:
                # Ждем приветственное сообщение
                welcome_msg = await websocket.recv()
                welcome_data = json.loads(welcome_msg)
                assert welcome_data["type"] == "connection_established"
                logger.info("Initial connection established")
                
                # Закрываем соединение
                await websocket.close()
                logger.info("Initial connection closed")
                
                # Пробуем переподключиться
                async with websockets.connect(
                    WS_URL,
                    extra_headers={
                        "Origin": "http://localhost:8001",
                        "User-Agent": "pytest-websocket-client"
                    }
                ) as new_websocket:
                    # Ждем приветственное сообщение
                    welcome_msg = await new_websocket.recv()
                    welcome_data = json.loads(welcome_msg)
                    assert welcome_data["type"] == "connection_established"
                    logger.info("Reconnection established")
                    
                    assert new_websocket.open
                    
                    # Ждем сообщение на новом соединении
                    try:
                        message = await asyncio.wait_for(new_websocket.recv(), timeout=30.0)
                        data = json.loads(message)
                        assert "text" in data
                        logger.info("Received message after reconnection")
                    except asyncio.TimeoutError:
                        logger.error("Timeout waiting for message after reconnection")
                        pytest.fail("Timeout waiting for message after reconnection")
        except Exception as e:
            logger.error(f"Error in test_connection_recovery: {e}")
            raise
