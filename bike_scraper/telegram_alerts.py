"""
Telegram Alert Service

Отправлять уведомления о выгодных велосипедах в Telegram
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass
import os

try:
    from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.error import TelegramError
except ImportError:
    # Fallback for testing without python-telegram-bot
    Bot = None
    InlineKeyboardMarkup = None
    InlineKeyboardButton = None
    TelegramError = Exception

try:
    from bike_scraper.models import SentAlert
except ImportError:
    SentAlert = None

logger = logging.getLogger(__name__)


@dataclass
class DealAlert:
    """Single deal alert"""
    listing_id: str
    bike_name: str
    asking_price: float
    market_price: float
    discount_percent: float
    profit_potential: float
    size: Optional[str]
    groupset: str
    year: Optional[int]
    confidence: float
    comparable_count: int
    listing_url: str
    deal_grade: str
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class TelegramAlertService:
    """
    Service for sending bike deal alerts to Telegram

    Conditions for sending:
    - confidence >= 85%
    - comparables >= 20
    - discount_percent >= 15%
    - profit_potential >= €500

    Rate limit: max 20 messages/hour
    Deduplication: track listing_id to avoid duplicates
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        db_session: Optional[object] = None,
        rate_limit: int = 20,  # per hour
        min_confidence: float = 85.0,
        min_comparables: int = 20,
        min_discount: float = 15.0,
        min_profit: float = 500.0,
    ):
        """Initialize Telegram Alert Service

        Args:
            bot_token: Telegram bot token (or use TELEGRAM_BOT_TOKEN env var)
            chat_id: Telegram chat ID (or use TELEGRAM_CHAT_ID env var)
            db_session: SQLAlchemy session for persistent tracking (optional)
            rate_limit: Max messages per hour
            min_confidence: Minimum confidence % for alerts
            min_comparables: Minimum comparable listings
            min_discount: Minimum discount % for alerts
            min_profit: Minimum profit EUR for alerts
        """

        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

        if not self.bot_token or not self.chat_id:
            logger.warning("⚠️  Telegram credentials not set. Alerts disabled.")
            logger.warning("   Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
            self.bot = None
        else:
            self.bot = Bot(token=self.bot_token) if Bot else None

        # Database session for persistent tracking
        self.db_session = db_session

        # Rate limiting
        self.rate_limit = rate_limit
        self.sent_messages: List[datetime] = []

        # Validation thresholds
        self.min_confidence = min_confidence
        self.min_comparables = min_comparables
        self.min_discount = min_discount
        self.min_profit = min_profit

        # Deduplication: In-memory fallback (for backward compatibility)
        self.sent_listing_ids: set = set()
        self.alert_log: List[Dict] = []

    def validate_deal(self, alert: DealAlert) -> tuple[bool, str]:
        """
        Validate if deal meets criteria for sending alert

        Returns: (is_valid, reason)
        """

        if alert.confidence < self.min_confidence:
            return False, f"Confidence {alert.confidence:.0f}% < {self.min_confidence:.0f}%"

        if alert.comparable_count < self.min_comparables:
            return False, f"Comparables {alert.comparable_count} < {self.min_comparables}"

        if alert.discount_percent < self.min_discount:
            return False, f"Discount {alert.discount_percent:.1f}% < {self.min_discount:.1f}%"

        if alert.profit_potential < self.min_profit:
            return False, f"Profit €{alert.profit_potential:.0f} < €{self.min_profit:.0f}"

        return True, "Valid"

    def is_already_sent(self, listing_id: str) -> bool:
        """Check if alert for this listing was already sent

        First checks database (persistent), then falls back to in-memory set
        """
        # Database check (persistent across restarts)
        if self.db_session and SentAlert:
            try:
                result = self.db_session.query(SentAlert).filter(
                    SentAlert.listing_id == listing_id
                ).first()
                if result:
                    return True
            except Exception as e:
                logger.warning(f"⚠️  Database check failed: {str(e)}, falling back to memory")

        # In-memory fallback
        return listing_id in self.sent_listing_ids

    def mark_as_sent(self, listing_id: str, alert: 'DealAlert', telegram_message_id: Optional[int] = None):
        """Mark listing as sent to avoid duplicates

        Saves to database (persistent) and in-memory set (fast lookup)
        """
        # Database persistence (survives restarts)
        if self.db_session and SentAlert:
            try:
                sent_alert = SentAlert(
                    listing_id=listing_id,
                    listing_url=alert.listing_url,
                    deal_grade=alert.deal_grade,
                    bike_name=alert.bike_name,
                    asking_price=alert.asking_price,
                    market_price=alert.market_price,
                    discount_percent=alert.discount_percent,
                    telegram_message_id=telegram_message_id
                )
                self.db_session.add(sent_alert)
                self.db_session.commit()
            except Exception as e:
                logger.error(f"❌ Failed to save to database: {str(e)}")
                self.db_session.rollback()

        # In-memory set (fast fallback)
        self.sent_listing_ids.add(listing_id)

    def _check_rate_limit(self) -> bool:
        """Check if rate limit allows sending message"""

        # Remove old entries (older than 1 hour)
        cutoff_time = datetime.now() - timedelta(hours=1)
        self.sent_messages = [msg_time for msg_time in self.sent_messages if msg_time > cutoff_time]

        if len(self.sent_messages) >= self.rate_limit:
            logger.warning(f"⚠️  Rate limit exceeded: {len(self.sent_messages)}/{self.rate_limit} in last hour")
            return False

        return True

    def _build_message(self, alert: DealAlert) -> str:
        """Build Telegram message text"""

        message = f"""🚨 {alert.deal_grade} DEAL FOUND

🚴 {alert.bike_name}

💰 Price: €{alert.asking_price:,.0f}
📈 Market: €{alert.market_price:,.0f}

🔥 Discount: {alert.discount_percent:.1f}%

💵 Potential Profit: €{alert.profit_potential:,.0f}

📏 Size: {alert.size or 'Unknown'}
⚙️ Groupset: {alert.groupset}
📅 Year: {alert.year or 'Unknown'}

🎯 Confidence: {alert.confidence:.0f}%
📊 Comparables: {alert.comparable_count}

🔗 {alert.listing_url}"""

        return message

    def _build_keyboard(self, alert: DealAlert):
        """Build inline keyboard with action buttons"""

        if not self.bot or not InlineKeyboardMarkup:
            return None

        keyboard = [
            [
                InlineKeyboardButton("🌐 Open Listing", url=alert.listing_url),
            ],
            [
                InlineKeyboardButton("✅ Bought", callback_data=f"bought_{alert.listing_id}"),
                InlineKeyboardButton("❌ Ignore", callback_data=f"ignore_{alert.listing_id}"),
            ],
        ]

        return InlineKeyboardMarkup(keyboard)

    async def send_deal_alert(self, alert: DealAlert) -> bool:
        """
        Send deal alert to Telegram

        Returns: True if sent successfully, False otherwise
        """

        # Check if already sent (database + memory)
        if self.is_already_sent(alert.listing_id):
            logger.info(f"⏭️  Skipping {alert.listing_id}: already sent")
            return False

        # Validate deal
        is_valid, reason = self.validate_deal(alert)
        if not is_valid:
            logger.debug(f"❌ {alert.listing_id}: {reason}")
            return False

        # Check rate limit
        if not self._check_rate_limit():
            logger.warning(f"❌ {alert.listing_id}: rate limit exceeded")
            return False

        # Send message
        if not self.bot:
            logger.warning(f"⚠️  {alert.listing_id}: bot not initialized")
            return False

        try:
            message_text = self._build_message(alert)
            keyboard = self._build_keyboard(alert)

            sent_message = await self.bot.send_message(
                chat_id=self.chat_id,
                text=message_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

            # Mark as sent with telegram message ID
            telegram_message_id = sent_message.message_id if sent_message else None
            self.mark_as_sent(alert.listing_id, alert, telegram_message_id)
            self.sent_messages.append(datetime.now())

            # Log
            self.alert_log.append({
                "timestamp": datetime.now().isoformat(),
                "listing_id": alert.listing_id,
                "deal_grade": alert.deal_grade,
                "telegram_sent": True,
                "bike_name": alert.bike_name,
                "profit_potential": alert.profit_potential,
                "telegram_message_id": telegram_message_id,
            })

            logger.info(f"✅ Sent alert for {alert.listing_id}: {alert.bike_name} ({alert.deal_grade})")
            return True

        except TelegramError as e:
            logger.error(f"❌ Failed to send alert for {alert.listing_id}: {str(e)}")
            return False

    async def send_daily_summary(self, deals: List[DealAlert]) -> bool:
        """
        Send daily summary of found deals

        Returns: True if sent successfully
        """

        if not self.bot or not deals:
            return False

        # Filter valid deals
        valid_deals = [d for d in deals if self.validate_deal(d)[0]]

        if not valid_deals:
            logger.info("No valid deals for summary")
            return False

        # Build summary
        summary = f"""📊 DAILY DEAL SUMMARY

Total deals found: {len(deals)}
Valid deals: {len(valid_deals)}

Top deals:
"""

        # Sort by profit potential and take top 5
        top_deals = sorted(valid_deals, key=lambda x: x.profit_potential, reverse=True)[:5]

        for i, deal in enumerate(top_deals, 1):
            summary += f"""
{i}. {deal.bike_name}
   💰 €{deal.asking_price:,.0f} → €{deal.market_price:,.0f}
   🔥 {deal.discount_percent:.1f}% discount
   💵 Profit: €{deal.profit_potential:,.0f}
"""

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=summary,
                parse_mode="HTML"
            )

            logger.info("✅ Sent daily summary")
            return True

        except TelegramError as e:
            logger.error(f"❌ Failed to send summary: {str(e)}")
            return False

    def get_alert_log(self) -> List[Dict]:
        """Get log of sent alerts"""
        return self.alert_log

    def get_statistics(self) -> Dict:
        """Get alert statistics"""
        return {
            "total_alerts_logged": len(self.alert_log),
            "total_sent_message_count": len(self.sent_messages),
            "unique_listings_sent": len(self.sent_listing_ids),
            "rate_limit": f"{len(self.sent_messages)}/{self.rate_limit} (last hour)",
            "avg_profit_per_alert": (
                sum(a["profit_potential"] for a in self.alert_log) / len(self.alert_log)
                if self.alert_log else 0
            ),
        }


class TelegramAlertWorker:
    """
    Background worker for processing and sending alerts

    Designed to run continuously on Railway
    """

    def __init__(self, alert_service: TelegramAlertService, check_interval: int = 60):
        """
        Initialize worker

        Args:
            alert_service: TelegramAlertService instance
            check_interval: seconds between checks for new deals
        """
        self.alert_service = alert_service
        self.check_interval = check_interval
        self.is_running = False

    async def process_alert(self, alert: DealAlert):
        """Process a single alert"""
        await self.alert_service.send_deal_alert(alert)

    async def run(self):
        """Start worker (for continuous deployment)"""
        self.is_running = True
        logger.info("🚀 TelegramAlertWorker started")

        # This would be integrated with your main scraper
        # For now, just log that it's running
        try:
            while self.is_running:
                await asyncio.sleep(self.check_interval)
                # Integration point: fetch deals from scraper
                # await self.process_deals(new_deals)
        except KeyboardInterrupt:
            logger.info("🛑 TelegramAlertWorker stopped")
            self.is_running = False

    def stop(self):
        """Stop the worker"""
        self.is_running = False


# Demo/Testing
async def demo():
    """Demo of TelegramAlertService"""

    # Create service (use mock bot for demo)
    service = TelegramAlertService(
        bot_token="DEMO_TOKEN",
        chat_id="DEMO_CHAT_ID"
    )

    # Create sample deal
    sample_deal = DealAlert(
        listing_id="1234567890",
        bike_name="Canyon Aeroad CF SLX 8 Di2 2022",
        asking_price=5500,
        market_price=8000,
        discount_percent=31.2,
        profit_potential=1750,
        size="M",
        groupset="Ultegra Di2",
        year=2022,
        confidence=96.0,
        comparable_count=35,
        listing_url="https://wallapop.com/item/1234567890",
        deal_grade="A-Tier"
    )

    # Validate
    is_valid, reason = service.validate_deal(sample_deal)
    print(f"Deal validation: {is_valid} ({reason})")

    # Build message (don't send in demo)
    message = service._build_message(sample_deal)
    print(f"\nMessage preview:\n{message}")

    # Show statistics
    print(f"\nStatistics: {service.get_statistics()}")


if __name__ == "__main__":
    # Run demo
    asyncio.run(demo())
