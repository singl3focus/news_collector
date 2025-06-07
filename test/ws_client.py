import asyncio
import json
import websockets


async def websocket_client(uri: str):
    """Простой клиент для WebSocket сервера"""
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Успешно подключились к серверу {uri}")
            print("⌛ Ожидаем сообщения...")

            while True:
                message = await websocket.recv()
                try:
                    # Пытаемся разобрать JSON
                    data = json.loads(message)
                    print("\n📨 Получено сообщение:")
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    # Если не JSON, выводим как есть
                    print("\n📨 Получено сообщение (не JSON):")
                    print(message)
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")


if __name__ == "__main__":
    # Настройки подключения (должны совпадать с настройками сервера)
    SERVER_HOST = "localhost"  # или IP-адрес сервера
    SERVER_PORT = 9999  # порт по умолчанию в примере
    SERVER_URI = f"ws://{SERVER_HOST}:{SERVER_PORT}"

    print(f"🚀 Запускаем клиент для подключения к {SERVER_URI}")
    asyncio.run(websocket_client(SERVER_URI))
