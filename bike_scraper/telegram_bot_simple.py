"""Simple Telegram bot for testing"""
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

print("📦 Importing telegram_bot_simple...")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    try:
        print(f"📨 /start from user {update.effective_user.id}")
        keyboard = [
            [KeyboardButton("🔍 Поиск"), KeyboardButton("📊 Статистика")],
            [KeyboardButton("💰 Мониторинг"), KeyboardButton("💡 Помощь")],
        ]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "👋 Привет! Я бот мониторинга велосипедов на Wallapop.",
            reply_markup=markup
        )
        print(f"✅ Sent menu to {update.effective_user.id}")
    except Exception as e:
        print(f"❌ Error in start: {e}")
        await update.message.reply_text(f"Ошибка: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button clicks and messages"""
    try:
        text = update.message.text
        print(f"📨 Message from {update.effective_user.id}: {text}")

        if text == "🔍 Поиск":
            await update.message.reply_text("🔍 Введите название велосипеда для поиска")
        elif text == "📊 Статистика":
            await update.message.reply_text("📊 Статистика парсинга:\n- Объявлений найдено: 0\n- Новых: 0")
        elif text == "💰 Мониторинг":
            await update.message.reply_text("💰 Мониторинг цен активирован")
        elif text == "💡 Помощь":
            await update.message.reply_text("💡 Используйте кнопки ниже для навигации")
        else:
            await update.message.reply_text(f"Вы написали: {text}")

        print(f"✅ Response sent")
    except Exception as e:
        print(f"❌ Error in handle_message: {e}")


def main():
    """Start the bot."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ No TELEGRAM_BOT_TOKEN!")
        return

    print(f"🤖 Bot starting...")
    app = Application.builder().token(token).build()

    print("➕ Adding handlers...")
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Starting polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
