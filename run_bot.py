#!/usr/bin/env python3
"""Run Telegram bot"""
import asyncio
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from bike_scraper.telegram_bot import create_telegram_bot

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set!")
        sys.exit(1)

    logger.info(f"✅ Bot token found: {token[:20]}...")
    bot = create_telegram_bot(token)
    asyncio.run(bot.run())
except Exception as e:
    logger.error(f"❌ Bot error: {e}", exc_info=True)
    sys.exit(1)
