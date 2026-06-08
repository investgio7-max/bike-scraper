#!/usr/bin/env python3
"""Run FastAPI with Telegram bot as background thread"""
import threading
from bike_scraper.api_main import app
from bike_scraper.config import API_HOST, API_PORT
import uvicorn

print(f"🚀 Starting on {API_HOST}:{API_PORT}")

def run_telegram_bot():
    """Run Telegram bot in background thread"""
    print("📞 Starting Telegram bot...")
    try:
        from bike_scraper.telegram_bot_final import main
        main()
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        import traceback
        traceback.print_exc()

# Start Telegram bot in daemon thread
bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
bot_thread.start()
print("✅ Telegram thread started")

# Run FastAPI
print(f"🌐 Starting FastAPI on {API_HOST}:{API_PORT}")
uvicorn.run(
    app,
    host=API_HOST,
    port=API_PORT,
    log_level="info"
)
