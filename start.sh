#!/bin/bash

echo "🚀 Starting Bike Scraper on Railway..."
echo "✅ Dependencies already installed by Railway"
echo "🔧 Using python3 for all processes"

# Start Telegram bot in background
python3 << 'EOF' &
import asyncio
from bike_scraper.telegram_bot import create_telegram_bot
import os

print("🤖 Starting Telegram Bot...")
try:
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if token:
        bot = create_telegram_bot(token)
        asyncio.run(bot.run())
    else:
        print("⚠️  TELEGRAM_BOT_TOKEN not set, skipping bot")
except Exception as e:
    print(f"❌ Bot error: {e}")
EOF

# Start scheduler in background
python3 << 'EOF' &
import time
import sys
from bike_scraper.scheduler import BikeScraperScheduler

print("⏰ Starting Scheduler...")
try:
    scheduler = BikeScraperScheduler()
    scheduler.run()
except KeyboardInterrupt:
    print("Scheduler stopped")
    sys.exit(0)
except Exception as e:
    print(f"Scheduler error: {e}")
    sys.exit(1)
EOF

# Run API in foreground (this is what Railway waits for)
echo "📡 Starting API on port $PORT..."
exec python3 -m uvicorn bike_scraper.api_main:app --host 0.0.0.0 --port $PORT
