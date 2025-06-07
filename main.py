import asyncio
import threading
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from websocket import WebSocketApp

user_socket_connections = {}
user_socket_stop_flags = {}

TOKEN = "7603471934:AAGHOqMsthzpCsoxuY1zm2Uy0UqiGELIr5I"  # ⚠️ Замени на свой токен


# Команда /start — показать клавиатуру
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update)


async def show_main_menu(update: Update):
    keyboard = [["📊 Общее саммари по рынку", "🧠 Live новости"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выбери действие:", reply_markup=reply_markup)


# Обработка нажатий на кнопки
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if text == "📊 Общее саммари по рынку":
        await update.message.reply_text("📈 Общее саммари по рынку:\n(здесь будет саммари)")

    elif text == "🧠 Live новости":
        loop = asyncio.get_running_loop()
        start_socket_stream(user_id, context.bot, loop)

        # Показываем кнопку остановки
        keyboard = [["⛔️ Остановить новости"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Live новости запущены", reply_markup=reply_markup)

    elif text == "⛔️ Остановить новости":
        stop_socket_stream(user_id)
        await update.message.reply_text("🛑 Новости остановлены.")
        await show_main_menu(update)


# Запуск WebSocket в потоке
def start_socket_stream(user_id, bot, loop):
    stop_flag = threading.Event()
    user_socket_stop_flags[user_id] = stop_flag

    def on_message(ws, message):
        if stop_flag.is_set():
            ws.close()
            return
        asyncio.run_coroutine_threadsafe(
            bot.send_message(chat_id=user_id, text=f"🆕 Новость: {message}"),
            loop
        )

    def on_error(ws, error):
        print(f"Ошибка сокета: {error}")

    def on_close(ws, code, reason):
        print("Сокет закрыт")

    def run_socket():
        ws = WebSocketApp(
            "ws://localhost:8765",
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.run_forever()

    # Если ещё не запущен — запускаем
    if user_id not in user_socket_connections:
        thread = threading.Thread(target=run_socket, daemon=True)
        thread.start()
        user_socket_connections[user_id] = thread


# Остановка WebSocket потока
def stop_socket_stream(user_id):
    if user_id in user_socket_stop_flags:
        user_socket_stop_flags[user_id].set()
        del user_socket_stop_flags[user_id]

    if user_id in user_socket_connections:
        # Поток закроется сам после установки stop_flag
        del user_socket_connections[user_id]


# Запуск бота
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
