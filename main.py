import os
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from dotenv import load_dotenv

# --- 1. Configuration ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

client = genai.Client(api_key=API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# --- 2. Data Gathering Modules (Unchanged) ---
def fetch_crypto_prices():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data['bitcoin']['usd'], data['ethereum']['usd']
    except requests.RequestException:
        return None, None

def fetch_fear_and_greed_index():
    url = "https://api.alternative.me/fng/?limit=1"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        value = data['data'][0]['value']
        sentiment = data['data'][0]['value_classification']
        return value, sentiment
    except requests.RequestException:
        return None, None

# --- 3. AI Processing Module ---
def generate_ai_analysis(btc, eth, fng_val, fng_sent, mode):
    """Generates analysis based on the user's selected mode."""
    
    # We change the prompt based on what button they clicked
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

# This runs when the user types /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Create the keyboard (buttons)
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        InlineKeyboardButton("📊 Dry Numbers Only", callback_data="raw_data"),
        InlineKeyboardButton("🇺🇸 AI Report (English)", callback_data="ai_english"),
        InlineKeyboardButton("🌍 AI Report (Bilingual)", callback_data="ai_bilingual")
    )
    
    welcome_text = "Welcome to Just Another Crypto AI 🐺\nChoose your report format:"
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

# This runs when the user clicks a button
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    # Inform Telegram we received the click (stops the loading animation on the button)
    bot.answer_callback_query(call.id, "Gathering data...")
    bot.send_message(call.message.chat.id, "📡 Fetching market data. Please wait...")

    btc, eth = fetch_crypto_prices()
    fng_val, fng_sent = fetch_fear_and_greed_index()

    if not all([btc, eth, fng_val, fng_sent]):
        bot.send_message(call.message.chat.id, "⚠️ API Error: Missing data.")
        return

    # Check which button was pressed
    if call.data == "raw_data":
        report = f"💰 **Raw Market Data:**\nBTC: ${btc}\nETH: ${eth}\nFear & Greed: {fng_val}/100 ({fng_sent})"
        bot.send_message(call.message.chat.id, report, parse_mode="Markdown")
        
    elif call.data == "ai_english":
        report = generate_ai_analysis(btc, eth, fng_val, fng_sent, mode="english")
        bot.send_message(call.message.chat.id, report)
        
    elif call.data == "ai_bilingual":
        report = generate_ai_analysis(btc, eth, fng_val, fng_sent, mode="bilingual")
        bot.send_message(call.message.chat.id, report)

# --- 5. Main Execution Flow ---
if __name__ == "__main__":
    print("🤖 Bot is starting... Listening for Telegram messages.")
    # This keeps the script running 24/7 waiting for button clicks
    bot.infinity_polling()