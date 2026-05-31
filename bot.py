import os
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")
if OWNER_ID:
    try:
        OWNER_ID = int(OWNER_ID)
    except ValueError:
        OWNER_ID = None

LOGS_DIR = "daily_messages"
os.makedirs(LOGS_DIR, exist_ok=True)

# ==================== ВРЕМЕННАЯ ЗОНА ====================
# Всегда используем московское время (MSK), даже если сервер в UTC/США
MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def get_filename(dt: datetime, fmt: str = "txt") -> str:
    """Возвращает имя файла за указанную дату в нужном формате (txt или md)"""
    date_str = dt.strftime("%Y-%m-%d")
    ext = fmt.lower().strip()
    if ext not in ("txt", "md"):
        ext = "txt"
    return os.path.join(LOGS_DIR, f"messages_{date_str}.{ext}")


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
        "Я бот-дневник. Всё, что ты мне напишешь — сохраняю в ежедневные файлы "
        "в двух форматах: <b>TXT</b> и <b>MD</b>.\n\n"
        "🕒 Время везде — **московское** (MSK)\n\n"
        "📁 Файлы: <code>daily_messages/messages_YYYY-MM-DD.txt</code> и "
        "<code>daily_messages/messages_YYYY-MM-DD.md</code>\n"
        "📅 Каждый день — новые файлы\n\n"
        "Команды:\n"
        "/today — показать сообщения за сегодня (в TXT)\n"
        "/export или /exportTXT — скачать TXT-файл за сегодня\n"
        "/exportMD — скачать MD-файл за сегодня\n"
        "/yesterday или /yesterdayTXT — скачать TXT-файл за вчера\n"
        "/yesterdayMD — скачать MD-файл за вчера"
    )


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"/today от @{user.username or user.first_name} (ID: {user.id})")
    if not await is_owner(update):
        return
    filename = get_filename(datetime.now(MOSCOW_TZ), "txt")
    if not os.path.exists(filename):
        await update.message.reply_text("Сегодня пока нет сообщений.")
        return
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        await update.message.reply_text("Сегодня пока нет сообщений.")
        return
    await update.message.reply_text(f"📅 Сообщения за сегодня:\n\n{content}")


async def send_daily_file(update: Update, days_offset: int, fmt: str):
    """Общая функция отправки файла за сегодня (offset=0) или вчера (offset=1)"""
    if not await is_owner(update):
        return
    target_date = datetime.now(MOSCOW_TZ) - timedelta(days=days_offset)
    caption_prefix = "Сегодняшний" if days_offset == 0 else "Вчерашний"
    filename = get_filename(target_date, fmt)
    if not os.path.exists(filename):
        date_str = target_date.strftime("%d.%m.%Y")
        await update.message.reply_text(f"Нет сообщений за {date_str} в формате {fmt.upper()}.")
        return
    try:
        with open(filename, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=os.path.basename(filename),
                caption=f"📄 {caption_prefix} файл {fmt.upper()} ({target_date.strftime('%d.%m.%Y')})"
            )
        logger.info(f"Файл {filename} отправлен пользователю")
    except Exception as e:
        logger.error(f"Ошибка при отправке файла: {e}")
        await update.message.reply_text("Не удалось отправить файл. Попробуй позже.")


async def export_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_daily_file(update, days_offset=0, fmt="txt")


async def export_md(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_daily_file(update, days_offset=0, fmt="md")


async def yesterday_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_daily_file(update, days_offset=1, fmt="txt")


async def yesterday_md(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_daily_file(update, days_offset=1, fmt="md")


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

    now_msk = datetime.now(MOSCOW_TZ)
    timestamp = now_msk.strftime("%H:%M:%S")
    user_name = user.username or user.first_name or str(user.id)
    today = now_msk

    # === Сохраняем в TXT ===
    txt_file = get_filename(today, "txt")
    file_exists_txt = os.path.exists(txt_file)
    with open(txt_file, "a", encoding="utf-8") as f:
        if not file_exists_txt:
            date_str = today.strftime("%d.%m.%Y")
            f.write(f"=== Сообщения за {date_str} ===\n\n")
        f.write(f"[{timestamp}] {user_name}: {text}\n")

    # === Сохраняем в MD (красивое форматирование) ===
    md_file = get_filename(today, "md")
    file_exists_md = os.path.exists(md_file)
    with open(md_file, "a", encoding="utf-8") as f:
        if not file_exists_md:
            date_str = today.strftime("%d.%m.%Y")
            f.write(f"# Сообщения за {date_str}\n\n")
        f.write(f"### [{timestamp}] — {user_name}\n\n")
        f.write(f"{text}\n\n")
        f.write("---\n\n")

    logger.info(f"Сообщение сохранено в TXT и MD")
    await update.message.reply_text("✅ Сохранено")


def main():
    if not BOT_TOKEN:
        logger.error("Переменная окружения BOT_TOKEN не установлена!")
        return
    logger.info("Бот запускается...")
    application = Application.builder().token(BOT_TOKEN).build()

    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("today", today))

    # Экспорт сегодня
    application.add_handler(CommandHandler("export", export_txt))
    application.add_handler(CommandHandler("exportTXT", export_txt))
    application.add_handler(CommandHandler("exportMD", export_md))

    # Экспорт вчера
    application.add_handler(CommandHandler("yesterday", yesterday_txt))
    application.add_handler(CommandHandler("yesterdayTXT", yesterday_txt))
    application.add_handler(CommandHandler("yesterdayMD", yesterday_md))

    # Сохранение обычных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_message))

    logger.info("Бот успешно запущен и готов принимать сообщения")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
