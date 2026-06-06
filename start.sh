#!/bin/bash

echo "🚀 Starting Bike Scraper on Railway..."
echo "✅ Dependencies already installed by Railway"

# Start scheduler in background
python << 'EOF' &
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
exec python -m uvicorn bike_scraper.api_main:app --host 0.0.0.0 --port $PORT
