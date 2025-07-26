from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
import json

# Load products from JSON file
with open('products.json', 'r') as f:
    PRODUCTS = json.load(f)

def start(update: Update, context: CallbackContext) -> None:
    keyboard = []
    for product in PRODUCTS.keys():
        keyboard.append([InlineKeyboardButton(product, callback_data=product)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please choose a product:', reply_markup=reply_markup)

def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    selected_product = query.data
    product_link = PRODUCTS[selected_product]
    query.edit_message_text(text=f"Here is your link:
{product_link}")
