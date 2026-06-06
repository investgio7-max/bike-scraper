"""
Telegram бот для управления скрейпером и получения отчетов
"""

import os
import logging
from typing import List, Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)
from sqlalchemy import func
from bike_scraper.models import Listing, Bike, MonitoringSearch, ListingNotification
from bike_scraper.database import get_db, Session
from bike_scraper.telegram_reports import TelegramReportGenerator
from bike_scraper.utils_logger import get_logger

logger = get_logger('telegram_bot')

# No longer using ConversationHandler - using user_data for state tracking


class BikeScraperBot:
    """Telegram бот для управления скрейпером"""

    def __init__(self, token: str):
        self.token = token
        self.app = None
        self.reports = TelegramReportGenerator()

    @staticmethod
    def get_main_menu() -> ReplyKeyboardMarkup:
        """Главное меню"""
        keyboard = [
            [KeyboardButton("🔍 Поиск"), KeyboardButton("📊 Статистика")],
            [KeyboardButton("💰 Мониторинг"), KeyboardButton("💡 Помощь")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    @staticmethod
    def get_search_menu() -> ReplyKeyboardMarkup:
        """Меню поиска"""
        keyboard = [
            [KeyboardButton("🤑 Лучшие цены"), KeyboardButton("📈 Анализ цен")],
            [KeyboardButton("🔄 Статус"), KeyboardButton("⬅️ Назад")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    @staticmethod
    def get_monitoring_menu() -> ReplyKeyboardMarkup:
        """Меню мониторинга"""
        keyboard = [
            [KeyboardButton("➕ Добавить поиск"), KeyboardButton("📋 Мои поиски")],
            [KeyboardButton("➖ Удалить поиск"), KeyboardButton("⬅️ Назад")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    @staticmethod
    def get_stats_menu() -> ReplyKeyboardMarkup:
        """Меню статистики"""
        keyboard = [
            [KeyboardButton("📊 Статистика рынка"), KeyboardButton("🔔 Статус системы")],
            [KeyboardButton("⬅️ Назад")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start - Главное меню"""
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
        return MAIN_MENU

    async def handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка главного меню"""
        text = update.message.text
        user_id = update.effective_user.id

        if text == "🔍 Поиск":
            msg = "Выберите тип поиска:"
            await update.message.reply_text(
                msg,
                reply_markup=self.get_search_menu(),
                parse_mode='Markdown'
            )

        elif text == "📊 Статистика":
            msg = "Выберите что посмотреть:"
            await update.message.reply_text(
                msg,
                reply_markup=self.get_stats_menu(),
                parse_mode='Markdown'
            )

        elif text == "💰 Мониторинг":
            msg = "Управление мониторингом:"
            await update.message.reply_text(
                msg,
                reply_markup=self.get_monitoring_menu(),
                parse_mode='Markdown'
            )

        elif text == "💡 Помощь":
            help_text = self.reports.get_help()
            await update.message.reply_text(
                help_text,
                reply_markup=self.get_main_menu(),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❓ Не понимаю. Выберите из предложенных кнопок:",
                reply_markup=self.get_main_menu()
            )

    async def handle_search_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка меню поиска"""
        text = update.message.text

        if text == "🤑 Лучшие цены":
            context.user_data['mode'] = 'deals'
            await update.message.reply_text(
                "Введите что ищете (например: Canyon, Specialized Tarmac):",
                reply_markup=ReplyKeyboardMarkup(
                    [[KeyboardButton("⬅️ Назад")]],
                    resize_keyboard=True
                )
            )

        elif text == "📈 Анализ цен":
            context.user_data['mode'] = 'price'
            await update.message.reply_text(
                "Введите название бренда для анализа (например: Canyon, Specialized):",
                reply_markup=ReplyKeyboardMarkup(
                    [[KeyboardButton("⬅️ Назад")]],
                    resize_keyboard=True
                )
            )

        elif text == "🔄 Статус":
            status = self.reports.get_system_status()
            await update.message.reply_text(
                status,
                reply_markup=self.get_search_menu(),
                parse_mode='Markdown'
            )

        elif text == "⬅️ Назад":
            context.user_data['mode'] = None
            await update.message.reply_text(
                "Главное меню:",
                reply_markup=self.get_main_menu(),
                parse_mode='Markdown'
            )

    async def handle_monitoring_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка меню мониторинга"""
        text = update.message.text
        user_id = update.effective_user.id

        if text == "➕ Добавить поиск":
            context.user_data['mode'] = 'add_search'
            await update.message.reply_text(
                "Введите название поиска (например: Canyon Aeroad):",
                reply_markup=ReplyKeyboardMarkup(
                    [[KeyboardButton("⬅️ Назад")]],
                    resize_keyboard=True
                )
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
                logger.error(f"Error listing searches: {e}")
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
                        "❌ Нет активных поисков для удаления",
                        reply_markup=self.get_monitoring_menu()
                    )
                else:
                    msg = "Введите ID поиска для удаления:\n\n"
                    for search in searches:
                        msg += f"ID {search.id}: {search.search_term}\n"
                    await update.message.reply_text(
                        msg,
                        reply_markup=ReplyKeyboardMarkup(
                            [[KeyboardButton("⬅️ Назад")]],
                            resize_keyboard=True
                        )
                    )
            except Exception as e:
                logger.error(f"Error: {e}")
                await update.message.reply_text("❌ Ошибка")

        elif text == "⬅️ Назад":
            context.user_data['mode'] = None
            await update.message.reply_text(
                "Главное меню:",
                reply_markup=self.get_main_menu(),
                parse_mode='Markdown'
            )

    async def handle_stats_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка меню статистики"""
        text = update.message.text

        if text == "📊 Статистика рынка":
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

        elif text == "⬅️ Назад":
            context.user_data['mode'] = None
            await update.message.reply_text(
                "Главное меню:",
                reply_markup=self.get_main_menu(),
                parse_mode='Markdown'
            )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = self.reports.get_help()
        await update.message.reply_text(
            help_text,
            reply_markup=self.get_main_menu(),
            parse_mode='Markdown'
        )


    async def create_monitoring_search(self, user_id: int, search_term: str, update: Update):
        """Создать поиск для мониторинга"""
        try:
            db = next(get_db())

            # Проверим что такого поиска еще нет
            existing = db.query(MonitoringSearch).filter(
                MonitoringSearch.user_id == user_id,
                MonitoringSearch.search_term == search_term,
                MonitoringSearch.is_active == True
            ).first()

            if existing:
                await update.message.reply_text(
                    f"⚠️ Вы уже мониторите '{search_term}'",
                    parse_mode='Markdown'
                )
                db.close()
                return

            # Проверим что есть результаты
            sample_listings = db.query(Listing).filter(
                Listing.title.ilike(f"%{search_term}%")
            ).limit(1).all()

            if not sample_listings:
                await update.message.reply_text(
                    f"❌ По запросу '{search_term}' ничего не найдено на Wallapop",
                    parse_mode='Markdown'
                )
                db.close()
                return

            # Создаем поиск
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
                f"📬 Вы будете получать отчеты о новых предложениях.",
                reply_markup=self.get_monitoring_menu(),
                parse_mode='Markdown'
            )
            logger.info(f"User {user_id} added search: {search_term}")

        except Exception as e:
            logger.error(f"Error creating search: {e}")
            await update.message.reply_text("❌ Ошибка добавления поиска")

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений в зависимости от режима"""
        text = update.message.text
        user_id = update.effective_user.id
        mode = context.user_data.get('mode', None)

        # Обработка главного меню
        if mode is None or text in ["🔍 Поиск", "📊 Статистика", "💰 Мониторинг", "💡 Помощь"]:
            await self.handle_main_menu(update, context)

        # Обработка меню поиска
        elif mode == 'search' or text in ["🤑 Лучшие цены", "📈 Анализ цен", "🔄 Статус"]:
            if text in ["🤑 Лучшие цены", "📈 Анализ цен", "🔄 Статус"]:
                context.user_data['mode'] = 'search'
                await self.handle_search_menu(update, context)
            elif mode == 'deals':
                if text == "⬅️ Назад":
                    context.user_data['mode'] = None
                    await update.message.reply_text("Главное меню:", reply_markup=self.get_main_menu())
                else:
                    deals = self.reports.get_best_deals(text, limit=5)
                    await update.message.reply_text(deals, reply_markup=self.get_search_menu(), parse_mode='Markdown')
            elif mode == 'price':
                if text == "⬅️ Назад":
                    context.user_data['mode'] = None
                    await update.message.reply_text("Главное меню:", reply_markup=self.get_main_menu())
                else:
                    analysis = self.reports.get_price_analysis(text)
                    await update.message.reply_text(analysis, reply_markup=self.get_search_menu(), parse_mode='Markdown')

        # Обработка меню мониторинга
        elif mode == 'monitoring' or text in ["➕ Добавить поиск", "📋 Мои поиски", "➖ Удалить поиск"]:
            if text in ["➕ Добавить поиск", "📋 Мои поиски", "➖ Удалить поиск"]:
                context.user_data['mode'] = 'monitoring'
                await self.handle_monitoring_menu(update, context)
            elif mode == 'add_search':
                if text == "⬅️ Назад":
                    context.user_data['mode'] = None
                    await update.message.reply_text("Главное меню:", reply_markup=self.get_main_menu())
                else:
                    await self.create_monitoring_search(user_id, text, update)
                    context.user_data['mode'] = None
            elif mode == 'delete_search':
                if text == "⬅️ Назад":
                    context.user_data['mode'] = None
                    await update.message.reply_text("Главное меню:", reply_markup=self.get_main_menu())
                elif text.isdigit():
                    search_id = int(text)
                    try:
                        db = next(get_db())
                        search = db.query(MonitoringSearch).filter(
                            MonitoringSearch.id == search_id,
                            MonitoringSearch.user_id == user_id
                        ).first()
                        if not search:
                            await update.message.reply_text("❌ Поиск не найден", reply_markup=self.get_monitoring_menu())
                        else:
                            search.is_active = False
                            db.commit()
                            db.close()
                            await update.message.reply_text(f"✅ Поиск '{search.search_term}' удален!", reply_markup=self.get_monitoring_menu())
                            logger.info(f"User {user_id} removed search {search_id}")
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        await update.message.reply_text("❌ Ошибка удаления поиска")

        # Обработка меню статистики
        elif mode == 'stats' or text in ["📊 Статистика рынка", "🔔 Статус системы"]:
            if text in ["📊 Статистика рынка", "🔔 Статус системы"]:
                context.user_data['mode'] = 'stats'
            await self.handle_stats_menu(update, context)

        else:
            await update.message.reply_text("Выберите из предложенных кнопок:", reply_markup=self.get_main_menu())

    def setup_handlers(self):
        """Настроить обработчики команд"""
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))

    async def setup(self):
        """Инициализировать приложение"""
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
        await self.app.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    async def stop(self):
        """Остановить бота"""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            logger.info("✅ Telegram bot stopped")


def create_telegram_bot(token: str = None) -> BikeScraperBot:
    """Factory для создания Telegram бота"""
    if not token:
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен в переменных окружения")

    return BikeScraperBot(token)
