from telegram.ext import CommandHandler, CallbackQueryHandler
import os

TOKEN = os.getenv('TOKEN')

from handlers import start, button

start_handler = CommandHandler("start", start)
button_handler = CallbackQueryHandler(button)
