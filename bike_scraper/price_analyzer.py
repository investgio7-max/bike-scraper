"""
💰 Price Analyzer - Анализ цен и расчет выгодных сделок

Функции:
- Поиск аналогичных велосипедов (по бренду, модели, году)
- Расчет средней цены за 30 дней
- Расчет потенциального профита
- Определение выгодных сделок
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
import statistics
import logging

from bike_scraper.models import Listing, ListingHistory
from bike_scraper.utils_logger import get_logger

logger = get_logger('price_analyzer')


class PriceAnalyzer:
    """Анализатор цен велосипедов"""

    def __init__(self, db: Session):
        self.db = db

    def find_comparable_bikes(
        self,
        brand: str,
        model: str,
        year: Optional[int] = None,
        frame_size: Optional[str] = None,
        days_back: int = 30
    ) -> List[Listing]:
        """
        Найти аналогичные велосипеды на рынке

        Args:
            brand: Бренд велосипеда
            model: Модель велосипеда
            year: Год выпуска (опционально)
            frame_size: Размер рамы (опционально)
            days_back: Сколько дней смотреть (по умолчанию 30)

        Returns:
            Список аналогичных объявлений
        """
        if not brand or not model:
            logger.warning(f"⚠️ Неполные данные для поиска аналогов: {brand} {model}")
            return []

        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        query = self.db.query(Listing).filter(
            and_(
                Listing.is_active == True,
                Listing.date_collected >= cutoff_date,
                Listing.raw_data['ai_analysis']['brand'].astext.ilike(f"%{brand}%"),
                Listing.raw_data['ai_analysis']['model'].astext.ilike(f"%{model}%")
            )
        )

        # Опционально фильтруем по году
        if year:
            query = query.filter(
                Listing.raw_data['ai_analysis']['year'].astext == str(year)
            )

        # Опционально фильтруем по размеру
        if frame_size:
            query = query.filter(
                Listing.raw_data['ai_analysis']['size'].astext.ilike(f"%{frame_size}%")
            )

        comparable = query.all()
        logger.info(f"📊 Найдено {len(comparable)} аналогичных велосипедов {brand} {model}")

        return comparable

    def calculate_market_price(self, comparable_bikes: List[Listing]) -> Dict:
        """
        Расчет средней рыночной цены

        Returns:
            {
                'mean': средняя цена,
                'median': медианная цена,
                'min': минимальная цена,
                'max': максимальная цена,
                'count': количество аналогов,
                'samples': исходные цены
            }
        """
        if not comparable_bikes:
            return {
                'mean': 0,
                'median': 0,
                'min': 0,
                'max': 0,
                'count': 0,
                'samples': []
            }

        prices = [bike.price for bike in comparable_bikes if bike.price > 0]

        if not prices:
            return {
                'mean': 0,
                'median': 0,
                'min': 0,
                'max': 0,
                'count': 0,
                'samples': []
            }

        return {
            'mean': round(statistics.mean(prices), 2),
            'median': round(statistics.median(prices), 2),
            'min': min(prices),
            'max': max(prices),
            'count': len(prices),
            'samples': sorted(prices)
        }

    def calculate_profit(
        self,
        current_price: float,
        market_price: Dict,
        min_comparable: int = 3
    ) -> Dict:
        """
        Расчет потенциального профита

        Args:
            current_price: Текущая цена велосипеда
            market_price: Данные о рыночной цене (из calculate_market_price)
            min_comparable: Минимум аналогов для расчета

        Returns:
            {
                'is_deal': Выгодная ли сделка,
                'profit_euros': Потенциальный профит в евро,
                'profit_percent': Потенциальный профит в %,
                'market_avg': Средняя рыночная цена,
                'discount': Скидка от рынка в %,
                'confidence': Уверенность в анализе (зависит от кол-ва аналогов)
            }
        """
        if market_price['count'] < min_comparable:
            return {
                'is_deal': False,
                'profit_euros': 0,
                'profit_percent': 0,
                'market_avg': 0,
                'discount': 0,
                'confidence': 0,
                'reason': f'Недостаточно аналогов ({market_price["count"]} < {min_comparable})'
            }

        market_avg = market_price['median']  # Используем медиану вместо среднего

        if current_price >= market_avg:
            return {
                'is_deal': False,
                'profit_euros': 0,
                'profit_percent': 0,
                'market_avg': market_avg,
                'discount': 0,
                'confidence': 100,
                'reason': f'Цена выше или равна рынку (€{current_price} vs €{market_avg})'
            }

        profit_euros = market_avg - current_price
        profit_percent = round((profit_euros / market_avg) * 100, 2)

        # Уверенность зависит от количества аналогов
        confidence = min(100, market_price['count'] * 10)

        return {
            'is_deal': profit_percent >= 10,  # Выгода >= 10%
            'profit_euros': round(profit_euros, 2),
            'profit_percent': profit_percent,
            'market_avg': round(market_avg, 2),
            'discount': round(((market_avg - current_price) / market_avg) * 100, 2),
            'confidence': confidence,
            'comparable_count': market_price['count']
        }

    def analyze_listing(self, listing: Listing) -> Dict:
        """
        Полный анализ объявления

        Returns:
            {
                'listing_id': ID объявления,
                'title': Название,
                'price': Цена,
                'market_analysis': Результаты анализа
            }
        """
        if not listing.raw_data or 'ai_analysis' not in listing.raw_data:
            return {
                'listing_id': str(listing.id),
                'title': listing.title,
                'price': listing.price,
                'market_analysis': None,
                'reason': 'Нет AI анализа'
            }

        ai_data = listing.raw_data['ai_analysis']
        brand = ai_data.get('brand')
        model = ai_data.get('model')
        year = ai_data.get('year')
        frame_size = ai_data.get('size')

        # Ищем аналоги
        comparables = self.find_comparable_bikes(brand, model, year, frame_size)

        # Исключаем само объявление из аналогов
        comparables = [b for b in comparables if b.id != listing.id]

        if len(comparables) < 3:
            comparables = self.find_comparable_bikes(brand, model, year, None)
            comparables = [b for b in comparables if b.id != listing.id]

        # Расчитываем цены
        market_prices = self.calculate_market_price(comparables)

        # Расчитываем профит
        profit_analysis = self.calculate_profit(listing.price, market_prices)

        logger.info(
            f"💰 {brand} {model}: €{listing.price} | "
            f"Рынок: €{market_prices['median']} | "
            f"Профит: {profit_analysis['profit_percent']}%"
        )

        return {
            'listing_id': str(listing.id),
            'title': listing.title,
            'price': listing.price,
            'bike': {
                'brand': brand,
                'model': model,
                'year': year,
                'size': frame_size
            },
            'market_analysis': {
                'comparable_count': market_prices['count'],
                'market_median': market_prices['median'],
                'market_mean': market_prices['mean'],
                'market_range': (market_prices['min'], market_prices['max']),
                'profit_euros': profit_analysis['profit_euros'],
                'profit_percent': profit_analysis['profit_percent'],
                'discount_percent': profit_analysis['discount'],
                'is_deal': profit_analysis['is_deal'],
                'confidence': profit_analysis['confidence']
            }
        }
