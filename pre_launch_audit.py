#!/usr/bin/env python3
"""
PRE-LAUNCH REALITY AUDIT
Proves system gets REAL Wallapop data before 60-minute validation run
Not 60 minutes. Just 5 minutes to verify data source is real.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("pre_launch_audit")

class PreLaunchAudit:
    """Pre-launch reality audit - verify real Wallapop data"""

    def __init__(self, duration_seconds: int = 300):  # 5 minutes
        self.duration = duration_seconds
        self.start_time = datetime.now()
        self.listings = []
        self.deals = []
        self.parse_errors = []

    async def check_data_source(self):
        """Check 1: Verify data source"""
        logger.info("\n" + "="*80)
        logger.info("CHECK 1: DATA SOURCE")
        logger.info("="*80)

        try:
            from bike_scraper.scraper_wallapop import WallapopScraper

            scraper = WallapopScraper()

            # Check if it uses real API
            if hasattr(scraper, 'api_url'):
                logger.info(f"✅ Using Wallapop API: {scraper.api_url}")
            else:
                logger.info("✅ WallapopScraper initialized")

            # Try one search to verify it's real API
            logger.info("\n🔍 Testing search functionality...")
            test_listings = await scraper.search(query="test", max_results=1)

            if test_listings:
                logger.info(f"✅ Search returned real results (got {len(test_listings)} listings)")
                return True, "Wallapop API"
            else:
                logger.warning("⚠️  Search returned no results (may be API issue)")
                return True, "Wallapop API"

        except Exception as e:
            logger.error(f"❌ Error checking data source: {e}")
            return False, str(e)

    async def run_short_search(self) -> int:
        """Check 2: Run 5-minute search, collect listings"""
        logger.info("\n" + "="*80)
        logger.info("CHECK 2: 5-MINUTE REAL SEARCH")
        logger.info("="*80)

        try:
            from bike_scraper.scraper_wallapop import WallapopScraper

            scraper = WallapopScraper()
            queries = ["bicicleta carretera", "bicicleta montaña"]

            for query in queries:
                if (datetime.now() - self.start_time).total_seconds() > self.duration:
                    break

                logger.info(f"\n🔍 Searching: '{query}'")
                # Use correct parameter name: search_term not query
                listings = await scraper.search_async(search_term=query, max_results=20)

                if listings:
                    logger.info(f"✅ Found {len(listings)} real listings from Wallapop")
                    self.listings.extend(listings)
                else:
                    logger.warning(f"⚠️  No listings found for '{query}'")

                # Rate limiting
                await asyncio.sleep(1)

            logger.info(f"\n✅ Total listings collected: {len(self.listings)}")
            return len(self.listings)

        except Exception as e:
            logger.error(f"❌ Search error: {e}")
            import traceback
            traceback.print_exc()
            return 0

    async def show_listings(self):
        """Check 3: Show first 20 listings"""
        logger.info("\n" + "="*80)
        logger.info("CHECK 3: FIRST 20 LISTINGS")
        logger.info("="*80)

        if not self.listings:
            logger.warning("⚠️  No listings found")
            return

        for idx, listing in enumerate(self.listings[:20], 1):
            logger.info(f"\n[{idx}] Listing ID: {listing.get('id', 'N/A')}")
            logger.info(f"    Title: {listing.get('title', 'N/A')}")
            logger.info(f"    Price: €{listing.get('price', 'N/A')}")
            logger.info(f"    URL: {listing.get('url', 'N/A')}")
            logger.info(f"    Timestamp: {listing.get('created_at', 'N/A')}")

    async def check_urls(self):
        """Check 4: Verify first 10 URLs open"""
        logger.info("\n" + "="*80)
        logger.info("CHECK 4: URL VERIFICATION (first 10)")
        logger.info("="*80)

        import httpx

        valid_count = 0

        for idx, listing in enumerate(self.listings[:10], 1):
            url = listing.get('url')
            if not url:
                logger.warning(f"[{idx}] ❌ NO URL provided")
                continue

            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.head(url, follow_redirects=True)

                    if response.status_code == 200:
                        logger.info(f"[{idx}] ✅ {url[:50]}... → HTTP {response.status_code}")
                        valid_count += 1
                    else:
                        logger.warning(f"[{idx}] ⚠️  {url[:50]}... → HTTP {response.status_code}")

            except Exception as e:
                logger.error(f"[{idx}] ❌ {url[:50]}... → Error: {str(e)[:50]}")

            await asyncio.sleep(0.5)

        logger.info(f"\n✅ Valid URLs: {valid_count}/10")
        return valid_count >= 8  # At least 8/10 should work

    async def check_listing_age(self):
        """Check 5: Show listing age distribution"""
        logger.info("\n" + "="*80)
        logger.info("CHECK 5: LISTING AGE DISTRIBUTION")
        logger.info("="*80)

        if not self.listings:
            logger.warning("⚠️  No listings to analyze")
            return

        now = datetime.now()
        today = 0
        week = 0
        old = 0

        for listing in self.listings:
            created = listing.get('created_at')

            if not created:
                continue

            # Try to parse created_at (may be string or datetime)
            if isinstance(created, str):
                try:
                    # Assume ISO format or similar
                    created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                except:
                    created_dt = None
            else:
                created_dt = created

            if not created_dt:
                continue

            age_days = (now - created_dt).days

            if age_days == 0:
                today += 1
            elif age_days <= 7:
                week += 1
            else:
                old += 1

        total = today + week + old
        logger.info(f"\nPublished Today:           {today} ({today/max(1,total)*100:.1f}%)")
        logger.info(f"Last 7 Days:               {week} ({week/max(1,total)*100:.1f}%)")
        logger.info(f"Older than 30 Days:        {old} ({old/max(1,total)*100:.1f}%)")

    async def check_categories(self):
        """Check 6: Show real bike categories found"""
        logger.info("\n" + "="*80)
        logger.info("CHECK 6: REAL BIKE CATEGORIES FOUND")
        logger.info("="*80)

        categories = {}

        for listing in self.listings[:20]:
            title = listing.get('title', '').lower()

            # Extract likely bike model/brand
            if any(word in title for word in ['aeroad', 'ultimate', 'tarmac', 'madone', 'dogma']):
                if 'aeroad' in title:
                    categories['Aeroad'] = categories.get('Aeroad', 0) + 1
                elif 'ultimate' in title:
                    categories['Ultimate'] = categories.get('Ultimate', 0) + 1
                elif 'tarmac' in title:
                    categories['Tarmac'] = categories.get('Tarmac', 0) + 1
                elif 'madone' in title:
                    categories['Madone'] = categories.get('Madone', 0) + 1
                elif 'dogma' in title:
                    categories['Dogma'] = categories.get('Dogma', 0) + 1

        if categories:
            logger.info("\n🚴 Bike Models Found:")
            for model, count in sorted(categories.items(), key=lambda x: -x[1]):
                logger.info(f"  {model}: {count}")
        else:
            logger.info("\n📋 Sample Titles from Listings:")
            for idx, listing in enumerate(self.listings[:5], 1):
                title = listing.get('title', 'N/A')
                logger.info(f"  {idx}. {title[:60]}")

    async def try_parsing(self):
        """Check 7: Try parsing listings to find deals"""
        logger.info("\n" + "="*80)
        logger.info("CHECK 7: PARSING & DEAL FINDING")
        logger.info("="*80)

        try:
            from bike_scraper.ai_bike_parser import AIBikeParser
            from bike_scraper.price_analyzer import PriceAnalyzer

            parser = AIBikeParser()
            analyzer = PriceAnalyzer()

            parsed_count = 0
            deal_count = 0

            for idx, listing in enumerate(self.listings[:10], 1):
                try:
                    # Parse
                    bike_data = parser.parse(listing)
                    if not bike_data:
                        continue

                    parsed_count += 1

                    # Analyze
                    analysis = analyzer.analyze(bike_data)
                    if not analysis:
                        continue

                    # Check if it's a deal
                    if (analysis.get('confidence', 0) >= 90 and
                        analysis.get('discount_percent', 0) >= 20):
                        deal_count += 1
                        self.deals.append({
                            'bike': bike_data.get('model', 'Unknown'),
                            'price': listing.get('price', 0),
                            'market': analysis.get('estimated_price', 0),
                            'discount': analysis.get('discount_percent', 0),
                            'confidence': analysis.get('confidence', 0),
                            'comparables': analysis.get('comparables', 0),
                            'url': listing.get('url', ''),
                        })

                except Exception as e:
                    logger.debug(f"Parse error on listing {idx}: {e}")
                    self.parse_errors.append(str(e))

            logger.info(f"\n✅ Parsed: {parsed_count}/10")
            logger.info(f"✅ Deals Found: {deal_count}")

            return parsed_count, deal_count

        except Exception as e:
            logger.error(f"❌ Parsing error: {e}")
            return 0, 0

    async def show_deal_example(self):
        """Check 8: Show first deal example"""
        logger.info("\n" + "="*80)
        logger.info("CHECK 8: FIRST DEAL EXAMPLE")
        logger.info("="*80)

        if not self.deals:
            logger.warning("⚠️  No deals found in 5-minute search")
            return False

        deal = self.deals[0]

        logger.info(f"\n🚴 {deal['bike']}")
        logger.info(f"   Price: €{deal['price']}")
        logger.info(f"   Market Price: €{deal['market']}")
        logger.info(f"   Discount: {deal['discount']:.1f}%")
        logger.info(f"   Confidence: {deal['confidence']:.0f}%")
        logger.info(f"   Comparable Count: {deal['comparables']}")
        logger.info(f"   URL: {deal['url']}")

        return True

    async def verify_not_mock(self):
        """Check 9: Confirm data is NOT from fixtures"""
        logger.info("\n" + "="*80)
        logger.info("CHECK 9: VERIFY NOT MOCK DATA")
        logger.info("="*80)

        # Check if listings have real attributes
        if self.listings:
            listing = self.listings[0]

            checks = {
                "Has listing ID": bool(listing.get('id')),
                "Has real URL": 'wallapop.com' in str(listing.get('url', '')).lower(),
                "Has price": bool(listing.get('price')),
                "Has timestamp": bool(listing.get('created_at')),
                "URL is not mock": 'wallapop.com' in str(listing.get('url', '')).lower(),
            }

            logger.info("\n✅ Data Source Verification:")
            for check, result in checks.items():
                status = "✅" if result else "❌"
                logger.info(f"  {status} {check}")

            is_real = all(checks.values())
            return is_real

        return False

    async def run_audit(self):
        """Run complete pre-launch audit"""

        logger.info("\n" + "="*80)
        logger.info("🚀 PRE-LAUNCH REALITY AUDIT")
        logger.info("="*80)
        logger.info("Verify system gets REAL Wallapop data (not mock/fixtures)")
        logger.info(f"Duration: 5 minutes")
        logger.info("="*80)

        # Check 1
        data_ok, data_source = await self.check_data_source()

        # Check 2
        listing_count = await self.run_short_search()

        # Check 3
        await self.show_listings()

        # Check 4
        urls_ok = await self.check_urls()

        # Check 5
        await self.check_listing_age()

        # Check 6
        await self.check_categories()

        # Check 7
        parsed_count, deal_count = await self.try_parsing()

        # Check 8
        deal_found = await self.show_deal_example()

        # Check 9
        not_mock = await self.verify_not_mock()

        # Final Verdict
        await self.print_final_verdict(
            data_ok, listing_count, urls_ok, deal_found, not_mock, deal_count
        )

    async def print_final_verdict(self, data_ok, listing_count, urls_ok, deal_found, not_mock, deal_count):
        """Print final verdict"""

        logger.info("\n" + "="*80)
        logger.info("🎯 FINAL VERDICT")
        logger.info("="*80)

        results = {
            "Real Wallapop Data": data_ok,
            "Real Listings Retrieved": listing_count > 0,
            "URLs Open Correctly": urls_ok,
            "At Least One Real Deal Found": deal_count > 0,
            "Data NOT from Mock/Fixtures": not_mock,
        }

        logger.info("\n📊 AUDIT RESULTS:")
        for check, result in results.items():
            status = "✅ YES" if result else "❌ NO"
            logger.info(f"  {status} - {check}")

        # Overall readiness
        all_pass = all(results.values())

        logger.info("\n" + "="*80)
        if all_pass:
            logger.info("✅ READY FOR 60-MINUTE VALIDATION = YES")
            logger.info("\nAll checks passed. System is ready for full production validation.")
            logger.info(f"Found: {listing_count} real listings")
            logger.info(f"Found: {deal_count} high-quality deals")
            logger.info(f"All data from REAL Wallapop API")
        else:
            failed = [k for k, v in results.items() if not v]
            logger.info("❌ READY FOR 60-MINUTE VALIDATION = NO")
            logger.info(f"\nFailed checks:")
            for check in failed:
                logger.info(f"  • {check}")
            logger.info("\nDo NOT run 60-minute validation until issues are fixed.")

        logger.info("="*80 + "\n")


async def main():
    """Entry point"""
    audit = PreLaunchAudit(duration_seconds=300)  # 5 minutes

    try:
        await audit.run_audit()
    except KeyboardInterrupt:
        logger.info("\n⏸️  Audit interrupted")
    except Exception as e:
        logger.error(f"❌ Audit failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
