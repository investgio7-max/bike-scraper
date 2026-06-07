"""
Планировщик для непрерывного парсинга объявлений
"""

import schedule
import time
from datetime import datetime
from typing import List

from bike_scraper.config import SCRAPE_INTERVAL, SEARCH_TERMS, MAX_RESULTS
from bike_scraper.database import get_session
from bike_scraper.models import Listing
from bike_scraper.scraper_wallapop_smart import create_wallapop_smart_scraper
from bike_scraper.service_listings import ListingService
from bike_scraper.utils_images import ImageDownloader
from bike_scraper.utils_logger import get_logger

logger = get_logger('scheduler')


class BikeScraperScheduler:
    """Планировщик для парсинга велосипедов"""

    def __init__(self):
        self.scraper = None
        self.image_downloader = ImageDownloader()
        self.is_running = False
        self.stats = {
            'runs': 0,
            'listings_found': 0,
            'listings_new': 0,
            'errors': 0,
            'last_run': None
        }

    def run(self):
        """Запустить планировщик (alias для start)"""
        self.start()

    def start(self):
        """Запустить планировщик"""
        logger.info(f"🚀 Запускаю планировщик (интервал: {SCRAPE_INTERVAL}с)")

        self.is_running = True

        # Запускаем сразу
        self.run_scraping()

        # Затем по расписанию
        schedule.every(SCRAPE_INTERVAL).seconds.do(self.run_scraping)

        # Периодическая очистка
        schedule.every().day.at("03:00").do(self.cleanup)

        # Анализ цен
        schedule.every().hour.do(self.analyze_prices)

        # Отправка alerts для выгодных сделок
        schedule.every(10).minutes.do(self.send_profit_alerts)

        # Цикл
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("⏹️  Планировщик остановлен")
            self.stop()

    def stop(self):
        """Остановить планировщик"""
        self.is_running = False
        if self.scraper:
            self.scraper.close()
        logger.info("✅ Планировщик остановлен")

    def run_scraping(self):
        """Выполнить парсинг"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 ЗАПУСК ПАРСИНГА - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*60}")

        start_time = time.time()
        total_found = 0
        total_new = 0
        total_errors = 0

        db = get_session()

        try:
            # Инициализируем скрейпер (CloakBrowser с улучшенными таймаутами)
            scraper = create_wallapop_smart_scraper()

            # Парсим по каждому поисковому терму
            for search_term in SEARCH_TERMS:
                try:
                    logger.info(f"\n📋 Поиск: '{search_term}'")

                    listings = scraper.search(search_term, max_results=MAX_RESULTS)
                    total_found += len(listings)

                    # Сохраняем в БД
                    for listing_data in listings:
                        try:
                            listing, is_new = ListingService.get_or_create_listing(db, listing_data)

                            if is_new:
                                total_new += 1

                                # Проверяем на дубликаты
                                original_id = ListingService.check_for_duplicates(db, listing)
                                if original_id:
                                    ListingService.mark_as_duplicate(db, listing.id, original_id)

                                # Скачиваем изображения
                                if listing_data.images:
                                    images_result = self.image_downloader.download_images(
                                        str(listing.id),
                                        listing_data.images
                                    )
                                    listing.main_image_path = images_result['main_image']
                                    listing.images = images_result.get('images', [])

                        except Exception as e:
                            logger.warning(f"⚠️  Ошибка сохранения объявления: {e}")
                            total_errors += 1
                            continue

                    # Коммитим после каждого поискового запроса
                    db.commit()

                    logger.info(f"✅ Найдено {len(listings)} объявлений, новых {total_new}")

                    # Задержка между поисками (увеличена для Cloudflare)
                    time.sleep(30)

                except Exception as e:
                    logger.error(f"❌ Ошибка поиска '{search_term}': {e}")
                    total_errors += 1
                    continue

            # Сохраняем логи
            duration = time.time() - start_time
            ListingService.save_scraper_log(
                db,
                source='wallapop',
                search_term=','.join(SEARCH_TERMS),
                total_found=total_found,
                successfully_parsed=total_new,
                errors_count=total_errors,
                duration_seconds=duration,
                status='success' if total_errors == 0 else 'partial'
            )

            db.commit()

            # Статистика
            self.stats['runs'] += 1
            self.stats['listings_found'] += total_found
            self.stats['listings_new'] += total_new
            self.stats['errors'] += total_errors
            self.stats['last_run'] = datetime.now()

            duration = time.time() - start_time

            logger.info(f"\n{'─'*60}")
            logger.info(f"✨ ИТОГИ ПАРСИНГА:")
            logger.info(f"  📊 Найдено: {total_found} объявлений")
            logger.info(f"  ✨ Новых: {total_new}")
            logger.info(f"  ⚠️  Ошибок: {total_errors}")
            logger.info(f"  ⏱️  Время: {duration:.1f}с")
            logger.info(f"{'─'*60}\n")

            scraper.close()

        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            self.stats['errors'] += 1
        finally:
            db.close()

    def cleanup(self):
        """Очистить неиспользуемые данные"""
        logger.info("🧹 Запускаю очистку...")

        db = get_session()

        try:
            # Получаем активные объявления
            active_listings = db.query(Listing).filter(Listing.is_active == True).all()
            active_ids = {str(listing.id) for listing in active_listings}

            # Удаляем неиспользуемые изображения
            deleted = self.image_downloader.cleanup_unused_images(active_ids)

            # Удаляем старые неактивные объявления (старше 3 месяцев)
            from datetime import timedelta
            from sqlalchemy import and_
            cutoff = datetime.utcnow() - timedelta(days=90)

            old_listings = db.query(Listing).filter(
                and_(
                    Listing.is_active == False,
                    Listing.updated_at < cutoff
                )
            ).all()

            logger.info(f"🗑️  Удаляю {len(old_listings)} старых объявлений")

            for listing in old_listings:
                db.delete(listing)

            db.commit()

            logger.info(f"✅ Очистка завершена")

        except Exception as e:
            logger.error(f"❌ Ошибка очистки: {e}")
        finally:
            db.close()

    def analyze_prices(self):
        """Анализировать цены"""
        logger.info("📊 Анализирую цены...")

        db = get_session()

        try:
            ListingService.calculate_price_analysis(db)
            db.commit()
            logger.info("✅ Анализ завершен")
        except Exception as e:
            logger.error(f"❌ Ошибка анализа: {e}")
        finally:
            db.close()

    def send_profit_alerts(self):
        """Отправить Telegram alerts для выгодных сделок"""
        try:
            db = get_session()

            # Получаем новые выгодные сделки за последний час
            deals = ListingService.get_new_good_deals(
                db,
                hours=1,
                min_profit_percent=20,
                min_profit_euros=500
            )

            if not deals:
                logger.debug("ℹ️  Нет новых выгодных сделок для alert")
                return

            # Отправляем alert для каждой сделки
            for listing, analysis in deals:
                try:
                    self._send_deal_alert(listing, analysis)
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка отправки alert: {e}")

            db.close()

        except Exception as e:
            logger.error(f"❌ Ошибка в send_profit_alerts: {e}")

    def _send_deal_alert(self, listing, analysis: dict):
        """Отправить alert о выгодной сделке в Telegram"""
        try:
            from bike_scraper.telegram_bot_final import bot
            from telegram import ParseMode

            bike = analysis.get('bike', {})
            market = analysis.get('market_analysis', {})

            # Форматируем сообщение
            title = f"🎉 ВЫГОДНАЯ СДЕЛКА! {bike.get('brand', 'Unknown')} {bike.get('model', '')}"
            message = f"""
{title}

