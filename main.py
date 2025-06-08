import asyncio
import json
import threading
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from websocket import WebSocketApp

user_socket_connections = {}
user_socket_stop_flags = {}
user_state = {}
user_tickers = {}
user_sources = {}

TOKEN = "7603471934:AAGHOqMsthzpCsoxuY1zm2Uy0UqiGELIr5I"  # 🔒 Замени на свой токен

# Главное меню
async def show_main_menu(update: Update):
    keyboard = [
        ["📊 Общее саммари по рынку", "🧠 Live новости"],
        ["📋 Список тикеров", "📋 Список источников"],
        ["⚙️ Настройки"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выбери действие:", reply_markup=reply_markup)

# Меню настроек
async def show_settings_menu(update: Update):
    keyboard = [
        ["➕ Добавить тикеры", "🗞 Добавить источники"],
        ["🧹 Очистить тикеры", "🧹 Очистить источники"],
        ["🔙 Назад"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Настройки:", reply_markup=reply_markup)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update)

# Обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    state = user_state.get(user_id)

    # Обработка режима ввода
    if state == "awaiting_tickers":
        tickers = [t.strip() for t in text.split(",") if t.strip()]
        user_tickers[user_id] = tickers
        user_state.pop(user_id)
        await update.message.reply_text(f"✅ Тикеры сохранены: {', '.join(tickers)}")
        await show_main_menu(update)
        return

    elif state == "awaiting_sources":
        sources = [s.strip() for s in text.split(",") if s.strip()]
        user_sources[user_id] = sources
        user_state.pop(user_id)
        await update.message.reply_text(f"✅ Источники сохранены: {', '.join(sources)}")
        await show_main_menu(update)
        return

    # Главное меню
    if text == "📊 Общее саммари по рынку":
        await update.message.reply_text("📈 Общее саммари по рынку:\n(здесь будет саммари)")

    elif text == "🧠 Live новости":
        loop = asyncio.get_running_loop()
        start_socket_stream(user_id, context.bot, loop)
        keyboard = [["⛔️ Остановить новости"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Live новости запущены", reply_markup=reply_markup)

    elif text == "⛔️ Остановить новости":
        stop_socket_stream(user_id)
        await update.message.reply_text("🛑 Новости остановлены.")
        await show_main_menu(update)

    elif text == "📋 Список тикеров":
        tickers = user_tickers.get(user_id)
        if tickers:
            await update.message.reply_text(f"📋 Твои тикеры: {', '.join(tickers)}")
        else:
            await update.message.reply_text("📭 Список тикеров пуст.")

    elif text == "📋 Список источников":
        sources = user_sources.get(user_id)
        if sources:
            await update.message.reply_text(f"📋 Твои источники: {', '.join(sources)}")
        else:
            await update.message.reply_text("📭 Список источников пуст.")

    # Настройки
    elif text == "⚙️ Настройки":
        await show_settings_menu(update)

    elif text == "➕ Добавить тикеры":
        user_state[user_id] = "awaiting_tickers"
        await update.message.reply_text("Введите тикеры через запятую (например: AAPL, TSLA, BTC):")

    elif text == "🗞 Добавить источники":
        user_state[user_id] = "awaiting_sources"
        await update.message.reply_text("Введите источники через запятую (например: https://t.me/example1, https://t.me/example2):")

    elif text == "🧹 Очистить тикеры":
        if user_id in user_tickers:
            del user_tickers[user_id]
            await update.message.reply_text("🧼 Тикеры очищены.")
        else:
            await update.message.reply_text("✅ У тебя ещё нет сохранённых тикеров.")
        await show_settings_menu(update)

    elif text == "🧹 Очистить источники":
        if user_id in user_sources:
            del user_sources[user_id]
            await update.message.reply_text("🧼 Источники очищены.")
        else:
            await update.message.reply_text("✅ У тебя ещё нет сохранённых источников.")
        await show_settings_menu(update)

    elif text == "🔙 Назад":
        await show_main_menu(update)

# WebSocket подключение
def start_socket_stream(user_id, bot, loop):
    stop_flag = threading.Event()
    user_socket_stop_flags[user_id] = stop_flag

    def on_message(ws, message):
        print(message)
        tmp = json.loads(message)
        if stop_flag.is_set():
            ws.close()
            return
        asyncio.run_coroutine_threadsafe(
            bot.send_message(chat_id=user_id, text=f"🆕 Новость: {tmp['text']}"),
            loop
        )

    def on_error(ws, error):
        print(f"Ошибка сокета: {error}")

    def on_close(ws, code, reason):
        print("Сокет закрыт")

    def run_socket():
        ws = WebSocketApp(
            "ws://172.20.10.2:9999",
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.run_forever()

    if user_id not in user_socket_connections:
        thread = threading.Thread(target=run_socket, daemon=True)
        thread.start()
        user_socket_connections[user_id] = thread

# Остановка сокета
def stop_socket_stream(user_id):
    if user_id in user_socket_stop_flags:
        user_socket_stop_flags[user_id].set()
        del user_socket_stop_flags[user_id]
    if user_id in user_socket_connections:
        del user_socket_connections[user_id]

# Запуск бота
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
