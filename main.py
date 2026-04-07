import os
import json
import threading
import requests
import pytz
import telebot
from http.server import BaseHTTPRequestHandler, HTTPServer
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

# ==========================================
# 1. CONFIGURATION & INITIALIZATION
# ==========================================
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AUTHORIZED_USER_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

client = genai.Client(api_key=API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Initialize scheduler without a default timezone (it will be set dynamically)
scheduler = BackgroundScheduler()
PREFS_FILE = "user_preferences.json"

if AUTHORIZED_USER_ID:
    try:
        bot.send_message(AUTHORIZED_USER_ID, "🚀 Just Another Crypto AI is officially ONLINE!")
    except Exception as e:
        print(f"Startup notification failed: {e}")

# ==========================================
# 2. STATE MANAGEMENT (JSON DATABASE)
# ==========================================
def get_user_prefs():
    """Loads preferences or sets defaults: 08:00 at UTC+0"""
    if os.path.exists(PREFS_FILE):
        with open(PREFS_FILE, 'r') as f:
            prefs = json.load(f)
            user_data = prefs.get(AUTHORIZED_USER_ID, {})
            return user_data.get("time", "08:00"), user_data.get("tz_offset", 0)
    return "08:00", 0

def save_user_pref(key, value):
    """Saves a specific preference to the JSON file"""
    prefs = {}
    if os.path.exists(PREFS_FILE):
        with open(PREFS_FILE, 'r') as f:
            prefs = json.load(f)
            
    if AUTHORIZED_USER_ID not in prefs:
        prefs[AUTHORIZED_USER_ID] = {"time": "08:00", "tz_offset": 0}
        
    prefs[AUTHORIZED_USER_ID][key] = value
    
    with open(PREFS_FILE, 'w') as f:
        json.dump(prefs, f)

# ==========================================
# 3. DATA GATHERING MODULES (APIs)
# ==========================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_crypto_prices():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data['bitcoin']['usd']), float(data['ethereum']['usd'])
    except requests.RequestException as e:
        print(f"❌ CoinGecko API Error: {e}", flush=True)
        return None, None

def fetch_fear_and_greed_index():
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data['data'][0]['value'], data['data'][0]['value_classification']
    except requests.RequestException as e:
        print(f"❌ Fear & Greed API Error: {e}", flush=True)
        return None, None

# ==========================================
# 4. AI PROCESSING MODULE
# ==========================================
def generate_ai_analysis(btc, eth, fng_val, fng_sent, mode):
    format_instructions = "Provide the response only in 🇬🇧 English."
    if mode == "bilingual":
        format_instructions = "Provide the response in two formats: 🇬🇧 English first, then 🇷🇺 Russian."

    prompt = f"""
    You are an expert, slightly sarcastic crypto analyst. 
    Current market snapshot:
    - Bitcoin: ${btc}
    - Ethereum: ${eth}
    - Fear & Greed: {fng_val}/100 ({fng_sent})

    Write a short, punchy market update (3-4 sentences) explaining what this means for retail traders.
    {format_instructions}
    """
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return response.text
    except Exception as e:
        return f"❌ AI Error: {e}"

# ==========================================
# 5. PROACTIVE AUTOMATION & SCHEDULING
# ==========================================
def send_morning_report():
    if not AUTHORIZED_USER_ID: return
    print("⏰ Executing scheduled morning report...", flush=True)
    
    btc, eth = fetch_crypto_prices()
    fng_val, fng_sent = fetch_fear_and_greed_index()

    if btc and eth:
        report = generate_ai_analysis(btc, eth, fng_val or "N/A", fng_sent or "N/A", mode="english")
        bot.send_message(AUTHORIZED_USER_ID, f"🌅 **Wolf's Morning Briefing**\n\n{report}")
    else:
        bot.send_message(AUTHORIZED_USER_ID, "⚠️ Morning routine failed: API Error fetching prices.")

def update_schedule():
    """Reads JSON DB and updates cron job with correct Time and Timezone Offset"""
    saved_time, tz_offset = get_user_prefs()
    h, m = map(int, saved_time.split(":"))
    
    # Convert integer offset to a mathematically perfect timezone object for APScheduler
    custom_tz = pytz.FixedOffset(tz_offset * 60)
    
    scheduler.add_job(
        send_morning_report, 
        'cron', 
        hour=h, 
        minute=m, 
        timezone=custom_tz,
        id='daily_briefing', 
        replace_existing=True
    )
    
    sign = "+" if tz_offset >= 0 else ""
    print(f"⏱️ Schedule set to {saved_time} (UTC{sign}{tz_offset})", flush=True)

def init_scheduler():
    update_schedule()
    scheduler.start()

# ==========================================
# 6. TELEGRAM HANDLERS (UI & ROUTING)
# ==========================================
@bot.message_handler(func=lambda msg: str(msg.chat.id) != AUTHORIZED_USER_ID)
def block_strangers(msg):
    bot.reply_to(msg, "⛔ Access Denied. Private AI instance.")

@bot.callback_query_handler(func=lambda call: str(call.message.chat.id) != AUTHORIZED_USER_ID)
def block_stranger_callbacks(call):
    bot.answer_callback_query(call.id, "⛔ Access Denied.", show_alert=True)

@bot.message_handler(commands=['start'])
def send_welcome(m):
    saved_time, tz_offset = get_user_prefs()
    sign = "+" if tz_offset >= 0 else ""
    
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        InlineKeyboardButton("📊 Dry Numbers Only", callback_data="raw_data"),
        InlineKeyboardButton("🇺🇸 AI Report (English)", callback_data="ai_english"),
        InlineKeyboardButton("🌍 AI Report (Bilingual)", callback_data="ai_bilingual"),
        InlineKeyboardButton(f"⏰ Set Time ({saved_time})", callback_data="menu_set_time"),
        InlineKeyboardButton(f"🌍 Set Timezone (UTC{sign}{tz_offset})", callback_data="menu_set_tz")
    )
    bot.send_message(m.chat.id, "Welcome to Just Another Crypto AI, boss 🐺\nChoose an action:", reply_markup=markup)

