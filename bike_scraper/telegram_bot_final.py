"""Telegram bot with simple menu system and real search"""
import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

print("📦 Loading telegram_bot_final...")

# Import callback handlers for Telegram inline buttons
try:
    from bike_scraper.telegram_callback_handlers import register_callbacks
    print("✅ Imported callback handlers")
except Exception as e:
    print(f"⚠️  Could not import callback handlers: {e}")
    register_callbacks = None

# Import async search handler (works properly in async bot context)
try:
    from bike_scraper.bot_search_handler_async import search_bikes_async, format_search_results
    print("✅ Imported async search handler")
except Exception as e:
    print(f"⚠️ Could not import search handler: {e}")
    search_bikes_async = None

# Import MonitoringService and database
try:
    from bike_scraper.service_listings import MonitoringService
    from bike_scraper.config import DATABASE_URL
    engine = create_engine(DATABASE_URL)
    print("✅ Imported MonitoringService and database")
except Exception as e:
    print(f"⚠️ Could not import MonitoringService: {e}")
    MonitoringService = None
    engine = None

# Store user states
user_states = {}
user_search_queries = {}  # Store search queries for users


def get_main_menu():
    """Main menu"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("🔍 Поиск"), KeyboardButton("📊 Статистика")],
        [KeyboardButton("💰 Мониторинг"), KeyboardButton("💡 Помощь")],
    ], resize_keyboard=True)


def get_search_menu():
    """Search submenu"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎯 Точный поиск"), KeyboardButton("📊 Все велосипеды")],
        [KeyboardButton("📈 Анализ"), KeyboardButton("⬅️ Назад")],
    ], resize_keyboard=True)


