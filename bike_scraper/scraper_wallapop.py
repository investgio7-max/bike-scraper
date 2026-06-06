"""
Парсер для Wallapop (Испания)
"""

from typing import List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import re

from scraper_base import BaseScraper, ListingData
from config import WALLAPOP_SEARCH_URL, MIN_PRICE, MAX_PRICE
from utils_parser import BikeParser, normalize_price, parse_location
from utils_logger import get_logger

logger = get_logger('wallapop')


class WallapopScraper(BaseScraper):
    """Парсер для Wallapop"""

    def __init__(self):
        super().__init__('wallapop')
        self.base_url = WALLAPOP_SEARCH_URL

    def search(self, search_term: str, max_results: int = 100) -> List[ListingData]:
        """
        Искать велосипеды на Wallapop
        """
        logger.info(f"🔍 Ищу '{search_term}' на Wallapop...")

        all_results = []
        page = 0

        while len(all_results) < max_results:
            try:
                # URL с параметрами поиска
                url = f"{self.base_url}?keywords={search_term.replace(' ', '+')}&start={page * 50}"

                logger.debug(f"📄 Загружаю страницу {page + 1}")

                # Загружаем страницу
                html = self.fetch_page(url)
                if not html:
                    break

                # Парсим HTML
                soup = BeautifulSoup(html, 'html.parser')
                listings = soup.find_all('div', class_='ItemCard')

                if not listings:
                    logger.debug(f"Страница {page + 1} пуста")
                    break

                # Парсим каждое объявление
                for listing_elem in listings:
                    if len(all_results) >= max_results:
                        break

                    try:
                        listing_data = self._parse_listing_element(listing_elem)
                        if listing_data:
                            all_results.append(listing_data)
                    except Exception as e:
                        logger.warning(f"⚠️  Ошибка парсинга объявления: {e}")
                        continue

                page += 1

                # Задержка между страницами
                self.random_delay(2, 5)

            except Exception as e:
                logger.error(f"❌ Ошибка на странице {page}: {e}")
                break

        logger.info(f"✅ Найдено {len(all_results)} объявлений")
        return all_results

    def _parse_listing_element(self, element) -> Optional[ListingData]:
        """Парсить элемент объявления из HTML"""
        try:
            # ID объявления из атрибута
            listing_id = element.get('data-id', '')
            if not listing_id:
                return None

            # Название
            title_elem = element.find('span', class_='ItemTitle')
            title = title_elem.text.strip() if title_elem else ''

            if not title:
                return None

            # Ссылка
            link_elem = element.find('a', class_='ItemCardLink')
            url = link_elem.get('href', '') if link_elem else ''

            # Цена
            price_elem = element.find('span', class_='Price')
            price_text = price_elem.text.strip() if price_elem else ''
            price = normalize_price(price_text)

            if not price or price < MIN_PRICE or price > MAX_PRICE:
                return None

            # Локация
            location_elem = element.find('span', class_='ItemLocation')
            location = location_elem.text.strip() if location_elem else ''

            # Дата
            date_elem = element.find('span', class_='ItemDate')
            date_text = date_elem.text.strip() if date_elem else ''
            date_posted = self._parse_date(date_text)

            # Информация о продавце (если видна)
            seller_elem = element.find('span', class_='SellerName')
            seller_name = seller_elem.text.strip() if seller_elem else 'Unknown'

            # Изображение
            img_elem = element.find('img', class_='ItemImage')
            image_url = img_elem.get('src', '') if img_elem else ''

            # Собираем данные
            listing = ListingData(
                source='wallapop',
                listing_id=listing_id,
                url=url,
                title=title,
                description='',  # Описание полного объявления получаем отдельно
                price=price,
                currency='EUR',
                seller_name=seller_name,
                location=location,
                country='Spain',
                date_posted=date_posted,
                images=[image_url] if image_url else [],
                raw_data={
                    'html_element': str(element)[:500]  # Сохраняем часть HTML
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

    def parse_listing(self, listing_data: dict) -> ListingData:
        """
        Реализация абстрактного метода
        """
        return ListingData(**listing_data)


def create_wallapop_scraper() -> WallapopScraper:
    """Factory для создания Wallapop скрейпера"""
    return WallapopScraper()
