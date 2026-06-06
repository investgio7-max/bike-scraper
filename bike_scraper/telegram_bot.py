"""
Минимальный Telegram бот для проверки
"""

import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logger = logging.getLogger(__name__)


class BikeScraperBot:
    """Telegram бот"""

    def __init__(self, token: str):
        self.token = token
        self.app = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start"""
        try:
            keyboard = [
                [KeyboardButton("🔍 Поиск"), KeyboardButton("📊 Статистика")],
                [KeyboardButton("💰 Мониторинг"), KeyboardButton("💡 Помощь")],
            ]
            markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await update.message.reply_text(
                "👋 Привет! Я бот мониторинга велосипедов на Wallapop.",
                reply_markup=markup
            )
            print(f"✅ Sent response to user {update.effective_user.id}")
        except Exception as e:
            print(f"❌ Error in start: {e}")
            await update.message.reply_text(f"Error: {e}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all text messages"""
        try:
            text = update.message.text
            print(f"📨 Received: {text} from {update.effective_user.id}")

            await update.message.reply_text(f"Вы написали: {text}")
            print(f"✅ Sent echo response")
        except Exception as e:
            print(f"❌ Error in handle_message: {e}")

    def setup_handlers(self):
        """Setup handlers"""
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(MessageHandler(filters.TEXT, self.handle_message))
        print("✅ Handlers setup complete")

    async def setup(self):
        """Initialize app"""
        print("🔧 Setting up bot...")
        self.app = Application.builder().token(self.token).build()
        self.setup_handlers()
        print("✅ Bot setup complete")

    async def run(self):
        """Run bot"""
        try:
            if not self.app:
                await self.setup()

            print("🤖 Starting polling...")
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(allowed_updates=['message', 'edited_message'])
            print("✅ Bot polling started")
        except Exception as e:
            print(f"❌ Error in run: {e}")
            raise

    async def stop(self):
        """Stop bot"""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            print("✅ Bot stopped")


def create_telegram_bot(token: str = None) -> BikeScraperBot:
    """Create bot"""
    if not token:
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")

    print(f"🔑 Token: {token[:20]}...")
    return BikeScraperBot(token)
