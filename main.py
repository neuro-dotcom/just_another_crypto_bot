import os
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import json

# Built-in libraries for our dummy web server
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- 1. Configuration ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

client = genai.Client(api_key=API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# CRITICAL SEC FIX: Strip invisible spaces from the Hugging Face secret
AUTHORIZED_USER_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Send a proactive notification on startup
if AUTHORIZED_USER_ID:
    bot.send_message(AUTHORIZED_USER_ID, "🚀 Just Another Crypto AI is officially ONLINE on Hugging Face!")


# ==========================================
# --- THE LOCKDOWN (WOLF PATCH 1.0) ---
# ==========================================

# 1. Block unauthorized TEXT and COMMANDS (like /start)
@bot.message_handler(func=lambda message: str(message.chat.id) != AUTHORIZED_USER_ID)
def block_strangers(message):
    print(f"🛡️ Security: Blocked text from {message.chat.id} (Expected: {AUTHORIZED_USER_ID})", flush=True)
    bot.reply_to(message, "⛔ Access Denied. This is a private Wolf-class AI instance.")

# 2. Block unauthorized BUTTON CLICKS (Callback Bypass)
@bot.callback_query_handler(func=lambda call: str(call.message.chat.id) != AUTHORIZED_USER_ID)
def block_stranger_callbacks(call):
    print(f"🛡️ Security: Blocked button click from {call.message.chat.id}", flush=True)
    bot.answer_callback_query(call.id, "⛔ Access Denied. Wolf only.", show_alert=True)

# ==========================================


# --- 2. Data Gathering Modules ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_crypto_prices():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        btc_price = float(data['bitcoin']['usd'])
        eth_price = float(data['ethereum']['usd'])
        return btc_price, eth_price
    except requests.RequestException as e:
        print(f"❌ CoinGecko API Error: {e}", flush=True)
        return None, None

def fetch_fear_and_greed_index():
    url = "https://api.alternative.me/fng/?limit=1"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        value = data['data'][0]['value']
        sentiment = data['data'][0]['value_classification']
        return value, sentiment
    except requests.RequestException as e:
        print(f"❌ Fear & Greed API Error: {e}", flush=True)
        return None, None


# --- 3. AI Processing Module ---
def generate_ai_analysis(btc, eth, fng_val, fng_sent, mode):
    if mode == "bilingual":
        format_instructions = "Provide the response in two formats: 🇬🇧 English first, then 🇷🇺 Russian."
    elif mode == "english":
        format_instructions = "Provide the response only in 🇬🇧 English."
    else:
        return "⚠️ Unknown format requested."

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
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"❌ AI Error: {e}"


# --- 4. Telegram Bot Handlers ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # THE ADMIN PATH (For You)
    if str(message.chat.id) == str(AUTHORIZED_USER_ID):
        markup = InlineKeyboardMarkup()
        markup.row_width = 1
        markup.add(
            InlineKeyboardButton("📊 Dry Numbers Only", callback_data="raw_data"),
            InlineKeyboardButton("🇺🇸 AI Report (English)", callback_data="ai_english"),
            InlineKeyboardButton("🌍 AI Report (Bilingual)", callback_data="ai_bilingual")
        )
        welcome_text = "Welcome to Just Another Crypto AI, boss 🐺\nChoose your report format:"
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup)
        
    # THE GUEST PATH (For HR and Recruiters)
    else:
        guest_text = (
            "👋 **Hello! I am the Just Another Crypto AI.**\n\n"
            "I was built by neuro-dotcom as an autonomous AI Ops portfolio project. \n\n"
            "🔒 **Security Lock Active:** To prevent API credit exhaustion, my core LLM generation features are restricted to Admin access only via Role-Based Access Control (RBAC).\n\n"
            "However, my cloud infrastructure is fully operational! You can review my source code, Docker configuration, and CI/CD pipeline on GitHub."
        )
        bot.send_message(message.chat.id, guest_text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    # ✅ GHOST CLEANUP: This runs for YOU (the authorized user)
    try:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            reply_markup=None
        )
    except Exception:
        pass # If buttons are already gone, do nothing
    
    if call.data.startswith("set_"):
        new_time = call.data.split("_")[1]
        save_user_time(new_time)
        update_schedule(new_time)
        bot.answer_callback_query(call.id, f"✅ Time set to {new_time}")
        bot.send_message(call.message.chat.id, f"🚀 **Confirmed!** Your morning report is now scheduled for {new_time} UTC daily.", parse_mode="Markdown")
        return # Stop here so it doesn't try to fetch crypto news!
    
    bot.answer_callback_query(call.id, "Gathering data...")
    bot.send_message(call.message.chat.id, "📡 Fetching market data. Please wait...")

    btc, eth = fetch_crypto_prices()
    fng_val, fng_sent = fetch_fear_and_greed_index()

    if not btc or not eth:
        bot.send_message(call.message.chat.id, "⚠️ API Error: Could not fetch crypto prices from CoinGecko.")
        return

    if not fng_val or not fng_sent:
        fng_val = "N/A"
        fng_sent = "Data Unavailable"

    if call.data == "raw_data":
        report = f"💰 **Raw Market Data:**\nBTC: ${btc}\nETH: ${eth}\nFear & Greed: {fng_val}/100 ({fng_sent})"
        # Removed parse_mode="Markdown" here as well to prevent silent API crashes on bad characters
        bot.send_message(call.message.chat.id, report)
        
    elif call.data == "ai_english":
        report = generate_ai_analysis(btc, eth, fng_val, fng_sent, mode="english")
        bot.send_message(call.message.chat.id, report)
        
    elif call.data == "ai_bilingual":
        report = generate_ai_analysis(btc, eth, fng_val, fng_sent, mode="bilingual")
        bot.send_message(call.message.chat.id, report)

