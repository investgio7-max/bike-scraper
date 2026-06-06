#!/usr/bin/env python3
"""Run Telegram bot"""
import sys

print("🤖 Starting bot process...")

try:
    from bike_scraper.telegram_bot_menu import main
    print("✅ Imported bot")
    print("🚀 Running bot...")
    main()
except Exception as e:
    print(f"❌ Bot error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
