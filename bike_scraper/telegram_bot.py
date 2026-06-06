"""
Telegram бот для управления скрейпером и получения отчетов
"""

import os
import logging
from typing import List, Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

# Conversation states
SEARCH_INPUT, CONFIRM_SEARCH = range(2)


class BikeScraperBot:
    """Telegram бот для управления скрейпером"""

    def __init__(self, token: str):
        self.token = token
        self.app = None
        self.reports = TelegramReportGenerator()

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

Введи `/help` чтобы увидеть все команды.
"""
        await update.message.reply_text(welcome, parse_mode='Markdown')
        logger.info(f"User {user_id} started bot")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = self.reports.get_help()
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /status"""
        status = self.reports.get_system_status()
        await update.message.reply_text(status, parse_mode='Markdown')

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats"""
        stats = self.reports.get_market_stats()
        await update.message.reply_text(stats, parse_mode='Markdown')

    async def deals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /deals [поиск]"""
        search_term = ' '.join(context.args) if context.args else None
        deals = self.reports.get_best_deals(search_term, limit=5)
        await update.message.reply_text(deals, parse_mode='Markdown')

    async def price_analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /price_analysis"""
        brand = ' '.join(context.args) if context.args else None
        analysis = self.reports.get_price_analysis(brand)
        await update.message.reply_text(analysis, parse_mode='Markdown')

    async def add_search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /add_search [название]"""
        user_id = update.effective_user.id

        if not context.args:
            await update.message.reply_text(
                "❌ Используй: `/add_search Canyon Aeroad`",
                parse_mode='Markdown'
            )
            return

        search_term = ' '.join(context.args)
        await self.create_monitoring_search(user_id, search_term, update)

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
            search_id = search.id
            db.close()

            keyboard = [[
                InlineKeyboardButton("✅ Готово", callback_data=f"confirm_search_{search_id}"),
                InlineKeyboardButton("❌ Отмена", callback_data="cancel_search")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"✅ Поиск '{search_term}' добавлен!\n\n"
                f"📬 Вы будете получать отчеты о новых предложениях.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            logger.info(f"User {user_id} added search: {search_term}")

        except Exception as e:
            logger.error(f"Error creating search: {e}")
            await update.message.reply_text("❌ Ошибка добавления поиска")

    async def list_searches_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /list_searches"""
        user_id = update.effective_user.id

        try:
            db = next(get_db())
            searches = db.query(MonitoringSearch).filter(
                MonitoringSearch.user_id == user_id,
                MonitoringSearch.is_active == True
            ).all()

            if not searches:
                await update.message.reply_text(
                    "📋 У вас нет активных поисков\n\n"
                    "Добавьте новый: `/add_search Canyon Aeroad`",
                    parse_mode='Markdown'
                )
                db.close()
                return

            searches_text = "📋 **ВАШ СПИСОК ПОИСКОВ:**\n\n"
            for i, search in enumerate(searches, 1):
                count = db.query(Listing).filter(
                    Listing.title.ilike(f"%{search.search_term}%")
                ).count()
                searches_text += f"{i}. `{search.search_term}` ({count} объявлений)\n"
                searches_text += f"   🆔 ID: {search.id}\n"
                searches_text += f"   📅 Добавлен: {search.created_at.strftime('%d.%m.%Y')}\n\n"

            searches_text += "➖ Удалить: `/remove_search [id]`"

            await update.message.reply_text(searches_text, parse_mode='Markdown')
            db.close()

        except Exception as e:
            logger.error(f"Error listing searches: {e}")
            await update.message.reply_text("❌ Ошибка получения списка")

    async def remove_search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /remove_search [id]"""
        user_id = update.effective_user.id

        if not context.args:
            await update.message.reply_text(
                "❌ Используй: `/remove_search [id]`\n"
                "Получи ID через `/list_searches`",
                parse_mode='Markdown'
            )
            return

        try:
            search_id = int(context.args[0])
            db = next(get_db())

            search = db.query(MonitoringSearch).filter(
                MonitoringSearch.id == search_id,
                MonitoringSearch.user_id == user_id
            ).first()

            if not search:
                await update.message.reply_text("❌ Поиск не найден")
                db.close()
                return

            search.is_active = False
            db.commit()
            db.close()

            await update.message.reply_text(
                f"✅ Поиск '{search.search_term}' удален",
                parse_mode='Markdown'
            )
            logger.info(f"User {user_id} removed search {search_id}")

        except ValueError:
            await update.message.reply_text("❌ ID должен быть числом")
        except Exception as e:
            logger.error(f"Error removing search: {e}")
            await update.message.reply_text("❌ Ошибка удаления поиска")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопок"""
        query = update.callback_query
        await query.answer()

        if query.data.startswith("confirm_search_"):
            search_id = int(query.data.split("_")[-1])
            await query.edit_message_text("✅ Поиск активирован! Начинаем мониторинг.")
            logger.info(f"Search {search_id} confirmed")

        elif query.data == "cancel_search":
            await query.edit_message_text("❌ Отмена добавления поиска")

    def setup_handlers(self):
        """Настроить обработчики команд"""
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        self.app.add_handler(CommandHandler("deals", self.deals_command))
        self.app.add_handler(CommandHandler("price_analysis", self.price_analysis_command))
        self.app.add_handler(CommandHandler("add_search", self.add_search_command))
        self.app.add_handler(CommandHandler("list_searches", self.list_searches_command))
        self.app.add_handler(CommandHandler("remove_search", self.remove_search_command))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))

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
