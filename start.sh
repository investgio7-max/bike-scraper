#!/bin/bash

echo "🚀 Starting Bike Scraper on Railway..."
echo "🔧 Using python3"

# Start Telegram Bot
echo "🤖 Starting Telegram Bot in background..."
/usr/local/bin/python3 << 'BOTEOF' &
import asyncio
import os
from bike_scraper.telegram_bot import create_telegram_bot

token = os.getenv('TELEGRAM_BOT_TOKEN')
if token:
    print("✅ Bot token found")
    bot = create_telegram_bot(token)
    asyncio.run(bot.run())
else:
    print("⚠️ No bot token")
BOTEOF

sleep 2

# Start Scheduler
echo "⏰ Starting Scheduler in background..."
/usr/local/bin/python3 << 'SCHEDEOF' &
import sys
from bike_scraper.scheduler import BikeScraperScheduler

print("Starting scheduler...")
try:
    scheduler = BikeScraperScheduler()
    scheduler.run()
except KeyboardInterrupt:
    print("Scheduler stopped")
    sys.exit(0)
except Exception as e:
    print(f"Scheduler error: {e}")
    sys.exit(1)
SCHEDEOF

sleep 2

# Start API
echo "📡 Starting API on port $PORT..."
exec /usr/local/bin/python3 -m uvicorn bike_scraper.api_main:app --host 0.0.0.0 --port $PORT
