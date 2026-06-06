"""
Обработчик уведомлений для Telegram
Отправляет уведомления о новых объявлениях и изменении цен
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import func
from telegram import Bot

from bike_scraper.models import (
    Listing, MonitoringSearch, ListingNotification, ListingHistory
)
from bike_scraper.database import get_db
from bike_scraper.utils_logger import get_logger

logger = get_logger('notification')


class NotificationHandler:
    """Обработчик уведомлений"""

    def __init__(self, telegram_token: str):
        self.bot = Bot(token=telegram_token)

    async def check_and_send_notifications(self):
        """Проверить новые объявления и отправить уведомления"""
        try:
            db = next(get_db())

            # Получаем все активные поиски
            searches = db.query(MonitoringSearch).filter(
                MonitoringSearch.is_active == True
            ).all()

            logger.info(f"🔔 Проверяю {len(searches)} активных поисков...")

            for search in searches:
                await self.process_search(search, db)

            db.close()
            logger.info("✅ Проверка уведомлений завершена")

        except Exception as e:
            logger.error(f"❌ Ошибка проверки уведомлений: {e}")

    async def process_search(self, search: MonitoringSearch, db):
        """Обработать один поиск"""
        try:
            # Получаем новые объявления с момента последней проверки
            new_listings = db.query(Listing).filter(
                Listing.title.ilike(f"%{search.search_term}%"),
                Listing.date_collected >= (search.last_checked or datetime.now() - timedelta(hours=24)),
                Listing.is_active == True
            ).order_by(Listing.date_collected.desc()).all()

            logger.debug(f"📋 Поиск '{search.search_term}': найдено {len(new_listings)} новых объявлений")

            # Отправляем уведомления о новых объявлениях
            if search.notify_new_listings and new_listings:
                for listing in new_listings[:5]:  # Максимум 5 объявлений за раз
                    await self.send_new_listing_notification(search.user_id, search.id, listing, db)

            # Проверяем падение цен
            if search.notify_price_drop and search.price_drop_threshold:
                await self.check_price_drops(search, db)

            # Обновляем последнюю проверку
            search.last_checked = datetime.utcnow()
            search.listings_found = len(new_listings)
            db.commit()

        except Exception as e:
            logger.error(f"❌ Ошибка обработки поиска {search.search_term}: {e}")

    async def send_new_listing_notification(self, user_id: int, search_id: int, listing: Listing, db):
        """Отправить уведомление о новом объявлении"""
        try:
            # Проверяем что мы уже отправляли это уведомление
            existing = db.query(ListingNotification).filter(
                ListingNotification.user_id == user_id,
                ListingNotification.listing_id == listing.id,
                ListingNotification.notification_type == 'new_listing'
            ).first()

            if existing and existing.is_sent:
                return  # Уже отправляли

            # Формируем сообщение
            message = f"""🚴 **НОВОЕ ОБЪЯВЛЕНИЕ**

{listing.title}

💰 Цена: €{listing.price}
📍 Локация: {listing.location}
👤 Продавец: {listing.seller_name}

🔗 [Посмотреть полностью]({listing.url})
"""

            # Отправляем сообщение
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )

            # Логируем отправку
            notification = ListingNotification(
                user_id=user_id,
                search_id=search_id,
                listing_id=listing.id,
                notification_type='new_listing',
                title=listing.title,
                price=listing.price,
                url=listing.url,
                is_sent=True,
                sent_at=datetime.utcnow()
            )
            db.add(notification)
            db.commit()

            logger.info(f"📤 Отправил уведомление пользователю {user_id} о {listing.title}")

        except Exception as e:
            logger.warning(f"⚠️ Ошибка отправки уведомления: {e}")

    async def check_price_drops(self, search: MonitoringSearch, db):
        """Проверить падение цен"""
        try:
            # Получаем последние изменения цен
            price_changes = db.query(ListingHistory).filter(
                ListingHistory.checked_at >= (search.last_checked or datetime.now() - timedelta(hours=24)),
                ListingHistory.price_new < ListingHistory.price_old
            ).all()

            for change in price_changes:
                price_drop = change.price_old - change.price_new

                if price_drop >= search.price_drop_threshold:
                    # Получаем объявление
                    listing = db.query(Listing).filter(
                        Listing.id == change.listing_id
                    ).first()

                    if listing and listing.title.ilike(f"%{search.search_term}%"):
                        await self.send_price_drop_notification(
                            search.user_id, search.id, listing, change.price_old, db
                        )

        except Exception as e:
            logger.warning(f"⚠️ Ошибка проверки падения цен: {e}")

    async def send_price_drop_notification(self, user_id: int, search_id: int, listing: Listing, old_price: float, db):
        """Отправить уведомление о падении цены"""
        try:
            # Проверяем что не отправляли недавно
            recent = db.query(ListingNotification).filter(
                ListingNotification.user_id == user_id,
                ListingNotification.listing_id == listing.id,
                ListingNotification.notification_type == 'price_drop',
                ListingNotification.sent_at >= datetime.utcnow() - timedelta(hours=1)
            ).first()

            if recent:
                return  # Недавно отправляли

            price_drop = old_price - listing.price
            drop_percent = (price_drop / old_price) * 100

            message = f"""🤑 **ЦЕНА УПАЛА!**

{listing.title}

💰 Была: €{old_price:.0f}
💚 Теперь: €{listing.price:.0f}
📉 Снижение: €{price_drop:.0f} (-{drop_percent:.1f}%)

🔗 [Посмотреть полностью]({listing.url})
"""

            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )

            # Логируем отправку
            notification = ListingNotification(
                user_id=user_id,
                search_id=search_id,
                listing_id=listing.id,
                notification_type='price_drop',
                title=listing.title,
                price=listing.price,
                url=listing.url,
                previous_price=old_price,
                is_sent=True,
                sent_at=datetime.utcnow()
            )
            db.add(notification)
            db.commit()

            logger.info(f"📤 Отправил уведомление о падении цены пользователю {user_id}")

        except Exception as e:
            logger.warning(f"⚠️ Ошибка отправки уведомления о цене: {e}")


async def run_notification_service(telegram_token: str):
    """Запустить сервис уведомлений"""
    handler = NotificationHandler(telegram_token)

    logger.info("🔔 Запуск сервиса уведомлений...")

    while True:
        try:
            await handler.check_and_send_notifications()
            # Проверяем каждые 5 минут
            await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"❌ Ошибка в сервисе уведомлений: {e}")
            await asyncio.sleep(60)  # Ждем минуту перед повторной попыткой
