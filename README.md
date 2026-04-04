# 🐺 Just Another Crypto AI Bot

An autonomous, bilingual AI agent that aggregates real-time cryptocurrency market data and generates professional sentiment analysis using **Google Gemini 3 Flash**.

---

## 🚀 Overview
This bot provides a seamless bridge between raw market data and actionable human insights. It targets retail traders by synthesizing price action with market sentiment (Fear & Greed Index) to deliver "no-nonsense" market updates.

### ✨ Key Features
* **Real-time Data Aggregation:** Fetches live BTC/ETH prices via CoinGecko API.
* **Sentiment Analysis:** Integrates the Crypto Fear & Greed Index to provide market context.
* **AI-Powered Insights:** Uses **Gemini 3 Flash Preview** to generate sarcastic, professional, and punchy market reports.
* **Bilingual Support:** Full English (🇬🇧) and Russian (🇷🇺) output.
* **Interactive UI:** Telegram Inline Keyboards for a smooth user experience.
* **Cloud Native:** Fully deployed on **Render** with a CI/CD pipeline.

---

## 🛠️ Tech Stack
* **Language:** Python 3.12+
* **LLM:** Google Gemini 3 Flash (via `google-genai` SDK)
* **APIs:** Telegram Bot API, CoinGecko, Alternative.me
* **Infrastructure:** Git, GitHub, Render (Cloud Hosting)
* **Architecture:** Modular, functional programming with integrated health-check dummy server for cloud port-binding.

---

## 🔧 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/neuro-dotcom/just_another_crypto_bot.git](https://github.com/neuro-dotcom/just_another_crypto_bot.git)
   cd just_another_crypto_bot

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt

3. **Configure Environment Variables:**

   Create a .env file in the root directory:
   ```bash
   GOOGLE_API_KEY=your_gemini_key
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id

4. **Run the bot:**   
   ```bash
   python main.py

👨‍💻 Author
neuro-dotcom AI Operations & Automation Engineer "Building the intersection of AI and Finance."

---