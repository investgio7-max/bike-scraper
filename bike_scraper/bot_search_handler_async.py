"""Search handler for async Telegram bot - uses CloakBrowser"""
from typing import List
import asyncio
from bike_scraper.scraper_wallapop_smart import WallapopScraperSmart
from bike_scraper.utils_logger import get_logger

logger = get_logger('bot_search')


async def search_bikes_async(search_term: str, max_results: int = 50) -> List[dict]:
    """
    Search for bikes on Wallapop using CloakBrowser (async version for bot)
    Returns list of listings with price, location, etc.

    This version works correctly in async context (Telegram bot event loop)
    """
    try:
        logger.info(f"🔍 Searching for: {search_term}")

        scraper = WallapopScraperSmart()

        # Convert to category-based search (official Wallapop category)
        # category_id=17000 = Bicicletas y triciclos
        search_params = {
            'keywords': search_term,
            'category_id': 17000,
            'subcategory_id': 10438
        }

        # Call the sync search which internally uses CloakBrowser/curl_cffi
        listings = await asyncio.to_thread(scraper.search, search_params, max_results)
        scraper.close()

        # Convert to simple dict format for bot, with deduplication
        results = []
        seen_ids = set()
        for listing in listings[:max_results]:
            if listing.listing_id not in seen_ids:
                seen_ids.add(listing.listing_id)
                results.append({
                    'title': listing.title,
                    'price': listing.price,
                    'location': listing.location,
                    'seller': listing.seller_name,
                    'url': listing.url,
                })

        logger.info(f"✅ Found {len(results)} listings")
        return results

    except Exception as e:
        logger.error(f"❌ Search error: {e}")
        return []


def format_listing_for_bot(listing: dict) -> str:
    """Format a listing for display in Telegram"""
    return (
        f"💰 {listing['title']}\n"
        f"€ {listing['price']}\n"
        f"📍 {listing['location']}\n"
        f"👤 {listing['seller']}\n"
        f"🔗 {listing['url'][:50]}..."
    )


def format_search_results(listings: List[dict]) -> str:
    """Format search results for bot"""
    if not listings:
        return "❌ Объявления не найдены"

    message = f"🎯 Найдено {len(listings)} объявлений:\n\n"

    # Show all listings (up to max_results which is 10)
    for i, listing in enumerate(listings, 1):
        message += f"{i}. {format_listing_for_bot(listing)}\n\n"

    return message
