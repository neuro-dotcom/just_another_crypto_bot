import os
import requests
from google import genai
from dotenv import load_dotenv

# --- 1. Configuration ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=API_KEY)

# --- 2. Data Gathering Modules ---
def fetch_crypto_prices():
    """Fetches current BTC and ETH prices from CoinGecko."""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data['bitcoin']['usd'], data['ethereum']['usd']
    except requests.RequestException as e:
        print(f"❌ Error fetching prices: {e}")
        return None, None

def fetch_fear_and_greed_index():
    """Fetches the current Crypto Fear & Greed Index."""
    url = "https://api.alternative.me/fng/?limit=1"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        value = data['data'][0]['value']
        sentiment = data['data'][0]['value_classification']
        return value, sentiment
    except requests.RequestException as e:
        print(f"❌ Error fetching F&G Index: {e}")
        return None, None

# --- 3. AI Processing Module ---
def generate_ai_analysis(btc, eth, fng_val, fng_sent):
    """Generates bilingual market analysis using Gemini."""
    prompt = f"""
    You are an expert, slightly sarcastic crypto analyst. 
    Current market snapshot:
    - Bitcoin (BTC): ${btc}
    - Ethereum (ETH): ${eth}
    - Fear & Greed Index: {fng_val}/100 (Sentiment: {fng_sent})

    Write a short, punchy market update (3-4 sentences) explaining what the combination of the current price and the Fear & Greed index means for retail traders right now. 
    
    Provide your response in two formats:
    🇬🇧 English version first.
    🇷🇺 Russian translation second.
    """
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"❌ AI Generation Error: {e}")
        return None

# --- 4. Delivery Module (Telegram) ---
def send_telegram_message(text):
    """Pushes the generated report to your Telegram app."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("✅ Message successfully delivered to Telegram!")
    except requests.RequestException as e:
        print(f"❌ Telegram Delivery Error: {e}")

# --- 5. Main Execution Flow ---
def main():
    print("--- 📡 Fetching market data... ---")
    
    btc_price, eth_price = fetch_crypto_prices()
    fng_value, fng_sentiment = fetch_fear_and_greed_index()

    if not all([btc_price, eth_price, fng_value, fng_sentiment]):
        print("⚠️ Missing data. Aborting analysis to prevent AI hallucinations.")
        return

    print(f"✅ Data secured! BTC: ${btc_price} | ETH: ${eth_price}")
    print("--- 🧠 Passing data to Gemini... ---")

    report = generate_ai_analysis(btc_price, eth_price, fng_value, fng_sentiment)
    
    if report:
        print("--- 📱 Dispatching to Telegram... ---")
        send_telegram_message(report)

if __name__ == "__main__":
    main()