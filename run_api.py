#!/usr/bin/env python3
"""Run FastAPI with Telegram bot as background worker"""
import sys
import threading

print("🚀 Starting FastAPI with Telegram bot...")

def run_telegram_bot():
    """Run Telegram bot in background thread"""
    print("📞 Starting Telegram bot in background thread...")
    try:
        from bike_scraper.telegram_bot_final import main
        print("✅ Imported Telegram bot")
        main()
    except Exception as e:
        print(f"❌ Telegram bot error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    from bike_scraper.api_main import app
    from bike_scraper.config import API_HOST, API_PORT
    import uvicorn

    print("⚙️  Starting Telegram bot in background thread...")
    # Start Telegram bot in background thread
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    print("✅ Telegram bot thread started")

    print(f"🌐 Starting FastAPI on {API_HOST}:{API_PORT}...")
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        log_level="info",
        access_log=True
    )
