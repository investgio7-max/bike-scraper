"""
Сервис для управления объявлениями в БД
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
import json

from bike_scraper.models import Listing, ListingHistory, ScraperLog, SellerProfile, PriceAnalysis
from bike_scraper.scraper_base import ListingData
from bike_scraper.utils_logger import get_logger
from bike_scraper.ai_bike_parser import AIBikeParser
from bike_scraper.price_analyzer import PriceAnalyzer

logger = get_logger('service')


class ListingService:
    """Сервис для работы с объявлениями"""

    @staticmethod
    def get_or_create_listing(db: Session, listing_data: ListingData) -> Tuple[Listing, bool]:
        """
        Получить или создать объявление
        Возвращает (listing, is_new)
        """
        # Ищем существующее объявление
        existing = db.query(Listing).filter(
            and_(
                Listing.source == listing_data.source,
                Listing.listing_id == listing_data.listing_id
            )
        ).first()

        if existing:
            # Обновляем цену и дату проверки если изменилась
            price_changed = existing.price != listing_data.price

            if price_changed:
                # Сохраняем историю
                history = ListingHistory(
                    listing_id=existing.id,
                    source=listing_data.source,
                    source_listing_id=listing_data.listing_id,
                    price_old=existing.price,
                    price_new=listing_data.price,
                    change_type='price_changed'
                )
                db.add(history)
                logger.info(f"💹 Цена изменилась: €{existing.price} → €{listing_data.price}")

            # Обновляем данные
            existing.price = listing_data.price
            existing.date_updated = datetime.utcnow()
            existing.date_collected = datetime.utcnow()

            return existing, False

        # Создаем новое объявление
        listing = Listing(
            source=listing_data.source,
            listing_id=listing_data.listing_id,
            url=listing_data.url,
            title=listing_data.title,
            description=listing_data.description,
            price=listing_data.price,
            currency=listing_data.currency,
            seller_name=listing_data.seller_name,
            seller_id=listing_data.seller_id,
            seller_rating=listing_data.seller_rating,
            seller_reviews_count=listing_data.seller_reviews_count,
            location=listing_data.location,
            country=listing_data.country,
            date_posted=listing_data.date_posted,
            images=listing_data.images or [],
            main_image_url=listing_data.images[0] if listing_data.images else None,
            raw_data=listing_data.raw_data or {},
            is_active=True,
            date_collected=datetime.utcnow(),
        )

        # Парсим велосипед с помощью AI парсера
        try:
            ai_parser = AIBikeParser(use_vision=True)
            bike = ai_parser.parse(
                title=listing_data.title,
                description=listing_data.description,
                images=listing_data.images or [],
                analyze_images=True  # Включаем Claude Vision для анализа изображений
            )
            bike_dict = bike.to_dict()

            # Сохраняем результаты парсинга
            listing.frame_size = bike_dict.get('size')
            listing.bike_type = bike_dict.get('bike_type')
            listing.raw_data['ai_analysis'] = bike_dict

            logger.info(f"🤖 AI парсер: {bike_dict.get('brand')} {bike_dict.get('model')} ({bike_dict.get('confidence'):.0f}%)")

            # Анализируем цену (сначала сохраняем, потом анализируем)
            try:
                db.add(listing)
                db.flush()  # Чтобы листинг был в БД для анализа

                analyzer = PriceAnalyzer(db)
                price_analysis = analyzer.analyze_listing(listing)

                market = price_analysis.get('market_analysis')
                if market:
                    logger.info(
                        f"💰 Анализ цены: {bike_dict.get('brand')} {bike_dict.get('model')} €{listing.price} | "
                        f"Рынок: €{market.get('market_median')} | "
                        f"Профит: {market.get('profit_percent')}%"
                    )

                    # Сохраняем результаты анализа цены
                    listing.raw_data['price_analysis'] = market

                    if market.get('is_deal'):
                        logger.info(f"🎉 ВЫГОДНАЯ СДЕЛКА! Профит: {market.get('profit_euros')}€ ({market.get('profit_percent')}%)")

            except Exception as e:
                logger.debug(f"⚠️ Ошибка анализа цены: {e}")

        except Exception as e:
            logger.warning(f"⚠️ AI парсер ошибка: {e}")

        db.add(listing)

        logger.info(f"✨ Новое объявление: {listing_data.title} - €{listing_data.price}")

        return listing, True

    @staticmethod
    def check_for_duplicates(db: Session, listing: Listing) -> Optional[UUID]:
        """
        Проверить есть ли дубликаты этого объявления
        Возвращает ID оригинального объявления если найден дубликат
        """
        # Ищем похожие объявления (та же цена, продавец, тип велосипеда)
        similar = db.query(Listing).filter(
            and_(
                Listing.id != listing.id,
                Listing.price == listing.price,
                Listing.seller_name == listing.seller_name,
                Listing.bike_type == listing.bike_type,
                Listing.source == listing.source,
                Listing.is_duplicate == False,
                Listing.is_active == True
            )
        ).order_by(Listing.created_at).first()

        if similar:
            return similar.id

        return None

    @staticmethod
    def mark_as_duplicate(db: Session, duplicate_id: UUID, original_id: UUID):
        """Отметить объявление как дубликат"""
        duplicate = db.query(Listing).get(duplicate_id)
        if duplicate:
            duplicate.is_duplicate = True
            duplicate.original_listing_id = original_id
            logger.debug(f"🔄 Отмечено как дубликат: {duplicate.id}")

    @staticmethod
    def deactivate_listing(db: Session, listing_id: UUID):
        """Деактивировать объявление (удалено или продано)"""
        listing = db.query(Listing).get(listing_id)
        if listing:
            listing.is_active = False
            logger.info(f"❌ Объявление деактивировано: {listing.id}")

    @staticmethod
    def get_new_listings(db: Session, hours: int = 24, limit: int = 100) -> List[Listing]:
        """Получить новые объявления за последние N часов"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        return db.query(Listing).filter(
            and_(
                Listing.created_at >= cutoff,
                Listing.is_active == True,
                Listing.is_duplicate == False
            )
        ).order_by(desc(Listing.created_at)).limit(limit).all()

    @staticmethod
    def get_good_deals(db: Session, limit: int = 50, min_profit_percent: float = 10) -> List[Tuple[Listing, Dict]]:
        """
        Получить выгодные предложения (профит >= min_profit_percent)
        """
        analyzer = PriceAnalyzer(db)
        good_deals = []

        # Получаем все активные объявления с AI анализом
        listings = db.query(Listing).filter(
            and_(
                Listing.is_active == True,
                Listing.is_duplicate == False,
                Listing.raw_data['ai_analysis'].isnot(None)
            )
        ).order_by(Listing.created_at.desc()).limit(limit * 3).all()

        # Анализируем каждое
        for listing in listings:
            try:
                analysis = analyzer.analyze_listing(listing)
                market = analysis.get('market_analysis')

                if market and market.get('profit_percent', 0) >= min_profit_percent:
                    good_deals.append((listing, analysis))

            except Exception as e:
                logger.debug(f"⚠️ Ошибка анализа цены: {e}")
                continue

        # Сортируем по профиту (по убыванию)
        good_deals.sort(
            key=lambda x: x[1].get('market_analysis', {}).get('profit_percent', 0),
            reverse=True
        )

        logger.info(f"💰 Найдено {len(good_deals)} выгодных сделок (профит >= {min_profit_percent}%)")
        return good_deals[:limit]

    @staticmethod
    def save_scraper_log(db: Session, source: str, search_term: str,
                        total_found: int, successfully_parsed: int,
                        errors_count: int, duration_seconds: float,
                        status: str = 'success', errors: list = None):
        """Сохранить лог парсинга"""
        log = ScraperLog(
            source=source,
            search_term=search_term,
            total_found=total_found,
            successfully_parsed=successfully_parsed,
            errors_count=errors_count,
            duration_seconds=duration_seconds,
            status=status,
            errors=errors or [],
            started_at=datetime.utcnow() - timedelta(seconds=duration_seconds),
            completed_at=datetime.utcnow()
        )
        db.add(log)
        logger.info(f"📊 Лог: найдено {total_found}, спарсено {successfully_parsed}, ошибок {errors_count}")

    @staticmethod
    def get_statistics(db: Session) -> dict:
        """Получить статистику по объявлениям"""
        total = db.query(Listing).count()
        active = db.query(Listing).filter(Listing.is_active == True).count()
        duplicates = db.query(Listing).filter(Listing.is_duplicate == True).count()

        # По источникам
        by_source = db.query(Listing.source, Listing.is_active).group_by(
            Listing.source, Listing.is_active
        ).all()

        # По типам велосипедов
        by_type = db.query(Listing.bike_type, Listing.is_active).group_by(
            Listing.bike_type, Listing.is_active
        ).all()

        # Цены
        from sqlalchemy import func
        price_stats = db.query(
            func.min(Listing.price).label('min'),
            func.avg(Listing.price).label('avg'),
            func.max(Listing.price).label('max')
        ).filter(Listing.is_active == True).first()

        return {
            'total_listings': total,
            'active_listings': active,
            'duplicate_listings': duplicates,
            'by_source': by_source,
            'by_type': by_type,
            'price_stats': {
                'min': float(price_stats.min) if price_stats.min else 0,
                'avg': float(price_stats.avg) if price_stats.avg else 0,
                'max': float(price_stats.max) if price_stats.max else 0,
            }
        }

    @staticmethod
    def calculate_price_analysis(db: Session):
        """
        Рассчитать анализ цен для разных брендов/моделей
        """
        from sqlalchemy import func

        # Группируем по бренду и типу велосипеда
        analysis_data = db.query(
            Listing.bike_type,
            func.count(Listing.id).label('count'),
            func.avg(Listing.price).label('avg_price'),
            func.min(Listing.price).label('min_price'),
            func.max(Listing.price).label('max_price'),
        ).filter(
            Listing.is_active == True,
            Listing.bike_type.isnot(None)
        ).group_by(Listing.bike_type).all()

        for bike_type, count, avg_price, min_price, max_price in analysis_data:
            if count > 5:  # Только если достаточно данных
                logger.info(f"📈 {bike_type}: {count} шт, avg €{avg_price:.0f}")
