#!/usr/bin/env python3
"""Run both Telegram bot and FastAPI server"""
import sys
import threading
from time import sleep

print("🚀 Starting combined bot+API process...")

# Start FastAPI in background thread
def run_api():
    """Run FastAPI server in background"""
    import os
    print("📡 Starting FastAPI server in background thread...")
    try:
        from bike_scraper.api_main import app
        from bike_scraper.config import API_HOST, API_PORT
        import uvicorn
        print("✅ Imported FastAPI app")
        print(f"🌐 Starting uvicorn on {API_HOST}:{API_PORT}...")
        uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")
    except Exception as e:
        print(f"❌ FastAPI error: {e}")
        import traceback
        traceback.print_exc()

# Start API in background thread
api_thread = threading.Thread(target=run_api, daemon=False)
api_thread.start()
print("✅ FastAPI thread started (daemon=False)")

# Give API time to start
sleep(3)

# Run Telegram bot in main thread
print("🤖 Starting Telegram bot in main thread...")
try:
    from bike_scraper.telegram_bot_final import main
    print("✅ Imported bot")
    print("📞 Running bot polling...")
    main()
except Exception as e:
    print(f"❌ Bot error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
