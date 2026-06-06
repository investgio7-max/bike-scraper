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
        """Инициализировать браузер (CloakBrowser с humanize или Chromium)"""
        if self.page:
            return  # Уже инициализирован

        try:
            # Используем CloakBrowser Python пакет
            if self.use_cloak:
                from cloakbrowser import launch_async

                self.browser = await launch_async(
                    headless=True,
                    humanize=True,  # Human-like behavior
                )
                logger.info("✅ CloakBrowser (stealth) запущен")
            else:
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(headless=True)
                logger.info("✅ Chromium запущен")

        except Exception as e:
            logger.warning(f"⚠️ CloakBrowser недоступен, используем Chromium: {e}")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)

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

                # Парсим HTML
                soup = BeautifulSoup(html, 'html.parser')
                # Пробуем несколько селекторов
                listings = soup.find_all('div', class_=lambda x: x and 'ItemCard' in x)
                if not listings:
                    listings = soup.find_all('article')

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
            # Попробуем получить ID из разных атрибутов
            listing_id = None

            # 1. Попробуем найти link и извлечь ID
            links = element.find_all('a')
            for link in links:
                href = link.get('href', '')
                # /item/123456 или /listings/123456
                match = re.search(r'/(item|listings)/(\d+)', href)
                if match:
                    listing_id = match.group(2)
                    break

            if not listing_id:
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
                return None

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

            # Цена - ищем текст с €
            price_text = ''
            all_text = element.get_text()

            # Найдем первое вхождение цены в формате "€X.XXX"
            price_match = re.search(r'€\s*([\d.,]+)', all_text)
            if price_match:
                price_text = price_match.group(0)

            price = normalize_price(price_text)

            if not price or price < MIN_PRICE or price > MAX_PRICE:
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
