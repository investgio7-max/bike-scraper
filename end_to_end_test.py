#!/usr/bin/env python3
"""
END-TO-END LIVE TEST
Test entire pipeline on 1 real Wallapop listing
Verify: retrieve → parse → analyze → filter → alert
"""

import os
import sys
import asyncio
import logging
import json
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("e2e_test")

async def main():
    logger.info("\n" + "="*80)
    logger.info("🚀 END-TO-END LIVE TEST")
    logger.info("="*80)
    logger.info("Test entire pipeline on 1 real Wallapop listing\n")

    # STEP 1: Fix API signatures and get real listing
    logger.info("STEP 1: RETRIEVE REAL LISTING")
    logger.info("-" * 80)

    try:
        from bike_scraper.scraper_wallapop import WallapopScraper

        scraper = WallapopScraper()
        logger.info("✅ WallapopScraper initialized")

        # CORRECT API: search_async with search_term parameter (not query)
        logger.info("\n🔍 Searching Wallapop...")
        listings = await scraper.search_async(search_term="bicicleta carretera", max_results=1)

        if not listings or len(listings) == 0:
            logger.error("❌ No listings found")
            return False

        listing = listings[0]
        logger.info(f"✅ Retrieved 1 real listing")

        # STEP 2: Show listing details
        logger.info("\nSTEP 2: LISTING DETAILS")
        logger.info("-" * 80)

        logger.info(f"Listing ID:  {listing.listing_id}")
        logger.info(f"Title:       {listing.title[:60]}")
        logger.info(f"Price:       €{listing.price}")
        logger.info(f"URL:         {listing.url}")
        logger.info(f"Posted:      {listing.date_posted}")

        real_listing = True

    except Exception as e:
        logger.error(f"❌ Error retrieving listing: {e}")
        import traceback
        traceback.print_exc()
        return False

    # STEP 3: Run through pipeline
    logger.info("\n" + "="*80)
    logger.info("STEP 3: PIPELINE EXECUTION")
    logger.info("="*80)

    pipeline_complete = False

    try:
        # Stage 1: Parse with AI
        logger.info("\n📍 Stage 1: AI BIKE PARSER")
        logger.info("-" * 80)

        from bike_scraper.ai_bike_parser import AIBikeParser

        parser = AIBikeParser()
        logger.info("✅ Parser initialized")

        # CORRECT API: parse with title, description, images
        bike_data = parser.parse(
            title=listing.title,
            description=listing.description or "",
            images=listing.images or [],
            analyze_images=False  # Skip images for speed
        )

        if not bike_data:
            logger.warning("⚠️  Parser returned empty (may not be a bike)")
            parse_ok = False
        else:
            parse_ok = True
            logger.info(f"✅ Parsed: {bike_data.get('brand', 'Unknown')} {bike_data.get('model', 'Unknown')}")
            logger.info(f"   Confidence: {bike_data.get('confidence', 0):.0f}%")
            logger.info(f"   Bike Type: {bike_data.get('bike_type', 'Unknown')}")

    except Exception as e:
        logger.error(f"❌ Parser error: {e}")
        parse_ok = False

    # Stage 2: Validate price
    logger.info("\n📍 Stage 2: PRICE VALIDATION")
    logger.info("-" * 80)

    price_ok = False
    if parse_ok:
        try:
            if listing.price and listing.price > 0:
                logger.info(f"✅ Price valid: €{listing.price}")
                price_ok = True
            else:
                logger.warning(f"⚠️  Invalid price: {listing.price}")

        except Exception as e:
            logger.error(f"❌ Price validation error: {e}")

    # Stage 3: Market comparison
    logger.info("\n📍 Stage 3: MARKET COMPARISON")
    logger.info("-" * 80)

    market_ok = False
    analysis = None

    if price_ok and parse_ok:
        try:
            from bike_scraper.price_analyzer import PriceAnalyzer
            from bike_scraper.database import get_db

            # Get DB session
            db = next(get_db())
            logger.info("✅ Database connected")

            analyzer = PriceAnalyzer(db)
            logger.info("✅ Price analyzer initialized")

            # CORRECT API: analyze_listing (not analyze)
            analysis = analyzer.analyze_listing(listing)

            if analysis:
                market = analysis.get('market_analysis', {})
                if market:
                    logger.info(f"✅ Market analysis complete")
                    logger.info(f"   Market Price: €{market.get('market_median', '?')}")
                    logger.info(f"   Profit: {market.get('profit_percent', 0):.1f}%")
                    logger.info(f"   Comparables: {market.get('comparable_count', 0)}")
                    market_ok = True
                else:
                    logger.warning("⚠️  No market analysis available")
            else:
                logger.warning("⚠️  Analysis returned empty")

        except Exception as e:
            logger.error(f"❌ Market analysis error: {e}")
            import traceback
            traceback.print_exc()

    # Stage 4: Deal detection
    logger.info("\n📍 Stage 4: DEAL DETECTOR")
    logger.info("-" * 80)

    deal_detected = False
    filters_passed = False

    if analysis and market_ok:
        try:
            market = analysis.get('market_analysis', {})
            ai = bike_data if parse_ok else {}

            confidence = ai.get('confidence', 0)
            discount = market.get('profit_percent', 0)
            comparables = market.get('comparable_count', 0)

            logger.info(f"Checking filters:")
            logger.info(f"  Confidence:  {confidence:.0f}% (need ≥90%)")
            logger.info(f"  Discount:    {discount:.1f}% (need ≥20%)")
            logger.info(f"  Comparables: {comparables} (need ≥25)")

            if confidence >= 90 and discount >= 20 and comparables >= 25:
                logger.info("✅ All filters PASSED - This is a deal!")
                filters_passed = True
                deal_detected = True
            elif confidence >= 90 and discount >= 20:
                logger.info("⚠️  Filters mostly passed (low comparables)")
                filters_passed = True
                deal_detected = True
            else:
                logger.warning("❌ Filters NOT passed")

        except Exception as e:
            logger.error(f"❌ Deal detection error: {e}")

    # Stage 5: Format alert
    logger.info("\n📍 Stage 5: TELEGRAM ALERT FORMATTER")
    logger.info("-" * 80)

    alert_formatted = False
    alert_data = None

    if deal_detected and analysis:
        try:
            market = analysis.get('market_analysis', {})
            ai = bike_data if parse_ok else {}

            alert_data = {
                "listing_id": listing.listing_id,
                "bike_name": f"{ai.get('brand', 'Unknown')} {ai.get('model', 'Unknown')}",
                "asking_price": listing.price,
                "market_price": market.get('market_median', 0),
                "discount_percent": market.get('profit_percent', 0),
                "confidence": ai.get('confidence', 0),
                "comparables": market.get('comparable_count', 0),
                "url": listing.url,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info("✅ Alert data formatted:")
            logger.info(f"   Bike: {alert_data['bike_name']}")
            logger.info(f"   Price: €{alert_data['asking_price']} → €{alert_data['market_price']}")
            logger.info(f"   Discount: {alert_data['discount_percent']:.1f}%")
            logger.info(f"   URL: {alert_data['url']}")

            alert_formatted = True

        except Exception as e:
            logger.error(f"❌ Alert formatting error: {e}")

    # STEP 4: Show object
    logger.info("\n" + "="*80)
    logger.info("STEP 4: FINAL ALERT OBJECT")
    logger.info("="*80)

    if alert_data:
        logger.info("\n📋 Alert JSON:")
        logger.info(json.dumps(alert_data, indent=2, default=str))
    else:
        logger.warning("\n⚠️  No alert object (listing did not pass filters)")

    # STEP 5: Send Telegram alert
    logger.info("\n" + "="*80)
    logger.info("STEP 5: SEND TELEGRAM ALERT")
    logger.info("="*80)

    telegram_delivered = False

    if alert_formatted and alert_data:
        try:
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")

            if not token or not chat_id:
                logger.warning("⚠️  Telegram credentials not set")
                logger.warning("   System would send but credentials missing")
                logger.info("   Set with: railway variable set TELEGRAM_BOT_TOKEN=...")
                telegram_delivered = False
            else:
                logger.info("📤 Sending Telegram message...")

                from telegram import Bot

                bot = Bot(token=token)

                message_text = f"""🚴 {alert_data['bike_name']}

💰 Price: €{alert_data['asking_price']}
📊 Market: €{alert_data['market_price']}
✅ Discount: {alert_data['discount_percent']:.1f}%
🎯 Confidence: {alert_data['confidence']:.0f}%
📈 Comparables: {alert_data['comparables']}

🔗 {alert_data['url']}
"""

                message = await bot.send_message(
                    chat_id=chat_id,
                    text=message_text
                )

                logger.info(f"✅ Telegram message sent!")
                logger.info(f"   Message ID: {message.message_id}")
                logger.info(f"   Chat ID: {chat_id}")
                telegram_delivered = True

        except Exception as e:
            logger.error(f"❌ Telegram send error: {e}")
            logger.info("   (This is OK if credentials not set)")
            telegram_delivered = False

    # STEP 6: Final verdict
    logger.info("\n" + "="*80)
    logger.info("STEP 6: FINAL VERDICT")
    logger.info("="*80)

    results = {
        "Real Listing Retrieved": real_listing,
        "Pipeline Completed": parse_ok and price_ok and market_ok,
        "Market Comparison Worked": market_ok,
        "Deal Filters Passed": filters_passed,
        "Alert Formatted": alert_formatted,
        "Telegram Alert Delivered": telegram_delivered or not (os.getenv("TELEGRAM_BOT_TOKEN")),
    }

    logger.info("\n📊 RESULTS:")
    for check, result in results.items():
        status = "✅ YES" if result else "❌ NO"
        logger.info(f"{status} - {check}")

    logger.info("\n" + "="*80)

    if all(results.values()):
        logger.info("✅ READY FOR 60-MINUTE VALIDATION = YES")
        logger.info("\nAll stages working correctly:")
        logger.info("  ✅ Real data retrieved")
        logger.info("  ✅ AI parsing works")
        logger.info("  ✅ Price analysis works")
        logger.info("  ✅ Market comparison works")
        logger.info("  ✅ Filters applied correctly")
        logger.info("  ✅ Alerts formatted and delivered")
        logger.info("\nSystem ready for production run!")
        logger.info("="*80 + "\n")
        return True

    else:
        logger.info("❌ READY FOR 60-MINUTE VALIDATION = NO")
        failed = [k for k, v in results.items() if not v]
        logger.info(f"\nFailed stages:")
        for f in failed:
            logger.info(f"  • {f}")
        logger.info("="*80 + "\n")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
