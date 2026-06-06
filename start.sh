#!/bin/bash

echo "🚀 Starting Bike Scraper on Railway... (v3)"
echo "🔧 Using python3"
echo "📍 Working directory: $(pwd)"

# Kill any existing bot processes (avoid conflicts)
echo "🔪 Killing old bot processes..."
# Use precise killing - find PID and kill only that process
PIDS=$(pgrep -f "run_bot.py" || true)
if [ ! -z "$PIDS" ]; then
    echo "Found old bot PID(s): $PIDS, killing..."
    kill -9 $PIDS || true
    sleep 1
fi

# Double check with ps
ps aux | grep "run_bot" | grep -v grep || echo "No old processes found"
sleep 1

echo "📄 Files present:"
ls -la run_bot.py 2>&1 || echo "❌ run_bot.py not found!"

# Start Telegram Bot in background with logging to console
echo "🤖 Starting Telegram Bot in background..."
if [ -f run_bot.py ]; then
    /usr/local/bin/python3 run_bot.py 2>&1 &
    BOT_PID=$!
    echo "✅ Bot PID: $BOT_PID"
    sleep 1
    if ps -p $BOT_PID > /dev/null; then
        echo "✅ Bot process is running"
    else
        echo "❌ Bot process failed to start"
    fi
else
    echo "❌ run_bot.py not found!"
fi

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
