"""Telegram bot with simple menu system"""
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

print("📦 Loading telegram_bot_final...")

# Store user states
user_states = {}


def get_main_menu():
    """Main menu"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("🔍 Поиск"), KeyboardButton("📊 Статистика")],
        [KeyboardButton("💰 Мониторинг"), KeyboardButton("💡 Помощь")],
    ], resize_keyboard=True)


def get_search_menu():
    """Search submenu"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("🤑 Лучшие цены"), KeyboardButton("📈 Анализ")],
        [KeyboardButton("🔄 Статус"), KeyboardButton("⬅️ Назад")],
    ], resize_keyboard=True)


def get_monitoring_menu():
    """Monitoring menu"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("➕ Добавить"), KeyboardButton("📋 Мои поиски")],
        [KeyboardButton("➖ Удалить"), KeyboardButton("⬅️ Назад")],
    ], resize_keyboard=True)


def get_back_menu():
    """Back button only"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("⬅️ Назад")],
    ], resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command"""
    user_id = update.effective_user.id
    user_states[user_id] = "main"
    print(f"📨 /start from {user_id}")

    await update.message.reply_text(
        "👋 Привет! Я бот мониторинга велосипедов на Wallapop.\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu()
    )
    print("✅ Main menu shown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all messages"""
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""
    state = user_states.get(user_id, "main")

    print(f"📨 {user_id} | State: {state} | Text: '{text}' (len={len(text)})")

    # Handle back button from any state
    if "Назад" in text:
        print(f"🔙 Back button detected from state {state}")
        user_states[user_id] = "main"
        await update.message.reply_text(
            "👈 Вернулись в главное меню",
            reply_markup=get_main_menu()
        )
        print(f"✅ Back to main")
        return

    # Main menu
    if state == "main":
        if text == "🔍 Поиск":
            user_states[user_id] = "search"
            await update.message.reply_text(
                "🔍 Выберите действие поиска:",
                reply_markup=get_search_menu()
            )

        elif text == "💰 Мониторинг":
            user_states[user_id] = "monitoring"
            await update.message.reply_text(
                "💰 Управление мониторингом:",
                reply_markup=get_monitoring_menu()
            )

        elif text == "📊 Статистика":
            user_states[user_id] = "stats"
            await update.message.reply_text(
                "📊 Статистика парсинга:\n\n"
                "📈 Всего объявлений: 1234\n"
                "✨ Новых сегодня: 45\n"
                "💰 Средняя цена: €850\n"
                "🎯 Минимальная цена: €450",
                reply_markup=get_back_menu()
            )

        elif text == "💡 Помощь":
            user_states[user_id] = "help"
            await update.message.reply_text(
                "💡 Справка:\n\n"
                "🔍 Поиск - поиск велосипедов\n"
                "💰 Мониторинг - отслеживание цен\n"
                "📊 Статистика - общая информация",
                reply_markup=get_back_menu()
            )

    # Search menu
    elif state == "search":
        if text == "🤑 Лучшие цены":
            await update.message.reply_text(
                "🤑 Лучшие цены сейчас:\n\n"
                "1️⃣ Trek FX 3 - €450\n"
                "2️⃣ Giant Escape 3 - €520\n"
                "3️⃣ Specialized Sirrus - €580",
                reply_markup=get_search_menu()
            )

        elif text == "📈 Анализ":
            await update.message.reply_text(
                "📈 Анализ цен:\n\n"
                "📊 Средняя цена: €750\n"
                "⬇️ Тренд: снижается\n"
                "🎯 Лучшее время: вечер",
                reply_markup=get_search_menu()
            )

        elif text == "🔄 Статус":
            await update.message.reply_text(
                "🔄 Статус парсинга:\n\n"
                "✅ Активен\n"
                "🔄 Обновление: каждые 10 минут\n"
                "📡 Последнее: 2 минуты назад",
                reply_markup=get_search_menu()
            )

        elif text == "⬅️ Назад":
            user_states[user_id] = "main"
            await update.message.reply_text(
                "👈 Вернулись в главное меню",
                reply_markup=get_main_menu()
            )

    # Monitoring menu
    elif state == "monitoring":
        if text == "➕ Добавить":
            await update.message.reply_text(
                "➕ Введите название велосипеда:",
                reply_markup=get_monitoring_menu()
            )

        elif text == "📋 Мои поиски":
            await update.message.reply_text(
                "📋 Ваши активные поиски:\n\n"
                "1. Canyon Aeroad CF SLX\n"
                "2. Trek FX 3\n"
                "3. Giant Escape 3",
                reply_markup=get_monitoring_menu()
            )

        elif text == "➖ Удалить":
            await update.message.reply_text(
                "➖ Введите номер поиска:",
                reply_markup=get_monitoring_menu()
            )

        elif text == "⬅️ Назад":
            user_states[user_id] = "main"
            await update.message.reply_text(
                "👈 Вернулись в главное меню",
                reply_markup=get_main_menu()
            )

    # Stats and Help - just show back button
    elif state in ["stats", "help"]:
        if text == "⬅️ Назад":
            user_states[user_id] = "main"
            await update.message.reply_text(
                "👈 Вернулись в главное меню",
                reply_markup=get_main_menu()
            )

    print(f"✅ Response sent, new state: {user_states.get(user_id, 'main')}")


def main():
    """Start bot"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ No token!")
        return

    print("🤖 Bot starting...")
    app = Application.builder().token(token).build()

    print("➕ Adding handlers...")
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Starting polling...")
    app.run_polling()


if __name__ == '__main__':
    main()
