"""
Wallapop scraper using curl_cffi (lightweight, fast, no full browser needed)
"""
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
from curl_cffi import requests
import re

from bike_scraper.scraper_base import BaseScraper, ListingData
from bike_scraper.config import WALLAPOP_SEARCH_URL, MIN_PRICE, MAX_PRICE
from bike_scraper.utils_parser import BikeParser, normalize_price, parse_location
from bike_scraper.utils_logger import get_logger

logger = get_logger('wallapop_curl')


class WallapopScraperCurl(BaseScraper):
    """Lightweight Wallapop scraper using curl_cffi"""

    def __init__(self):
        super().__init__('wallapop_curl')
        self.base_url = WALLAPOP_SEARCH_URL
        self.session = requests.Session()

        # Set browser-like headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.wallapop.com/',
        })

    def search(self, search_term: str, max_results: int = 100) -> List[ListingData]:
        """Search for bikes using curl_cffi (synchronous)"""
        logger.info(f"🔍 Searching: {search_term}")

        all_listings = []
        page = 0

        while len(all_listings) < max_results:
            try:
                # Build URL with search params
                url = f"{self.base_url}?keywords={search_term.replace(' ', '+')}&start={page * 50}"

                logger.debug(f"📄 Fetching: {url}")

                # Use curl_cffi to fetch (impersonates Chrome)
                response = self.session.get(
                    url,
                    impersonate="chrome120",  # Impersonate Chrome 120
                    timeout=30
                )

                logger.debug(f"📊 Response status: {response.status_code}, size: {len(response.text)} bytes")

                if response.status_code != 200:
                    logger.warning(f"⚠️ Status {response.status_code}")
                    logger.debug(f"Response: {response.text[:500]}")
                    break

                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find listings (adapt selectors if needed)
                listings = soup.find_all('div', class_=lambda x: x and 'ItemCard' in x)
                logger.debug(f"🔍 Found {len(listings)} ItemCard divs")

                if not listings:
                    listings = soup.find_all('article')
                    logger.debug(f"🔍 Found {len(listings)} article tags")

                if not listings:
                    # Try alternative selector
                    listings = soup.find_all('a', attrs={'href': lambda x: x and '/item/' in x})
                    logger.debug(f"🔍 Found {len(listings)} item links")

                if not listings:
                    logger.debug(f"No listings found on page {page + 1}")
                    break

                logger.info(f"📋 Found {len(listings)} listings on page {page + 1}")

                # Parse each listing
                for listing_elem in listings:
                    if len(all_listings) >= max_results:
                        break

                    try:
                        listing = self._parse_listing(listing_elem)
                        if listing:
                            all_listings.append(listing)
                    except Exception as e:
                        logger.debug(f"⚠️ Parse error: {e}")
                        continue

                page += 1

            except Exception as e:
                logger.error(f"❌ Error on page {page}: {e}")
                break

        logger.info(f"✅ Found {len(all_listings)} total listings")
        return all_listings

    def parse_listing(self, elem) -> ListingData:
        """Parse a single listing element"""
        try:
            # Extract title
            title_elem = elem.find('h2') or elem.find('a')
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"

            # Extract price
            price_elem = elem.find('span', class_=lambda x: x and 'Price' in x)
            if not price_elem:
                # Try alternative price selectors
                price_elem = elem.find('span', class_=lambda x: x and 'price' in (x or '').lower())
            if not price_elem:
                price_elem = elem.find('span', attrs={'data-test': 'product-price'})

            price_text = price_elem.get_text(strip=True) if price_elem else "0"
            price = normalize_price(price_text)

            logger.info(f"💰 Parsed: {title[:50]}... Price: {price_text}")

            # Extract location
            location_elem = elem.find('span', class_=lambda x: x and 'location' in (x or '').lower())
            location = location_elem.get_text(strip=True) if location_elem else "Unknown"

            # Extract seller
            seller_elem = elem.find('span', class_=lambda x: x and 'seller' in (x or '').lower())
            seller = seller_elem.get_text(strip=True) if seller_elem else "Unknown"

            # Extract URL
            link_elem = elem.find('a', href=True)
            url = link_elem['href'] if link_elem else ""
            if not url.startswith('http'):
                url = f"https://www.wallapop.com{url}"

            # Filter by price
            if price and (price < MIN_PRICE or price > MAX_PRICE):
                logger.info(f"💸 Filtered by price: {title[:40]}... (€{price}, range: €{MIN_PRICE}-€{MAX_PRICE})")
                return None

            return ListingData(
                title=title,
                price=price,
                location=location,
                seller_name=seller,
                url=url,
                images=[],
                condition="unknown",
                description=title
            )

        except Exception as e:
            logger.debug(f"Parse error: {e}")
            return None

    def close(self):
        """Close session"""
        if self.session:
            self.session.close()
        logger.info("✅ Session closed")


def create_wallapop_curl_scraper() -> WallapopScraperCurl:
    """Factory function"""
    return WallapopScraperCurl()
