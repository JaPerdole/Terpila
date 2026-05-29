import os
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "ТОКЕН_ТВОЕГО_БОТА"          # ← Вставь сюда токен от @BotFather
OWNER_ID = None                           # ← Вставь свой ID (число) или оставь None, чтобы бот был публичным

LOGS_DIR = "daily_messages"
os.makedirs(LOGS_DIR, exist_ok=True)


def get_daily_filename() -> str:
    """Возвращает имя файла за сегодня"""
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(LOGS_DIR, f"messages_{today}.txt")


async def is_owner(update: Update) -> bool:
    """Проверка, что сообщение от хозяина"""
    if OWNER_ID is None:
        return True
    return update.effective_user.id == OWNER_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        await update.message.reply_text("Извини, этот бот только для хозяина.")
        return

    await update.message.reply_text(
        "Привет! 👋\n\n"
        "Я бот-дневник. Всё, что ты мне напишешь, я сохраняю в ежедневные файлы.\n\n"
        "📁 Файлы лежат в папке <code>daily_messages/</code>\n"
        "📅 Каждый день — новый файл\n\n"
        "Доступные команды:\n"
        "/today — показать все сообщения за сегодня\n"
        "/start — это сообщение"
    )


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        return

    filename = get_daily_filename()

    if not os.path.exists(filename):
        await update.message.reply_text("Сегодня пока нет сохранённых сообщений.")
        return

    with open(filename, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        await update.message.reply_text("Сегодня пока нет сохранённых сообщений.")
        return

    await update.message.reply_text(f"📅 Сообщения за сегодня:\n\n{content}")


async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        await update.message.reply_text("Извини, этот бот только для хозяина.")
        return

    text = update.message.text
    if not text:
        await update.message.reply_text("Пока я сохраняю только текстовые сообщения.")
        return

    filename = get_daily_filename()
    timestamp = datetime.now().strftime("%H:%M:%S")
    user_name = update.effective_user.username or update.effective_user.first_name or str(update.effective_user.id)

    file_exists = os.path.exists(filename)

    with open(filename, "a", encoding="utf-8") as f:
        if not file_exists:
            date_str = datetime.now().strftime("%d.%m.%Y")
            f.write(f"=== Сообщения за {date_str} ===\n\n")
        f.write(f"[{timestamp}] {user_name}: {text}\n")

    await update.message.reply_text("✅ Сохранено")


def main():
    if BOT_TOKEN == "ТОКЕН_ТВОЕГО_БОТА":
        print("❌ Ошибка: не указан BOT_TOKEN!")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("today", today))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_message))

    print("🤖 Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
