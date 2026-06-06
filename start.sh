#!/bin/bash

echo "🚀 Starting Bike Scraper on Railway..."
echo "🔧 Using python3"

# Start Telegram Bot in background with logging
echo "🤖 Starting Telegram Bot in background..."
/usr/local/bin/python3 run_bot.py > /tmp/bot.log 2>&1 &
BOT_PID=$!
echo "Bot PID: $BOT_PID"

sleep 2

# Start Scheduler in background with logging
echo "⏰ Starting Scheduler in background..."
/usr/local/bin/python3 << 'SCHEDEOF' > /tmp/scheduler.log 2>&1 &
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
    import traceback
    traceback.print_exc()
    sys.exit(1)
SCHEDEOF

sleep 2

# Show logs
echo "📡 Starting API on port $PORT..."
echo ""
echo "Logs:"
echo "  Bot: tail -f /tmp/bot.log"
echo "  Scheduler: tail -f /tmp/scheduler.log"
echo ""

# Start API in foreground
exec /usr/local/bin/python3 -m uvicorn bike_scraper.api_main:app --host 0.0.0.0 --port $PORT
