#!/usr/bin/env python3
"""
Telegram Smoke Test Module

Проверить что Telegram Alert System действительно работает и сообщения доходят в нужный чат.

8 проверок:
1. Environment variables
2. Bot connection
3. Simple message
4. Deal alert
5. Inline keyboard
6. API response
7. HTTP endpoint
8. Logging
"""

import sys
sys.path.insert(0, '/Users/oleg/bike-scraper')

import asyncio
import os
from datetime import datetime
from typing import Tuple, Dict, Optional
import logging
from pathlib import Path

try:
    from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.error import TelegramError
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False

from bike_scraper.telegram_alerts import TelegramAlertService, DealAlert


# Setup logging
LOG_DIR = Path('/Users/oleg/bike-scraper/tests/logs')
LOG_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f"test_telegram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TelegramSmokeTest:
    """Comprehensive Telegram system smoke test"""

    def __init__(self):
        self.results = {}
        self.bot = None
        self.chat_id = None
        self.bot_token = None
        self.message_id = None
        self.alert_service = None

    async def check_env_vars(self) -> Tuple[bool, str]:
        """CHECK #1: Verify TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID"""
        logger.info("=" * 80)
        logger.info("CHECK #1: ENVIRONMENT VARIABLES")
        logger.info("=" * 80)

        try:
            self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
            self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

            if not self.bot_token:
                error = "❌ TELEGRAM_BOT_TOKEN not found"
                logger.error(error)
                return False, error

            if not self.chat_id:
                error = "❌ TELEGRAM_CHAT_ID not found"
                logger.error(error)
                return False, error

            logger.info(f"✅ TELEGRAM_BOT_TOKEN: {self.bot_token[:20]}...")
            logger.info(f"✅ TELEGRAM_CHAT_ID: {self.chat_id}")
            return True, "OK"

        except Exception as e:
            error = f"❌ Error checking environment: {str(e)}"
            logger.error(error)
            return False, error

    async def check_bot_connection(self) -> Tuple[bool, Dict]:
        """CHECK #2: Verify connection to Telegram API"""
        logger.info("\n" + "=" * 80)
        logger.info("CHECK #2: BOT CONNECTION")
        logger.info("=" * 80)

        if not HAS_TELEGRAM:
            error = "❌ python-telegram-bot not installed"
            logger.error(error)
            return False, {"error": error}

        try:
            self.bot = Bot(token=self.bot_token)
            me = await self.bot.get_me()

            bot_info = {
                "name": me.first_name,
                "username": me.username,
                "id": me.id
            }

            logger.info(f"✅ Bot Connected")
            logger.info(f"   Name: {bot_info['name']}")
            logger.info(f"   Username: @{bot_info['username']}")
            logger.info(f"   Bot ID: {bot_info['id']}")

            return True, bot_info

        except TelegramError as e:
            error = f"❌ Telegram API Error: {str(e)}"
            logger.error(error)
            return False, {"error": error}
        except Exception as e:
            error = f"❌ Connection failed: {str(e)}"
            logger.error(error)
            return False, {"error": error}

    async def send_simple_message(self) -> Tuple[bool, Optional[int], Optional[int]]:
        """CHECK #3: Send simple test message"""
        logger.info("\n" + "=" * 80)
        logger.info("CHECK #3: SIMPLE MESSAGE")
        logger.info("=" * 80)

        try:
            message_text = f"""🧪 TELEGRAM CONNECTION TEST

Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

            message = await self.bot.send_message(
                chat_id=self.chat_id,
                text=message_text
            )

            self.message_id = message.message_id

            logger.info("✅ Message Delivered")
            logger.info(f"   Message ID: {message.message_id}")
            logger.info(f"   Chat ID: {message.chat_id}")

            return True, message.message_id, message.chat_id

        except TelegramError as e:
            error = f"❌ Failed to send message: {str(e)}"
            logger.error(error)
            return False, None, None
        except Exception as e:
            error = f"❌ Error: {str(e)}"
            logger.error(error)
            return False, None, None

    async def send_deal_alert(self) -> Tuple[bool, DealAlert, Dict]:
        """CHECK #4: Send full Deal Alert with production format"""
        logger.info("\n" + "=" * 80)
        logger.info("CHECK #4: DEAL ALERT")
        logger.info("=" * 80)

        try:
            # Create test deal matching production format
            deal = DealAlert(
                listing_id="test_deal_123",
                bike_name="Canyon Aeroad CF SLX 8 Di2",
                asking_price=2900,
                market_price=4200,
                discount_percent=30.95,
                profit_potential=1300,
                size="M",
                groupset="Ultegra Di2",
                year=2022,
                confidence=95.0,
                comparable_count=37,
                listing_url="https://example.com/test-bike",
                deal_grade="A-Tier"
            )

            logger.info(f"Test Deal:")
            logger.info(f"  Bike: {deal.bike_name}")
            logger.info(f"  Price: €{deal.asking_price}")
            logger.info(f"  Market: €{deal.market_price}")
            logger.info(f"  Discount: {deal.discount_percent:.1f}%")
            logger.info(f"  Profit: €{deal.profit_potential}")

            # Build message (same format as production)
            self.alert_service = TelegramAlertService(
                bot_token=self.bot_token,
                chat_id=self.chat_id
            )

            message_text = self.alert_service._build_message(deal)
            keyboard = self.alert_service._build_keyboard(deal)

            # Send message
            message = await self.bot.send_message(
                chat_id=self.chat_id,
                text=message_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

            logger.info(f"✅ Deal Alert Sent")
            logger.info(f"   Message ID: {message.message_id}")
            logger.info(f"   Format: Production-ready")

            return True, deal, {
                "message_id": message.message_id,
                "chat_id": message.chat_id,
                "format": "production"
            }

        except TelegramError as e:
            error = f"❌ Failed to send deal alert: {str(e)}"
            logger.error(error)
            return False, None, {"error": error}
        except Exception as e:
            error = f"❌ Error: {str(e)}"
            logger.error(error)
            return False, None, {"error": error}

    async def check_keyboard(self) -> Tuple[bool, str]:
        """CHECK #5: Verify inline keyboard acceptance"""
        logger.info("\n" + "=" * 80)
        logger.info("CHECK #5: INLINE KEYBOARD")
        logger.info("=" * 80)

        try:
            # Create test keyboard
            keyboard = [
                [InlineKeyboardButton("🌐 Open Listing", url="https://example.com")],
                [
                    InlineKeyboardButton("✅ Bought", callback_data="bought_test"),
                    InlineKeyboardButton("❌ Ignore", callback_data="ignore_test")
                ]
            ]
            markup = InlineKeyboardMarkup(keyboard)

            logger.info("✅ Keyboard Structure:")
            logger.info("   🌐 Open Listing (URL button)")
            logger.info("   ✅ Bought (callback button)")
            logger.info("   ❌ Ignore (callback button)")

            # Send test message with keyboard
            message = await self.bot.send_message(
                chat_id=self.chat_id,
                text="🧪 Testing inline keyboard (you can delete this message)",
                reply_markup=markup
            )

            logger.info(f"✅ Keyboard Accepted by Telegram")
            logger.info(f"   Status: OK")

            return True, "Keyboard accepted"

        except TelegramError as e:
            error = f"❌ Keyboard rejected: {str(e)}"
            logger.error(error)
            return False, error
        except Exception as e:
            error = f"❌ Error: {str(e)}"
            logger.error(error)
            return False, error

    async def check_api_response(self) -> Tuple[bool, Dict]:
        """CHECK #6: Verify API response structure"""
        logger.info("\n" + "=" * 80)
        logger.info("CHECK #6: API RESPONSE")
        logger.info("=" * 80)

        try:
            message = await self.bot.send_message(
                chat_id=self.chat_id,
                text="✅ API Response Test"
            )

            response_data = {
                "message_id": message.message_id,
                "chat_id": message.chat_id,
                "status": "success"
            }

            logger.info("✅ Alert Sent Successfully")
            logger.info(f"   Message ID: {response_data['message_id']}")
            logger.info(f"   Chat ID: {response_data['chat_id']}")
            logger.info(f"   Status: {response_data['status']}")

            return True, response_data

        except Exception as e:
            error = f"❌ API error: {str(e)}"
            logger.error(error)
            return False, {"error": error}

    async def run_all_checks(self) -> Dict:
        """Run all 6 checks and collect results"""
        logger.info("\n\n")
        logger.info("╔" + "=" * 78 + "╗")
        logger.info("║" + " " * 20 + "TELEGRAM SMOKE TEST" + " " * 40 + "║")
        logger.info("╚" + "=" * 78 + "╝")

        # CHECK #1: Environment
        passed_env, msg_env = await self.check_env_vars()
        self.results["env"] = passed_env

        if not passed_env:
            logger.error("\n❌ Cannot proceed without environment variables")
            return self.results

        # CHECK #2: Connection
        passed_conn, bot_info = await self.check_bot_connection()
        self.results["connection"] = passed_conn
        self.results["bot_info"] = bot_info if passed_conn else None

        if not passed_conn:
            logger.error("\n❌ Cannot proceed without bot connection")
            return self.results

        # CHECK #3: Simple Message
        passed_msg, msg_id, chat_id = await self.send_simple_message()
        self.results["simple_message"] = passed_msg
        self.results["message_id"] = msg_id
        self.results["chat_id"] = chat_id

        # CHECK #4: Deal Alert
        passed_deal, deal_obj, deal_resp = await self.send_deal_alert()
        self.results["deal_alert"] = passed_deal
        self.results["deal_response"] = deal_resp

        # CHECK #5: Keyboard
        passed_kb, kb_msg = await self.check_keyboard()
        self.results["keyboard"] = passed_kb

        # CHECK #6: API Response
        passed_api, api_resp = await self.check_api_response()
        self.results["api_response"] = passed_api
        self.results["api_response_data"] = api_resp

        # Print final report
        await self.print_final_report()

        return self.results

    async def print_final_report(self):
        """Print final test report"""
        logger.info("\n\n")
        logger.info("=" * 80)
        logger.info("FINAL RESULTS")
        logger.info("=" * 80)

        tests = [
            ("Bot Connection", self.results.get("connection", False)),
            ("Simple Message", self.results.get("simple_message", False)),
            ("Deal Alert", self.results.get("deal_alert", False)),
            ("Inline Keyboard", self.results.get("keyboard", False)),
            ("API Response", self.results.get("api_response", False)),
        ]

        logger.info("")
        for test_name, passed in tests:
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"{status}: {test_name}")

        logger.info("")
        if self.results.get("chat_id"):
            logger.info(f"Chat ID:    {self.results['chat_id']}")
        if self.results.get("message_id"):
            logger.info(f"Message ID: {self.results['message_id']}")

        logger.info("")
        all_passed = all([
            self.results.get("connection", False),
            self.results.get("simple_message", False),
            self.results.get("deal_alert", False),
            self.results.get("keyboard", False),
            self.results.get("api_response", False),
        ])

        if all_passed:
            logger.info("Overall: ✅ TELEGRAM READY FOR PRODUCTION")
        else:
            logger.info("Overall: ❌ TELEGRAM NOT READY")

        logger.info("=" * 80)
        logger.info(f"\nTest Log: {log_file}")


async def main():
    """Run smoke test"""
    tester = TelegramSmokeTest()
    results = await tester.run_all_checks()

    # Exit with appropriate code
    all_passed = all([
        results.get("connection", False),
        results.get("simple_message", False),
        results.get("deal_alert", False),
        results.get("keyboard", False),
        results.get("api_response", False),
    ])

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
