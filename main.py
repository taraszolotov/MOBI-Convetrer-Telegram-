import os
import logging
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram.ext.dispatcher import run_async
import subprocess
from functools import wraps

# Налаштування журналювання
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelень) - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не встановлений в середовищі")

bot = Bot(TOKEN)

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Привіт! Надішліть мені файл електронної книги, і я перетворю його у формат MOBI.')

@run_async
def convert_to_mobi(file_path, author, title):
    try:
        subprocess.run(
            ['ebook-convert', file_path, file_path.replace('.pdf', '.mobi'), 
             '--authors', author, '--title', title],
            check=True,
            timeout=120
        )
        return file_path.replace('.pdf', '.mobi')
    except subprocess.TimeoutExpired:
        try:
            subprocess.run(
                ['calibre-debug', '-r', 'convert', file_path, file_path.replace('.pdf', '.mobi'), 
                 '--authors', author, '--title', title],
                check=True,
                timeout=120
            )
            return file_path.replace('.pdf', '.mobi')
        except Exception as e:
            logger.error(f"Помилка під час конвертації: {e}")
            return None
    except Exception as e:
        logger.error(f"Помилка під час конвертації: {e}")
        return None

def send_file(update: Update, context: CallbackContext, file_path: str) -> None:
    chat_id = update.message.chat_id
    context.bot.send_document(chat_id, document=open(file_path, 'rb'))

def handle_document(update: Update, context: CallbackContext) -> None:
    file = update.message.document
    file_path = os.path.join('/tmp', file.file_name)
    file.get_file().download(file_path)
    update.message.reply_text("Напишіть ім'я автора книги")
    context.user_data['file_path'] = file_path

def handle_author(update: Update, context: CallbackContext) -> None:
    author = update.message.text
    context.user_data['author'] = author
    update.message.reply_text("Тепер напишіть назву книги")

def handle_title(update: Update, context: CallbackContext) -> None:
    title = update.message.text
    context.user_data['title'] = title
    update.message.reply_text("Конвертую...")
    file_path = context.user_data['file_path']
    author = context.user_data['author']
    title = context.user_data['title']
    result = convert_to_mobi(file_path, author, title)
    if result:
        send_file(update, context, result)
    else:
        update.message.reply_text("Сталася помилка під час конвертації файлу.")

def main() -> None:
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.document.mime_type("application/pdf"), handle_document))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_author))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_title))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
