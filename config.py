import os

# Ensure the environment variable is set
TOKEN = os.getenv('TOKEN')
if not TOKEN:
    raise ValueError("TOKEN environment variable is not set")

print(f"TOKEN: {TOKEN}")  # Debug print to verify TOKEN is read correctly

from handlers import start, button

start_handler = CommandHandler("start", start)
button_handler = CallbackQueryHandler(button)