def get_monitoring_menu():
    """Monitoring menu"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("➕ Добавить"), KeyboardButton("📋 Мои поиски")],
        [KeyboardButton("🔔 Вкл/Выкл"), KeyboardButton("➖ Удалить")],
        [KeyboardButton("⬅️ Назад")],
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


async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get chat ID command"""
    chat_id_value = update.effective_chat.id
    user_id = update.effective_user.id

    message = f"""
📋 ID ИНФОРМАЦИЯ:

🔹 Chat ID: `{chat_id_value}`
🔹 User ID: `{user_id}`
🔹 Chat Type: {update.effective_chat.type}

➡️ Используй этот Chat ID для отправки alerts!
"""

    await update.message.reply_text(message, parse_mode="Markdown")
    print(f"✅ Chat ID sent: {chat_id_value}")


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

    # Exact search mode
    elif state == "search_exact":
        if text == "⬅️ Назад":
            user_states[user_id] = "search"
            await update.message.reply_text(
                "🔍 Выберите действие поиска:",
                reply_markup=get_search_menu()
            )
        else:
            user_search_queries[user_id] = text
            await update.message.reply_text(
                f"🎯 Точный поиск: '{text}'\n⏳ Это может занять 30-60 секунд...",
                reply_markup=get_back_menu()
            )

            if search_bikes_async:
                try:
                    print(f"🎯 EXACT search for: {text}")
                    results = await search_bikes_async(text, max_results=10)
                    result_text = format_search_results(results)

                    await update.message.reply_text(
                        result_text,
                        reply_markup=get_search_menu()
                    )
                    user_states[user_id] = "search"
                except Exception as e:
                    print(f"❌ Search error: {e}")
                    await update.message.reply_text(
                        f"❌ Ошибка: {e}",
                        reply_markup=get_search_menu()
                    )
                    user_states[user_id] = "search"
            else:
                await update.message.reply_text(
                    "⚠️ Поиск недоступен",
                    reply_markup=get_search_menu()
                )
                user_states[user_id] = "search"

    # All bikes search mode
    elif state == "search_all":
        if text == "⬅️ Назад":
            user_states[user_id] = "search"
            await update.message.reply_text(
                "🔍 Выберите действие поиска:",
                reply_markup=get_search_menu()
            )
        else:
            user_search_queries[user_id] = text
            await update.message.reply_text(
                f"📊 Поиск: '{text}'\n⏳ Это может занять 30-60 секунд...",
                reply_markup=get_back_menu()
            )

            if search_bikes_async:
                try:
                    print(f"📊 ALL search for: {text}")
                    results = await search_bikes_async(text, max_results=20)
                    result_text = format_search_results(results)

                    await update.message.reply_text(
                        result_text,
                        reply_markup=get_search_menu()
                    )
                    user_states[user_id] = "search"
                except Exception as e:
                    print(f"❌ Search error: {e}")
                    await update.message.reply_text(
                        f"❌ Ошибка: {e}",
                        reply_markup=get_search_menu()
                    )
                    user_states[user_id] = "search"
            else:
                await update.message.reply_text(
                    "⚠️ Поиск недоступен",
                    reply_markup=get_search_menu()
                )
                user_states[user_id] = "search"

    # Search menu
    elif state == "search":
        if text == "🎯 Точный поиск":
            user_states[user_id] = "search_exact"
            await update.message.reply_text(
                "🎯 Введите точное название велосипеда:\n\n"
                "Пример: Canyon Aeroad CFR",
                reply_markup=get_back_menu()
            )

        elif text == "📊 Все велосипеды":
            user_states[user_id] = "search_all"
            await update.message.reply_text(
                "📊 Введите бренд для поиска:\n\n"
                "Пример: Canyon, Trek, Specialized",
                reply_markup=get_back_menu()
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
            user_states[user_id] = "monitoring_add"
            await update.message.reply_text(
                "➕ Введите название велосипеда для мониторинга:\n\n"
                "Пример: Canyon Aeroad CFR, Trek FX 3",
                reply_markup=get_back_menu()
            )

        elif text == "📋 Мои поиски":
            if MonitoringService and engine:
                try:
                    with Session(engine) as db:
                        monitoring_list = MonitoringService.get_user_monitoring(db, user_id)
                        result_text = MonitoringService.format_monitoring_list(monitoring_list)
                except Exception as e:
                    print(f"❌ Error getting monitoring: {e}")
                    result_text = "❌ Ошибка получения списка поисков"
            else:
                result_text = "⚠️ Сервис мониторинга недоступен"

            await update.message.reply_text(
                result_text,
                reply_markup=get_monitoring_menu()
            )

        elif text == "🔔 Вкл/Выкл":
            await update.message.reply_text(
                "🔔 Введите название велосипеда для включения/выключения:\n\n"
                "Пример: Canyon Aeroad CF SLX",
                reply_markup=get_back_menu()
            )
            user_states[user_id] = "monitoring_toggle"

        elif text == "➖ Удалить":
            await update.message.reply_text(
                "➖ Введите название велосипеда для удаления:",
                reply_markup=get_back_menu()
            )
            user_states[user_id] = "monitoring_delete"

        elif text == "⬅️ Назад":
            user_states[user_id] = "main"
            await update.message.reply_text(
                "👈 Вернулись в главное меню",
                reply_markup=get_main_menu()
            )

    # Add monitoring
    elif state == "monitoring_add":
        if text == "⬅️ Назад":
            user_states[user_id] = "monitoring"
            await update.message.reply_text(
                "💰 Управление мониторингом:",
                reply_markup=get_monitoring_menu()
            )
        else:
            # Add monitoring
            if MonitoringService and engine:
                try:
                    with Session(engine) as db:
                        MonitoringService.add_monitoring(db, user_id, text)
                        db.commit()
                    await update.message.reply_text(
                        f"✅ Мониторинг добавлен: '{text}'",
                        reply_markup=get_monitoring_menu()
                    )
                except Exception as e:
                    print(f"❌ Error adding monitoring: {e}")
                    await update.message.reply_text(
                        f"❌ Ошибка: {e}",
                        reply_markup=get_monitoring_menu()
                    )
            else:
                await update.message.reply_text(
                    "⚠️ Сервис мониторинга недоступен",
                    reply_markup=get_monitoring_menu()
                )
            user_states[user_id] = "monitoring"

    # Toggle monitoring
    elif state == "monitoring_toggle":
        if text == "⬅️ Назад":
            user_states[user_id] = "monitoring"
            await update.message.reply_text(
                "💰 Управление мониторингом:",
                reply_markup=get_monitoring_menu()
            )
        else:
            if MonitoringService and engine:
                try:
                    with Session(engine) as db:
                        new_state = MonitoringService.toggle_monitoring(db, user_id, text)
                        db.commit()

                    if new_state is not None:
                        status = "ВКЛ 🔔" if new_state else "ВЫКЛ 🔕"
                        await update.message.reply_text(
                            f"✅ Мониторинг для '{text}': {status}",
                            reply_markup=get_monitoring_menu()
                        )
                    else:
                        await update.message.reply_text(
                            f"❌ Поиск '{text}' не найден",
                            reply_markup=get_monitoring_menu()
                        )
                except Exception as e:
                    print(f"❌ Error toggling monitoring: {e}")
                    await update.message.reply_text(
                        f"❌ Ошибка: {e}",
                        reply_markup=get_monitoring_menu()
                    )
            else:
                await update.message.reply_text(
                    "⚠️ Сервис мониторинга недоступен",
                    reply_markup=get_monitoring_menu()
                )
            user_states[user_id] = "monitoring"

    # Delete monitoring
    elif state == "monitoring_delete":
        if text == "⬅️ Назад":
            user_states[user_id] = "monitoring"
            await update.message.reply_text(
                "💰 Управление мониторингом:",
                reply_markup=get_monitoring_menu()
            )
        else:
            if MonitoringService and engine:
                try:
                    with Session(engine) as db:
                        success = MonitoringService.delete_monitoring(db, user_id, text)
                        db.commit()

                    if success:
                        await update.message.reply_text(
                            f"🗑️ '{text}' удален из мониторинга",
                            reply_markup=get_monitoring_menu()
                        )
                    else:
                        await update.message.reply_text(
                            f"❌ Поиск '{text}' не найден",
                            reply_markup=get_monitoring_menu()
                        )
                except Exception as e:
                    print(f"❌ Error deleting monitoring: {e}")
                    await update.message.reply_text(
                        f"❌ Ошибка: {e}",
                        reply_markup=get_monitoring_menu()
                    )
            else:
                await update.message.reply_text(
                    "⚠️ Сервис мониторинга недоступен",
                    reply_markup=get_monitoring_menu()
                )
            user_states[user_id] = "monitoring"

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
    app.add_handler(CommandHandler("chat_id", chat_id))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register callback handlers for inline buttons
    if register_callbacks:
        print("➕ Registering callback handlers...")
        register_callbacks(app)
    else:
        print("⚠️  Callback handlers not available (optional)")

    print("🚀 Starting polling...")
    # drop_pending_updates=True helps avoid conflict errors from previous instances
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == '__main__':
    main()
