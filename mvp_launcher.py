#!/usr/bin/env python3
"""MVP Launcher: Real deal stream with Telegram alerts"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("mvp_launcher")

# Statistics
stats = {
    "deals_found": 0,
    "deals_rejected": 0,
    "deals_sent": 0,
    "sent_alerts": [],
    "start_time": datetime.now(),
    "last_24h": {}
}

FILTERS = {
    "confidence": 90,
    "comparables": 25,
    "discount_percent": 20,
}

def format_alert_message(deal: Dict) -> str:
    """Format deal as Telegram message"""
    return f"""🚴 {deal.get('bike_name', 'Unknown Bike')}

💰 Price: €{deal.get('asking_price', '?')}
📊 Market: €{deal.get('market_price', '?')}
✅ Discount: {deal.get('discount_percent', 0):.1f}%
📈 Profit: €{deal.get('potential_profit', 0):.0f}
🎯 Confidence: {deal.get('confidence', 0):.0f}%

🔗 {deal.get('listing_url', 'No URL')}
"""

async def send_telegram_alert(deal: Dict) -> bool:
    """Send deal via Telegram API"""
    import httpx

    try:
        chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "-5008721963")
        token = os.getenv("TELEGRAM_BOT_TOKEN")

        if not token:
            logger.warning("TELEGRAM_BOT_TOKEN not set")
            return False

        from telegram import Bot

        bot = Bot(token=token)
        message = await bot.send_message(
            chat_id=chat_id,
            text=format_alert_message(deal)
        )

        logger.info(f"✅ Alert sent: {deal.get('bike_name')} (msg_id: {message.message_id})")
        return True

    except Exception as e:
        logger.error(f"❌ Send failed: {e}")
        return False

def apply_filters(deal: Dict) -> bool:
    """Check if deal passes all filters"""

    # Confidence filter
    confidence = deal.get("confidence", 0)
    if confidence < FILTERS["confidence"]:
        return False

    # Comparables filter
    comparables = deal.get("comparables", 0)
    if comparables < FILTERS["comparables"]:
        return False

    # Discount filter
    discount = deal.get("discount_percent", 0)
    if discount < FILTERS["discount_percent"]:
        return False

    return True

async def run_mvp_launcher():
    """Main MVP launcher"""

    logger.info("=" * 60)
    logger.info("🚀 MVP LAUNCHER STARTED")
    logger.info("=" * 60)
    logger.info(f"Filters: confidence>={FILTERS['confidence']}%, comparables>={FILTERS['comparables']}, discount>={FILTERS['discount_percent']}%")
    logger.info("=" * 60)

    try:
        # Import scraper and analyzers
        from bike_scraper.scraper_wallapop import WallapopScraper
        from bike_scraper.price_analyzer import PriceAnalyzer
        from bike_scraper.ai_bike_parser import AIBikeParser

        logger.info("✅ Modules imported")

        # Initialize
        scraper = WallapopScraper()
        analyzer = PriceAnalyzer()
        parser = AIBikeParser()

        logger.info("✅ Services initialized")
        logger.info(f"📍 Starting search for high-confidence deals...")
        logger.info("")

        # Search Wallapop
        listings = await scraper.search(max_results=50)

        if not listings:
            logger.warning("⚠️ No listings found")
            return

        logger.info(f"📋 Found {len(listings)} listings")

        # Process each listing
        for listing in listings:
            try:
                # Parse bike
                bike_analysis = parser.parse(listing)

                if not bike_analysis:
                    stats["deals_rejected"] += 1
                    continue

                # Analyze price
                market_analysis = analyzer.analyze(bike_analysis)

                if not market_analysis:
                    stats["deals_rejected"] += 1
                    continue

                # Build deal object
                deal = {
                    "bike_name": bike_analysis.get("model", "Unknown"),
                    "asking_price": listing.get("price"),
                    "market_price": market_analysis.get("estimated_price"),
                    "discount_percent": market_analysis.get("discount_percent", 0),
                    "potential_profit": market_analysis.get("profit_potential", 0),
                    "confidence": market_analysis.get("confidence", 0),
                    "comparables": market_analysis.get("comparables", 0),
                    "listing_url": listing.get("url"),
                }

                stats["deals_found"] += 1

                # Apply filters
                if not apply_filters(deal):
                    stats["deals_rejected"] += 1
                    logger.debug(f"❌ Rejected: {deal['bike_name']} (conf:{deal['confidence']}%, disc:{deal['discount_percent']}%)")
                    continue

                # Send alert
                sent = await send_telegram_alert(deal)
                if sent:
                    stats["deals_sent"] += 1
                    stats["sent_alerts"].append({
                        "bike": deal["bike_name"],
                        "timestamp": datetime.now().isoformat(),
                        "price": deal["asking_price"],
                        "discount": deal["discount_percent"],
                    })

            except Exception as e:
                logger.error(f"Error processing listing: {e}")
                continue

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()

    # Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 SUMMARY")
    logger.info("=" * 60)
    logger.info(f"⏱️  Duration: {(datetime.now() - stats['start_time']).total_seconds():.1f}s")
    logger.info(f"📈 Deals Found: {stats['deals_found']}")
    logger.info(f"❌ Deals Rejected: {stats['deals_rejected']}")
    logger.info(f"✅ Alerts Sent: {stats['deals_sent']}")

    if stats['sent_alerts']:
        logger.info("")
        logger.info("📲 Last Sent Alerts:")
        for alert in stats['sent_alerts'][-10:]:
            logger.info(f"   • {alert['bike']} - €{alert['price']} ({alert['discount']:.1f}% discount)")

    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_mvp_launcher())
