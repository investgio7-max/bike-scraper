"""Telegram bot with hierarchical menu system"""
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

print("📦 Loading telegram_bot_menu...")

# Menu states
MAIN_MENU = "main"
SEARCH_MENU = "search"
SEARCH_RESULTS = "search_results"
MONITORING_MENU = "monitoring"
STATS_MENU = "stats"
HELP_MENU = "help"


def get_main_menu():
    """Main menu keyboard"""
    keyboard = [
        [KeyboardButton("🔍 Поиск"), KeyboardButton("📊 Статистика")],
        [KeyboardButton("💰 Мониторинг"), KeyboardButton("💡 Помощь")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_search_menu():
    """Search submenu keyboard"""
    keyboard = [
        [KeyboardButton("🤑 Лучшие цены"), KeyboardButton("📈 Анализ")],
        [KeyboardButton("🔄 Статус"), KeyboardButton("⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_monitoring_menu():
    """Monitoring menu keyboard"""
    keyboard = [
        [KeyboardButton("➕ Добавить"), KeyboardButton("📋 Мои поиски")],
        [KeyboardButton("➖ Удалить"), KeyboardButton("⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_back_menu():
    """Simple back button"""
    keyboard = [[KeyboardButton("⬅️ Назад")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Start command - show main menu"""
    print(f"📨 /start from {update.effective_user.id}")
    await update.message.reply_text(
        "👋 Привет! Я бот мониторинга велосипедов на Wallapop.",
        reply_markup=get_main_menu()
    )
    print("✅ Main menu shown")
    return MAIN_MENU


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Handle main menu buttons"""
    text = update.message.text
    print(f"📨 Main menu: {text}")

    if text == "🔍 Поиск":
        await update.message.reply_text(
            "🔍 Выберите действие поиска:",
            reply_markup=get_search_menu()
        )
        return SEARCH_MENU

    elif text == "💰 Мониторинг":
        await update.message.reply_text(
            "💰 Управление мониторингом:",
            reply_markup=get_monitoring_menu()
        )
        return MONITORING_MENU

    elif text == "📊 Статистика":
        await update.message.reply_text(
            "📊 Статистика парсинга:\n\n"
            "📈 Всего объявлений: 1234\n"
            "✨ Новых сегодня: 45\n"
            "💰 Средняя цена: €850\n"
            "🎯 Минимальная цена: €450",
            reply_markup=get_back_menu()
        )
        return STATS_MENU

    elif text == "💡 Помощь":
        await update.message.reply_text(
            "💡 Справка:\n\n"
            "🔍 Поиск - поиск велосипедов по названию\n"
            "💰 Мониторинг - отслеживание цен\n"
            "📊 Статистика - общая информация",
            reply_markup=get_back_menu()
        )
        return HELP_MENU

    return MAIN_MENU


async def handle_search_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Handle search submenu"""
    text = update.message.text
    print(f"📨 Search menu: {text}")

    if text == "🤑 Лучшие цены":
        await update.message.reply_text(
            "🤑 Лучшие цены сейчас:\n\n"
            "1️⃣ Trek FX 3 - €450\n"
            "2️⃣ Giant Escape 3 - €520\n"
            "3️⃣ Specialized Sirrus - €580",
            reply_markup=get_search_menu()
        )
        return SEARCH_MENU

    elif text == "📈 Анализ":
        await update.message.reply_text(
            "📈 Анализ цен:\n\n"
            "📊 Средняя цена: €750\n"
            "⬇️ Тренд: снижается\n"
            "🎯 Лучшее время: вечер",
            reply_markup=get_search_menu()
        )
        return SEARCH_MENU

    elif text == "🔄 Статус":
        await update.message.reply_text(
            "🔄 Статус парсинга:\n\n"
            "✅ Активен\n"
            "🔄 Обновление: каждые 10 минут\n"
            "📡 Последнее: 2 минуты назад",
            reply_markup=get_search_menu()
        )
        return SEARCH_MENU

    elif text == "⬅️ Назад":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=get_main_menu()
        )
        return MAIN_MENU

    return SEARCH_MENU


async def handle_monitoring_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Handle monitoring menu"""
    text = update.message.text
    print(f"📨 Monitoring menu: {text}")

    if text == "➕ Добавить":
        await update.message.reply_text(
            "➕ Введите название велосипеда для мониторинга:\n\n"
            "Пример: Trek FX 3"
        )
        return SEARCH_RESULTS

    elif text == "📋 Мои поиски":
        await update.message.reply_text(
            "📋 Ваши активные поиски:\n\n"
            "1. Canyon Aeroad CF SLX\n"
            "2. Trek FX 3\n"
            "3. Giant Escape 3",
            reply_markup=get_monitoring_menu()
        )
        return MONITORING_MENU

    elif text == "➖ Удалить":
        await update.message.reply_text(
            "➖ Введите номер поиска для удаления (1-3):"
        )
        return SEARCH_RESULTS

    elif text == "⬅️ Назад":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=get_main_menu()
        )
        return MAIN_MENU

    return MONITORING_MENU


async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Handle back button from any submenu"""
    text = update.message.text
    if text == "⬅️ Назад":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=get_main_menu()
        )
        return MAIN_MENU
    return MAIN_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel conversation"""
    await update.message.reply_text("Отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    """Start the bot"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ No TELEGRAM_BOT_TOKEN!")
        return

    print(f"🤖 Bot starting...")
    app = Application.builder().token(token).build()

    # Conversation handler for menu navigation
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)],
            SEARCH_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_menu)],
            MONITORING_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_monitoring_menu)],
            STATS_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_back)],
            HELP_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_back)],
            SEARCH_RESULTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_monitoring_menu)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    print("➕ Adding handlers...")
    app.add_handler(conv_handler)

    print("🚀 Starting polling...")
    app.run_polling(allowed_updates=['message', 'edited_message'])


if __name__ == '__main__':
    main()
