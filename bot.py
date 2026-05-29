import os
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Настройка логирования (чтобы видеть в логах сервиса, что происходит)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== НАСТРОЙКИ ====================
# Бот берёт токен и ID из переменных окружения (рекомендуется для хостинга)
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")

if OWNER_ID:
    try:
        OWNER_ID = int(OWNER_ID)
    except ValueError:
        OWNER_ID = None

LOGS_DIR = "daily_messages"
os.makedirs(LOGS_DIR, exist_ok=True)


def get_daily_filename() -> str:
    """Возвращает имя файла за сегодня"""
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(LOGS_DIR, f"messages_{today}.txt")


async def is_owner(update: Update) -> bool:
    if OWNER_ID is None:
        return True
    user_id = update.effective_user.id
    is_authorized = user_id == OWNER_ID
    if not is_authorized:
        logger.warning(f"Отклонено сообщение от неавторизованного пользователя: {user_id}")
    return is_authorized


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"/start от @{user.username or user.first_name} (ID: {user.id})")

    if not await is_owner(update):
        await update.message.reply_text("Извини, этот бот только для хозяина.")
        return

    await update.message.reply_text(
        "Привет! 👋\n\n"
        "Я бот-дневник. Всё, что ты мне напишешь — сохраняю в ежедневные файлы.\n\n"
        "📁 Файлы: <code>daily_messages/messages_YYYY-MM-DD.txt</code>\n"
        "📅 Каждый день — новый файл\n\n"
        "Команды:\n"
        "/today — показать сообщения за сегодня"
    )


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"/today от @{user.username or user.first_name} (ID: {user.id})")

    if not await is_owner(update):
        return

    filename = get_daily_filename()

    if not os.path.exists(filename):
        await update.message.reply_text("Сегодня пока нет сообщений.")
        return

    with open(filename, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        await update.message.reply_text("Сегодня пока нет сообщений.")
        return

    await update.message.reply_text(f"📅 Сообщения за сегодня:\n\n{content}")


async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"Получено сообщение от @{user.username or user.first_name} (ID: {user.id}): {update.message.text[:50]}...")

    if not await is_owner(update):
        await update.message.reply_text("Извини, этот бот только для хозяина.")
        return

    text = update.message.text
    if not text:
        await update.message.reply_text("Пока сохраняю только текстовые сообщения.")
        return

    filename = get_daily_filename()
    timestamp = datetime.now().strftime("%H:%M:%S")
    user_name = user.username or user.first_name or str(user.id)

    file_exists = os.path.exists(filename)

    with open(filename, "a", encoding="utf-8") as f:
        if not file_exists:
            date_str = datetime.now().strftime("%d.%m.%Y")
            f.write(f"=== Сообщения за {date_str} ===\n\n")
        f.write(f"[{timestamp}] {user_name}: {text}\n")

    logger.info(f"Сообщение сохранено в {filename}")
    await update.message.reply_text("✅ Сохранено")


def main():
    if not BOT_TOKEN:
        logger.error("Переменная окружения BOT_TOKEN не установлена!")
        return

    logger.info("Бот запускается...")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("today", today))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_message))

    logger.info("Бот успешно запущен и готов принимать сообщения")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
