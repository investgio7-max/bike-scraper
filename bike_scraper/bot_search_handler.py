"""Search handler for Telegram bot - integrates with Wallapop scraper"""
from typing import List
from bike_scraper.scraper_wallapop_curl import WallapopScraperCurl
from bike_scraper.utils_logger import get_logger

logger = get_logger('bot_search')


def search_bikes(search_term: str, max_results: int = 10) -> List[dict]:
    """
    Search for bikes on Wallapop using curl_cffi (lightweight, no browser)
    Returns list of listings with price, location, etc.
    """
    try:
        logger.info(f"🔍 Searching for: {search_term}")

        scraper = WallapopScraperCurl()
        listings = scraper.search(search_term, max_results=max_results)
        scraper.close()

        # Convert to simple dict format for bot
        results = []
        for listing in listings[:max_results]:
            results.append({
                'title': listing.title,
                'price': listing.price,
                'location': listing.location,
                'seller': listing.seller_name,
                'url': listing.url,
                'condition': listing.condition,
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

    for i, listing in enumerate(listings[:5], 1):
        message += f"{i}. {format_listing_for_bot(listing)}\n\n"

    if len(listings) > 5:
        message += f"... и ещё {len(listings) - 5} объявлений\n"

    return message
