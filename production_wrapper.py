#!/usr/bin/env python3
"""
PRODUCTION WRAPPER
Integrates production_scheduler with FastAPI for Railway deployment
Maintains API availability while 24/7 scheduler runs in background
"""

import os
import sys
import asyncio
import logging
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("production_wrapper")

# Import production components
from production_scheduler import ProductionScheduler
from bike_scraper.database import get_db

# FastAPI app
app = FastAPI(title="Bike Scraper Production")

# Global production scheduler instance
production_scheduler = None
scheduler_task = None

@app.on_event("startup")
async def startup_event():
    """Start production scheduler on API startup"""
    global production_scheduler, scheduler_task

    logger.info("\n" + "="*70)
    logger.info("🚀 PRODUCTION MODE INITIALIZATION")
    logger.info("="*70 + "\n")

    production_scheduler = ProductionScheduler()

    # Start scheduler in background
    scheduler_task = asyncio.create_task(production_scheduler.run_24_7())

    logger.info("\n✅ Production scheduler started in background\n")

@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shutdown scheduler"""
    global production_scheduler, scheduler_task

    if production_scheduler:
        production_scheduler.status["production_started"] = False

    if scheduler_task:
        scheduler_task.cancel()

    logger.info("\n✅ Production mode shutdown complete\n")

@app.get("/health")
async def health_check():
    """Production health check endpoint"""
    global production_scheduler

    if not production_scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "production_started": production_scheduler.status["production_started"],
        "monitoring_enabled": production_scheduler.status["monitoring_enabled"],
        "safe_mode": production_scheduler.status["safe_mode"],
        "safe_mode_reason": production_scheduler.status["safe_mode_reason"],
        "total_listings_processed": production_scheduler.stats["total_listings"],
        "total_alerts_sent": production_scheduler.stats["total_alerts"],
    }

@app.get("/production/status")
async def production_status():
    """Get detailed production status"""
    global production_scheduler

    if not production_scheduler:
        return {"error": "Scheduler not initialized"}

    return {
        "status": "healthy" if not production_scheduler.status["safe_mode"] else "safe_mode",
        "production": {
            "started": production_scheduler.status["production_started"],
            "monitoring_enabled": production_scheduler.status["monitoring_enabled"],
            "safe_mode": production_scheduler.status["safe_mode"],
            "safe_mode_reason": production_scheduler.status["safe_mode_reason"],
        },
        "statistics": {
            "total_listings": production_scheduler.stats["total_listings"],
            "total_parsed": production_scheduler.stats["total_parsed"],
            "total_deals": production_scheduler.stats["total_deals"],
            "total_alerts": production_scheduler.stats["total_alerts"],
            "total_rejected": production_scheduler.stats["total_rejected"],
        },
        "circuit_breaker": {
            "telegram_errors": production_scheduler.circuit_breaker["telegram_errors"],
            "wallapop_empty": production_scheduler.circuit_breaker["wallapop_empty"],
            "database_errors": production_scheduler.circuit_breaker["database_errors"],
            "threshold": production_scheduler.circuit_breaker["threshold"],
        },
        "timestamp": datetime.now().isoformat(),
    }

@app.get("/production/logs")
async def production_logs():
    """Get last 100 log lines"""
    log_file = "/tmp/production_logs/production_{}.log".format(
        datetime.now().strftime('%Y%m%d')
    )

    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()

        # Return last 100 lines
        last_lines = lines[-100:] if len(lines) > 100 else lines

        return {
            "log_file": log_file,
            "line_count": len(last_lines),
            "lines": [line.rstrip() for line in last_lines]
        }
    except FileNotFoundError:
        return {
            "error": "Log file not found yet",
            "expected_path": log_file
        }

@app.get("/production/daily-reports")
async def production_reports():
    """Get all daily reports"""
    global production_scheduler

    if not production_scheduler:
        return {"error": "Scheduler not initialized"}

    return {
        "total_reports": len(production_scheduler.daily_reports),
        "reports": production_scheduler.daily_reports
    }

@app.post("/test-alert")
async def send_test_alert(db: Session = Depends(get_db)):
    """Send test deal alert to Telegram (smoke test)

    Verifies that Telegram alert system is working correctly.
    Returns message_id and chat_id for verification.
    """
    try:
        from bike_scraper.telegram_alerts import TelegramAlertService, DealAlert
        from telegram import Bot

        # Get Telegram credentials
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if not bot_token or not chat_id:
            raise HTTPException(
                status_code=400,
                detail="TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured"
            )

        # Create test deal alert
        test_deal = DealAlert(
            listing_id="test_deal_api",
            bike_name="Canyon Aeroad CF SLX 8 Di2 2022",
            asking_price=2900,
            market_price=4200,
            discount_percent=30.95,
            profit_potential=1300,
            size="M",
            groupset="Ultegra Di2",
            year=2022,
            confidence=95.0,
            comparable_count=37,
            listing_url="https://example.com/test-bike",
            deal_grade="A-Tier"
        )

        # Send via Telegram Bot API
        bot = Bot(token=bot_token)
        alert_service = TelegramAlertService(
            bot_token=bot_token,
            chat_id=chat_id,
            db_session=db
        )

        message_text = alert_service._build_message(test_deal)
        keyboard = alert_service._build_keyboard(test_deal)

        message = await bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        logger.info(f"✅ Test alert sent: message_id={message.message_id}")

        return {
            "status": "success",
            "message": "test alert sent to Telegram",
            "chat_id": message.chat_id,
            "message_id": message.message_id,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to send test alert: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send test alert: {str(e)}"
        )

def run_with_scheduler():
    """Run FastAPI + production scheduler together"""
    import uvicorn

    port = int(os.getenv('PORT', 8080))

    logger.info(f"\n🚀 Starting FastAPI on port {port}...")
    logger.info(f"Health check: http://localhost:{port}/health")
    logger.info(f"Status: http://localhost:{port}/production/status\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    try:
        run_with_scheduler()
    except KeyboardInterrupt:
        logger.info("\n✅ Server shutdown")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
