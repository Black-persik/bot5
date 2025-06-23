import requests

from fastapi import FastAPI, Request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes, ConversationHandler,
)
import os
from datetime import timezone
import httpx

app = FastAPI()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Используйте переменные окружения Vercel
WEBHOOK_URL = os.getenv("WEBHOOK_URL")   # URL вашего Vercel приложения

application = Application.builder().token(TOKEN).build()
# Клавиатура для главного меню
main_keyboard = ReplyKeyboardMarkup(
    [["/ask", "/help"]],
    resize_keyboard=True,
    one_time_keyboard=False,
)

# Обработчики команд

START, GET_NAME = range(2)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "Привет! Я первая версия бота для нашего супер проекта про рекомендательные системы",


        reply_markup=main_keyboard,
    )
    api_check_user = f"https://swpdb-production.up.railway.app/users/{update.effective_user.id}/"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(api_check_user)

        if response.status_code == 200:
            await update.message.reply_text(
                "Вы уже зарегистрированы!",
                reply_markup=main_keyboard,
            )
            return ConversationHandler.END
    except httpx.RequestError:
        pass  # можно логировать, если нужно
    await update.message.reply_text(
        "Пожалуйста, введите ваше имя: ",
        reply_markup=main_keyboard,
    )
    return GET_NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение и сохранение имени пользователя"""
    user_name = update.message.text
    context.user_data['name'] = user_name  # Сохраняем имя

    await update.message.reply_text(
        f"Отлично, {user_name}! Теперь вы можете пользоваться ботом.",
        reply_markup=main_keyboard,
    )
    payload_name_json = {
        "_id" : update.effective_user.id,
        "name" : user_name,
    }
    api_create_user = "https://swpdb-production.up.railway.app/users/"
    response_name = requests.post(api_create_user, json=payload_name_json)
    # if response_name.status_code == 200:
    #     print("yra")
    # else:
    #     print("no")

    return ConversationHandler.END
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена ввода имени"""
    await update.message.reply_text(
        "Отмена",
        reply_markup=main_keyboard,
    )

    return ConversationHandler.END




async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Доступные команды:\n"
        "/ask - задать вопрос\n"
        "/help - основные правила пользования ботом\n",
    
        reply_markup=main_keyboard,
    )







WAITING_MESSAGE = 1
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
    api_create_conv = "https://swpdb-production.up.railway.app/conversations/"
    #api_get_user = f"https://swpdb-production.up.railway.app/users/{update.effective_user.id}/"
    # response_get_name = requests.get(api_create_conv)
    # response_name = response_get_name.json().get("name")
    payload_create_conv = {
        "user_id": update.effective_user.id,
        "messages": [
            {
                "sender" : "user",
                "text" : "STARTING_MESSAGE",
                "time" : "2025-06-22T19:52:30.467Z"
            }
        ]
    }
    #update.message.date.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    response_create_conv = requests.post(api_create_conv, json=payload_create_conv)
    # if response_create_conv.status_code == 200:
    #     print("yra")
    # else:
    #     print("no")
    #     print(response_create_conv.text)
    response_create_conv_json = response_create_conv.json()
    context.user_data['conv_id'] = response_create_conv_json.get("_id")

    return WAITING_MESSAGE
async def ask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_text = update.message.text
    context.user_data['last_message'] = user_text
    await update.message.reply_text(
        f"ваш текст: {user_text}",
        reply_markup = main_keyboard
    )

    api_add_message = f"https://swpdb-production.up.railway.app/conversations/{context.user_data['conv_id']}/messages"
    payload_add_message = {
        "sender" : "user",
        "text" : user_text,
        "time" : update.message.date.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    }
    response_add_message = requests.post(api_add_message, json=payload_add_message)
    # if response_add_message.status_code == 200:
    #     print("yra")
    # else:
    #     print("no")
    #     print(response_add_message.json())

    return WAITING_MESSAGE



# Регистрация обработчиков
def register_handlers():
    application.add_handler(CommandHandler("help", help_command))
    conv_handler_start = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GET_NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_name
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("ask", ask)],
        states={
            WAITING_MESSAGE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    ask_handler
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex("^Отмена$"), cancel),
        ],
    )
    application.add_handler(conv_handler)

    application.add_handler(conv_handler_start)

register_handlers()
# Webhook эндпоинт для Telegram
@app.post("/webhook")
async def webhook(request: Request):
    try:
        if not application._initialized:
            print("⚠️ Инициализируем и запускаем application вручную (cold start)")
            await application.initialize()

        json_data = await request.json()
        print("📡 Получен update:", json_data)
        update = Update.de_json(json_data, application.bot)
        await application.process_update(update)
        return {"status": "ok"}

    except Exception as e:
        print("❌ Ошибка при обработке webhook:", str(e))
        return {"status": "error", "message": str(e)}

# Эндпоинт для проверки работоспособности
@app.get("/")
async def index():
    return {"message": "Bot is running"}

# Инициализация при запуске
@app.on_event("startup")
async def startup():
    await application.initialize()
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

@app.on_event("shutdown")
async def on_shutdown():
    # удаляем вебхук и чисто останавливаем бота
    await application.bot.delete_webhook()
    await application.shutdown()



# # Для локальной разработки (опционально)
# if __name__ == "__main__":
#     import uvicorn
#     register_handlers()
#     uvicorn.run(app, host="127.0.0.1", port=8000)
