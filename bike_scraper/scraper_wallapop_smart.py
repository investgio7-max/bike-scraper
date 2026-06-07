"""
Smart Wallapop scraper - tries CloakBrowser first, falls back to curl_cffi
"""
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
import re
import asyncio

from bike_scraper.scraper_base import BaseScraper, ListingData
from bike_scraper.config import WALLAPOP_SEARCH_URL, MIN_PRICE, MAX_PRICE
from bike_scraper.utils_parser import BikeParser, normalize_price, parse_location
from bike_scraper.utils_logger import get_logger

logger = get_logger('wallapop_smart')

# Try to import CloakBrowser
try:
    from cloakbrowser import launch_async
    HAS_CLOAK = True
    logger.info("✅ CloakBrowser available")
except ImportError:
    HAS_CLOAK = False
    logger.warning("⚠️ CloakBrowser not available, will use curl_cffi")

# Import curl_cffi as fallback
try:
    from curl_cffi import requests
    HAS_CURL = True
except ImportError:
    HAS_CURL = False


class WallapopScraperSmart(BaseScraper):
    """Smart scraper that uses CloakBrowser or curl_cffi"""

    def __init__(self):
        super().__init__('wallapop_smart')
        self.base_url = WALLAPOP_SEARCH_URL
        self.use_cloak = HAS_CLOAK

        if not self.use_cloak and HAS_CURL:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            })

    def search(self, search_term: str, max_results: int = 100) -> List[ListingData]:
        """Search - uses sync or async depending on available tools"""
        if self.use_cloak:
            logger.info("🎭 Using CloakBrowser for search")
            return asyncio.run(self._search_cloak(search_term, max_results))
        elif HAS_CURL:
            logger.info("📡 Using curl_cffi for search")
            return self._search_curl(search_term, max_results)
        else:
            logger.error("❌ No scraping tool available!")
            return []

    async def _search_cloak(self, search_term: str, max_results: int = 100) -> List[ListingData]:
        """Search using CloakBrowser"""
        all_listings = []
        page = 0

        try:
            logger.info("🎭 Launching CloakBrowser...")
            browser = await launch_async(headless=True)
            logger.info("✅ CloakBrowser launched")
            page_obj = await browser.new_page()
            logger.info("✅ Page created")

            while len(all_listings) < max_results:
                url = f"{self.base_url}?keywords={search_term.replace(' ', '+')}&start={page * 50}"
                logger.info(f"📄 Loading: {url}")

                await page_obj.goto(url, wait_until='networkidle', timeout=30000)
                logger.info("✅ Page loaded")

                await page_obj.wait_for_timeout(3000)  # Wait for JS to load
                logger.info("✅ Waited for JS")

                html = await page_obj.content()
                logger.info(f"📊 HTML size: {len(html)} bytes")

                # Log first 1000 chars of HTML
                logger.debug(f"HTML preview: {html[:1000]}")

                soup = BeautifulSoup(html, 'html.parser')

                # Try multiple selectors
                listings = soup.find_all('div', class_=lambda x: x and 'ItemCard' in x)
                logger.info(f"🔍 ItemCard divs: {len(listings)}")

                if not listings:
                    listings = soup.find_all('article')
                    logger.info(f"🔍 article tags: {len(listings)}")

                if not listings:
                    listings = soup.find_all('a', attrs={'data-testid': lambda x: x and 'item' in x.lower()})
                    logger.info(f"🔍 data-testid items: {len(listings)}")

                logger.info(f"📋 Total listings found: {len(listings)} on page {page + 1}")

                if not listings:
                    logger.warning("⚠️ No listings found, stopping search")
                    break

                for elem in listings:
                    if len(all_listings) >= max_results:
                        break
                    listing = self.parse_listing(elem)
                    if listing:
                        all_listings.append(listing)

                page += 1

            await page_obj.close()
            await browser.close()

        except Exception as e:
            logger.error(f"❌ CloakBrowser error: {e}")
            # Fallback to curl_cffi
            if HAS_CURL:
                logger.info("⚠️ Falling back to curl_cffi")
                return self._search_curl(search_term, max_results)
            return []

        logger.info(f"✅ Found {len(all_listings)} listings (CloakBrowser)")
        return all_listings

    def _search_curl(self, search_term: str, max_results: int = 100) -> List[ListingData]:
        """Search using curl_cffi"""
        all_listings = []
        page = 0

        while len(all_listings) < max_results:
            try:
                url = f"{self.base_url}?keywords={search_term.replace(' ', '+')}&start={page * 50}"
                logger.debug(f"📄 Fetching: {url}")

                response = self.session.get(
                    url,
                    impersonate="chrome120",
                    timeout=30
                )

                logger.debug(f"📊 Status: {response.status_code}, size: {len(response.text)}")

                if response.status_code != 200:
                    break

                soup = BeautifulSoup(response.text, 'html.parser')

                listings = soup.find_all('div', class_=lambda x: x and 'ItemCard' in x)
                if not listings:
                    listings = soup.find_all('article')

                logger.debug(f"📋 Found {len(listings)} on page {page + 1}")

                if not listings:
                    break

                for elem in listings:
                    if len(all_listings) >= max_results:
                        break
                    listing = self.parse_listing(elem)
                    if listing:
                        all_listings.append(listing)

                page += 1

            except Exception as e:
                logger.error(f"❌ curl_cffi error: {e}")
                break

        logger.info(f"✅ Found {len(all_listings)} listings (curl_cffi)")
        return all_listings

    def parse_listing(self, elem) -> ListingData:
        """Parse listing element"""
        try:
            title_elem = elem.find('h2') or elem.find('a')
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"

            price_elem = elem.find('span', class_=lambda x: x and 'Price' in x)
            price_text = price_elem.get_text(strip=True) if price_elem else "0"
            price = normalize_price(price_text)

            location_elem = elem.find('span', class_=lambda x: x and 'location' in (x or '').lower())
            location = location_elem.get_text(strip=True) if location_elem else "Unknown"

            seller_elem = elem.find('span', class_=lambda x: x and 'seller' in (x or '').lower())
            seller = seller_elem.get_text(strip=True) if seller_elem else "Unknown"

            link_elem = elem.find('a', href=True)
            url = link_elem['href'] if link_elem else ""
            if not url.startswith('http'):
                url = f"https://www.wallapop.com{url}"

            logger.debug(f"📄 Parsed: {title[:50]}... Price: {price_text} (€{price})")

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
        """Close resources"""
        if hasattr(self, 'session'):
            self.session.close()
        logger.info("✅ Session closed")


def create_wallapop_smart_scraper() -> WallapopScraperSmart:
    """Factory function"""
    return WallapopScraperSmart()
