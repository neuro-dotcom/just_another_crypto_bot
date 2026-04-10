import os
import json
import threading
import requests
import pytz
import telebot
import time  # <-- Using for the extended backoff buffer
from http.server import BaseHTTPRequestHandler, HTTPServer
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from groq import Groq
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

# ==========================================
# 1. CONFIGURATION
# ==========================================
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AUTHORIZED_USER_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

client = genai.Client(api_key=API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)
scheduler = BackgroundScheduler()
PREFS_FILE = "user_preferences.json"

if AUTHORIZED_USER_ID:
    try:
        bot.send_message(AUTHORIZED_USER_ID, "🚀 Just Another Crypto AI is officially ONLINE!")
    except Exception: pass

# ==========================================
# 2. STATE MANAGEMENT
# ==========================================
def get_user_prefs():
    if os.path.exists(PREFS_FILE):
        with open(PREFS_FILE, 'r') as f:
            prefs = json.load(f)
            user_data = prefs.get(AUTHORIZED_USER_ID, {})
            return user_data.get("time", "08:00"), user_data.get("tz_offset", 0)
    return "08:00", 0

def save_user_pref(key, value):
    prefs = {}
    if os.path.exists(PREFS_FILE):
        with open(PREFS_FILE, 'r') as f: prefs = json.load(f)
    if AUTHORIZED_USER_ID not in prefs:
        prefs[AUTHORIZED_USER_ID] = {"time": "08:00", "tz_offset": 0}
    prefs[AUTHORIZED_USER_ID][key] = value
    with open(PREFS_FILE, 'w') as f: json.dump(prefs, f)

# ==========================================
# 3. DATA & AI MODULES (PATCHED EXTENDED BACKOFF)
# ==========================================
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_data():
    try:
        r1 = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd", headers=HEADERS, timeout=10)
        r2 = requests.get("https://api.alternative.me/fng/?limit=1", headers=HEADERS, timeout=10)
        r1.raise_for_status(); r2.raise_for_status()
        
        d1, d2 = r1.json(), r2.json()
        return (float(d1['bitcoin']['usd']), float(d1['ethereum']['usd']), 
                d2['data'][0]['value'], d2['data'][0]['value_classification'])
    except Exception as e:
        print(f"API Error: {e}")
        return None, None, None, None

def generate_report(mode):
    btc, eth, fng_val, fng_sent = fetch_data()
    if not btc: return "⚠️ API Error: Could not fetch market data."
    
    if mode == "raw":
        return f"💰 **Raw Data:**\nBTC: ${btc}\nETH: ${eth}\nF&G: {fng_val}/100 ({fng_sent})"

    fmt = "Provide response only in 🇬🇧 English." if mode == "english" else "Provide response: 🇬🇧 English first, then 🇷🇺 Russian."
    prompt = f"Expert crypto update. BTC: ${btc}, ETH: ${eth}, F&G: {fng_val}/100 ({fng_sent}). 3-4 sentences. {fmt}"
    
    # 1. Primary Engine: Google Gemini
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(model="gemini-2.0-flash", contents=prompt).text
        except Exception as e:
            error_message = str(e)
            if "503" in error_message or "UNAVAILABLE" in error_message or "429" in error_message or "Quota" in error_message:
                if attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1)
                    print(f"⚠️ Gemini busy. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print("❌ Gemini failed completely. Initiating Groq Failover...")
                    break # Break the loop to trigger failover
            else:
                print(f"Critical AI Error: {error_message}")
                break # Break the loop to trigger failover

    # 2. Fallback Engine: Groq (Llama 3 8B)
    if groq_client:
        try:
            print("🚀 Routing request to Groq...")
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-8b-8192",
            )
            return chat_completion.choices[0].message.content
        except Exception as groq_e:
            print(f"❌ Groq Failover Error: {groq_e}")
            return "🤖 Both primary and backup AI networks are currently unavailable."
    
    return "🤖 AI network offline. Please try again later."

# ==========================================
# 4. SCHEDULER & AUTOMATION
# ==========================================
def get_main_menu_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📊 Raw Data", callback_data="run_raw"),
        InlineKeyboardButton("🇺🇸 AI (English)", callback_data="run_english"),
        InlineKeyboardButton("🌍 AI (Bilingual)", callback_data="run_bilingual"),
        InlineKeyboardButton("⚙️ Settings", callback_data="nav_settings")
    )
    return markup

