"""
Парсер для Wallapop (Испания)
Использует CloakBrowser + Playwright для обработки JavaScript контента
"""

from typing import List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import re
import asyncio
from playwright.async_api import async_playwright

from bike_scraper.scraper_base import BaseScraper, ListingData
from bike_scraper.config import WALLAPOP_SEARCH_URL, MIN_PRICE, MAX_PRICE
from bike_scraper.utils_parser import BikeParser, normalize_price, parse_location
from bike_scraper.utils_logger import get_logger

logger = get_logger('wallapop')


class WallapopScraper(BaseScraper):
    """Парсер для Wallapop с поддержкой CloakBrowser + Playwright"""

    def __init__(self, use_cloak: bool = True):
        super().__init__('wallapop')
        self.base_url = WALLAPOP_SEARCH_URL
        self.use_cloak = use_cloak
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None

    async def init_browser(self):
        """Инициализировать браузер (Cloak или стандартный Chromium)"""
        if self.page:
            return  # Уже инициализирован

        self.playwright = await async_playwright().start()

        try:
            # Пытаемся запустить CloakBrowser
            if self.use_cloak:
                self.browser = await self.playwright.chromium.launch(
                    executable_path="/Applications/Cloak.app/Contents/MacOS/Cloak",
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-first-run",
                        "--no-default-browser-check",
                    ]
                )
                logger.info("✅ CloakBrowser запущен")
            else:
                self.browser = await self.playwright.chromium.launch(headless=True)
                logger.info("✅ Chromium запущен")
        except Exception as e:
            logger.warning(f"⚠️ CloakBrowser не найден, используем Chromium: {e}")
            self.browser = await self.playwright.chromium.launch(headless=True)

        # Создать контекст
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

        logger.info("✅ Контекст браузера инициализирован")

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

                # Ждем загрузки контента
                await self.page.wait_for_selector('div[data-qa="ItemCard"]', timeout=10000)

                # Получаем HTML
                html = await self.page.content()

                # Парсим HTML
                soup = BeautifulSoup(html, 'html.parser')
                listings = soup.find_all('div', {'data-qa': 'ItemCard'})

                if not listings:
                    logger.debug(f"Страница {page + 1} пуста")
                    break

                logger.info(f"📋 Найдено {len(listings)} объявлений на странице {page + 1}")

                # Парсим каждое объявление
                for listing_elem in listings:
                    if len(all_results) >= max_results:
                        break

                    try:
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

        logger.info(f"✅ Найдено {len(all_results)} объявлений")
        return all_results

    def search(self, search_term: str, max_results: int = 100) -> List[ListingData]:
        """
        Синхронная обертка для асинхронного поиска
        """
        return asyncio.run(self.search_async(search_term, max_results))

    def _parse_listing_element(self, element) -> Optional[ListingData]:
        """Парсить элемент объявления из HTML (современная структура Wallapop)"""
        try:
            # Попробуем получить ID из атрибута data-qa
            listing_id = element.get('data-qa', '') or element.get('data-id', '')

            # Или найти ссылку и извлечь ID из URL
            if not listing_id:
                link_elem = element.find('a')
                if link_elem:
                    href = link_elem.get('href', '')
                    match = re.search(r'/item/(\d+)', href)
                    if match:
                        listing_id = match.group(1)

            if not listing_id:
                return None

            # Название (разные варианты селекторов)
            title_elem = element.find('h2') or element.find('a', attrs={'data-qa': re.compile('.*title.*')})
            title = title_elem.text.strip() if title_elem else ''

            if not title:
                return None

            # Ссылка
            link_elem = element.find('a')
            url = link_elem.get('href', '') if link_elem else ''
            if url and not url.startswith('http'):
                url = 'https://es.wallapop.com' + url

            # Цена
            price_elem = element.find(attrs={'data-qa': re.compile('.*price.*')}) or element.find('span', {'class': re.compile('.*price.*', re.I)})
            price_text = price_elem.text.strip() if price_elem else ''
            price = normalize_price(price_text)

            if not price or price < MIN_PRICE or price > MAX_PRICE:
                return None

            # Локация
            location_elem = element.find(attrs={'data-qa': re.compile('.*location.*')})
            location = location_elem.text.strip() if location_elem else ''

            # Дата (обычно в relative формате)
            date_elem = element.find(attrs={'data-qa': re.compile('.*time.*')}) or element.find('time')
            date_text = date_elem.text.strip() if date_elem else ''
            date_posted = self._parse_date(date_text)

            # Информация о продавце
            seller_elem = element.find(attrs={'data-qa': re.compile('.*seller.*')})
            seller_name = seller_elem.text.strip() if seller_elem else 'Unknown'

            # Изображение
            img_elem = element.find('img')
            image_url = img_elem.get('src', '') or img_elem.get('data-src', '') if img_elem else ''

            # Собираем данные
            listing = ListingData(
                source='wallapop',
                listing_id=listing_id,
                url=url,
                title=title,
                description='',  # Описание получим из деталей
                price=price,
                currency='EUR',
                seller_name=seller_name,
                location=location,
                country='Spain',
                date_posted=date_posted,
                images=[image_url] if image_url else [],
                raw_data={
                    'html_element': str(element)[:500]
                }
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
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("✅ Браузер закрыт")

    def parse_listing(self, listing_data: dict) -> ListingData:
        """
        Реализация абстрактного метода
        """
        return ListingData(**listing_data)


def create_wallapop_scraper() -> WallapopScraper:
    """Factory для создания Wallapop скрейпера"""
    return WallapopScraper()
