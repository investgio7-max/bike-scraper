#!/bin/bash

echo "🚀 Starting Bike Scraper on Railway..."

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Initialize database
echo "💾 Initializing database..."
python bike_scraper/init_project.py

# Start the application
echo "✨ Starting FastAPI + Scheduler..."
python << 'PYTHON_END'
import os
import sys
sys.path.insert(0, '/app')

# Start API in background
import subprocess
import threading

def start_api():
    os.system('python -m uvicorn bike_scraper.api_main:app --host 0.0.0.0 --port 3000')

# Start scheduler in background
def start_scheduler():
    from bike_scraper.scheduler import BikeScraperScheduler
    scheduler = BikeScraperScheduler()
    scheduler.run()

api_thread = threading.Thread(target=start_api, daemon=True)
scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)

api_thread.start()
scheduler_thread.start()

# Keep running
api_thread.join()
scheduler_thread.join()
PYTHON_END
