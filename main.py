import os
import logging
from telegram import Update, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
from telegram.error import BadRequest
import ebooklib
from ebooklib import epub
from PyPDF2 import PdfReader
import tempfile
import subprocess
import uuid

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

AUTHOR, TITLE, FILE = range(3)

def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Привіт! Надішліть мені файл електронної книги, і я перетворю його у формат MOBI.")
    return FILE

def handle_file(update: Update, context: CallbackContext) -> int:
    file = update.message.document
    file_name = file.file_name
    new_file = context.bot.get_file(file.file_id)
    
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        new_file.download(custom_path=tf.name)
        context.user_data['file_path'] = tf.name
        context.user_data['original_file_name'] = file_name
    
    update.message.reply_text("Напиши ім'я автора книги:")
    return AUTHOR

def ask_title(update: Update, context: CallbackContext) -> int:
    author = update.message.text
    context.user_data['author'] = author
    update.message.reply_text("Тепер напиши назву книги:")
    return TITLE

def convert_book(update: Update, context: CallbackContext) -> int:
    title = update.message.text
    author = context.user_data['author']
    file_path = context.user_data['file_path']
    original_file_name = context.user_data['original_file_name']

    output_file = os.path.splitext(original_file_name)[0] + '.mobi'
    output_path = os.path.join(tempfile.gettempdir(), output_file)
    
    try:
        update.message.reply_text("Конвертую...")
        
        result = subprocess.run([
            'ebook-convert', file_path, output_path,
            '--authors', author,
            '--title', title
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            raise Exception(result.stderr)
        
        with open(output_path, 'rb') as f:
            update.message.reply_document(document=f, filename=output_file)
    except subprocess.TimeoutExpired:
        update.message.reply_text("Конвертація триває занадто довго. Спробуйте інший файл або зменшіть розмір файлу.")
    except BadRequest as e:
        if "File is too big" in str(e):
            update.message.reply_text("Файл завеликий.")
        else:
            update.message.reply_text(f"Сталася помилка: {str(e)}")
    except Exception as e:
        update.message.reply_text(f"Сталася помилка під час конвертації: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(output_path):
            os.remove(output_path)
    
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Операція скасована.')
    return ConversationHandler.END

def main() -> None:
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN не встановлений в середовищі")
    
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FILE: [MessageHandler(Filters.document, handle_file)],
            AUTHOR: [MessageHandler(Filters.text & ~Filters.command, ask_title)],
            TITLE: [MessageHandler(Filters.text & ~Filters.command, convert_book)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
