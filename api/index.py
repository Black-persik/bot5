from fastapi import FastAPI
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler
)
import logging
import asyncio
import requests
from datetime import datetime, timezone
from typing import Optional
import os

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация FastAPI
app = FastAPI()

# Конфигурация бота
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Используйте переменные окружения Vercel
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = "/webhook"

# Клавиатура для главного меню
main_keyboard = ReplyKeyboardMarkup(
    [["/ask", "/help"]],
    resize_keyboard=True,
    one_time_keyboard=False,
)

# Состояния для ConversationHandler
START, GET_NAME, WAITING_MESSAGE = range(3)

# Глобальная переменная для хранения бота
bot_application: Optional[Application] = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Привет! Я первая версия бота для нашего супер проекта про рекомендательные системы",
        reply_markup=main_keyboard,
    )

    api_check_user = f"https://swpdb-production.up.railway.app/users/{update.effective_user.id}/"
    if requests.get(api_check_user).status_code == 200:
        await update.message.reply_text(
            "Вы уже зарегистрированы!",
            reply_markup=main_keyboard,
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Пожалуйста, введите ваше имя: ",
        reply_markup=main_keyboard,
    )
    return GET_NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_name = update.message.text
    context.user_data['name'] = user_name

    await update.message.reply_text(
        f"Отлично, {user_name}! Теперь вы можете пользоваться ботом.",
        reply_markup=main_keyboard,
    )

    payload_name_json = {
        "_id": update.effective_user.id,
        "name": user_name,
    }
    api_create_user = "https://swpdb-production.up.railway.app/users/"
    requests.post(api_create_user, json=payload_name_json)

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Отмена",
        reply_markup=main_keyboard,
    )
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Доступные команды:\n"
        "/ask - задать вопрос\n"
        "/help - основные правила пользования ботом\n"
        "/reload - обновить чат\n",
        reply_markup=main_keyboard,
    )


async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['last_message'] = None

    ask_keyboard = ReplyKeyboardMarkup(
        [["Отмена"]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await update.message.reply_text(
        "Напишите свой запрос! Я постараюсь помочь вам!",
        reply_markup=ask_keyboard
    )

    payload_create_conv = {
        "user_id": update.effective_user.id,
        "messages": [
            {
                "sender": "user",
                "text": "STARTING_MESSAGE",
                "time": "2025-06-22T19:52:30.467Z"
            }
        ]
    }

    api_create_conv = "https://swpdb-production.up.railway.app/conversations/"
    response_create_conv = requests.post(api_create_conv, json=payload_create_conv)
    response_create_conv_json = response_create_conv.json()
    context.user_data['conv_id'] = response_create_conv_json.get("_id")

    return WAITING_MESSAGE


async def ask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_text = update.message.text
    context.user_data['last_message'] = user_text

    await update.message.reply_text(
        f"ваш текст: {user_text}",
        reply_markup=main_keyboard
    )

    api_add_message = f"https://swpdb-production.up.railway.app/conversations/{context.user_data['conv_id']}/messages"
    payload_add_message = {
        "sender": "user",
        "text": user_text,
        "time": update.message.date.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    }
    requests.post(api_add_message, json=payload_add_message)

    return WAITING_MESSAGE


def register_handlers(application):
    application.add_handler(CommandHandler("help", help_command))

    conv_handler_start = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_handler_ask = ConversationHandler(
        entry_points=[CommandHandler("ask", ask)],
        states={
            WAITING_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_handler)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex("^Отмена$"), cancel),
        ],
    )

    application.add_handler(conv_handler_start)
    application.add_handler(conv_handler_ask)


async def setup_bot():
    """Настройка и запуск бота"""
    global bot_application

    bot_application = Application.builder().token(TOKEN).build()
    register_handlers(bot_application)

    # Настройка вебхука
    await bot_application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

    logger.info("Бот инициализирован и готов к работе")


@app.on_event("startup")
async def on_startup():
    """Запуск бота при старте FastAPI"""
    await setup_bot()


@app.post("/webhook")
async def webhook(update: dict):
    """Обработка вебхуков от Telegram"""
    global bot_application
    if bot_application is None:
        return {"status": "error", "message": "Bot not initialized"}

    telegram_update = Update.de_json(update, bot_application.bot)
    await bot_application.process_update(telegram_update)
    return {"status": "ok"}


@app.get("/")
async def root():
    """Проверка работоспособности сервера"""
    return {"status": "running", "bot": "active"}
