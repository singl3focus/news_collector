import asyncio
import websockets
import json
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket():
    uri = "ws://localhost:8001/ws"
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to WebSocket server")
            
            # Ждем приветственное сообщение
            welcome = await websocket.recv()
            logger.info(f"Received welcome message: {welcome}")
            
            # Слушаем сообщения
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    logger.info(f"Received message: {data}")
                except websockets.exceptions.ConnectionClosed:
                    logger.error("Connection closed")
                    break
                except Exception as e:
                    logger.error(f"Error receiving message: {e}")
                    break
                    
    except Exception as e:
        logger.error(f"Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket()) 