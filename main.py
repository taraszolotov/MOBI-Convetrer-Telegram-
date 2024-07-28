import os
import logging
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram.error import BadRequest
from telegram.constants import ParseMode
import subprocess

# Ініціалізація логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("TOKEN")

async def start(update: Update, context):
    await update.message.reply_text("Привіт! Надішліть мені файл електронної книги, і я перетворю його у формат MOBI.")

async def convert_book(update: Update, context):
    if not update.message.document:
        await update.message.reply_text("Будь ласка, надішліть файл у форматі PDF, TXT або FB2.")
        return

    file = await context.bot.get_file(update.message.document.file_id)
    await update.message.reply_text("Напиши ім'я автора книги")

    def author_name_handler(update: Update, context):
        context.user_data['author'] = update.message.text
        update.message.reply_text("Тепер напиши назву книги")

        context.dispatcher.remove_handler(context.user_data['author_handler'])
        context.dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, book_title_handler))

    def book_title_handler(update: Update, context):
        context.user_data['title'] = update.message.text

        document = update.message.document
        file_name = document.file_name
        file_path = f"/tmp/{file_name}"
        file.download(file_path)

        output_file = f"/tmp/{file_name.split('.')[0]}.mobi"
        convert_cmd = [
            'ebook-convert',
            file_path,
            output_file,
            '--authors', context.user_data['author'],
            '--title', context.user_data['title']
        ]

        try:
            await update.message.reply_text("Конвертую...")
            subprocess.run(convert_cmd, check=True, timeout=120)
            await update.message.reply_document(document=output_file)
        except subprocess.TimeoutExpired:
            await update.message.reply_text("Конвертація зайняла надто багато часу.")
        except subprocess.CalledProcessError:
            await update.message.reply_text("Пробач, я не зміг конвертувати цей файл.")
        except Exception:
            await update.message.reply_text("Стався технічний збій, спробуй пізніше.")

        context.dispatcher.remove_handler(context.user_data['title_handler'])

    context.dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, author_name_handler))

def main():
    application = ApplicationBuilder().token(TOKEN).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    document_handler = MessageHandler(filters.Document.ALL, convert_book)
    application.add_handler(document_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
