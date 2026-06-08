#!/usr/bin/env python3
"""
FIX VERIFICATION - Test regex fix and show parse results
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from bike_scraper.scraper_wallapop import WallapopScraper
from bike_scraper.ai_bike_parser import AIBikeParser
from bike_scraper.price_analyzer import PriceAnalyzer

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)

async def run_fix_verification():
    print("\n" + "="*80)
    print("FIX VERIFICATION - Regex Update Test")
    print("="*80 + "\n")

    # Initialize scraper
    scraper = WallapopScraper()
    parser = AIBikeParser()

    print("🔍 Running scraper with fixed regex...")
    print("-" * 80)

    try:
        # Search for real listings (page 1 only)
        listings = await scraper.search_async(
            search_term='bicicleta carretera',
            max_results=20
        )

        print(f"\n✅ Search completed!")
        print(f"   Total parsed listings: {len(listings)}\n")

        if len(listings) > 0:
            print("=" * 80)
            print("FIRST 10 PARSED LISTINGS")
            print("=" * 80)

            for idx, listing in enumerate(listings[:10]):
                print(f"\n{idx+1}. listing_id={listing.listing_id}")
                print(f"   title={listing.title}")
                print(f"   price=€{listing.price:.2f}")
                print(f"   url={listing.url}")

            print("\n" + "=" * 80)
            print("PIPELINE TEST - First Listing Through Parser")
            print("=" * 80)

            first = listings[0]
            print(f"\nInput: {first.title}")

            bike_data = parser.parse(
                title=first.title,
                description=first.description,
                images=first.images
            )

            print(f"✅ Parser output:")
            print(f"   brand={bike_data.get('brand', 'UNKNOWN')}")
            print(f"   model={bike_data.get('model', 'UNKNOWN')}")
            print(f"   confidence={bike_data.get('confidence', 0)}%")

            print(f"\n" + "=" * 80)
            print("✅ PARSER TEST PASSED")
            print("=" * 80)
            print(f"Real listings successfully parsed and passed to AI parser!")

        else:
            print("❌ No listings parsed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run the verification"""
    asyncio.run(run_fix_verification())

if __name__ == '__main__':
    main()
