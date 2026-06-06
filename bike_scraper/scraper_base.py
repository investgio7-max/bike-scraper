"""
Базовый класс для скрейпера
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass
from curl_cffi.requests import Session
import random

from bike_scraper.config import USER_AGENTS, REQUEST_TIMEOUT, USE_PROXIES, PROXIES_LIST
from bike_scraper.utils_logger import get_logger

logger = get_logger(__name__)


@dataclass
class ListingData:
    """Структура данных для объявления"""
    source: str
    listing_id: str
    url: str
    title: str
    description: str
    price: float
    currency: str
    seller_name: str
    seller_id: Optional[str] = None
    seller_rating: Optional[float] = None
    seller_reviews_count: Optional[int] = None
    location: str = ''
    country: str = 'Spain'
    date_posted: Optional[datetime] = None
    images: List[str] = None
    raw_data: dict = None

    def __post_init__(self):
        if self.images is None:
            self.images = []
        if self.raw_data is None:
            self.raw_data = {}


class BaseScraper(ABC):
    """Базовый класс для всех скрейперов"""

    def __init__(self, source_name: str):
        self.source_name = source_name
        self.session = self._create_session()
        self.current_proxy = None
        self.logger = get_logger(source_name)

    def _create_session(self) -> Session:
        """Создать сессию с curl_cffi"""
        session = Session()
        session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Accept-Language': 'es-ES,es;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
        })
        return session

    def _rotate_user_agent(self):
        """Ротировать User-Agent"""
        self.session.headers.update({
            'User-Agent': random.choice(USER_AGENTS)
        })

    def _rotate_proxy(self):
        """Ротировать прокси"""
        if not USE_PROXIES or not PROXIES_LIST:
            return

        self.current_proxy = random.choice(PROXIES_LIST)
        self.logger.debug(f"🔄 Используюю прокси: {self.current_proxy}")

    def _get_proxies_dict(self) -> dict:
        """Получить dict для requests"""
        if not self.current_proxy:
            return {}

        return {
            'http': self.current_proxy,
            'https': self.current_proxy,
        }

    def fetch_page(self, url: str, **kwargs) -> Optional[str]:
        """
        Загрузить страницу с защитой от блокировок
        """
        try:
            # Ротируем User-Agent
            self._rotate_user_agent()

            # Ротируем прокси
            self._rotate_proxy()

            # Делаем запрос
            response = self.session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                impersonate='chrome120',
                **kwargs
            )

            response.raise_for_status()

            return response.text

        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки {url}: {e}")
            return None

    def random_delay(self, min_sec: float = 1, max_sec: float = 3):
        """Случайная задержка для избежания блокировок"""
        import time
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    @abstractmethod
    def search(self, search_term: str, max_results: int = 100) -> List[ListingData]:
        """
        Искать объявления
        Должен быть реализован в подклассе
        """
        pass

    @abstractmethod
    def parse_listing(self, listing_data: dict) -> ListingData:
        """
        Парсить объявление
        Должен быть реализован в подклассе
        """
        pass

    def close(self):
        """Закрыть сессию"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
