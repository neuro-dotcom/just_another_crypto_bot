import os
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from dotenv import load_dotenv

# NEW: Built-in libraries for our dummy web server
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- 1. Configuration ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

client = genai.Client(api_key=API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Send a proactive notification on startup
MY_ID = os.getenv("TELEGRAM_CHAT_ID")
if MY_ID:
    bot.send_message(MY_ID, "🚀 Just Another Crypto AI is officially ONLINE on Hugging Face!")

# --- THE LOCKDOWN STARTS HERE ---
@bot.message_handler(func=lambda message: str(message.chat.id) != MY_ID_ID)
def block_strangers(message):
    """Intercepts every message from anyone who isn't YOU."""
    unauthorized_msg = "⛔ **Access Denied.** This is a private Wolf-class AI instance."
    bot.reply_to(message, unauthorized_msg, parse_mode="Markdown")
    print(f"🛡️ Security Alert: Unauthorized access attempt from {message.chat.id}")
# --- THE LOCKDOWN ENDS HERE ---


# --- 2. Data Gathering Modules ---
# We add a fake User-Agent so APIs don't block us for acting like a server bot
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_crypto_prices():
    try:
        # Switched to CoinGecko: No US geoblocking!
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
        
        # We reuse the HEADERS defined above so CoinGecko knows we are a friendly bot
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # CoinGecko returns: {"bitcoin": {"usd": 50000}, "ethereum": {"usd": 3000}}
        btc_price = float(data['bitcoin']['usd'])
        eth_price = float(data['ethereum']['usd'])
        
        return btc_price, eth_price
    except requests.RequestException as e:
        print(f"❌ CoinGecko API Error: {e}")
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
        print(f"❌ Fear & Greed API Error: {e}")
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
            model="gemini-3-flash-preview",
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"❌ AI Error: {e}"

# --- 4. Telegram Bot Handlers ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        InlineKeyboardButton("📊 Dry Numbers Only", callback_data="raw_data"),
        InlineKeyboardButton("🇺🇸 AI Report (English)", callback_data="ai_english"),
        InlineKeyboardButton("🌍 AI Report (Bilingual)", callback_data="ai_bilingual")
    )
    welcome_text = "Welcome to Just Another Crypto AI 🐺\nChoose your report format:"
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    bot.answer_callback_query(call.id, "Gathering data...")
    bot.send_message(call.message.chat.id, "📡 Fetching market data. Please wait...")

    # Fetch the data
    btc, eth = fetch_crypto_prices()
    fng_val, fng_sent = fetch_fear_and_greed_index()

    # CRITICAL FIX: Only fail if the prices (BTC/ETH) fail. 
    if not btc or not eth:
        bot.send_message(call.message.chat.id, "⚠️ API Error: Could not fetch crypto prices from CoinGecko.")
        return

    # Resilient Fix: If Fear & Greed fails, use a fallback instead of crashing
    if not fng_val or not fng_sent:
        fng_val = "N/A"
        fng_sent = "Data Unavailable"

    # Route the request based on the button clicked
    if call.data == "raw_data":
        report = f"💰 **Raw Market Data:**\nBTC: ${btc}\nETH: ${eth}\nFear & Greed: {fng_val}/100 ({fng_sent})"
        bot.send_message(call.message.chat.id, report, parse_mode="Markdown")
        
    elif call.data == "ai_english":
        report = generate_ai_analysis(btc, eth, fng_val, fng_sent, mode="english")
        bot.send_message(call.message.chat.id, report)
        
    elif call.data == "ai_bilingual":
        report = generate_ai_analysis(btc, eth, fng_val, fng_sent, mode="bilingual")
        bot.send_message(call.message.chat.id, report)

# --- 5. Dummy Web Server (The Render Fix) ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")
        
    def log_message(self, format, *args):
        pass # Suppress standard HTTP server logs to keep terminal clean

def start_dummy_server():
    # Hugging Face and most platforms use the PORT env var
    port = int(os.environ.get("PORT", 7860)) 
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    print(f"🌐 Dummy web server running on port {port}", flush=True)
    server.serve_forever()

# --- 6. Main Execution Flow ---
if __name__ == "__main__":
    print("🚀 Starting background processes...")
    
    # Start the dummy web server in a parallel thread so it doesn't block the bot
    threading.Thread(target=start_dummy_server, daemon=True).start()

    # ADD THIS LINE: This forces Telegram to sever any weird phantom connections
    bot.remove_webhook()

    print("🤖 Bot is starting... Listening for Telegram messages.")
    bot.infinity_polling()