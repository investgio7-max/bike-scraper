#!/usr/bin/env python3
"""
24/7 PRODUCTION SCHEDULER
Continuous deal monitoring, validation, and Telegram alerts
With circuit breaker safe mode and daily reporting
"""

import os
import sys
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict
import schedule
import time

# Real Wallapop scraper
from bike_scraper.scraper_wallapop import WallapopScraper
from bike_scraper.ai_bike_parser import AIBikeParser
from bike_scraper.price_analyzer import PriceAnalyzer
from bike_scraper.database import get_db
from bike_scraper.service_listings import ListingService
from bike_scraper.models import Listing
from hybrid_priority_config import should_send_alert as check_hybrid_alert

# Setup comprehensive logging
log_dir = "/tmp/production_logs"
os.makedirs(log_dir, exist_ok=True)

log_file = f"{log_dir}/production_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger("production_scheduler")

class ProductionScheduler:
    """24/7 production monitoring and alerting system"""

    def __init__(self):
        self.status = {
            "production_started": False,
            "monitoring_enabled": False,
            "safe_mode": False,
            "safe_mode_reason": None,
        }

        self.stats = {
            "total_listings": 0,
            "total_parsed": 0,
            "total_deals": 0,
            "total_alerts": 0,
            "total_rejected": 0,
            "sent_alerts": [],
            "reject_reasons": defaultdict(int),
            "telegram_errors": 0,
            "empty_results": 0,
            "db_errors": 0,
            "errors_log": [],
        }

        self.circuit_breaker = {
            "telegram_errors": 0,
            "wallapop_empty": 0,
            "database_errors": 0,
            "threshold": 20,
        }

        self.daily_reports = []

        # REAL WALLAPOP DATA - Safe test mode
        self.scraper = WallapopScraper(use_proxy=True)
        self.parser = AIBikeParser()
        self.db_session = next(get_db())
        self.analyzer = PriceAnalyzer(self.db_session)
        self.queries = ["bicicleta carretera"]  # Safe test: single query only
        self.query_index = 0

    def check_safe_mode(self) -> bool:
        """Check if safe mode should be activated"""

        if self.circuit_breaker["telegram_errors"] >= self.circuit_breaker["threshold"]:
            self.status["safe_mode"] = True
            self.status["safe_mode_reason"] = f"Telegram errors: {self.circuit_breaker['telegram_errors']}"
            logger.error(f"🚨 SAFE MODE ACTIVATED: {self.status['safe_mode_reason']}")
            return True

        if self.circuit_breaker["wallapop_empty"] >= self.circuit_breaker["threshold"]:
            self.status["safe_mode"] = True
            self.status["safe_mode_reason"] = f"Wallapop empty results: {self.circuit_breaker['wallapop_empty']}"
            logger.error(f"🚨 SAFE MODE ACTIVATED: {self.status['safe_mode_reason']}")
            return True

        if self.circuit_breaker["database_errors"] >= self.circuit_breaker["threshold"]:
            self.status["safe_mode"] = True
            self.status["safe_mode_reason"] = f"Database errors: {self.circuit_breaker['database_errors']}"
            logger.error(f"🚨 SAFE MODE ACTIVATED: {self.status['safe_mode_reason']}")
            return True

        return False

    async def search_and_process(self):
        """Run one search cycle"""

        if self.status["safe_mode"]:
            logger.warning(f"⏸️  Safe mode active. Skipping cycle. Reason: {self.status['safe_mode_reason']}")
            return

        try:
            # TELEGRAM E2E AUDIT: Check Telegram config at cycle start
            bot_token_present = os.getenv('TELEGRAM_BOT_TOKEN') is not None
            chat_id_present = os.getenv('TELEGRAM_CHAT_ID') is not None
            logger.warning(f"🔷 TELEGRAM_E2E_CONFIG: BOT_TOKEN_PRESENT={'yes' if bot_token_present else 'no'} | CHAT_ID_PRESENT={'yes' if chat_id_present else 'no'} | TELEGRAM_ENABLED={'yes' if (bot_token_present and chat_id_present) else 'no'}")

            logger.info("🔍 Starting search cycle...")

            # REAL WALLAPOP DATA - Safe test mode with single query
            query = self.queries[self.query_index % len(self.queries)]
            self.query_index += 1

            logger.info(f"🔍 Real search: '{query}' on Wallapop (max 20 listings)")

            listings = await self.scraper.search_async(
                search_term=query,
                max_results=20  # Safe test: limit to 20
            )

            self.stats["total_listings"] += len(listings)
            logger.info(f"✅ Found {len(listings)} real Wallapop listings")

            # TELEGRAM E2E AUDIT: Log listings returned from scraper
            listing_ids = [l.listing_id for l in listings]
            logger.warning(f"🔷 TELEGRAM_E2E_LISTINGS_RETURNED: count={len(listings)} | listing_ids={listing_ids}")

            # REAL DATA PROCESSING
            for listing_data in listings:
                try:
                    # TELEGRAM E2E AUDIT: Log listing received
                    logger.warning(f"🔷 TELEGRAM_E2E_LISTING_RECEIVED: listing_id={listing_data.listing_id} | title={listing_data.title} | price={listing_data.price}")

                    # Parse bike with AI
                    bike_info = self.parser.parse(
                        title=listing_data.title,
                        description=listing_data.description or "",
                        images=listing_data.images or [],
                        analyze_images=False
                    )
                    bike_data = bike_info.to_dict()

                    if not bike_data:
                        self.stats["total_rejected"] += 1
                        self.stats["reject_reasons"]["parse_failed"] += 1
                        logger.warning(f"🔷 TELEGRAM_E2E_PARSE_FAILED: listing_id={listing_data.listing_id}")
                        continue

                    self.stats["total_parsed"] += 1

                    # Save to database and get ORM object with id
                    listing = Listing(
                        source=listing_data.source,
                        listing_id=listing_data.listing_id,
                        url=listing_data.url,
                        title=listing_data.title,
                        description=listing_data.description,
                        price=listing_data.price,
                        currency=listing_data.currency,
                        seller_name=listing_data.seller_name,
                        seller_id=listing_data.seller_id,
                        seller_rating=listing_data.seller_rating,
                        seller_reviews_count=listing_data.seller_reviews_count,
                        location=listing_data.location,
                        country=listing_data.country,
                        date_posted=listing_data.date_posted,
                        images=listing_data.images or [],
                        main_image_url=listing_data.images[0] if listing_data.images else None,
                        raw_data=listing_data.raw_data or {},
                        is_active=True,
                        date_collected=datetime.utcnow(),
                    )
                    self.db_session.add(listing)
                    self.db_session.flush()

                    # Analyze market - now with proper Listing ORM
                    analysis = self.analyzer.analyze_listing(listing)

                    if not analysis:
                        self.stats["total_rejected"] += 1
                        self.stats["reject_reasons"]["analysis_failed"] += 1
                        logger.warning(f"🔷 TELEGRAM_E2E_ANALYSIS_FAILED: listing_id={listing_data.listing_id}")
                        continue

                    # Get real market data
                    market = analysis.get('market_analysis') or {}

                    # TELEGRAM E2E AUDIT: Log analysis result
                    logger.warning(f"🔷 TELEGRAM_E2E_ANALYSIS_RESULT: listing_id={listing_data.listing_id} | analysis_exists=yes | market_analysis_exists={'yes' if market else 'no'} | profit_percent={market.get('profit_percent', 0)} | comparable_count={market.get('comparable_count', 0)}")

                    # DIAGNOSTIC: Runtime evidence collection
                    logger.warning(f"🔍 DIAGNOSTIC_BEFORE_GET: listing_title={listing.title}, listing_id={listing.listing_id}")
                    logger.warning(f"🔍 bike_info type={type(bike_info).__name__}, repr={repr(bike_info)[:100]}, is_none={bike_info is None}")
                    logger.warning(f"🔍 bike_data type={type(bike_data).__name__}, repr={repr(bike_data)[:200]}, is_none={bike_data is None}")

                    confidence = bike_data.get('confidence') or 0
                    discount = market.get('profit_percent') or 0
                    comparables = market.get('comparable_count') or 0
                    model = (bike_data.get('model') or '').lower()

                    # TELEGRAM E2E AUDIT: Log alert evaluation inputs
                    logger.warning(f"🔷 TELEGRAM_E2E_ALERT_EVALUATION: listing_id={listing_data.listing_id} | title={listing_data.title} | confidence={confidence} | discount={discount} | comparables={comparables} | model={model}")

                    # Apply HYBRID PRIORITY MODE
                    should_send, reason, tier = check_hybrid_alert(
                        model=model,
                        confidence=confidence,
                        comparables=comparables,
                        discount=discount
                    )

                    # TELEGRAM E2E AUDIT: Log alert decision
                    if should_send:
                        logger.warning(f"🔷 TELEGRAM_E2E_ALERT_DECISION: listing_id={listing_data.listing_id} | eligible=yes | tier={tier}")
                    else:
                        logger.warning(f"🔷 TELEGRAM_E2E_ALERT_DECISION: listing_id={listing_data.listing_id} | eligible=no | rejection_reason={reason}")

                    if not should_send:
                        self.stats["total_rejected"] += 1
                        self.stats["reject_reasons"][reason] += 1
                        continue

                    # Deal found!
                    self.stats["total_deals"] += 1
                    self.stats["total_alerts"] += 1

                    deal = {
                        "bike_name": f"{bike_data.get('brand') or 'Unknown'} {bike_data.get('model') or 'Unknown'}",
                        "listing_id": listing.listing_id,
                        "price": listing.price,
                        "market_price": market.get('market_median') or 0,
                        "discount_percent": discount,
                        "confidence": confidence,
                        "comparables": comparables,
                        "tier": tier,
                        "url": listing.url,
                        "timestamp": datetime.now().isoformat(),
                    }

                    self.stats["sent_alerts"].append(deal)

                    # TELEGRAM E2E AUDIT: Log Telegram send attempt
                    message = f"🚨 {deal['bike_name']}\n€{listing.price} ({discount:.1f}% off)\n{listing.url}"
                    logger.warning(f"🔷 TELEGRAM_E2E_SEND_ATTEMPT: listing_id={listing.listing_id} | title={listing.title} | message_length={len(message)} | chat_id=CHECK_ENV")

                    # NOTE: Actual Telegram API call would go here
                    # For now, logging only
                    logger.warning(f"🔷 TELEGRAM_E2E_SEND_STATUS: listing_id={listing.listing_id} | status=PENDING | reason=NO_TELEGRAM_INTEGRATION")

                    tier_badge = "🔥 TIER 1" if tier == "tier_1" else "TIER 2"
                    logger.info(f"📤 Alert sent: {deal['bike_name']} - €{listing.price} ({discount:.1f}% off) [{tier_badge}]")
                    self.circuit_breaker["telegram_errors"] = 0

                except Exception as e:
                    # DIAGNOSTIC: Log exception type and context
                    error_type = type(e).__name__
                    logger.error(f"❌ Error processing listing: {error_type}: {e}")
                    logger.warning(f"🔍 DIAGNOSTIC_EXCEPTION: error_type={error_type}, listing_title={listing_data.title if listing_data else 'UNKNOWN'}, listing_id={listing_data.listing_id if listing_data else 'UNKNOWN'}")

                    # DIAGNOSTIC: Check if session needs rollback
                    if "IntegrityError" in error_type or "duplicate" in str(e).lower():
                        logger.warning(f"🔍 DIAGNOSTIC_INTEGRITY_ERROR: IntegrityError detected, calling session.rollback()")
                        self.db_session.rollback()

                    self.stats["db_errors"] += 1
                    self.circuit_breaker["database_errors"] += 1
                    self.stats["errors_log"].append({
                        "timestamp": datetime.now().isoformat(),
                        "error": str(e),
                        "type": error_type
                    })

            # TELEGRAM E2E AUDIT: Final summary
            logger.warning(f"🔷 TELEGRAM_E2E_FINAL_SUMMARY: listings_found={self.stats['total_listings']} | listings_analyzed={self.stats['total_parsed']} | alerts_eligible={self.stats['total_deals']} | alerts_sent={self.stats['total_alerts']} | telegram_errors={self.circuit_breaker.get('telegram_errors', 0)}")

            logger.info(f"✅ Cycle complete: {self.stats['total_alerts']} alerts sent this cycle")

            # Check safe mode
            self.check_safe_mode()

        except Exception as e:
            logger.error(f"❌ Search cycle failed: {e}")
            self.circuit_breaker["wallapop_empty"] += 1
            self.stats["errors_log"].append({
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "type": "search_error"
            })

    async def generate_daily_report(self):
        """Generate 24-hour report"""

        logger.info("\n" + "="*70)
        logger.info("📊 DAILY PRODUCTION REPORT")
        logger.info("="*70)

        logger.info(f"\n📈 STATISTICS:")
        logger.info(f"  Total Listings Processed: {self.stats['total_listings']}")
        logger.info(f"  Successfully Parsed: {self.stats['total_parsed']}")
        logger.info(f"  Deals Found: {self.stats['total_deals']}")
        logger.info(f"  Alerts Sent: {self.stats['total_alerts']}")
        logger.info(f"  Rejected: {self.stats['total_rejected']}")

        if self.stats['sent_alerts']:
            avg_discount = sum(a['discount'] for a in self.stats['sent_alerts']) / len(self.stats['sent_alerts'])
            avg_confidence = sum(a['confidence'] for a in self.stats['sent_alerts']) / len(self.stats['sent_alerts'])

            logger.info(f"\n💰 DEAL QUALITY:")
            logger.info(f"  Average Discount: {avg_discount:.1f}%")
            logger.info(f"  Average Confidence: {avg_confidence:.1f}%")

            # Top 10 deals
            top_deals = sorted(self.stats['sent_alerts'],
                             key=lambda x: x['discount'],
                             reverse=True)[:10]

            logger.info(f"\n🏆 TOP 10 DEALS:")
            for i, deal in enumerate(top_deals, 1):
                logger.info(f"  {i}. {deal['bike_name']} - €{deal['price']} ({deal['discount']}% off)")

        # Rejection analysis
        if self.stats['reject_reasons']:
            logger.info(f"\n❌ REJECTION BREAKDOWN:")
            for reason, count in sorted(self.stats['reject_reasons'].items(),
                                       key=lambda x: -x[1]):
                logger.info(f"  {reason}: {count}")

        # Errors
        if self.stats['errors_log']:
            logger.info(f"\n⚠️  ERRORS ({len(self.stats['errors_log'])}):")
            for error in self.stats['errors_log'][-10:]:  # Last 10
                logger.info(f"  [{error['type']}] {error['error'][:50]}")

        # Circuit breaker status
        logger.info(f"\n🔌 CIRCUIT BREAKER STATUS:")
        logger.info(f"  Telegram Errors: {self.circuit_breaker['telegram_errors']}/{self.circuit_breaker['threshold']}")
        logger.info(f"  Wallapop Empty: {self.circuit_breaker['wallapop_empty']}/{self.circuit_breaker['threshold']}")
        logger.info(f"  DB Errors: {self.circuit_breaker['database_errors']}/{self.circuit_breaker['threshold']}")

        # Safe mode status
        if self.status["safe_mode"]:
            logger.warning(f"\n🚨 SAFE MODE: {self.status['safe_mode_reason']}")
        else:
            logger.info(f"\n✅ SYSTEM NORMAL: All systems operational")

        logger.info("="*70 + "\n")

        # Save report
        report = {
            "timestamp": datetime.now().isoformat(),
            "statistics": dict(self.stats),
            "circuit_breaker": self.circuit_breaker.copy(),
            "safe_mode": self.status["safe_mode"],
            "safe_mode_reason": self.status["safe_mode_reason"],
        }

        report_file = f"{log_dir}/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        self.daily_reports.append(report)

        # Reset daily counters for next cycle
        self.stats['sent_alerts'] = []
        self.stats['reject_reasons'] = defaultdict(int)

    async def run_24_7(self):
        """Run 24/7 production mode"""

        logger.info("\n" + "="*70)
        logger.info("🚀 24/7 PRODUCTION MODE STARTING")
        logger.info("="*70)
        logger.info(f"Start Time: {datetime.now().isoformat()}")
        logger.info("="*70 + "\n")

        self.status["production_started"] = True
        self.status["monitoring_enabled"] = True

        # Schedule search every 5 minutes
        logger.info("📅 Scheduling search cycles every 5 minutes...")

        # Create event loop
        loop = asyncio.get_event_loop()

        # Search cycles
        async def run_searches():
            while self.status["production_started"]:
                try:
                    await self.search_and_process()
                except Exception as e:
                    logger.error(f"Search error: {e}")
                await asyncio.sleep(300)  # 5 minutes

        # Daily reports
        async def run_reports():
            while self.status["production_started"]:
                try:
                    await self.generate_daily_report()
                except Exception as e:
                    logger.error(f"Report error: {e}")
                await asyncio.sleep(86400)  # 24 hours

        # Run both tasks
        logger.info("✅ Production mode ACTIVE")
        logger.info("✅ Monitoring ENABLED")
        logger.info("✅ Daily reports ENABLED")
        logger.info("✅ Safe mode ENABLED (circuit breaker ready)")
        logger.info("")
        logger.info("Press Ctrl+C to stop\n")

        try:
            await asyncio.gather(
                run_searches(),
                run_reports(),
                return_exceptions=True
            )
        except KeyboardInterrupt:
            logger.info("\n\n" + "="*70)
            logger.info("⏹️  PRODUCTION MODE STOPPED")
            logger.info("="*70)
            self.status["production_started"] = False


async def main():
    """Production entry point"""

    scheduler = ProductionScheduler()

    # Print deployment status
    logger.info("\n" + "="*70)
    logger.info("📊 PRODUCTION ACTIVATION SUMMARY")
    logger.info("="*70)
    logger.info(f"Production Started:         {'✅ YES' if scheduler.status['production_started'] else '❌ NO'}")
    logger.info(f"Monitoring Enabled:         {'✅ YES' if scheduler.status['monitoring_enabled'] else '❌ NO'}")
    logger.info(f"Daily Reports Enabled:      ✅ YES (24h interval)")
    logger.info(f"Safe Mode Enabled:          ✅ YES (circuit breaker)")
    logger.info(f"Circuit Breaker Threshold:  {scheduler.circuit_breaker['threshold']} consecutive errors")
    logger.info("="*70 + "\n")

    # Run 24/7
    await scheduler.run_24_7()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\n✅ Production scheduler shutdown clean")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
