from fastapi import FastAPI, Request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import os

app = FastAPI()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Используйте переменные окружения Vercel
WEBHOOK_URL = os.getenv("WEBHOOK_URL")   # URL вашего Vercel приложения

# Клавиатура для главного меню
main_keyboard = ReplyKeyboardMarkup(
    [["/ask", "/help"], ["/reload"], ["/log_in", "/log_out"]],
    resize_keyboard=True,
    one_time_keyboard=False,
)

# Инициализация бота
application = Application.builder().token(TOKEN).build()

# Обработчики команд (остаются без изменений)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я первая версия бота для нашего супер проекта про рекомендательные системы",
        reply_markup=main_keyboard,
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Доступные команды:\n"
        "/ask - задать вопрос\n"
        "/help - основные правила пользования ботом\n"
        "/reload - обновить чат\n"
        "/log_out - выйти из аккаунта\n"
        "/log_in - войти в аккаунт",
        reply_markup=main_keyboard,
    )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        update.message.text,
        reply_markup=main_keyboard
    )

async def reload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Чат обновлен!",
        reply_markup=main_keyboard
    )
async def log_in(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Пройдите регистрацию в боте!",
        reply_markup=main_keyboard
    )
async def log_out(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Вы вышли из своего аккаунта",
        reply_markup=main_keyboard
    )
async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Специальная клавиатура для команды ask
    ask_keyboard = ReplyKeyboardMarkup(
        [["Отмена"]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await update.message.reply_text(
        "Напишите свой запрос! Я постараюсь помочь вам!",
        reply_markup=ask_keyboard
    )



# Регистрация обработчиков
def register_handlers():
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reload", reload))
    application.add_handler(CommandHandler("ask", ask))
    application.add_handler(CommandHandler("log_out", log_out))
    application.add_handler(CommandHandler("log_in", log_in))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# Webhook эндпоинт для Telegram
@app.post("/webhook")
async def webhook(request: Request):
    json_data = await request.json()
    update = Update.de_json(json_data, application.bot)
    await application.process_update(update)
    return {"status": "ok"}

# Эндпоинт для проверки работоспособности
@app.get("/")
async def index():
    return {"message": "Bot is running"}

# Инициализация при запуске
@app.on_event("startup")
async def startup():
    register_handlers()
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

# Для локальной разработки (опционально)
if __name__ == "__main__":
    import uvicorn
    register_handlers()
    uvicorn.run(app, host="0.0.0.0", port=8000)