def send_morning_report():
    if not AUTHORIZED_USER_ID: return
    report = generate_report("english")
    bot.send_message(AUTHORIZED_USER_ID, f"🌅 **Morning Briefing**\n\n{report}", reply_markup=get_main_menu_markup())

def update_schedule():
    saved_time, tz_offset = get_user_prefs()
    h, m = map(int, saved_time.split(":"))
    custom_tz = pytz.FixedOffset(tz_offset * 60)
    scheduler.add_job(send_morning_report, 'cron', hour=h, minute=m, timezone=custom_tz, id='daily', replace_existing=True)

# ==========================================
# 5. UI & TELEGRAM ROUTING
# ==========================================
@bot.message_handler(func=lambda msg: str(msg.chat.id) != AUTHORIZED_USER_ID)
def block_strangers(msg): bot.reply_to(msg, "⛔ Access Denied.")

@bot.message_handler(commands=['start'])
def send_welcome(m):
    bot.send_message(m.chat.id, "🐺 **Wolf AI Control Panel**", reply_markup=get_main_menu_markup(), parse_mode="Markdown")

# --- NEW: MANUAL TEST COMMAND ---
@bot.message_handler(commands=['test_briefing'])
def test_briefing_cmd(m):
    bot.send_message(m.chat.id, "🛠️ Forcing Morning Briefing execution for testing...")
    send_morning_report()

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    saved_time, tz_offset = get_user_prefs()

    if call.data == "nav_settings":
        sign = "+" if tz_offset >= 0 else ""
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton(f"⏰ Time ({saved_time})", callback_data="nav_time"),
            InlineKeyboardButton(f"🌍 TZ (UTC{sign}{tz_offset})", callback_data="nav_tz"),
            InlineKeyboardButton("🔙 Back to Main", callback_data="nav_main")
        )
        bot.edit_message_text("⚙️ **Settings Menu**", chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")
        return

    if call.data == "nav_time":
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("08:00", callback_data="set_time_08:00"), InlineKeyboardButton("12:00", callback_data="set_time_12:00"))
        markup.row(InlineKeyboardButton("18:00", callback_data="set_time_18:00"), InlineKeyboardButton("22:00", callback_data="set_time_22:00"))
        markup.add(InlineKeyboardButton("🔙 Back", callback_data="nav_settings"))
        bot.edit_message_text("⏰ **Select Briefing Time:**", chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")
        return

    if call.data == "nav_tz":
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("-8", callback_data="set_tz_-8"), InlineKeyboardButton("-5", callback_data="set_tz_-5"), InlineKeyboardButton("-3", callback_data="set_tz_-3"))
        markup.row(InlineKeyboardButton("UTC", callback_data="set_tz_0"), InlineKeyboardButton("+3", callback_data="set_tz_3"), InlineKeyboardButton("+5", callback_data="set_tz_5"))
        markup.add(InlineKeyboardButton("🔙 Back", callback_data="nav_settings"))
        bot.edit_message_text("🌍 **Select UTC Offset:**", chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")
        return

    if call.data == "nav_main":
        bot.edit_message_text("🐺 **Wolf AI Control Panel**", chat_id, msg_id, reply_markup=get_main_menu_markup(), parse_mode="Markdown")
        return

    if call.data.startswith("set_time_"):
        save_user_pref("time", call.data.split("_")[2])
        update_schedule()
        handle_query(telebot.types.CallbackQuery(call.id, call.from_user, call.data, call.chat_instance, call.message, data="nav_settings"))
        return

    if call.data.startswith("set_tz_"):
        save_user_pref("tz_offset", int(call.data.split("_")[2]))
        update_schedule()
        handle_query(telebot.types.CallbackQuery(call.id, call.from_user, call.data, call.chat_instance, call.message, data="nav_settings"))
        return

    if call.data.startswith("run_"):
        bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=None) 
        bot.send_message(chat_id, "📡 Fetching market data...")
        
        mode = call.data.split("_")[1]
        report = generate_report(mode)
        
        bot.send_message(chat_id, report, reply_markup=get_main_menu_markup(), parse_mode="Markdown")

# ==========================================
# 6. INFRASTRUCTURE & MAIN
# ==========================================
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header('Content-type', 'text/plain'); self.end_headers()
        self.wfile.write(b"Bot is alive!")
    def log_message(self, format, *args): pass

if __name__ == "__main__":
    threading.Thread(target=lambda: HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 7860))), DummyHandler).serve_forever(), daemon=True).start()
    update_schedule()
    scheduler.start()
    bot.remove_webhook()
    print("🤖 Operations Normal. Listening...", flush=True)
    bot.infinity_polling()