# ==========================================
# --- PROACTIVE AUTOMATION MODULE ---
# ==========================================
def send_morning_report():
    """Automatically fetches data and sends an AI report to the Admin."""
    if not AUTHORIZED_USER_ID:
        return

    print("⏰ Executing scheduled morning report...", flush=True)
    btc, eth = fetch_crypto_prices()
    fng_val, fng_sent = fetch_fear_and_greed_index()

    if btc and eth:
        # Generate the morning AI analysis
        report = generate_ai_analysis(btc, eth, fng_val or "N/A", fng_sent or "N/A", mode="english")
        header = "🌅 **Wolf's Morning Briefing**\n\n"
        bot.send_message(AUTHORIZED_USER_ID, header + report)
    else:
        bot.send_message(AUTHORIZED_USER_ID, "⚠️ Morning routine failed: API Error fetching prices.")

# --- 1. PREFERENCE HELPERS ---
PREFS_FILE = "user_preferences.json"

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

# --- 2. THE SET_TIME COMMAND ---
@bot.message_handler(commands=['set_time'])
def set_time_command(m):
    if str(m.chat.id) != AUTHORIZED_USER_ID: return
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🌅 08:00", callback_data="set_08:00"),
        InlineKeyboardButton("🏙️ 12:00", callback_data="set_12:00")
    )
    markup.row(
        InlineKeyboardButton("🌆 18:00", callback_data="set_18:00"),
        InlineKeyboardButton("🌃 22:00", callback_data="set_22:00")
    )
    bot.reply_to(m, "⏰ **Select your daily briefing time (UTC):**", 
               reply_markup=markup, parse_mode="Markdown")

# --- 3. DYNAMIC SCHEDULER ---
# Initialize the scheduler globally
scheduler = BackgroundScheduler(timezone=pytz.timezone('Europe/Berlin'))

def update_schedule(new_time):
    h, m = map(int, new_time.split(":"))
    # id='daily_briefing' allows us to replace the old job with the new one
    scheduler.add_job(send_morning_report, 'cron', hour=h, minute=m, id='daily_briefing', replace_existing=True)
    print(f"⏱️ Schedule updated to {new_time}", flush=True)

# Start it once at the beginning of the program
scheduler.start()


# --- 5. Dummy Web Server ---
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
        
    def log_message(self, format, *args):
        pass

def start_dummy_server():
    port = int(os.environ.get("PORT", 7860)) 
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    print(f"🌐 Dummy web server running on port {port}", flush=True)
    server.serve_forever()


# --- 6. Main Execution Flow ---
if __name__ == "__main__":
    print("🚀 Starting background processes...", flush=True)
    
    # Start the dummy web server in a parallel thread
    threading.Thread(target=start_dummy_server, daemon=True).start()

    # Start the autonomous scheduler
    start_scheduler()

    bot.remove_webhook()

    print("🤖 Bot is starting... Listening for Telegram messages.", flush=True)
    bot.infinity_polling()