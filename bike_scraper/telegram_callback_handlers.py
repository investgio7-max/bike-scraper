"""
Telegram Callback Handlers

Обработчики callback кнопок для Telegram Alert System.

Кнопки:
- 🌐 Open Listing (URL button, no callback)
- ✅ Bought (callback: bought_<listing_id>)
- ❌ Ignore (callback: ignore_<listing_id>)
"""

import logging
from typing import Optional
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session

from bike_scraper.database import get_session
from bike_scraper.models import UserDealAction, SentAlert

logger = logging.getLogger(__name__)


async def handle_bought_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle ✅ Bought button click

    Records that user marked a deal as bought.
    Prevents duplicate clicks on same message.
    """
    query = update.callback_query
    await query.answer()  # Remove loading state

    try:
        # Extract listing_id from callback_data
        # Format: "bought_<listing_id>"
        callback_data = query.data
        listing_id = callback_data.split("_", 1)[1] if "_" in callback_data else None

        if not listing_id:
            await query.edit_message_text(
                text="❌ Error: Could not extract listing ID from message"
            )
            return

        # Get user info
        user_id = query.from_user.id
        message_id = query.message.message_id

        # Get database session
        db = get_session()

        try:
            # Check if action already recorded (deduplication)
            existing_action = db.query(UserDealAction).filter(
                UserDealAction.telegram_message_id == message_id,
                UserDealAction.action_type == "bought"
            ).first()

            if existing_action:
                # Duplicate click - already marked as bought
                await query.edit_message_text(
                    text="✅ Already marked as BOUGHT previously"
                )
                logger.info(f"Duplicate 'bought' click for message {message_id}")
                return

            # Record action in database
            action = UserDealAction(
                user_id=user_id,
                listing_id=listing_id,
                telegram_message_id=message_id,
                action_type="bought",
                action_timestamp=datetime.utcnow()
            )
            db.add(action)
            db.commit()

            # Update message to show action was recorded
            await query.edit_message_text(
                text=query.message.text + f"\n\n✅ **Marked as BOUGHT** by user {user_id}"
            )

            # Remove inline buttons to prevent re-clicking
            await context.bot.edit_message_reply_markup(
                chat_id=query.message.chat_id,
                message_id=message_id,
                reply_markup=None
            )

            logger.info(f"✅ Deal {listing_id} marked as BOUGHT by user {user_id}")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error in 'bought' callback: {str(e)}")
        try:
            await query.edit_message_text(
                text=f"❌ Error processing action: {str(e)}"
            )
        except:
            pass


async def handle_ignore_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle ❌ Ignore button click

    Records that user ignored this deal.
    Prevents sending notifications about same deal in future.
    Prevents duplicate clicks on same message.
    """
    query = update.callback_query
    await query.answer()  # Remove loading state

    try:
        # Extract listing_id from callback_data
        # Format: "ignore_<listing_id>"
        callback_data = query.data
        listing_id = callback_data.split("_", 1)[1] if "_" in callback_data else None

        if not listing_id:
            await query.edit_message_text(
                text="❌ Error: Could not extract listing ID from message"
            )
            return

        # Get user info
        user_id = query.from_user.id
        message_id = query.message.message_id

        # Get database session
        db = get_session()

        try:
            # Check if action already recorded (deduplication)
            existing_action = db.query(UserDealAction).filter(
                UserDealAction.telegram_message_id == message_id,
                UserDealAction.action_type == "ignored"
            ).first()

            if existing_action:
                # Duplicate click - already ignored
                await query.edit_message_text(
                    text="❌ Already marked as IGNORED previously"
                )
                logger.info(f"Duplicate 'ignore' click for message {message_id}")
                return

            # Record action in database
            action = UserDealAction(
                user_id=user_id,
                listing_id=listing_id,
                telegram_message_id=message_id,
                action_type="ignored",
                action_timestamp=datetime.utcnow()
            )
            db.add(action)
            db.commit()

            # Update message to show action was recorded
            await query.edit_message_text(
                text=query.message.text + f"\n\n❌ **Ignored** by user {user_id}"
            )

            # Remove inline buttons to prevent re-clicking
            await context.bot.edit_message_reply_markup(
                chat_id=query.message.chat_id,
                message_id=message_id,
                reply_markup=None
            )

            logger.info(f"❌ Deal {listing_id} ignored by user {user_id}")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error in 'ignore' callback: {str(e)}")
        try:
            await query.edit_message_text(
                text=f"❌ Error processing action: {str(e)}"
            )
        except:
            pass


async def handle_marked_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle custom action button click (if implemented)

    Generic handler for other potential buttons.
    """
    query = update.callback_query
    await query.answer()

    try:
        # Extract data
        callback_data = query.data
        user_id = query.from_user.id
        message_id = query.message.message_id

        logger.info(f"Custom callback '{callback_data}' from user {user_id}")
        await query.edit_message_text(
            text=query.message.text + f"\n\n✅ Action received (callback: {callback_data})"
        )

    except Exception as e:
        logger.error(f"❌ Error in custom callback: {str(e)}")


def register_callbacks(app) -> None:
    """
    Register all callback handlers in Telegram Application

    Should be called during bot initialization:
        from telegram.ext import Application, CallbackQueryHandler
        from bike_scraper.telegram_callback_handlers import register_callbacks

        app = Application.builder().token(TOKEN).build()
        register_callbacks(app)
        app.run_polling()
    """
    from telegram.ext import CallbackQueryHandler

    # Register handlers for specific callback patterns
    app.add_handler(CallbackQueryHandler(handle_bought_callback, pattern=r'^bought_'))
    app.add_handler(CallbackQueryHandler(handle_ignore_callback, pattern=r'^ignore_'))
    app.add_handler(CallbackQueryHandler(handle_marked_callback))

    logger.info("✅ Callback handlers registered:")
    logger.info("   - bought_<listing_id>")
    logger.info("   - ignore_<listing_id>")
    logger.info("   - other callbacks")