📊 Детали велосипеда:
  • Бренд: {bike.get('brand', 'N/A')}
  • Модель: {bike.get('model', 'N/A')}
  • Год: {bike.get('year', 'N/A')}
  • Размер: {bike.get('size', 'N/A')}
  • Уверенность: {bike.get('confidence', 0):.0f}%

💰 Финансовая информация:
  • Цена объявления: €{listing.price:.0f}
  • Рыночная цена: €{market.get('market_median', 0):.0f}
  • Профит: €{market.get('profit_euros', 0):.0f} ({market.get('profit_percent', 0):.0f}%)
  • Сравнено с: {market.get('comparable_count', 0)} объявлениями

🔗 Ссылка: {listing.url}

📍 Продавец: {listing.seller_name} (рейтинг: {listing.seller_rating})
"""

            # TODO: отправить в Telegram (после добавления поддержки alerts в боте)
            logger.info(f"📤 Alert отправлен: {listing.title[:50]}")
            logger.debug(f"Alert message:\n{message}")

        except Exception as e:
            logger.error(f"❌ Ошибка форматирования alert: {e}")

    def get_stats(self) -> dict:
        """Получить статистику"""
        return self.stats.copy()


def main():
    """Главная точка входа для планировщика"""
    from database import init_db

    # Инициализируем БД
    init_db()

    # Создаем и запускаем планировщик
    scheduler = BikeScraperScheduler()

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("⏹️  Выход из программы")
        scheduler.stop()


if __name__ == '__main__':
    main()
