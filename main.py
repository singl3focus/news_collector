import asyncio
import json
import threading
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from websocket import WebSocketApp
import requests
from datetime import datetime


user_socket_connections = {}
user_socket_stop_flags = {}
user_state = {}
user_tickers = {}
user_sources = {}
userToken = "IGhG2bDGJTxRAAImJNvPVMj_mZpc-Pfz7rrDASV-Nnc"

TOKEN = "7603471934:AAGHOqMsthzpCsoxuY1zm2Uy0UqiGELIr5I"  # 🔒 Замени на свой токен

GlobalUrl = "4qzirm-31-131-157-99.ru.tuna.am"

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
    url = f'https://{GlobalUrl}/register?username={update.message.from_user.username}'
    response = requests.post(url)
    print(response.text)
    # tmp = json.loads(response.text)
    # userToken = tmp["token"]

def format_news(message: dict) -> str:
    tone_map = {1: "📈 <b>Позитив</b>", 0: "⚖️ <b>Нейтрально</b>", -1: "📉 <b>Негатив</b>"}
    trend_map = {1: "📊 <u>Тренд ↑</u>", 0: "⏸ <u>Без тренда</u>", -1: "📉 <u>Тренд ↓</u>"}
    volatility_map = {1: "🌪 <i>Высокая волатильность</i>", -1: "📏 <i>Низкая волатильность</i>"}

    tone = tone_map.get(message.get("tonality", -1), "❓ Неизвестно")
    trend = trend_map.get(message.get("trend", 0), "❓ Неизвестно")
    volatility = volatility_map.get(message.get("volatility", 0), "❓ Неизвестно")

    timestamp = message.get("timestamp")
    time_str = datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M")

    return (
        f"📰 <b>{message['channel_title']}</b>\n\n"
        f"<b>Новость:</b>\n<blockquote>{message['text']}</blockquote>\n"
        f"<b>Дата:</b> <code>{time_str}</code>\n\n"
        f"{tone} | {trend} | {volatility}"
    )

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
        for s in text.split(","):
            url = f'https://{GlobalUrl}/users/me/channels?channel_name={s}'
            headers = {
                'Authorization': userToken,
                'Content-Type': 'application/json'
            }
            response = requests.post(url, headers=headers)
            print(response)

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

    def on_open(ws):
        ws.send(json.dumps({"token": userToken}))

    def on_message(ws, message):
        tmp = json.loads(message)
        if stop_flag.is_set():
            ws.close()
            return
        
        asyncio.run_coroutine_threadsafe(
            bot.send_message(chat_id=user_id, text=format_news(tmp), parse_mode="HTML"),
            loop
        )

    def on_error(ws, error):
        print(f"Ошибка сокета: {error}")

    def on_close(ws, code, reason):
        print("Сокет закрыт")

    def run_socket():
        ws = WebSocketApp(
            f"wss://udlhlm-31-131-157-99.ru.tuna.am",
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
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
