"""
Парсер для Wallapop (Испания)
Использует CloakBrowser + Playwright для обработки JavaScript контента
"""

from typing import List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import re
import asyncio
import os
from playwright.async_api import async_playwright

from bike_scraper.scraper_base import BaseScraper, ListingData
from bike_scraper.config import WALLAPOP_SEARCH_URL, MIN_PRICE, MAX_PRICE
from bike_scraper.utils_parser import BikeParser, normalize_price, parse_location
from bike_scraper.utils_logger import get_logger

logger = get_logger('wallapop')


class WallapopScraper(BaseScraper):
    """Парсер для Wallapop с поддержкой CloakBrowser + Playwright + Proxy rotation"""

    def __init__(self, use_cloak: bool = True, use_proxy: bool = True):
        super().__init__('wallapop')
        self.base_url = WALLAPOP_SEARCH_URL
        self.use_cloak = use_cloak
        self.use_proxy = use_proxy
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.proxy_list = self._load_proxies()
        self.proxy_index = 0

    def _load_proxies(self) -> List[str]:
        """Загрузить proxies из environment variables"""
        proxies = []
        for i in range(1, 4):
            proxy_var = f"PROXY_{i}"
            proxy = os.getenv(proxy_var)
            if proxy:
                # Format: user:pass@ip:port -> http://user:pass@ip:port
                if not proxy.startswith("http"):
                    proxy = f"http://{proxy}"
                proxies.append(proxy)
                logger.info(f"✅ Загружен proxy {i}: {proxy.split('@')[1] if '@' in proxy else proxy[:30]}")
        return proxies

    def _get_next_proxy(self) -> Optional[str]:
        """Получить следующий proxy из списка (ротация)"""
        if not self.proxy_list:
            return None
        proxy = self.proxy_list[self.proxy_index % len(self.proxy_list)]
        self.proxy_index += 1
        logger.debug(f"📍 Используется proxy: {self.proxy_index % len(self.proxy_list) + 1}/{len(self.proxy_list)}")
        return proxy

    async def init_browser(self):
        """Инициализировать браузер (CloakBrowser с humanize или Chromium)"""
        if self.page:
            return  # Уже инициализирован

        try:
            # Используем CloakBrowser Python пакет
            if self.use_cloak:
                from cloakbrowser import launch_async

                # Параметры для CloakBrowser с proxy
                kwargs = {"headless": True}
                if self.use_proxy and self.proxy_list:
                    kwargs["proxy"] = self._get_next_proxy()

                self.browser = await launch_async(**kwargs)
                logger.info("✅ CloakBrowser (stealth) запущен")
            else:
                self.playwright = await async_playwright().start()

                # Параметры для Chromium с proxy
                kwargs = {"headless": True}
                if self.use_proxy and self.proxy_list:
                    kwargs["proxy"] = {"server": self._get_next_proxy()}

                self.browser = await self.playwright.chromium.launch(**kwargs)
                logger.info("✅ Chromium запущен")

        except Exception as e:
            logger.warning(f"⚠️ CloakBrowser недоступен, используем Chromium: {e}")
            self.playwright = await async_playwright().start()

            kwargs = {"headless": True}
            if self.use_proxy and self.proxy_list:
                kwargs["proxy"] = {"server": self._get_next_proxy()}

            self.browser = await self.playwright.chromium.launch(**kwargs)

        # Создать страницу
        try:
            # Для CloakBrowser
            self.page = await self.browser.new_page()
        except:
            # Для обычного Chromium через Playwright
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                viewport={"width": 1920, "height": 1080},
                locale="es-ES",
                timezone_id="Europe/Madrid",
            )
            await self.context.set_extra_http_headers({
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            })
            self.page = await self.context.new_page()

        self.page.set_default_timeout(30000)
        self.page.set_default_navigation_timeout(30000)

        logger.info("✅ Страница браузера инициализирована")

    async def search_async(self, search_term: str, max_results: int = 100) -> List[ListingData]:
        """
        Асинхронный поиск велосипедов на Wallapop с использованием CloakBrowser
        """
        await self.init_browser()

        logger.info(f"🔍 Ищу '{search_term}' на Wallapop (CloakBrowser)...")

        all_results = []
        page = 0

        while len(all_results) < max_results:
            try:
                # URL с параметрами поиска
                url = f"{self.base_url}?keywords={search_term.replace(' ', '+')}&start={page * 50}"

                logger.debug(f"📄 Загружаю страницу {page + 1}: {url}")

                # Загружаем страницу через браузер
                await self.page.goto(url, wait_until='networkidle', timeout=30000)

                # Ждем загрузки контента (пробуем несколько селекторов)
                try:
                    await self.page.wait_for_selector('div[class*="ItemCard"]', timeout=10000)
                except:
                    await self.page.wait_for_selector('article', timeout=10000)

                # Получаем HTML
                html = await self.page.content()

                # DEBUG: Log page details on first page
                if page == 0:
                    page_title = await self.page.title()
                    final_url = self.page.url
                    html_length = len(html)
                    html_first_5000 = html[:5000]

                    logger.info(f"PAGE_TITLE={page_title}")
                    logger.info(f"FINAL_URL={final_url}")
                    logger.info(f"HTML_LENGTH={html_length}")
                    logger.info(f"HTML_FIRST_5000={html_first_5000}")

                    # Count keyword occurrences
                    count_itemcard = html.count('ItemCard')
                    count_item_card = html.count('item-card')
                    count_wallapop = html.count('wallapop')
                    count_cloudflare = html.count('cloudflare')
                    count_captcha = html.count('captcha')
                    count_cookie = html.count('cookie')
                    count_consent = html.count('consent')

                    logger.info(f"COUNT_ItemCard={count_itemcard}")
                    logger.info(f"COUNT_item_card={count_item_card}")
                    logger.info(f"COUNT_wallapop={count_wallapop}")
                    logger.info(f"COUNT_cloudflare={count_cloudflare}")
                    logger.info(f"COUNT_captcha={count_captcha}")
                    logger.info(f"COUNT_cookie={count_cookie}")
                    logger.info(f"COUNT_consent={count_consent}")

                    # Deep HTML diagnostics
                    logger.info("=== DEEP HTML DIAGNOSTICS ===")

                    # 1. Count specific tags
                    count_wallapop_item_card = html.count('<wallapop-item-card')
                    count_item_card_tag = html.count('<item-card')
                    count_article = html.count('<article')
                    count_section = html.count('<section')
                    count_main = html.count('<main')

                    logger.info(f"TAG_wallapop-item-card={count_wallapop_item_card}")
                    logger.info(f"TAG_item-card={count_item_card_tag}")
                    logger.info(f"TAG_article={count_article}")
                    logger.info(f"TAG_section={count_section}")
                    logger.info(f"TAG_main={count_main}")

                    # 2. Find first 20 links with /item/ or /search/
                    import re
                    href_pattern = r'href=["\']((?:/item/|/search/)[^\s"\']*)'
                    href_matches = re.findall(href_pattern, html)

                    logger.info(f"LINKS_WITH_ITEM_OR_SEARCH={len(href_matches)}")
                    for idx, href in enumerate(href_matches[:20]):
                        logger.info(f"LINK_{idx}={href}")

                    # 3. Analyze script tags
                    script_count = html.count('<script')
                    logger.info(f"SCRIPT_TAGS_TOTAL={script_count}")

                    # Find script tags with size > 1000
                    script_pattern = r'<script[^>]*>(.*?)</script>'
                    scripts = re.findall(script_pattern, html, re.DOTALL)

                    for idx, script in enumerate(scripts):
                        if len(script) > 1000:
                            script_type = 'unknown'
                            if 'type="application/json"' in html[max(0, html.find(script)-200):html.find(script)]:
                                script_type = 'json'
                            elif 'type="text/javascript"' in html[max(0, html.find(script)-200):html.find(script)]:
                                script_type = 'javascript'

                            logger.info(f"SCRIPT_{idx}_TYPE={script_type} | LENGTH={len(script)} | FIRST_500={script[:500]}")

                    # 4. Check for data formats
                    count_next_data = html.count('__NEXT_DATA__')
                    count_ld_json = html.count('application/ld+json')
                    count_initial_state = html.count('initialState')
                    count_apollo = html.count('apollo')
                    count_search_result = html.count('searchResult')
                    count_items = html.count('"items"')
                    count_listings = html.count('listings')

                    logger.info(f"NEXT_DATA={count_next_data}")
                    logger.info(f"LD_JSON={count_ld_json}")
                    logger.info(f"initialState={count_initial_state}")
                    logger.info(f"apollo={count_apollo}")
                    logger.info(f"searchResult={count_search_result}")
                    logger.info(f"items={count_items}")
                    logger.info(f"listings={count_listings}")

                    # 5. Extract NEXT_DATA if found
                    if count_next_data > 0:
                        next_data_pattern = r'<script id="__NEXT_DATA__"[^>]*type="application/json">(.*?)</script>'
                        next_data_match = re.search(next_data_pattern, html, re.DOTALL)
                        if next_data_match:
                            next_data_content = next_data_match.group(1)
                            logger.info(f"NEXT_DATA_LENGTH={len(next_data_content)}")
                            logger.info(f"NEXT_DATA_FIRST_3000={next_data_content[:3000]}")

                # Парсим HTML
                soup = BeautifulSoup(html, 'html.parser')
                # Ищем карточки объявлений с фильтром: должна содержать ссылку на /item/
                all_items = soup.find_all('div', class_=lambda x: x and 'ItemCard' in x)
                logger.info(f"DEBUG_ALL_ITEMS={len(all_items)}")
                if all_items:
                    first_item = all_items[0]
                    first_link = first_item.find('a')
                    first_href = first_link.get('href', 'NO_HREF') if first_link else 'NO_LINK'
                    logger.info(f"DEBUG_ALL_ITEMS_FIRST: tag={first_item.name} | class={first_item.get('class', [])} | href={first_href}")

                listings = []
                for item in all_items:
                    # Проверяем что это реальное объявление (не реклама)
                    link = item.find('a', href=lambda x: x and '/item/' in x)
                    if link:
                        listings.append(item)

                logger.info(f"DEBUG_ITEM_LINKS={len(listings)} (из {len(all_items)})")
                if listings:
                    first_item = listings[0]
                    first_link = first_item.find('a', href=lambda x: x and '/item/' in x)
                    first_href = first_link.get('href', 'NO_HREF') if first_link else 'NO_LINK'
                    logger.info(f"DEBUG_ITEM_LINKS_FIRST: tag={first_item.name} | class={first_item.get('class', [])} | href={first_href}")

                if not listings and all_items:
                    # Fallback: если не нашли /item/, возьмём все ItemCard
                    logger.info("DEBUG_FALLBACK1_TRIGGERED")
                    listings = all_items

                if not listings:
                    logger.info("DEBUG_FALLBACK2_TRIGGERED")
                    listings = soup.find_all('article')
                    logger.info(f"DEBUG_ARTICLES={len(listings)}")
                    if listings:
                        first_item = listings[0]
                        first_link = first_item.find('a')
                        first_href = first_link.get('href', 'NO_HREF') if first_link else 'NO_LINK'
                        logger.info(f"DEBUG_ARTICLES_FIRST: tag={first_item.name} | class={first_item.get('class', [])} | href={first_href}")

                if not listings:
                    logger.debug(f"Страница {page + 1} пуста")
                    break

                logger.info(f"📋 Найдено {len(listings)} объявлений на странице {page + 1}")

                # Парсим каждое объявление
                for idx, listing_elem in enumerate(listings):
                    if len(all_results) >= max_results:
                        break

                    try:
                        # DEBUG: Log first card HTML on first page
                        if idx == 0 and page == 0:
                            html_str = str(listing_elem)[:2000]
                            logger.info(f"FIRST_CARD_HTML[0:2000]:\n{html_str}")

                        listing_data = self._parse_listing_element(listing_elem)
                        if listing_data:
                            all_results.append(listing_data)
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка парсинга объявления: {e}")
                        continue

                page += 1

                # Задержка между страницами
                await asyncio.sleep(self.random_delay_seconds(2, 5))

            except Exception as e:
                logger.error(f"❌ Ошибка на странице {page}: {e}")
                break

        logger.info(f"✅ Найдено {len(all_results)} объявлений из {total_cards_found if 'total_cards_found' in locals() else '?'} карточек")
        logger.info(f"PARSE_SUMMARY: total_cards={len(listings) if 'listings' in locals() else '?'} | successful_parses={len(all_results)} | failed_parses={len(listings) - len(all_results) if 'listings' in locals() else '?'}")
        return all_results

    def search(self, search_term: str, max_results: int = 100) -> List[ListingData]:
        """
        Синхронная обертка для асинхронного поиска
        """
        return asyncio.run(self.search_async(search_term, max_results))

    def _parse_listing_element(self, element) -> Optional[ListingData]:
        """Парсить элемент объявления из HTML (современная структура Wallapop)"""
        try:
            # Попробуем получить ID из разных атрибутов
            listing_id = None

            # 1. Попробуем найти link и извлечь ID
            links = element.find_all('a')
            for link in links:
                href = link.get('href', '')
                # /item/slug-text-123456 (new format) или /item/123456 (old format)
                # Try new format first: extract trailing numeric ID
                match = re.search(r'-(\d+)(?:\?|$)', href)
                if match:
                    listing_id = match.group(1)
                    break

            if not listing_id:
                logger.warning(f"PARSE FAILED: reason=NO_LISTING_ID | links_found={len(links)} | first_link_href={links[0].get('href', 'NONE') if links else 'NO_LINKS'}")
                return None

            # Название - ищем в разных местах
            title = ''

            # Попробуем найти span или div с классом, содержащим название
            title_candidates = element.find_all(['h2', 'h3', 'span', 'div'], limit=20)
            for candidate in title_candidates:
                text = candidate.text.strip()
                # Пропускаем короткие текст типа цены и фильтры
                if len(text) > 10 and len(text) < 200 and not text.startswith('€'):
                    # Проверяем что это не цена или другой сервисный текст
                    if text and ('/' not in text or 'Canyon' in text or 'Aeroad' in text):
                        title = text
                        break

            # Альтернативный способ - ищем в первой ссылке
            if not title:
                first_link = element.find('a')
                if first_link:
                    title = first_link.get('title', '') or first_link.text.strip()

            if not title or len(title) < 5:
                logger.warning(f"PARSE FAILED: reason=NO_TITLE | title_found={bool(title)} | title_length={len(title) if title else 0}")
                return None

            # Цена - ищем в названии в формате "310 €Название..."
            # Wallapop включает цену в начало названия
            price_text = ''
            price_match = re.match(r'^([\d.,]+)\s*€', title)
            if price_match:
                price_text = price_match.group(0)
                # Удаляем цену из названия
                title = re.sub(r'^([\d.,]+)\s*€\s*', '', title)

            # Если цены в названии не нашли, ищем в остальном тексте
            if not price_text:
                all_text = element.get_text()
                price_match = re.search(r'\b([\d.,]+)\s*€', all_text)
                if price_match:
                    price_text = price_match.group(0)

            # Очищаем название от артефактов
            title = re.sub(r'^\d+\s*/\s*\d+\s*', '', title)  # Удаляем "1 / 25"
            title = title.strip()

            # Ссылка
            url = ''
            if links:
                href = links[0].get('href', '')
                if href.startswith('/'):
                    url = 'https://es.wallapop.com' + href
                else:
                    url = href

            price = normalize_price(price_text)

            if not price or price < MIN_PRICE or price > MAX_PRICE:
                logger.warning(f"PARSE FAILED: reason=BAD_PRICE | price={price} | min={MIN_PRICE} | max={MAX_PRICE}")
                return None

            # Локация - обычно в конце объявления
            location = ''
            text_parts = all_text.split('\n')
            if len(text_parts) > 1:
                # Последний непустой текст часто - локация
                for part in reversed(text_parts):
                    part_clean = part.strip()
                    if part_clean and len(part_clean) < 50 and '€' not in part_clean:
                        location = part_clean
                        break

            # Продавец
            seller_name = 'Unknown'
            # Можно получить из других источников, но пока оставляем Unknown

            # Изображение
            image_url = ''
            img_elem = element.find('img')
            if img_elem:
                image_url = img_elem.get('src', '') or img_elem.get('data-src', '')

            # Собираем данные
            listing = ListingData(
                source='wallapop',
                listing_id=listing_id,
                url=url,
                title=title,
                description='',
                price=price,
                currency='EUR',
                seller_name=seller_name,
                location=location,
                country='Spain',
                date_posted=None,
                images=[image_url] if image_url else [],
                raw_data={'title': title, 'price': price_text}
            )

            return listing

        except Exception as e:
            logger.debug(f"Ошибка парсинга элемента: {e}")
            return None

    def get_listing_details(self, url: str) -> Optional[dict]:
        """
        Получить полную информацию о конкретном объявлении
        """
        try:
            logger.debug(f"📦 Получаю детали {url}")

            html = self.fetch_page(url)
            if not html:
                return None

            soup = BeautifulSoup(html, 'html.parser')

            # Полное описание
            description_elem = soup.find('div', class_='Description')
            description = description_elem.text.strip() if description_elem else ''

            # Все изображения
            images = []
            gallery = soup.find('div', class_='Gallery')
            if gallery:
                img_elements = gallery.find_all('img')
                images = [img.get('src', '') for img in img_elements if img.get('src')]

            # Информация о продавце
            seller_rating_elem = soup.find('span', class_='SellerRating')
            seller_rating = None
            if seller_rating_elem:
                try:
                    rating_text = seller_rating_elem.text.strip()
                    seller_rating = float(rating_text.replace(',', '.').split()[0])
                except:
                    pass

            return {
                'description': description,
                'images': images,
                'seller_rating': seller_rating,
            }

        except Exception as e:
            logger.warning(f"⚠️  Ошибка получения деталей: {e}")
            return None

    @staticmethod
    def _parse_date(date_text: str) -> Optional[datetime]:
        """
        Парсить дату из текста Wallapop
        Примеры: "2 hours ago", "1 day ago", "3 days ago"
        """
        if not date_text:
            return None

        try:
            date_text_lower = date_text.lower()
            now = datetime.now()

            # Часов назад
            match = re.search(r'(\d+)\s*hours?\s*ago', date_text_lower)
            if match:
                hours = int(match.group(1))
                from datetime import timedelta
                return now - timedelta(hours=hours)

            # Дней назад
            match = re.search(r'(\d+)\s*days?\s*ago', date_text_lower)
            if match:
                days = int(match.group(1))
                from datetime import timedelta
                return now - timedelta(days=days)

            # "1 day ago" vs "2 days ago"
            if 'ago' in date_text_lower:
                from datetime import timedelta
                return now - timedelta(hours=24)

            # Если это конкретная дата (DD/MM/YYYY)
            if '/' in date_text:
                return datetime.strptime(date_text, '%d/%m/%Y')

        except Exception as e:
            logger.debug(f"Ошибка парсинга даты '{date_text}': {e}")

        return None

    @staticmethod
    def random_delay_seconds(min_sec: float = 1, max_sec: float = 3) -> float:
        """Получить случайную задержку в секундах"""
        import random
        return random.uniform(min_sec, max_sec)

    async def close(self):
        """Закрыть браузер и контекст"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass  # Ignore errors during cleanup
        logger.info("✅ Браузер закрыт")

    def parse_listing(self, listing_data: dict) -> ListingData:
        """
        Реализация абстрактного метода
        """
        return ListingData(**listing_data)


def create_wallapop_scraper() -> WallapopScraper:
    """Factory для создания Wallapop скрейпера"""
    return WallapopScraper()
