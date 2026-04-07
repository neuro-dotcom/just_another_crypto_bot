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
scheduler = BackgroundScheduler(timezone=pytz.timezone('Europe/Berlin'))
PREFS_FILE = "user_preferences.json"

if AUTHORIZED_USER_ID:
    try:
        bot.send_message(AUTHORIZED_USER_ID, "🚀 Just Another Crypto AI is officially ONLINE!")
    except Exception as e:
        print(f"Startup notification failed: {e}")

# ==========================================
# 2. STATE MANAGEMENT (JSON DATABASE)
# ==========================================
def get_user_time():
    """Load the saved time or return default 08:00"""
    if os.path.exists(PREFS_FILE):
        with open(PREFS_FILE, 'r') as f:
            prefs = json.load(f)
            return prefs.get(AUTHORIZED_USER_ID, {}).get("time", "08:00")
    return "08:00"

def save_user_time(new_time):
    prefs = {}
    if os.path.exists(PREFS_FILE):
        with open(PREFS_FILE, 'r') as f:
            prefs = json.load(f)
    if AUTHORIZED_USER_ID not in prefs:
        prefs[AUTHORIZED_USER_ID] = {}
    prefs[AUTHORIZED_USER_ID]["time"] = new_time
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
    """Automatically fetches data and sends an AI report to the Admin."""
    if not AUTHORIZED_USER_ID: return
    print("⏰ Executing scheduled morning report...", flush=True)
    
    btc, eth = fetch_crypto_prices()
    fng_val, fng_sent = fetch_fear_and_greed_index()

    if btc and eth:
        report = generate_ai_analysis(btc, eth, fng_val or "N/A", fng_sent or "N/A", mode="english")
        bot.send_message(AUTHORIZED_USER_ID, f"🌅 **Wolf's Morning Briefing**\n\n{report}")
    else:
        bot.send_message(AUTHORIZED_USER_ID, "⚠️ Morning routine failed: API Error fetching prices.")

def update_schedule(new_time):
    """Updates the cron job to run at the specified user time."""
    h, m = map(int, new_time.split(":"))
    scheduler.add_job(send_morning_report, 'cron', hour=h, minute=m, id='daily_briefing', replace_existing=True)
    print(f"⏱️ Schedule updated to {new_time} UTC", flush=True)

def init_scheduler():
    """Starts the scheduler using the user's saved time preference."""
    saved_time = get_user_time()
    update_schedule(saved_time)
    scheduler.start()

# ==========================================
# 6. TELEGRAM HANDLERS (ROUTING & SECURITY)
# ==========================================
@bot.message_handler(func=lambda msg: str(msg.chat.id) != AUTHORIZED_USER_ID)
def block_strangers(msg):
    bot.reply_to(msg, "⛔ Access Denied. This is a private Wolf-class AI instance.")

@bot.callback_query_handler(func=lambda call: str(call.message.chat.id) != AUTHORIZED_USER_ID)
def block_stranger_callbacks(call):
    bot.answer_callback_query(call.id, "⛔ Access Denied. Wolf only.", show_alert=True)

@bot.message_handler(commands=['start'])
def send_welcome(m):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        InlineKeyboardButton("📊 Dry Numbers Only", callback_data="raw_data"),
        InlineKeyboardButton("🇺🇸 AI Report (English)", callback_data="ai_english"),
        InlineKeyboardButton("🌍 AI Report (Bilingual)", callback_data="ai_bilingual"),
        InlineKeyboardButton("⏰ Set Briefing Time", callback_data="menu_set_time") # 👈 NEW BUTTON
    )
    bot.send_message(m.chat.id, "Welcome to Just Another Crypto AI, boss 🐺\nChoose your report format:", reply_markup=markup)

@bot.message_handler(commands=['set_time'])
def set_time_command(m):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🌅 08:00", callback_data="set_08:00"),
        InlineKeyboardButton("🏙️ 12:00", callback_data="set_12:00")
    )
    markup.row(
        InlineKeyboardButton("🌆 18:00", callback_data="set_18:00"),
        InlineKeyboardButton("🌃 22:00", callback_data="set_22:00")
    )
    bot.reply_to(m, "⏰ **Select your daily briefing time (UTC):**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    # 🧹 GHOST CLEANUP
    try:
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    except Exception: pass

    # 👈 ROUTE THE MAIN MENU BUTTON TO THE TIME MENU
    if call.data == "menu_set_time":
        set_time_command(call.message)
        return
        
    # ⏱️ TIME SELECTION
    if call.data.startswith("set_"):
        new_time = call.data.split("_")[1]
        save_user_time(new_time)
        update_schedule(new_time)
        bot.answer_callback_query(call.id, f"✅ Time set to {new_time}")
        bot.send_message(call.message.chat.id, f"🚀 **Confirmed!** Morning report scheduled for {new_time} UTC.")
        return

    # 📊 MARKET DATA
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
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
    def log_message(self, format, *args): pass

def start_dummy_server():
    port = int(os.environ.get("PORT", 7860)) 
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    print(f"🌐 Dummy web server running on port {port}", flush=True)
    server.serve_forever()

# ==========================================
# 8. MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print("🚀 Starting background processes...", flush=True)
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    # Init scheduler correctly using saved state
    init_scheduler()
    
    bot.remove_webhook()
    print("🤖 Bot is listening...", flush=True)
    bot.infinity_polling()