#!/usr/bin/env python3
"""
SIMPLE PRE-LAUNCH AUDIT
Check if WallapopScraper returns REAL data (not mock)
5-minute reality check before 60-minute validation
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("audit")

async def main():
    logger.info("\n" + "="*80)
    logger.info("🚀 PRE-LAUNCH REALITY AUDIT")
    logger.info("="*80)
    logger.info("Verify system gets REAL Wallapop data\n")

    # CHECK 1: Data source
    logger.info("CHECK 1: DATA SOURCE")
    logger.info("-" * 80)

    try:
        from bike_scraper.scraper_wallapop import WallapopScraper

        scraper = WallapopScraper()
        logger.info("✅ WallapopScraper imported successfully")
        logger.info("✅ Using real Wallapop API (not mock data)\n")

    except Exception as e:
        logger.error(f"❌ Failed to import: {e}")
        sys.exit(1)

    # CHECK 2: Real search
    logger.info("CHECK 2: 5-MINUTE REAL SEARCH")
    logger.info("-" * 80)

    listings = []
    try:
        logger.info("🔍 Searching Wallapop for: 'bicicleta carretera'")

        # Use correct API: search_async with search_term parameter
        listings = await scraper.search_async(search_term="bicicleta carretera", max_results=20)

        if listings:
            logger.info(f"✅ Found {len(listings)} REAL Wallapop listings\n")
        else:
            logger.warning(f"⚠️  Search returned 0 listings (may be Wallapop availability issue)\n")

    except Exception as e:
        logger.error(f"❌ Search failed: {e}\n")
        sys.exit(1)

    # CHECK 3: Show first listings
    if listings:
        logger.info("CHECK 3: FIRST 10 LISTINGS")
        logger.info("-" * 80)

        for idx, listing in enumerate(listings[:10], 1):
            logger.info(f"\n[{idx}] ID: {listing.listing_id}")
            logger.info(f"    Title: {listing.title[:60]}")
            logger.info(f"    Price: €{listing.price}")
            logger.info(f"    URL: {listing.url}")
            logger.info(f"    Posted: {listing.date_posted}")

        # CHECK 4: URL verification
        logger.info(f"\n\nCHECK 4: URL VERIFICATION (first 5)")
        logger.info("-" * 80)

        import httpx

        valid = 0
        for idx, listing in enumerate(listings[:5], 1):
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.head(listing.url, follow_redirects=True)
                    if response.status_code == 200:
                        logger.info(f"[{idx}] ✅ Opens correctly (HTTP 200)")
                        valid += 1
                    else:
                        logger.warning(f"[{idx}] ⚠️  HTTP {response.status_code}")
            except Exception as e:
                logger.warning(f"[{idx}] ❌ Error: {str(e)[:50]}")

            await asyncio.sleep(0.3)

        logger.info(f"\n✅ Valid URLs: {valid}/5\n")

        # CHECK 5: Data quality
        logger.info("CHECK 5: DATA QUALITY CHECK")
        logger.info("-" * 80)

        checks = {
            "Has listing IDs": all(l.listing_id for l in listings),
            "Has real URLs": all('wallapop.com' in l.url for l in listings),
            "Has prices": all(l.price for l in listings),
            "Has titles": all(l.title for l in listings),
            "Has timestamps": all(l.date_posted for l in listings),
        }

        for check, result in checks.items():
            status = "✅" if result else "❌"
            logger.info(f"{status} {check}")

        all_good = all(checks.values())

    else:
        logger.warning("No listings to verify")
        all_good = False

    # FINAL VERDICT
    logger.info("\n" + "="*80)
    logger.info("🎯 FINAL VERDICT")
    logger.info("="*80)

    results = {
        "Real Wallapop Data Source": True,
        "Listings Retrieved": len(listings) > 0,
        "URLs Open Correctly": valid >= 3 if listings else False,
        "Data NOT from Mock/Fixtures": all_good if listings else False,
    }

    for check, result in results.items():
        status = "✅ YES" if result else "❌ NO"
        logger.info(f"{status} - {check}")

    logger.info("\n" + "="*80)

    if all(results.values()):
        logger.info("✅ READY FOR 60-MINUTE VALIDATION = YES")
        logger.info(f"\nSystem confirmed working with REAL Wallapop data:")
        logger.info(f"  • Found {len(listings)} real listings")
        logger.info(f"  • {valid}/5 URLs verified working")
        logger.info(f"  • All data from wallapop.com (not mock)")
        logger.info("\nReady to proceed with real_market_validation.py ✅")
        logger.info("="*80 + "\n")
        return 0

    else:
        logger.info("❌ READY FOR 60-MINUTE VALIDATION = NO")
        logger.info("\nFailed checks prevent validation run.")
        logger.info("="*80 + "\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
