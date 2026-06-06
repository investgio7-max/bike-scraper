#!/usr/bin/env python3
"""Run Telegram bot"""
import asyncio
import os
import sys
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("🤖 Starting bot process...")

try:
    print("📦 Importing create_telegram_bot...")
    from bike_scraper.telegram_bot import create_telegram_bot

    print("🔑 Checking token...")
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        sys.exit(1)

    print(f"✅ Bot token found: {token[:20]}...")
    print("🏗️ Creating bot instance...")
    bot = create_telegram_bot(token)

    print("🚀 Running bot.run()...")
    asyncio.run(bot.run())

except Exception as e:
    print(f"❌ Bot error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