def show_time_menu(chat_id):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("08:00", callback_data="time_08:00"), InlineKeyboardButton("12:00", callback_data="time_12:00"))
    markup.row(InlineKeyboardButton("18:00", callback_data="time_18:00"), InlineKeyboardButton("22:00", callback_data="time_22:00"))
    bot.send_message(chat_id, "⏰ **Select your daily briefing time:**", reply_markup=markup, parse_mode="Markdown")

def show_timezone_menu(chat_id):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("UTC", callback_data="tz_0"), InlineKeyboardButton("UTC +1", callback_data="tz_1"), InlineKeyboardButton("UTC +2", callback_data="tz_2"))
    markup.row(InlineKeyboardButton("UTC +3", callback_data="tz_3"), InlineKeyboardButton("UTC +4", callback_data="tz_4"), InlineKeyboardButton("UTC +5", callback_data="tz_5"))
    bot.send_message(chat_id, "🌍 **Select your local timezone offset:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    # 🧹 GHOST CLEANUP
    try:
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    except Exception: pass

    # --- UI MENU ROUTING ---
    if call.data == "menu_set_time":
        show_time_menu(call.message.chat.id)
        return
    if call.data == "menu_set_tz":
        show_timezone_menu(call.message.chat.id)
        return

    # --- TIMEZONE SELECTION LOGIC ---
    if call.data.startswith("tz_"):
        offset = int(call.data.split("_")[1])
        save_user_pref("tz_offset", offset)
        update_schedule()
        sign = "+" if offset >= 0 else ""
        bot.send_message(call.message.chat.id, f"🌍 **Timezone updated to UTC{sign}{offset}.**\nType /start to see your full schedule.", parse_mode="Markdown")
        return

    # --- TIME SELECTION LOGIC ---
    if call.data.startswith("time_"):
        new_time = call.data.split("_")[1]
        save_user_pref("time", new_time)
        update_schedule()
        bot.send_message(call.message.chat.id, f"⏰ **Time updated to {new_time}.**\nType /start to see your full schedule.", parse_mode="Markdown")
        return

    # --- MARKET DATA LOGIC ---
    bot.answer_callback_query(call.id, "Gathering data...")
    bot.send_message(call.message.chat.id, "📡 Fetching market data. Please wait...")

    btc, eth = fetch_crypto_prices()
    fng_val, fng_sent = fetch_fear_and_greed_index()

    if not btc or not eth:
        bot.send_message(call.message.chat.id, "⚠️ API Error: Could not fetch prices.")
        return

    fng_val, fng_sent = fng_val or "N/A", fng_sent or "Data Unavailable"

    if call.data == "raw_data":
        bot.send_message(call.message.chat.id, f"💰 **Raw Data:**\nBTC: ${btc}\nETH: ${eth}\nF&G: {fng_val}/100 ({fng_sent})")
    elif call.data == "ai_english":
        bot.send_message(call.message.chat.id, generate_ai_analysis(btc, eth, fng_val, fng_sent, "english"))
    elif call.data == "ai_bilingual":
        bot.send_message(call.message.chat.id, generate_ai_analysis(btc, eth, fng_val, fng_sent, "bilingual"))

# ==========================================
# 7. CLOUD INFRASTRUCTURE (WEB SERVER)
# ==========================================
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")
    def log_message(self, format, *args): pass

def start_dummy_server():
    port = int(os.environ.get("PORT", 7860)) 
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

# ==========================================
# 8. MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print("🚀 Starting background processes...", flush=True)
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    init_scheduler()
    bot.remove_webhook()
    
    print("🤖 Bot is listening...", flush=True)
    bot.infinity_polling()