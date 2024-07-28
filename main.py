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

TOKEN = os.getenv('TOKEN')

async def start(update: Update, context):
    await update.message.reply_text('Привіт! Надішліть мені файл електронної книги, і я перетворю його у формат MOBI.')

async def handle_document(update: Update, context):
    document = update.message.document
    if document:
        await update.message.reply_text('Напишіть ім\'я автора книги.')
        context.user_data['document'] = document

async def handle_author(update: Update, context):
    author = update.message.text
    if 'document' in context.user_data:
        context.user_data['author'] = author
        await update.message.reply_text('Тепер напишіть назву книги.')

async def handle_title(update: Update, context):
    title = update.message.text
    if 'author' in context.user_data and 'document' in context.user_data:
        document = context.user_data['document']
        author = context.user_data['author']
        file_path = await document.get_file().download()
        mobi_path = f"/tmp/{document.file_name.split('.')[0]}.mobi"
        try:
            await update.message.reply_text('Конвертую...')
            # Перша спроба конвертації
            command = f"ebook-convert '{file_path}' '{mobi_path}' --authors '{author}' --title '{title}'"
            result = subprocess.run(command, shell=True, timeout=120)
            if result.returncode != 0:
                raise Exception("Перша спроба конвертації не вдалася.")
            with open(mobi_path, 'rb') as mobi_file:
                await update.message.reply_document(mobi_file, filename=f"{title}.mobi")
        except subprocess.TimeoutExpired:
            await update.message.reply_text("Конвертація зайняла занадто багато часу. Спробуйте ще раз.")
        except Exception as e:
            await update.message.reply_text('Пробач, я не зміг конвертувати цей файл.')
        finally:
            context.user_data.clear()

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    document_handler = MessageHandler(filters.Document.ALL, handle_document)
    author_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_author)
    title_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_title)
    
    application.add_handler(start_handler)
    application.add_handler(document_handler)
    application.add_handler(author_handler)
    application.add_handler(title_handler)
    
    application.run_polling()

if __name__ == '__main__':
    main()
