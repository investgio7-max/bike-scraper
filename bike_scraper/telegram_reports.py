"""
Формирование отчетов для Telegram бота
"""

from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy import func
from bike_scraper.models import Listing, ListingHistory, Bike, PriceAnalysis
from bike_scraper.database import get_db
from bike_scraper.utils_logger import get_logger

logger = get_logger('telegram')


class TelegramReportGenerator:
    """Генератор отчетов для Telegram"""

    @staticmethod
    def get_system_status() -> str:
        """Статус системы"""
        try:
            db = next(get_db())

            # Количество объявлений
            total_listings = db.query(Listing).count()
            listings_today = db.query(Listing).filter(
                Listing.date_posted >= datetime.now() - timedelta(hours=24)
            ).count()

            # Последняя активность
            latest_log = db.query(func.max(Listing.date_posted)).scalar()

            status = f"""🔍 **СТАТУС СКРЕЙПЕРА**

📊 Всего объявлений: {total_listings}
📈 За последние 24h: {listings_today}
⏰ Последнее обновление: {latest_log.strftime('%H:%M:%S') if latest_log else 'N/A'}

✅ Система онлайн и работает
⚙️ Мониторинг: каждые 10 минут
"""
            db.close()
            return status
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return "❌ Ошибка получения статуса"

    @staticmethod
    def get_market_stats() -> str:
        """Статистика рынка"""
        try:
            db = next(get_db())

            # Средняя цена
            avg_price = db.query(func.avg(Listing.price)).scalar()
            min_price = db.query(func.min(Listing.price)).scalar()
            max_price = db.query(func.max(Listing.price)).scalar()

            # Топ бренды
            top_brands = db.query(
                Bike.brand,
                func.count(Bike.id).label('count')
            ).group_by(Bike.brand).order_by(func.count(Bike.id).desc()).limit(5).all()

            brands_text = "\n".join([f"  • {b[0]}: {b[1]} объявлений" for b in top_brands])

            stats = f"""📊 **СТАТИСТИКА РЫНКА**

💰 Средняя цена: €{avg_price:.0f}
📉 Мин. цена: €{min_price:.0f}
📈 Макс. цена: €{max_price:.0f}

🏆 Топ бренды:
{brands_text}
"""
            db.close()
            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return "❌ Ошибка получения статистики"

    @staticmethod
    def get_best_deals(search_term: str = None, limit: int = 5) -> str:
        """Лучшие предложения"""
        try:
            db = next(get_db())

            query = db.query(Listing).order_by(Listing.price).limit(limit)
            if search_term:
                query = query.filter(
                    Listing.title.ilike(f"%{search_term}%")
                )

            deals = query.all()

            if not deals:
                return "😢 Нет предложений по этому запросу"

            deals_text = ""
            for i, deal in enumerate(deals, 1):
                deals_text += f"""{i}. {deal.title[:50]}...
   💰 €{deal.price}
   🔗 {deal.url[:50]}...

"""

            report = f"""🤑 **ЛУЧШИЕ ПРЕДЛОЖЕНИЯ**

{deals_text}"""
            db.close()
            return report
        except Exception as e:
            logger.error(f"Error getting deals: {e}")
            return "❌ Ошибка получения предложений"

    @staticmethod
    def get_price_analysis(brand: str = None) -> str:
        """Анализ цен"""
        try:
            db = next(get_db())

            query = db.query(PriceAnalysis)
            if brand:
                query = query.filter(PriceAnalysis.brand == brand)

            analysis = query.order_by(PriceAnalysis.date_analyzed.desc()).first()

            if not analysis:
                return "📊 Нет данных для анализа"

            report = f"""📈 **АНАЛИЗ ЦЕН**

🏢 Бренд: {analysis.brand or 'Все'}
💰 Средняя цена: €{analysis.avg_price:.0f}
📉 Мин. цена: €{analysis.min_price:.0f}
📈 Макс. цена: €{analysis.max_price:.0f}
📊 Объявлений: {analysis.listing_count}
📅 Анализ: {analysis.date_analyzed.strftime('%d.%m.%Y %H:%M')}
"""
            db.close()
            return report
        except Exception as e:
            logger.error(f"Error getting analysis: {e}")
            return "❌ Ошибка анализа цен"

    @staticmethod
    def get_help() -> str:
        """Справка по командам"""
        return """🤖 **ТЕЛЕГРАМ БОТ - СПРАВКА**

**📋 Доступные команды:**

🔍 `/status` - Статус скрейпера
📊 `/stats` - Статистика рынка
🤑 `/deals [поиск]` - Лучшие предложения
📈 `/price_analysis` - Анализ цен

🔔 **Управление мониторингом:**

➕ `/add_search [название]` - Добавить поиск
➖ `/remove_search [id]` - Удалить поиск
📋 `/list_searches` - Список поисков
📧 `/subscribe [id]` - Подписаться на отчеты

**Пример:**
`/add_search Canyon Aeroad` - мониторить Canyon Aeroad
`/deals Canyon` - показать лучшие предложения Canyon
"""
