import asyncio
import websockets
import datetime
import random

FAKE_NEWS = [
    "📈 Apple растёт на 2.4% после отчёта",
    "📉 Nasdaq падает из-за слабых данных по занятости",
    "💰 Илон Маск продал акции Tesla на $2 млрд",
    "🔥 SEC снова подала иск против криптобиржи",
    "🌍 ОПЕК обсуждает снижение добычи нефти"
]

async def news_sender(websocket, path):
    while True:
        await websocket.send(random.choice(FAKE_NEWS))
        await asyncio.sleep(60)

async def main():
    async with websockets.serve(news_sender, "localhost", 8765):
        print("🧪 Сервер запущен")
        await asyncio.Future()  # ждем вечно

if __name__ == "__main__":
    asyncio.run(main())