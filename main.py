import asyncio
import threading
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from websocket import WebSocketApp

user_socket_connections = {}
TOKEN = "7603471934:AAGHOqMsthzpCsoxuY1zm2Uy0UqiGELIr5I"  # ⚠️ Обязательно замени токен!

# Команда /start — показать клавиатуру
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["📊 Общее саммари по рынку", "🧠 Live новости"]]  # Горизонтальные кнопки
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,   # делает кнопки меньше
        one_time_keyboard=False # кнопки останутся после нажатия
    )
    await update.message.reply_text("Выбери действие:", reply_markup=reply_markup)

# Обработка нажатий на кнопки
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if text == "📊 Общее саммари по рынку":
        await update.message.reply_text("📈 Общее саммари по рынку:\n(здесь будет саммари)")

    elif text == "🧠 Live новости":
        await update.message.reply_text("🔴 Подключаюсь к live новостям...")

        # Получаем текущий запущенный event loop
        loop = asyncio.get_running_loop()

        # Запускаем сокет стрим в отдельном потоке и передаём loop
        start_socket_stream(user_id, context.bot, loop)

# Подключение к WebSocket и отправка сообщений
def start_socket_stream(user_id, bot, loop):
    def on_message(ws, message):
        print(f"Новость для {user_id}: {message}")
        # Отправка сообщения в телеграм из другого потока через run_coroutine_threadsafe
        asyncio.run_coroutine_threadsafe(
            bot.send_message(chat_id=user_id, text=f"🆕 Новость: {message}"),
            loop
        )

    def on_error(ws, error):
        print(f"Ошибка сокета: {error}")

    def on_close(ws, close_status_code, close_msg):
        print("Сокет закрыт")

    def run_socket():
        ws = WebSocketApp(
            "ws://localhost:8765",  # ← сюда вставь рабочий сокет
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.run_forever()

    if user_id not in user_socket_connections:
        thread = threading.Thread(target=run_socket, daemon=True)
        thread.start()
        user_socket_connections[user_id] = thread

# Запуск бота
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
