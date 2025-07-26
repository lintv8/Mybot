from telegram.ext import CommandHandler, CallbackQueryHandler
import os

# Ensure the environment variable is set
TOKEN = os.getenv('TOKEN')
if not TOKEN:
    raise ValueError("TOKEN environment variable is not set")

from handlers import start, button

start_handler = CommandHandler("start", start)
button_handler = CallbackQueryHandler(button)
