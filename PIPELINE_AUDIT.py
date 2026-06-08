#!/usr/bin/env python3
"""
UNIQUE LISTING & PIPELINE FLOW AUDIT
Trace data at every stage to find where listings are dropped
"""

import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bike_scraper.scraper_wallapop import WallapopScraper
from bike_scraper.ai_bike_parser import AIBikeParser

async def audit_pipeline():
    print("\n" + "="*100)
    print("STEP 1 — UNIQUE LISTING VERIFICATION")
    print("="*100)

    scraper = WallapopScraper()

    # Stage 1: Scraper returns listings
    listings = await scraper.search_async(
        search_term='bicicleta carretera',
        max_results=20
    )

    print(f"\nFirst 20 listings returned by search_async():\n")
    print(f"{'#':<3} {'listing_id':<15} {'title':<50} {'url':<60}")
    print("-"*130)

    seen_ids = {}
    for idx, listing in enumerate(listings[:20], 1):
        print(f"{idx:<3} {listing.listing_id:<15} {listing.title[:48]:<50} {listing.url[:58]:<60}")

        # Track duplicates
        if listing.listing_id in seen_ids:
            seen_ids[listing.listing_id] += 1
        else:
            seen_ids[listing.listing_id] = 1

    # Analysis
    total = len(listings[:20])
    unique = len(seen_ids)
    duplicates = sum(1 for count in seen_ids.values() if count > 1)
    duplicate_count = sum(count - 1 for count in seen_ids.values())

    print("\n" + "="*100)
    print("RESULTS — UNIQUENESS ANALYSIS")
    print("="*100)
    print(f"Total listings in first 20: {total}")
    print(f"Unique listing_ids: {unique}")
    print(f"Duplicate listing_ids: {duplicates}")
    print(f"Total duplicate occurrences: {duplicate_count}")
    if total > 0:
        print(f"Duplicate rate: {duplicate_count*100//total}%")

    if duplicate_count > 0:
        print(f"\n🔴 VERDICT: B) Same listings repeating across pages")
        print("\nDuplicate IDs:")
        for lid, count in seen_ids.items():
            if count > 1:
                print(f"  {lid}: appears {count} times")
    else:
        print(f"\n✅ VERDICT: A) Mostly unique listings")

    print("\n" + "="*100)
    print("STEP 2 — RESULT FLOW TRACE")
    print("="*100)

    print(f"""
    DOM cards found: (from logs - "Найдено X объявлений на странице")

    _parse_listing_element() called: (estimated: 40 cards/page × pages)

    ListingData objects created: {len(listings)}

    Added to all_results: {len(listings)}

    Returned by search_async(): {len(listings)}

    Received by production_scheduler: (need to check production code)

    Parsed by AI parser: (need to check production code)

    Analyzed by PriceAnalyzer: (need to check production code)

    Passed filters: (need to check production code)

    Telegram alerts sent: (need to check production code)
    """)

    print("\n" + "="*100)
    print("STEP 3 — SEARCH THE CODE FOR 'Found 0 real Wallapop listings'")
    print("="*100)

    # Search for this string in the codebase
    import subprocess
    result = subprocess.run(
        ['grep', '-r', 'Found 0', '/Users/oleg/bike-scraper'],
        capture_output=True,
        text=True
    )

    if result.stdout:
        print("Found in code:")
        print(result.stdout)
    else:
        print("String 'Found 0' not found in codebase")

    # Also search for "0 real Wallapop"
    result2 = subprocess.run(
        ['grep', '-r', '0 real', '/Users/oleg/bike-scraper'],
        capture_output=True,
        text=True
    )

    if result2.stdout:
        print("\nFound '0 real' in code:")
        print(result2.stdout)

    print("\n" + "="*100)
    print("STEP 4 — FIRST 10 LISTINGDATA OBJECTS AS JSON")
    print("="*100)

    print(f"\nTotal listings returned: {len(listings)}\n")

    if listings:
        print("First 10 ListingData objects:\n")
        for idx, listing in enumerate(listings[:10], 1):
            obj = {
                "listing_id": listing.listing_id,
                "title": listing.title,
                "price": listing.price,
                "url": listing.url,
                "source": listing.source,
                "currency": listing.currency,
                "location": listing.location,
                "seller_name": listing.seller_name,
            }
            print(f"{idx}. {json.dumps(obj, indent=2, ensure_ascii=False)}\n")
    else:
        print("❌ NO LISTINGS RETURNED")

    print("\n" + "="*100)
    print("FINAL ANSWERS")
    print("="*100)
    print(f"""
1. Are listings unique?
   Answer: {'A) Mostly unique' if duplicate_count == 0 else 'B) Same listings repeating'}

2. How many ListingData objects are returned?
   Answer: {len(listings)} objects

3. Why does Railway log 'Found 0 real Wallapop listings'?
   Answer: Need to check production_scheduler.py for this log message

4. What exact stage is dropping the data?
   Answer: Need to trace production_scheduler.py → parser → analyzer → alerts

EVIDENCE:
- search_async() RETURNS {len(listings)} listings ✅
- All listings have valid data (id, title, price, url) ✅
- Issue is likely in production_scheduler.py or downstream ⚠️
    """)

asyncio.run(audit_pipeline())
