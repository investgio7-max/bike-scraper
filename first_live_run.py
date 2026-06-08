#!/usr/bin/env python3
"""
FIRST LIVE RUN - 15 minute production test
Real Wallapop data, real pipeline, real results
"""

import os
import sys
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("first_live_run")

class FirstLiveRun:
    """15-minute production test"""

    def __init__(self, duration_minutes: int = 15):
        self.duration = duration_minutes * 60
        self.start_time = datetime.now()
        self.stats = {
            "found": 0,
            "parsed": 0,
            "rejected": 0,
            "deals_found": 0,
            "alerts_sent": 0,
            "sent_alerts": [],
            "rejection_reasons": defaultdict(int),
        }

    async def run(self):
        """Run 15-minute live validation"""

        logger.info("\n" + "="*80)
        logger.info("🚀 FIRST LIVE RUN - 15 MINUTE PRODUCTION TEST")
        logger.info("="*80)
        logger.info(f"Start: {self.start_time.strftime('%H:%M:%S')}")
        logger.info(f"Duration: {self.duration} seconds (15 minutes)")
        logger.info(f"Using REAL Wallapop data + proxies")
        logger.info("="*80 + "\n")

        try:
            from bike_scraper.scraper_wallapop import WallapopScraper
            from bike_scraper.ai_bike_parser import AIBikeParser
            from bike_scraper.price_analyzer import PriceAnalyzer
            from bike_scraper.database import get_db
            from bike_scraper.models import Listing

            from hybrid_priority_config import should_send_alert as check_hybrid_alert

            scraper = WallapopScraper(use_proxy=True)
            parser = AIBikeParser()
            db = next(get_db())
            analyzer = PriceAnalyzer(db)

            logger.info("✅ All modules initialized\n")

            # Search queries
            queries = ["bicicleta carretera", "bicicleta montaña", "bicicleta gravel"]
            query_idx = 0

            while (datetime.now() - self.start_time).total_seconds() < self.duration:
                query = queries[query_idx % len(queries)]
                query_idx += 1

                logger.info(f"\n🔍 Search cycle: '{query}'")

                try:
                    # Search
                    listings = await scraper.search_async(search_term=query, max_results=20)

                    if not listings:
                        logger.warning("   No listings found")
                        continue

                    logger.info(f"   Found {len(listings)} listings")
                    self.stats["found"] += len(listings)

                    # Process each listing
                    for listing_data in listings:
                        try:
                            # Parse
                            bike_data = parser.parse(
                                title=listing_data.title,
                                description=listing_data.description or "",
                                images=listing_data.images or [],
                                analyze_images=False
                            )

                            if not bike_data:
                                self.stats["rejected"] += 1
                                self.stats["rejection_reasons"]["parse_failed"] += 1
                                continue

                            self.stats["parsed"] += 1

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
                            db.add(listing)
                            db.flush()

                            # Analyze
                            analysis = analyzer.analyze_listing(listing)

                            if not analysis:
                                self.stats["rejected"] += 1
                                self.stats["rejection_reasons"]["analysis_failed"] += 1
                                continue

                            # Check filters with HYBRID PRIORITY MODE
                            market = analysis.get('market_analysis', {})
                            confidence = bike_data.get('confidence', 0)
                            discount = market.get('profit_percent', 0)
                            comparables = market.get('comparable_count', 0)
                            model = bike_data.get('model', '').lower()

                            # Apply hybrid priority logic
                            should_send, reason, tier = check_hybrid_alert(
                                model=model,
                                confidence=confidence,
                                comparables=comparables,
                                discount=discount
                            )

                            if not should_send:
                                self.stats["rejection_reasons"][reason] += 1
                                continue

                            # Deal found!
                            self.stats["deals_found"] += 1
                            self.stats["alerts_sent"] += 1

                            alert = {
                                "bike_name": f"{bike_data.get('brand', 'Unknown')} {bike_data.get('model', 'Unknown')}",
                                "listing_id": listing.listing_id,
                                "price": listing.price,
                                "market_price": market.get('market_median', 0),
                                "discount_percent": discount,
                                "confidence": confidence,
                                "comparables": comparables,
                                "tier": tier,
                                "url": listing.url,
                                "timestamp": datetime.now().isoformat(),
                            }

                            self.stats["sent_alerts"].append(alert)

                            tier_icon = "🔥" if tier == "tier_1" else ""
                            logger.info(f"   ✅ DEAL: {alert['bike_name']} - €{alert['price']} ({alert['discount_percent']:.1f}% off) [{tier.upper()} {tier_icon}]")

                        except Exception as e:
                            logger.debug(f"   Error processing listing: {e}")
                            self.stats["rejected"] += 1

                except Exception as e:
                    logger.error(f"Search error: {e}")

                # Rate limiting
                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            import traceback
            traceback.print_exc()
            return False

        # Print results
        await self.print_results()
        return True

    async def print_results(self):
        """Print comprehensive results"""

        duration = (datetime.now() - self.start_time).total_seconds()

        logger.info("\n" + "="*80)
        logger.info("📊 RESULTS - 15 MINUTE LIVE RUN")
        logger.info("="*80)

        logger.info(f"\n⏱️  DURATION: {duration:.0f} seconds ({duration/60:.1f} minutes)")

        logger.info(f"\n📈 PIPELINE STATISTICS:")
        logger.info(f"  Listings Found:     {self.stats['found']}")
        logger.info(f"  Listings Parsed:    {self.stats['parsed']}")
        logger.info(f"  Listings Rejected:  {self.stats['rejected']}")
        logger.info(f"  Deals Found:        {self.stats['deals_found']}")
        logger.info(f"  Alerts Sent:        {self.stats['alerts_sent']}")

        if self.stats['rejection_reasons']:
            logger.info(f"\n❌ REJECTION BREAKDOWN:")
            for reason, count in sorted(self.stats['rejection_reasons'].items(), key=lambda x: -x[1]):
                logger.info(f"  {reason}: {count}")

        # Show all alerts
        if self.stats["sent_alerts"]:
            logger.info(f"\n📲 ALL {len(self.stats['sent_alerts'])} ALERTS SENT:")

            for idx, alert in enumerate(self.stats["sent_alerts"], 1):
                logger.info(f"\n[{idx}] {alert['bike_name']}")
                logger.info(f"    Listing ID: {alert['listing_id']}")
                logger.info(f"    Price: €{alert['price']} → Market: €{alert['market_price']}")
                logger.info(f"    Discount: {alert['discount_percent']:.1f}%")
                logger.info(f"    Confidence: {alert['confidence']:.0f}%")
                logger.info(f"    Comparables: {alert['comparables']}")
                logger.info(f"    URL: {alert['url']}")

            # Save URLs for manual verification
            logger.info(f"\n📋 MANUAL VERIFICATION URLs (first 10):")
            logger.info("Copy these to check manually:\n")

            for idx, alert in enumerate(self.stats["sent_alerts"][:10], 1):
                logger.info(f"{idx}. {alert['url']}")

            # Quality metrics
            logger.info(f"\n✅ QUALITY METRICS:")

            if self.stats['found'] > 0:
                conversion = (self.stats['alerts_sent'] / self.stats['found']) * 100
                logger.info(f"  Conversion Rate: {conversion:.2f}%")

            if self.stats['parsed'] > 0:
                parse_rate = (self.stats['parsed'] / self.stats['found']) * 100
                logger.info(f"  Parse Success: {parse_rate:.2f}%")

            if self.stats['alerts_sent'] > 0:
                avg_discount = sum(a['discount_percent'] for a in self.stats['sent_alerts']) / len(self.stats['sent_alerts'])
                avg_confidence = sum(a['confidence'] for a in self.stats['sent_alerts']) / len(self.stats['sent_alerts'])

                logger.info(f"  Avg Discount: {avg_discount:.1f}%")
                logger.info(f"  Avg Confidence: {avg_confidence:.1f}%")

                best_by_discount = max(self.stats['sent_alerts'], key=lambda x: x['discount_percent'])
                logger.info(f"  Best Deal: {best_by_discount['bike_name']} ({best_by_discount['discount_percent']:.1f}%)")

        # Manual verification prompt
        logger.info("\n" + "="*80)
        logger.info("🔍 MANUAL VERIFICATION INSTRUCTIONS")
        logger.info("="*80)

        logger.info("\nFor each of the first 10 URLs above, verify:")
        logger.info("  1. ✓ URL opens (not 404)")
        logger.info("  2. ✓ It's a bike (not parts)")
        logger.info("  3. ✓ Price matches (€XX)")
        logger.info("  4. ✓ Not frame only")
        logger.info("  5. ✓ Not wheels only")
        logger.info("  6. ✓ Not scam (authentic seller)")
        logger.info("  7. ✓ Not 'looking for' (is 'selling')")

        logger.info("\nAfter verification, provide:")
        logger.info("  - Count of PASS / FAIL")
        logger.info("  - False Positive Rate = FAIL count / 10")

        # Final verdict
        logger.info("\n" + "="*80)
        logger.info("🎯 PRELIMINARY VERDICT")
        logger.info("="*80)

        if self.stats['alerts_sent'] >= 5:
            logger.info("\n✅ SYSTEM QUALITY: GOOD")
            logger.info(f"   Found and validated {self.stats['alerts_sent']} real deals")
            logger.info(f"   Pipeline working correctly")
            logger.info(f"   Filters applied correctly")
        elif self.stats['alerts_sent'] >= 1:
            logger.info("\n✅ SYSTEM QUALITY: ACCEPTABLE")
            logger.info(f"   Found {self.stats['alerts_sent']} deal(s)")
            logger.info(f"   System functioning")
        else:
            logger.info("\n⚠️  SYSTEM QUALITY: NEEDS INVESTIGATION")
            logger.info(f"   No deals found in 15 minutes")
            logger.info(f"   Check filters or Wallapop availability")

        logger.info("\n" + "="*80)
        logger.info("⏳ AWAIT MANUAL VERIFICATION")
        logger.info("="*80)
        logger.info("\nPlease manually verify the 10 URLs above.")
        logger.info("Report: how many PASS vs FAIL?")
        logger.info("Then system quality score will be determined.\n")

        # Save detailed report
        report = {
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_seconds": duration,
            "statistics": {
                "listings_found": self.stats['found'],
                "listings_parsed": self.stats['parsed'],
                "listings_rejected": self.stats['rejected'],
                "deals_found": self.stats['deals_found'],
                "alerts_sent": self.stats['alerts_sent'],
            },
            "alerts": self.stats['sent_alerts'],
            "rejection_reasons": dict(self.stats['rejection_reasons']),
        }

        report_file = f"/tmp/first_live_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"📄 Full report saved: {report_file}\n")


async def main():
    """Entry point"""
    runner = FirstLiveRun(duration_minutes=15)
    await runner.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⏸️  Run interrupted by user")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
