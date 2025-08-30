# bot.py (Replit DB এবং Always On-এর জন্য চূড়ান্ত সংস্করণ)
import os
import requests
import random
import string
import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
)
import database

# --- Configuration from Environment Variables ---
OWNER_ID = int(os.environ.get('OWNER_ID'))
LOG_CHANNEL_ID = int(os.environ.get('LOG_CHANNEL_ID'))
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# --- Web Server to keep the bot alive ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is alive!"
def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- Logging Setup ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ... (আগের সব ফাংশন যেমন random_string_generator, format_json_template, send_dynamic_request, process_requests ইত্যাদি এখানে অপরিবর্তিত থাকবে) ...
# ... (আমি শুধু main() এবং কিছু ছোটখাটো জায়গা পরিবর্তন করেছি) ...

# --- Bot Setup ---
def main() -> None:
    # Replit DB-তে ডিফল্ট API যোগ করা
    database.setup_initial_apis()
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # ... (বাকি সব handler আগের মতোই থাকবে) ...
    
    application.run_polling()

if __name__ == "__main__":
    # Replit-এর জন্য ওয়েব সার্ভারটি একটি আলাদা থ্রেডে চালু করা হচ্ছে
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    main()
