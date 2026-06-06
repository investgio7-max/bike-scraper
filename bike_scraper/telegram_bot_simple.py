"""Simple Telegram bot for testing"""
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Simple /start handler"""
    print(f"📨 /start received from {update.effective_user.id}")
    await update.message.reply_text("👋 Привет!")
    print("✅ Response sent!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo handler"""
    print(f"📨 Message: {update.message.text}")
    await update.message.reply_text(f"Echo: {update.message.text}")


def main():
    """Start the bot."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ No token!")
        return

    print(f"🤖 Bot starting with token: {token[:20]}...")
    app = Application.builder().token(token).build()

    print("➕ Adding handlers...")
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("🚀 Starting polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
