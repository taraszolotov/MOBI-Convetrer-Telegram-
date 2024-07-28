import os
import logging
from telegram import Update, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram.error import BadRequest
import uuid
from pathlib import Path
import subprocess

# Встановіть ваш токен тут
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не встановлений в середовищі")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Де зберігати файли
DOWNLOAD_DIR = "downloads"

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Привіт! Надішліть мені файл електронної книги, і я перетворю його у формат MOBI.")

async def handle_file(update: Update, context: CallbackContext):
    file = update.message.document
    file_name = file.file_name
    file_extension = Path(file_name).suffix.lower()

    if file_extension not in ['.pdf', '.txt', '.fb2', '.epub']:
        await update.message.reply_text("Формат файлу не підтримується. Надішліть PDF, TXT, FB2 або EPUB файл.")
        return

    new_file_name = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(DOWNLOAD_DIR, new_file_name)
    
    await update.message.reply_text("Напишіть ім'я автора:")
    context.user_data['file_path'] = file_path
    context.user_data['file_name'] = file_name
    context.user_data['file'] = file

    return

async def author_response(update: Update, context: CallbackContext):
    context.user_data['author'] = update.message.text
    await update.message.reply_text("Тепер напишіть назву книги:")

async def title_response(update: Update, context: CallbackContext):
    context.user_data['title'] = update.message.text

    file = context.user_data['file']
    file_path = context.user_data['file_path']
    file_name = context.user_data['file_name']
    author = context.user_data['author']
    title = context.user_data['title']

    await file.get_file().download(file_path)

    await update.message.reply_text("Конвертую...")

    mobi_file_path = file_path.replace(Path(file_path).suffix, ".mobi")

    try:
        result = subprocess.run(
            ['ebook-convert', file_path, mobi_file_path, '--authors', author, '--title', title],
            check=True,
            capture_output=True,
            text=True,
            timeout=120
        )
    except subprocess.CalledProcessError as e:
        await update.message.reply_text("Пробач, я не зміг конвертувати цей файл.")
        logger.error(f"Conversion failed: {e}")
        return
    except subprocess.TimeoutExpired as e:
        await update.message.reply_text("Пробач, конвертація зайняла занадто багато часу.")
        logger.error(f"Conversion timed out: {e}")
        return
    except Exception as e:
        await update.message.reply_text("Стався технічний збій, спробуй пізніше.")
        logger.error(f"Unexpected error: {e}")
        return

    try:
        with open(mobi_file_path, 'rb') as mobi_file:
            await update.message.reply_document(mobi_file, filename=Path(mobi_file_path).name)
    except BadRequest as e:
        if "File is too big" in str(e):
            await update.message.reply_text("Файл завеликий.")
        else:
            await update.message.reply_text("Не вдалося відправити файл.")
        logger.error(f"Sending file failed: {e}")
    except Exception as e:
        await update.message.reply_text("Стався технічний збій при відправленні файлу.")
        logger.error(f"Unexpected error when sending file: {e}")

    # Очищення тимчасових файлів
    os.remove(file_path)
    os.remove(mobi_file_path)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.document & ~Filters.command, handle_file))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, author_response))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, title_response))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
