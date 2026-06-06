#!/bin/bash

echo "🚀 Starting Bike Scraper on Railway..."

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

# Initialize database
echo "💾 Initializing database..."
python3 bike_scraper/init_project.py

# Start the application
echo "✨ Starting FastAPI + Scheduler..."
python3 << 'PYTHON_END'
import os
import sys

# Start API and Scheduler
import subprocess
import threading
import time

def start_api():
    print("🌐 Starting FastAPI API on port 3000...")
    os.system('python3 -m uvicorn bike_scraper.api_main:app --host 0.0.0.0 --port 3000')

def start_scheduler():
    print("⏰ Starting Scheduler (every 10 minutes)...")
    time.sleep(5)  # Give API time to start
    from bike_scraper.scheduler import BikeScraperScheduler
    try:
        scheduler = BikeScraperScheduler()
        scheduler.run()
    except Exception as e:
        print(f"Scheduler error: {e}")

api_thread = threading.Thread(target=start_api, daemon=False)
scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)

api_thread.start()
scheduler_thread.start()

# Keep running
try:
    api_thread.join()
except KeyboardInterrupt:
    print("\n⏹️ Shutting down...")
PYTHON_END
