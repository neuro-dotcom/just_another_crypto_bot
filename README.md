---
title: Just Another Crypto AI
emoji: 🐺
colorFrom: gray
colorTo: blue
sdk: docker
pinned: false
---

# 🐺 Just Another Crypto AI Bot (AI Ops Portfolio Project)

An autonomous, bilingual AI agent that aggregates real-time cryptocurrency market data and generates professional sentiment analysis using **Google Gemini 3 Flash**.

---

## 🚀 Overview
This bot provides a seamless bridge between raw market data and actionable human insights. It targets retail traders by synthesizing price action with market sentiment (Fear & Greed Index) to deliver "no-nonsense" market updates. 

### ✨ Key Features
* **Real-time Data Aggregation:** Fetches live BTC/ETH prices via CoinGecko API.
* **Sentiment Analysis:** Integrates the Crypto Fear & Greed Index to provide market context.
* **AI-Powered Insights:** Uses **Gemini 3 Flash Preview** to generate sarcastic, professional, and punchy market reports.
* **Bilingual Support:** Full English (🇬🇧) and Russian (🇷🇺) output.
* **Proactive Automation:** Integrated `APScheduler` for timezone-aware (Europe/Berlin) proactive morning market briefings.
* **Portfolio Showcase Mode:** Features a public "Guest Path" that allows recruiters and engineering leads to verify the bot's live status and infrastructure without consuming private API credits.

---

## 🛠️ Architecture & Ops Integrations
* **Infrastructure:** Containerized via Docker and fully deployed on **Hugging Face Spaces**.
* **CI/CD:** Automated zero-touch deployment pipeline via **GitHub Actions**.
* **Hardened Security:** Strictly enforced Role-Based Access Control (RBAC) to prevent unauthorized Callback Query bypasses and API exhaustion.
* **Resilience:** Integrated HTTP health-check server with full `HEAD` request support, paired with UptimeRobot to bypass platform sleep cycles and maintain 100% uptime.

---

## 🧰 Tech Stack
* **Language:** Python 3.11+
* **LLM:** Google Gemini API (via `google-genai` SDK)
* **APIs:** Telegram Bot API (`pyTelegramBotAPI`), CoinGecko, Alternative.me
* **DevOps:** Git, GitHub Actions, Docker

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
neuro-dotcom 
AI Operations & Automation Engineer 
"Building the intersection of AI and Finance."