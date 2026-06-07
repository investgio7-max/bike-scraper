"""
Сервис для управления объявлениями в БД
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
import json

from bike_scraper.models import Listing, ListingHistory, ScraperLog, SellerProfile, PriceAnalysis, MonitoringSearch
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

    @staticmethod
    def get_new_good_deals(db: Session, hours: int = 1, min_profit_percent: float = 20, min_profit_euros: float = 500) -> List[Tuple[Listing, Dict]]:
        """
        Получить НОВЫЕ выгодные сделки за последние N часов (для alerts)

        Возвращает листинги с:
        - Profit >= min_profit_percent ИЛИ
        - Profit >= min_profit_euros
        """
        analyzer = PriceAnalyzer(db)
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        deals = []

        # Получаем новые активные листинги с AI анализом
        listings = db.query(Listing).filter(
            and_(
                Listing.is_active == True,
                Listing.is_duplicate == False,
                Listing.created_at >= cutoff,  # Только новые
                Listing.raw_data['ai_analysis'].isnot(None)
            )
        ).order_by(Listing.created_at.desc()).all()

        # Анализируем каждое
        for listing in listings:
            try:
                analysis = analyzer.analyze_listing(listing)
                market = analysis.get('market_analysis', {})

                if market:
                    profit_percent = market.get('profit_percent', 0)
                    profit_euros = market.get('profit_euros', 0)

                    # Проверяем если это выгодная сделка
                    if profit_percent >= min_profit_percent or profit_euros >= min_profit_euros:
                        deals.append((listing, analysis))
                        logger.info(
                            f"💰 ВЫГОДНАЯ СДЕЛКА НАЙДЕНА: {listing.title[:50]} "
                            f"€{listing.price} | Профит: {profit_percent:.0f}% (€{profit_euros:.0f})"
                        )

            except Exception as e:
                logger.debug(f"⚠️ Ошибка анализа сделки {listing.id}: {e}")
                continue

        logger.info(f"🎉 Найдено {len(deals)} новых выгодных сделок за последний час")
        return deals


class MonitoringService:
    """Сервис для управления мониторингом велосипедов пользователей"""

    @staticmethod
    def add_monitoring(db: Session, user_id: int, search_term: str) -> Optional[MonitoringSearch]:
        """Добавить новый мониторинг для пользователя"""
        # Проверяем есть ли уже такой поиск
        existing = db.query(MonitoringSearch).filter(
            and_(
                MonitoringSearch.user_id == user_id,
                MonitoringSearch.search_term == search_term
            )
        ).first()

        if existing:
            # Если был деактивирован, активируем его
            if not existing.is_active:
                existing.is_active = True
                logger.info(f"✅ Мониторинг переактивирован: {search_term} для пользователя {user_id}")
            else:
                logger.debug(f"ℹ️ Мониторинг уже существует: {search_term}")
            return existing

        # Создаем новый
        monitoring = MonitoringSearch(
            user_id=user_id,
            search_term=search_term,
            is_active=True,
            notify_new_listings=True,
            notify_price_drop=True,
            price_drop_threshold=50.0
        )
        db.add(monitoring)
        logger.info(f"✨ Новый мониторинг добавлен: {search_term} для пользователя {user_id}")
        return monitoring

    @staticmethod
    def delete_monitoring(db: Session, user_id: int, search_term: str) -> bool:
        """Удалить мониторинг (мягкое удаление - деактивация)"""
        monitoring = db.query(MonitoringSearch).filter(
            and_(
                MonitoringSearch.user_id == user_id,
                MonitoringSearch.search_term == search_term
            )
        ).first()

        if monitoring:
            monitoring.is_active = False
            logger.info(f"🗑️ Мониторинг удален: {search_term} для пользователя {user_id}")
            return True

        return False

    @staticmethod
    def toggle_monitoring(db: Session, user_id: int, search_term: str) -> Optional[bool]:
        """Переключить состояние мониторинга (вкл/выкл)"""
        monitoring = db.query(MonitoringSearch).filter(
            and_(
                MonitoringSearch.user_id == user_id,
                MonitoringSearch.search_term == search_term
            )
        ).first()

        if monitoring:
            monitoring.is_active = not monitoring.is_active
            status = "ВКЛ" if monitoring.is_active else "ВЫКЛ"
            logger.info(f"🔔 Мониторинг переключен на {status}: {search_term}")
            return monitoring.is_active

        return None

    @staticmethod
    def enable_monitoring(db: Session, user_id: int, search_term: str) -> bool:
        """Включить мониторинг"""
        monitoring = db.query(MonitoringSearch).filter(
            and_(
                MonitoringSearch.user_id == user_id,
                MonitoringSearch.search_term == search_term
            )
        ).first()

        if monitoring:
            monitoring.is_active = True
            logger.info(f"✅ Мониторинг включен: {search_term}")
            return True

        return False

    @staticmethod
    def disable_monitoring(db: Session, user_id: int, search_term: str) -> bool:
        """Выключить мониторинг"""
        monitoring = db.query(MonitoringSearch).filter(
            and_(
                MonitoringSearch.user_id == user_id,
                MonitoringSearch.search_term == search_term
            )
        ).first()

        if monitoring:
            monitoring.is_active = False
            logger.info(f"❌ Мониторинг выключен: {search_term}")
            return True

        return False

    @staticmethod
    def get_user_monitoring(db: Session, user_id: int, only_active: bool = False) -> List[MonitoringSearch]:
        """Получить все мониторинги пользователя"""
        query = db.query(MonitoringSearch).filter(MonitoringSearch.user_id == user_id)

        if only_active:
            query = query.filter(MonitoringSearch.is_active == True)

        return query.order_by(MonitoringSearch.created_at.desc()).all()

    @staticmethod
    def format_monitoring_list(monitoring_list: List[MonitoringSearch]) -> str:
        """Отформатировать список мониторингов для бота"""
        if not monitoring_list:
            return "📋 У вас нет активных поисков"

        message = "📋 Ваши активные поиски:\n\n"
        for i, m in enumerate(monitoring_list, 1):
            status = "🔔 ВКЛ" if m.is_active else "🔕 ВЫКЛ"
            message += f"{i}. {m.search_term} ({status})\n"

        message += "\nИспользуйте 'Вкл/Выкл' для переключения"
        return message
