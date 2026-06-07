"""
Smart Wallapop scraper - tries CloakBrowser first, falls back to curl_cffi
"""
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
import re
import asyncio
import os

from bike_scraper.scraper_base import BaseScraper, ListingData
from bike_scraper.config import WALLAPOP_SEARCH_URL, MIN_PRICE, MAX_PRICE
from bike_scraper.utils_parser import BikeParser, normalize_price, parse_location
from bike_scraper.utils_logger import get_logger
from bike_scraper.anti_ban_manager import AntiBanManager

logger = get_logger('wallapop_smart')

# STEP 2: Filter by type - only ROAD and GRAVEL allowed
EXCLUDED_KEYWORDS = [
    "infantil", "niño", "niña", "children", "kid",  # Детские
    "mtb", "mountain", "montaña",  # MTB
    "eléctrico", "electric", "e-bike",  # Электровелосипеды
    "urbano", "urban", "city", "ciudad",  # Городские
    "repuestos", "piezas", "parts", "spare",  # Запчасти
    "cuadro", "frame", "rueda", "wheel", "llanta",  # Рамы, колёса
    "fixed gear", "fixie",  # Fixed gear
]

ALLOWED_TYPES = [
    "road", "carretera", "gravel",  # Только шоссейные и гравел
]

# STEP 3: Filter by brand - priority brands
PRIORITY_BRANDS = [
    "Canyon", "Specialized", "Cervelo", "Scott", "Pinarello",
    "BMC", "Trek", "Factor", "Colnago", "Wilier", "Ridley"
]

# Allowed categories - only bikes!
ALLOWED_CATEGORIES = [
    "bicicletas y triciclos",
    "bicicletas de carretera",
    "bicicleta",
    "bike",
    "велосипед"
]

# Прокси ротация - используем несколько прокси для дополнительной защиты
PROXY_LIST = [
    # PROXY ID 4409181
    'http://c4q4gcymn334yzSF:c4q4gcymn334yzSF@185.90.61.65:10059',
    # PROXY ID 4409302
    'http://OOqXa3lweR8708rP:OOqXa3lweR8708rP@185.186.76.214:11114',
]

CURRENT_PROXY_INDEX = 0

def get_next_proxy() -> str:
    """Получить следующий прокси из списка (ротация)"""
    global CURRENT_PROXY_INDEX
    CURRENT_PROXY_INDEX = (CURRENT_PROXY_INDEX + 1) % len(PROXY_LIST)
    proxy = PROXY_LIST[CURRENT_PROXY_INDEX]
    logger.info(f"🔄 Ротация прокси #{CURRENT_PROXY_INDEX + 1}/{len(PROXY_LIST)}")
    return proxy

# Инициализируем PROXY_URL
PROXY_URL = os.getenv('PROXY_URL')

if not PROXY_URL:
    PROXY_URL = PROXY_LIST[0]  # Начинаем с первого прокси
    logger.info(f"✅ Прокси ротация активирована ({len(PROXY_LIST)} прокси доступно)")

if PROXY_URL:
    logger.info(f"✅ Proxy configured")
