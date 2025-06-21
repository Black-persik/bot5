import requests
from fastapi import FastAPI, Request
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler,
)
import os

app = FastAPI()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Используйте переменные окружения Vercel
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Без "/webhook" в конце!

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
NAME, SURNAME, GENDER = range(3)

async def log_in(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.message.chat_id
    api_get_user_by_id = f"https://swpdb-production.up.railway.app/users/tg/{chat_id}"
    response = requests.get(api_get_user_by_id)
    if response.status_code == 200:
        await update.message.reply_text(
            "Вы уже зарегистрированы",
            reply_markup=main_keyboard
        )
        return ConversationHandler.END
    


    await update.message.reply_text(
        "Пройдите регистрацию в боте! Введите имя: ",
        reply_markup=main_keyboard
    )
    return NAME
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text
    await update.message.reply_text(
        "Введите фамилию:",
        reply_markup=main_keyboard
    )
    return SURNAME
async def get_surname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['surname'] = update.message.text
    keyboard = [
        [InlineKeyboardButton("Мужской", callback_data='мужской')],
        [InlineKeyboardButton("Женский", callback_data='женский')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Ваш пол: ",
        reply_markup=reply_markup,
    )
    return GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    gender = "male" if query.data == 'male' else "female"
    gender_for_output = "мужской" if gender == "male" else "женский"
    context.user_data['gender'] = gender
    name = context.user_data.get('name', 'no name')
    surname = context.user_data.get('surname', 'no surname')
    await query.edit_message_text(
        f"Регистрация завершена!\n\n"
        f"Имя: {name}\n"
        f"Фамилия: {surname}\n"
        f"Пол: {gender_for_output}"
    )
    chat_id = update.effective_chat.id
    api_create_user = "https://swpdb-production.up.railway.app/users/"
    payload_json = {
        "tg_id": chat_id,
        "name": name,
        "surname": surname,
        "gender": gender,
        "language": "ru",
        "recommendation_method": "fixed",
        "launch_count": 0,
        "conversations_count": 0,
        "current_bundle_version": 0,
        "bundle_version_at_install": 0
    }
        
    response = requests.post(api_create_user, json=payload_json)
       
    

    return ConversationHandler.END

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
    #application.add_handler(CommandHandler("log_in", log_in))
    #application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("log_in", log_in)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_surname)],
            GENDER: [CallbackQueryHandler(get_gender, pattern='^(мужской|женский)$')]
        },
        fallbacks=[]
    ))
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
    uvicorn.run(app, host="127.0.0.1", port=8000)
