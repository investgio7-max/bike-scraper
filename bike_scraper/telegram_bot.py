"""
Telegram бот для управления скрейпером - упрощенная версия
"""

import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)
from bike_scraper.models import MonitoringSearch, Listing
from bike_scraper.database import get_db
from bike_scraper.telegram_reports import TelegramReportGenerator
from bike_scraper.utils_logger import get_logger

logger = get_logger('telegram_bot')


class BikeScraperBot:
    """Telegram бот для управления скрейпером"""

    def __init__(self, token: str):
        self.token = token
        self.app = None
        self.reports = TelegramReportGenerator()

    @staticmethod
    def get_main_menu():
        keyboard = [
            [KeyboardButton("🔍 Поиск"), KeyboardButton("📊 Статистика")],
            [KeyboardButton("💰 Мониторинг"), KeyboardButton("💡 Помощь")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    @staticmethod
    def get_search_menu():
        keyboard = [
            [KeyboardButton("🤑 Лучшие цены"), KeyboardButton("📈 Анализ цен")],
            [KeyboardButton("🔄 Статус"), KeyboardButton("⬅️ Назад")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    @staticmethod
    def get_monitoring_menu():
        keyboard = [
            [KeyboardButton("➕ Добавить поиск"), KeyboardButton("📋 Мои поиски")],
            [KeyboardButton("➖ Удалить поиск"), KeyboardButton("⬅️ Назад")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    @staticmethod
    def get_stats_menu():
        keyboard = [
            [KeyboardButton("📊 Статистика рынка"), KeyboardButton("🔔 Статус системы")],
            [KeyboardButton("⬅️ Назад")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "пользователь"

        welcome = f"""👋 Привет, {user_name}!

Я бот мониторинга велосипедов на Wallapop.

📚 Что я умею:
• 🔍 Мониторить цены на велосипеды
• 📊 Показывать статистику рынка
• 🤑 Находить лучшие предложения
• 📈 Анализировать тренды цен

Выберите операцию:
"""
        await update.message.reply_text(
            welcome,
            reply_markup=self.get_main_menu(),
            parse_mode='Markdown'
        )
        logger.info(f"User {user_id} started bot")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка всех текстовых сообщений"""
        text = update.message.text
        user_id = update.effective_user.id

        # Главное меню
        if text == "🔍 Поиск":
            await update.message.reply_text(
                "Выберите тип поиска:",
                reply_markup=self.get_search_menu()
            )

        elif text == "📊 Статистика":
            await update.message.reply_text(
                "Выберите статистику:",
                reply_markup=self.get_stats_menu()
            )

        elif text == "💰 Мониторинг":
            await update.message.reply_text(
                "Управление мониторингом:",
                reply_markup=self.get_monitoring_menu()
            )

        elif text == "💡 Помощь":
            help_text = self.reports.get_help()
            await update.message.reply_text(
                help_text,
                reply_markup=self.get_main_menu(),
                parse_mode='Markdown'
            )

        # Меню поиска
        elif text == "🤑 Лучшие цены":
            context.user_data['mode'] = 'deals'
            await update.message.reply_text(
                "Введите что ищете (например: Canyon, Specialized Tarmac):"
            )

        elif text == "📈 Анализ цен":
            context.user_data['mode'] = 'price'
            await update.message.reply_text(
                "Введите название бренда (например: Canyon):"
            )

        elif text == "🔄 Статус":
            status = self.reports.get_system_status()
            await update.message.reply_text(
                status,
                reply_markup=self.get_search_menu(),
                parse_mode='Markdown'
            )

        # Меню статистики
        elif text == "📊 Статистика рынка":
            stats = self.reports.get_market_stats()
            await update.message.reply_text(
                stats,
                reply_markup=self.get_stats_menu(),
                parse_mode='Markdown'
            )

        elif text == "🔔 Статус системы":
            status = self.reports.get_system_status()
            await update.message.reply_text(
                status,
                reply_markup=self.get_stats_menu(),
                parse_mode='Markdown'
            )

        # Меню мониторинга
        elif text == "➕ Добавить поиск":
            context.user_data['mode'] = 'add_search'
            await update.message.reply_text(
                "Введите название поиска (например: Canyon Aeroad):"
            )

        elif text == "📋 Мои поиски":
            try:
                db = next(get_db())
                searches = db.query(MonitoringSearch).filter(
                    MonitoringSearch.user_id == user_id,
                    MonitoringSearch.is_active == True
                ).all()

                if not searches:
                    msg = "📋 У вас нет активных поисков"
                else:
                    msg = "📋 **ВАШ СПИСОК ПОИСКОВ:**\n\n"
                    for i, search in enumerate(searches, 1):
                        count = db.query(Listing).filter(
                            Listing.title.ilike(f"%{search.search_term}%")
                        ).count()
                        msg += f"{i}. {search.search_term} ({count} объявлений)\n"
                        msg += f"   🆔 ID: {search.id}\n"

                db.close()
                await update.message.reply_text(
                    msg,
                    reply_markup=self.get_monitoring_menu(),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error: {e}")
                await update.message.reply_text("❌ Ошибка получения списка")

        elif text == "➖ Удалить поиск":
            context.user_data['mode'] = 'delete_search'
            try:
                db = next(get_db())
                searches = db.query(MonitoringSearch).filter(
                    MonitoringSearch.user_id == user_id,
                    MonitoringSearch.is_active == True
                ).all()
                db.close()

                if not searches:
                    await update.message.reply_text(
                        "❌ Нет активных поисков",
                        reply_markup=self.get_monitoring_menu()
                    )
                else:
                    msg = "Введите ID поиска:\n\n"
                    for search in searches:
                        msg += f"ID {search.id}: {search.search_term}\n"
                    await update.message.reply_text(msg)
            except Exception as e:
                logger.error(f"Error: {e}")
                await update.message.reply_text("❌ Ошибка")

        # Назад
        elif text == "⬅️ Назад":
            context.user_data['mode'] = None
            await update.message.reply_text(
                "Главное меню:",
                reply_markup=self.get_main_menu()
            )

        # Обработка режимов ввода
        else:
            mode = context.user_data.get('mode')

            if mode == 'deals':
                deals = self.reports.get_best_deals(text, limit=5)
                await update.message.reply_text(
                    deals,
                    reply_markup=self.get_search_menu(),
                    parse_mode='Markdown'
                )
                context.user_data['mode'] = None

            elif mode == 'price':
                analysis = self.reports.get_price_analysis(text)
                await update.message.reply_text(
                    analysis,
                    reply_markup=self.get_search_menu(),
                    parse_mode='Markdown'
                )
                context.user_data['mode'] = None

            elif mode == 'add_search':
                await self.create_monitoring_search(user_id, text, update)
                context.user_data['mode'] = None

            elif mode == 'delete_search':
                if text.isdigit():
                    search_id = int(text)
                    try:
                        db = next(get_db())
                        search = db.query(MonitoringSearch).filter(
                            MonitoringSearch.id == search_id,
                            MonitoringSearch.user_id == user_id
                        ).first()
                        if not search:
                            await update.message.reply_text("❌ Поиск не найден")
                        else:
                            search.is_active = False
                            db.commit()
                            db.close()
                            await update.message.reply_text(
                                f"✅ Поиск '{search.search_term}' удален!",
                                reply_markup=self.get_monitoring_menu()
                            )
                        db.close()
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        await update.message.reply_text("❌ Ошибка удаления")
                    context.user_data['mode'] = None
            else:
                await update.message.reply_text(
                    "❓ Выберите из меню:",
                    reply_markup=self.get_main_menu()
                )

    async def create_monitoring_search(self, user_id: int, search_term: str, update: Update):
        """Добавить поиск"""
        try:
            db = next(get_db())

            existing = db.query(MonitoringSearch).filter(
                MonitoringSearch.user_id == user_id,
                MonitoringSearch.search_term == search_term,
                MonitoringSearch.is_active == True
            ).first()

            if existing:
                await update.message.reply_text(
                    f"⚠️ Вы уже мониторите '{search_term}'",
                    reply_markup=self.get_monitoring_menu()
                )
                db.close()
                return

            sample = db.query(Listing).filter(
                Listing.title.ilike(f"%{search_term}%")
            ).limit(1).all()

            if not sample:
                await update.message.reply_text(
                    f"❌ По запросу '{search_term}' ничего не найдено",
                    reply_markup=self.get_monitoring_menu()
                )
                db.close()
                return

            search = MonitoringSearch(
                user_id=user_id,
                search_term=search_term,
                is_active=True,
                created_at=datetime.now()
            )
            db.add(search)
            db.commit()
            db.close()

            await update.message.reply_text(
                f"✅ Поиск '{search_term}' добавлен!\n\n"
                f"📬 Вы будете получать уведомления о новых предложениях.",
                reply_markup=self.get_monitoring_menu()
            )
            logger.info(f"User {user_id} added search: {search_term}")

        except Exception as e:
            logger.error(f"Error: {e}")
            await update.message.reply_text("❌ Ошибка добавления поиска")

    def setup_handlers(self):
        """Настроить обработчики"""
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def setup(self):
        """Инициализировать"""
        self.app = Application.builder().token(self.token).build()
        self.setup_handlers()
        logger.info("✅ Telegram bot initialized")

    async def run(self):
        """Запустить бота"""
        if not self.app:
            await self.setup()

        logger.info("🤖 Starting Telegram bot...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(allowed_updates=['message', 'edited_message'])

    async def stop(self):
        """Остановить бота"""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            logger.info("✅ Telegram bot stopped")


def create_telegram_bot(token: str = None) -> BikeScraperBot:
    """Factory"""
    if not token:
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")
    return BikeScraperBot(token)