else:
    logger.warning(f"⚠️ No proxy available!")



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
        self.anti_ban = AntiBanManager(min_delay=2, max_delay=8)  # 2-8 сек задержки

        if not self.use_cloak and HAS_CURL:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            })

    def search(self, search_term, max_results: int = 100) -> List[ListingData]:
        """Search - CloakBrowser primary (executes JS), curl_cffi fallback

        search_term can be:
        - str: "bicicleta carretera" (keyword search)
        - dict: {'keywords': 'Canyon', 'category_id': 17000} (category search)
        """
        # Use CloakBrowser first (renders JavaScript)
        if self.use_cloak:
            logger.info("🎭 Using CloakBrowser for search (primary - executes JS)")
            results = asyncio.run(self._search_cloak(search_term, max_results))
            if results:
                return results
            logger.warning("⚠️ CloakBrowser returned 0 results, trying curl_cffi...")

        # Fallback to curl_cffi if CloakBrowser failed
        if HAS_CURL:
            logger.info("📡 Using curl_cffi as fallback...")
            return self._search_curl(search_term, max_results)

        logger.error("❌ No scraping tool available!")
        return []

    async def _search_cloak(self, search_term, max_results: int = 100) -> List[ListingData]:
        """Search using CloakBrowser

        search_term can be str or dict with category_id
        """
        all_listings = []
        page = 0

        try:
            logger.info("🎭 Using CloakBrowser for search")

            # Prepare launch options с включением человеческого поведения
            launch_opts = {
                "headless": True,
                "proxy": PROXY_URL,  # Always pass proxy
                # 🤖 Встроенные функции человеческого поведения CloakBrowser:
                "human_behavior": True,  # Включаем имитацию человека
                "disable_blink_features": [
                    "AutomationControlled",  # Скрываем automation контроль
                    "ChromeHeadless"  # Скрываем headless режим
                ]
            }

            logger.info(f"🔗 CloakBrowser with human behavior + proxy")

            browser = await launch_async(**launch_opts)
            logger.info("✅ CloakBrowser launched")
            page_obj = await browser.new_page()
            logger.info("✅ Page created")

            while len(all_listings) < max_results:
                # Build URL - support both keyword search and category search
                if isinstance(search_term, dict):
                    # Category-based search
                    keywords = search_term.get('keywords', '').replace(' ', '+')
                    category_id = search_term.get('category_id', 17000)
                    subcategory_id = search_term.get('subcategory_id', 10438)
                    url = f"{self.base_url}?keywords={keywords}&category_id={category_id}&subcategory_ids={subcategory_id}&start={page * 50}"
                    search_display = f"{search_term['keywords']} (cat: {category_id})"
                else:
                    # Simple keyword search
                    url = f"{self.base_url}?keywords={search_term.replace(' ', '+')}&start={page * 50}"
                    search_display = search_term
                logger.info(f"📄 Loading: {search_display} (page {page + 1})")

                try:
                    # Try with domcontentloaded (faster than networkidle, sufficient for Wallapop)
                    response = await page_obj.goto(url, wait_until='domcontentloaded', timeout=60000)
                    logger.info(f"✅ Page loaded (domcontentloaded) - Status: {response.status if response else 'Unknown'}")

                    # 🤖 Имитация человеческого поведения:
                    # 1. Случайное прокручивание страницы
                    scroll_height = await page_obj.evaluate("document.body.scrollHeight")
                    for _ in range(random.randint(2, 4)):
                        scroll_y = random.randint(0, int(scroll_height))
                        await page_obj.evaluate(f"window.scrollBy(0, {scroll_y})")
                        await page_obj.wait_for_timeout(random.uniform(500, 1500))  # Пауза при "чтении"

                    logger.info("🤖 Human-like scrolling simulated")

                    # 2. Случайные движения мыши
                    await page_obj.mouse.move(
                        random.randint(100, 800),
                        random.randint(100, 600)
                    )
                    await page_obj.wait_for_timeout(random.uniform(300, 800))

                    # 3. Дополнительное ожидание для JS рендеринга (15 секунд)
                    await page_obj.wait_for_timeout(15000)
                    logger.info("✅ Extra wait for JS rendering (15s)")

                    # Check for Cloudflare blocks
                    if response:
                        logger.info(f"📡 Response status: {response.status}")
                        if response.status == 403:
                            logger.error("❌ 403 Forbidden - Cloudflare is blocking!")
                        elif response.status == 429:
                            logger.error("❌ 429 Too Many Requests - Rate limited!")
                        elif response.status >= 500:
                            logger.error(f"❌ {response.status} Server error!")

                except Exception as e:
                    logger.error(f"❌ Failed to load page: {e}")
                    if page == 0:
                        # First page failed, return what we have
                        break
                    else:
                        # Later page failed, stop and return results so far
                        logger.info(f"Stopping after page {page}")
                        break

                html = await page_obj.content()
                logger.info(f"📊 HTML size: {len(html)} bytes")

                # Check for Cloudflare error page markers
                if 'cloudflare' in html.lower():
                    logger.warning("⚠️ Cloudflare detected in HTML!")
                if 'error' in html.lower() or 'problem' in html.lower():
                    logger.warning("⚠️ Error keywords found in HTML")

                # Log first 1000 chars of HTML
                logger.debug(f"HTML preview: {html[:1000]}")

                # Save HTML to file for analysis
                with open(f'/tmp/wallapop_page_{page}.html', 'w') as f:
                    f.write(html)
                logger.debug(f"💾 HTML saved to /tmp/wallapop_page_{page}.html")

                soup = BeautifulSoup(html, 'html.parser')

                # Try to find listings - multiple selectors
                listings = []

                # Method 1: Try articles with item-card
                all_articles = soup.find_all('article')
                logger.info(f"📊 Total articles: {len(all_articles)}")

                if all_articles:
                    for idx, article in enumerate(all_articles[:3]):
                        classes = ' '.join(article.get('class', []))
                        text_preview = article.get_text(strip=True)[:80]
                        logger.info(f"  Article {idx}: {classes[:80]} | {text_preview}")

                for article in all_articles:
                    classes = ' '.join(article.get('class', []))
                    if 'item-card' in classes and 'vertical' in classes:
                        listings.append(article)

                if listings:
                    logger.info(f"✅ Found {len(listings)} articles with item-card+vertical")
                else:
                    # Method 2: Try divs with item-card class
                    logger.info("❌ No articles found, trying divs with item-card...")
                    divs_with_card = soup.find_all('div', class_=lambda x: x and 'item-card' in x and 'vertical' in x)
                    logger.info(f"🔍 Found {len(divs_with_card)} divs with item-card+vertical")
                    listings = divs_with_card

                if not listings:
                    logger.warning("⚠️ No listings found - might be empty results or error page")
                    # Log page title for debugging
                    title = soup.find('title')
                    if title:
                        logger.info(f"📄 Page title: {title.get_text()}")

                if not listings:
                    listings = soup.find_all('a', attrs={'data-testid': lambda x: x and 'item' in x.lower()})
                    logger.info(f"🔍 data-testid items: {len(listings)}")

                logger.info(f"📋 Total listings found: {len(listings)} on page {page + 1}")

                if not listings:
                    logger.warning("⚠️ No listings found, stopping search")
                    break

                logger.debug(f"🔎 Parsing {len(listings)} elements...")
                parsed_count = 0
                for i, elem in enumerate(listings):
                    if len(all_listings) >= max_results:
                        logger.info(f"✓ Reached max_results ({max_results})")
                        break
                    listing = self.parse_listing(elem)
                    if listing:
                        # Skip duplicate listings (same ID)
                        if listing.listing_id not in seen_ids:
                            parsed_count += 1
                            seen_ids.add(listing.listing_id)
                            all_listings.append(listing)
                        else:
                            logger.debug(f"Duplicate: {listing.listing_id}")

                logger.info(f"📊 Parsed {parsed_count}/{len(listings)} elements on page {page + 1}")

                page += 1

                # Add delay between pages to avoid Cloudflare blocks
                if len(all_listings) < max_results:
                    import time as time_module
                    logger.info("⏳ Waiting 5 seconds before next page...")
                    await asyncio.sleep(5)

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

    def _search_curl(self, search_term, max_results: int = 100) -> List[ListingData]:
        """Search using curl_cffi - supports str or dict with category_id"""
        global PROXY_URL  # Allow proxy rotation
        all_listings = []
        seen_ids = set()  # Track seen listing IDs to avoid duplicates
        page = 0

        while len(all_listings) < max_results:
            try:
                # Build URL - support both keyword search and category search
                if isinstance(search_term, dict):
                    keywords = search_term.get('keywords', '').replace(' ', '+')
                    category_id = search_term.get('category_id', 17000)
                    subcategory_id = search_term.get('subcategory_id', 10438)
                    url = f"{self.base_url}?keywords={keywords}&category_id={category_id}&subcategory_ids={subcategory_id}&start={page * 50}"
                else:
                    url = f"{self.base_url}?keywords={search_term.replace(' ', '+')}&start={page * 50}"
                logger.debug(f"📄 Fetching: {url}")

                try:
                    # Anti-ban: ждем перед запросом
                    self.anti_ban.wait_before_request()

                    # Prepare request kwargs with rotating User-Agent
                    kwargs = {
                        "impersonate": "chrome120",
                        "timeout": 30,
                        "headers": {
                            "User-Agent": self.anti_ban.get_random_user_agent()
                        }
                    }

                    # Add proxy if configured
                    if PROXY_URL:
                        kwargs["proxy"] = PROXY_URL
                        logger.debug(f"🔗 Using proxy for request")

                    response = self.session.get(url, **kwargs)
                    logger.info(f"📡 curl_cffi Status: {response.status_code}, size: {len(response.text)} bytes")

                    # Anti-ban: зафиксировать успех
                    if response.status_code == 200:
                        self.anti_ban.on_request_success()

                except Exception as e:
                    logger.error(f"❌ curl_cffi request failed: {e}")
                    self.anti_ban.on_request_error()
                    break

                if response.status_code == 403:
                    logger.error("❌ 403 Forbidden - Cloudflare is blocking curl_cffi!")
                    self.anti_ban.on_request_error(403)  # Сигнал о блокировке

                    # Пробуем переключиться на другой прокси
                    PROXY_URL = get_next_proxy()
                    logger.info(f"🔄 Переключился на другой прокси после 403")

                elif response.status_code == 429:
                    logger.error("❌ 429 Too Many Requests - Rate limited!")
                    self.anti_ban.on_request_error(429)
                elif response.status_code >= 500:
                    logger.error(f"❌ {response.status_code} Server error!")
                    self.anti_ban.on_request_error(response.status_code)

                if response.status_code != 200:
                    logger.warning(f"⚠️ Non-200 status, stopping: {response.status_code}")
                    break

                # Check for Cloudflare in response
                if 'cloudflare' in response.text.lower():
                    logger.warning("⚠️ Cloudflare detected in curl_cffi response!")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')

                listings = soup.find_all('div', class_=lambda x: x and 'ItemCard' in x)
                if not listings:
                    listings = soup.find_all('article')

                logger.debug(f"📋 Found {len(listings)} on page {page + 1}")

                if not listings:
                    break

                for i, elem in enumerate(listings):
                    if len(all_listings) >= max_results:
                        break
                    logger.debug(f"🔎 curl parsing element {i+1}")
                    listing = self.parse_listing(elem)
                    if listing:
                        # Skip duplicate listings (same ID)
                        if listing.listing_id not in seen_ids:
                            logger.info(f"✅ curl parsed: {listing.title[:50]}... (€{listing.price})")
                            seen_ids.add(listing.listing_id)
                            all_listings.append(listing)
                        else:
                            logger.debug(f"Duplicate: {listing.listing_id}")

                page += 1

            except Exception as e:
                logger.error(f"❌ curl_cffi error: {e}")
                break

        logger.info(f"✅ Found {len(all_listings)} listings (curl_cffi)")
        return all_listings

    def parse_listing(self, elem) -> ListingData:
        """Parse listing element - Wallapop structure: "1 / 3350 €Bicicleta Trek FX3" """
        try:
            # Skip non-item elements (badges, images, etc)
            classes = elem.get('class', [])
            class_str = ' '.join(classes) if isinstance(classes, list) else str(classes)

            logger.debug(f"Classes: {class_str[:100]}")

            if 'item-card_ItemCard--vertical' not in class_str:
                logger.debug(f"⚠️ Wrong class, skipping: {class_str[:100]}")
                return None

            # Get full text from article element
            text = elem.get_text(strip=True)
            if not text or '€' not in text:
                logger.info(f"⚠️ Element missing text or €: {text[:50] if text else 'empty'}")
                return None

            # Parse format: "1 / 3350 €Bicicleta Trek FX3 Gen 3"
            # Split on € to get price and title
            parts = text.split('€', 1)
            if len(parts) < 2:
                logger.info(f"⚠️ Could not split on €: {text[:100]}")
                return None

            # Extract price from first part (last number before €)
            price_part = parts[0].strip()
            # Get last number from price part
            import re as regex
            price_match = regex.search(r'(\d+(?:[.,]\d+)?)\s*$', price_part)
            if not price_match:
                logger.info(f"⚠️ No price found in: {price_part[:100]}")
                return None

            price_text = price_match.group(1)
            price = normalize_price(price_text)

            # Get title from second part
            title = parts[1].strip()
            if not title or title == "":
                logger.info(f"⚠️ Empty title after €")
                return None

            logger.info(f"✅ Parsed: {title[:50]}... (€{price})")

            # CRITICAL: Filter by CATEGORY - MUST be actual bike, not parts/clothes/accessories
            title_lower = title.lower()

            # STEP 1: Check if this is actually a BIKE (not clothing/accessories)
            # Reject common non-bike categories
            non_bike_keywords = [
                'guantes', 'gafas', 'casco', 'maillot', 'pantalón', 'short', 'medias',
                'zapatillas', 'zapatos', 'ropa', 'rayo', 'chaleco', 'jersey', 'camiseta',
                'chaqueta', 'bufanda', 'calcetines', 'complemento', 'accesorio',
                'luces', 'luz', 'faro', 'linterna', 'rodillo', 'entrenador',
                'soporte', 'cesta', 'caballete', 'manillar', 'lote', 'set', 'combo',
                'equipo', 'completo', 'catálogo', 'revista'
            ]

            if any(keyword in title_lower for keyword in non_bike_keywords):
                logger.debug(f"⚠️ Filtered (not a bike): {title[:40]}")
                return None

            # STEP 2: Must contain "bicicleta" or specific bike type
            has_bike_keyword = any(keyword in title_lower for keyword in ['bicicleta', 'bike', 'ciclo'])
            if not has_bike_keyword:
                logger.debug(f"⚠️ Filtered (no bike keyword): {title[:40]}")
                return None

            # STEP 3: Exclude unwanted types (kids bikes, MTB, electric, urban, etc.)
            for excluded in EXCLUDED_KEYWORDS:
                if excluded.lower() in title_lower:
                    logger.debug(f"⚠️ Excluded ({excluded}): {title[:40]}")
                    return None

            # STEP 4: Only accept ROAD or GRAVEL bikes
            is_allowed_type = any(t.lower() in title_lower for t in ALLOWED_TYPES)
            if not is_allowed_type:
                logger.debug(f"⚠️ Not ROAD/GRAVEL (filtered): {title[:40]}")
                return None

            # STEP 3: Check brand
            has_priority_brand = any(brand.lower() in title_lower for brand in PRIORITY_BRANDS)
            brand_status = "✨ Priority" if has_priority_brand else "📌 Other"
            logger.debug(f"🏢 Brand status: {brand_status} - {title[:40]}")

            # Filter by price
            if price and (price < MIN_PRICE or price > MAX_PRICE):
                logger.debug(f"💸 Filtered by price: {title[:40]}... (€{price}, range: €{MIN_PRICE}-€{MAX_PRICE})")
                return None

            # Try to find URL
            link_elem = elem.find('a', href=True)
            url = link_elem['href'] if link_elem else ""
            if not url.startswith('http'):
                url = f"https://www.wallapop.com{url}"

            # Extract listing_id from URL (/item/12345 -> 12345)
            listing_id = "unknown"
            if url:
                match = re.search(r'/item/(\d+)', url)
                if match:
                    listing_id = match.group(1)

            return ListingData(
                source='wallapop',
                listing_id=listing_id,
                url=url,
                title=title,
                description=title,
                price=price,
                currency='EUR',
                seller_name="",
                seller_id=None,
                seller_rating=None,
                seller_reviews_count=None,
                location="",
                country='Spain',
                date_posted=None,
                images=[],
                raw_data={}
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
