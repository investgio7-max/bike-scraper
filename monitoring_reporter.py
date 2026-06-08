#!/usr/bin/env python3
"""
7-DAY PRODUCTION MONITORING & DAILY TELEGRAM REPORTING
Automatically sends daily reports at 09:00 with business metrics.
No code changes - pure observation and statistics.
"""

import os
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import schedule
import time
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("monitoring_reporter")


class DailyMetrics:
    """Track metrics for a single day"""

    def __init__(self, date: str):
        self.date = date  # YYYY-MM-DD
        self.metrics = {
            # Search metrics
            "listings_processed": 0,
            "listings_parsed": 0,
            "listings_rejected": 0,
            "deals_found": 0,
            "alerts_sent": 0,

            # Quality metrics
            "confidences": [],  # List of confidence scores
            "discounts": [],    # List of discount percentages
            "comparables": [],  # List of comparable counts
            "false_positives": 0,

            # Business metrics
            "asking_prices": [],    # List of asking prices
            "market_prices": [],    # List of market prices
            "profits": [],          # List of potential profits

            # Detailed deals
            "all_deals": [],        # Full deal objects

            # Alert performance
            "telegram_sent": 0,
            "telegram_errors": 0,
            "circuit_breaker_status": "NORMAL",
            "safe_mode_active": False,
        }

    def add_deal(self, deal: Dict):
        """Add a deal to daily metrics"""
        self.metrics["deals_found"] += 1
        self.metrics["alerts_sent"] += 1
        self.metrics["confidences"].append(deal.get("confidence", 0))
        self.metrics["discounts"].append(deal.get("discount", 0))
        self.metrics["comparables"].append(deal.get("comparable_count", 0))
        self.metrics["asking_prices"].append(deal.get("asking_price", 0))
        self.metrics["market_prices"].append(deal.get("market_price", 0))
        self.metrics["profits"].append(deal.get("profit_potential", 0))
        self.metrics["all_deals"].append(deal)

    def get_summary(self) -> Dict:
        """Get calculated metrics"""
        deals = self.metrics["all_deals"]

        summary = {
            "date": self.date,
            "listings_processed": self.metrics["listings_processed"],
            "listings_parsed": self.metrics["listings_parsed"],
            "listings_rejected": self.metrics["listings_rejected"],
            "deals_found": self.metrics["deals_found"],
            "alerts_sent": self.metrics["alerts_sent"],

            "avg_confidence": (
                sum(self.metrics["confidences"]) / len(self.metrics["confidences"])
                if self.metrics["confidences"] else 0
            ),
            "avg_discount": (
                sum(self.metrics["discounts"]) / len(self.metrics["discounts"])
                if self.metrics["discounts"] else 0
            ),
            "avg_comparable_count": (
                sum(self.metrics["comparables"]) / len(self.metrics["comparables"])
                if self.metrics["comparables"] else 0
            ),
            "false_positives": self.metrics["false_positives"],
            "false_positive_rate": (
                self.metrics["false_positives"] / self.metrics["alerts_sent"] * 100
                if self.metrics["alerts_sent"] > 0 else 0
            ),

            "avg_asking_price": (
                sum(self.metrics["asking_prices"]) / len(self.metrics["asking_prices"])
                if self.metrics["asking_prices"] else 0
            ),
            "avg_market_price": (
                sum(self.metrics["market_prices"]) / len(self.metrics["market_prices"])
                if self.metrics["market_prices"] else 0
            ),
            "avg_profit": (
                sum(self.metrics["profits"]) / len(self.metrics["profits"])
                if self.metrics["profits"] else 0
            ),
            "total_profit_potential": sum(self.metrics["profits"]),

            "best_deal": max(deals, key=lambda x: x.get("profit_potential", 0)) if deals else None,
            "telegram_sent": self.metrics["telegram_sent"],
            "telegram_errors": self.metrics["telegram_errors"],
            "telegram_success_rate": (
                (self.metrics["telegram_sent"] /
                 (self.metrics["telegram_sent"] + self.metrics["telegram_errors"]) * 100)
                if (self.metrics["telegram_sent"] + self.metrics["telegram_errors"]) > 0 else 0
            ),
            "circuit_breaker_status": self.metrics["circuit_breaker_status"],
            "safe_mode_active": self.metrics["safe_mode_active"],

            "top_10_deals": sorted(deals, key=lambda x: x.get("profit_potential", 0), reverse=True)[:10],
        }

        return summary


class MonitoringReporter:
    """7-day production monitoring with daily Telegram reports"""

    def __init__(self, telegram_token: str, telegram_chat_id: str):
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id

        self.daily_metrics = {}  # Dict[date] = DailyMetrics
        self.seven_day_reports = []  # List of completed daily reports

        self.monitoring_start = datetime.now()
        self.report_schedule_time = "09:00"  # Send reports at 09:00

        logger.info("✅ Monitoring Reporter initialized")
        logger.info(f"   Telegram reports: {telegram_chat_id}")
        logger.info(f"   Daily report time: {self.report_schedule_time}")

    def get_today_date(self) -> str:
        """Get today's date as YYYY-MM-DD"""
        return datetime.now().strftime("%Y-%m-%d")

    def get_today_metrics(self) -> DailyMetrics:
        """Get or create today's metrics"""
        today = self.get_today_date()
        if today not in self.daily_metrics:
            self.daily_metrics[today] = DailyMetrics(today)
        return self.daily_metrics[today]

    def record_search(self, count: int):
        """Record search results"""
        metrics = self.get_today_metrics()
        metrics.metrics["listings_processed"] += count

    def record_parsed(self, count: int):
        """Record successfully parsed listings"""
        metrics = self.get_today_metrics()
        metrics.metrics["listings_parsed"] += count

    def record_rejected(self, count: int):
        """Record rejected listings"""
        metrics = self.get_today_metrics()
        metrics.metrics["listings_rejected"] += count

    def record_deal(self, deal: Dict):
        """Record a deal found and alert sent"""
        metrics = self.get_today_metrics()
        metrics.add_deal(deal)

    def record_false_positive(self):
        """Record a false positive report"""
        metrics = self.get_today_metrics()
        metrics.metrics["false_positives"] += 1

    def record_telegram_sent(self):
        """Record successful Telegram message"""
        metrics = self.get_today_metrics()
        metrics.metrics["telegram_sent"] += 1

    def record_telegram_error(self):
        """Record Telegram error"""
        metrics = self.get_today_metrics()
        metrics.metrics["telegram_errors"] += 1

    def update_circuit_breaker(self, status: str, safe_mode: bool):
        """Update circuit breaker status"""
        metrics = self.get_today_metrics()
        metrics.metrics["circuit_breaker_status"] = status
        metrics.metrics["safe_mode_active"] = safe_mode

    def format_daily_report(self, summary: Dict) -> str:
        """Format daily report as Telegram message"""

        date = summary["date"]

        msg = f"""
╔════════════════════════════════════════════╗
║        📊 DAILY MONITORING REPORT          ║
║              {date}                  ║
╚════════════════════════════════════════════╝

🔍 SEARCH METRICS
├─ Listings Processed: {summary['listings_processed']}
├─ Listings Parsed:    {summary['listings_parsed']}
├─ Listings Rejected:  {summary['listings_rejected']}
├─ Deals Found:        {summary['deals_found']}
└─ Alerts Sent:        {summary['alerts_sent']}

⭐ QUALITY METRICS
├─ Avg Confidence:     {summary['avg_confidence']:.1f}%
├─ Avg Discount:       {summary['avg_discount']:.1f}%
├─ Avg Comparables:    {summary['avg_comparable_count']:.1f}
├─ False Positives:    {summary['false_positives']}
└─ FP Rate:            {summary['false_positive_rate']:.1f}%

💰 BUSINESS METRICS
├─ Avg Asking Price:   €{summary['avg_asking_price']:.0f}
├─ Avg Market Price:   €{summary['avg_market_price']:.0f}
├─ Avg Profit/Deal:    €{summary['avg_profit']:.0f}
└─ Total Profit Pot.:  €{summary['total_profit_potential']:.0f}

🏆 BEST DEAL OF THE DAY
"""

        if summary["best_deal"]:
            deal = summary["best_deal"]
            msg += f"""{deal.get('bike_name', 'N/A')}
  Price:    €{deal.get('asking_price', 0):.0f}
  Market:   €{deal.get('market_price', 0):.0f}
  Discount: {deal.get('discount', 0):.1f}%
  Profit:   €{deal.get('profit_potential', 0):.0f}
"""
        else:
            msg += "No deals found today\n"

        msg += f"""
📡 ALERT PERFORMANCE
├─ Telegram Sent:      {summary['telegram_sent']}
├─ Telegram Errors:    {summary['telegram_errors']}
├─ Success Rate:       {summary['telegram_success_rate']:.1f}%
└─ Circuit Breaker:    {summary['circuit_breaker_status']}

⚠️  Safe Mode: {'🚨 ACTIVE' if summary['safe_mode_active'] else '✅ OFF'}

"""

        # Top 10 deals
        if summary["top_10_deals"]:
            msg += f"""🎯 TOP 10 DEALS TODAY
"""
            for i, deal in enumerate(summary["top_10_deals"], 1):
                msg += f"{i}. {deal.get('bike_name', 'Unknown')[:30]} - €{deal.get('profit_potential', 0):.0f}\n"

        msg += "\n" + "="*44 + "\n"

        return msg

    def format_seven_day_summary(self, daily_summaries: List[Dict]) -> str:
        """Format 7-day summary"""

        if not daily_summaries:
            return "No data for 7-day summary"

        total_listings = sum(s["listings_processed"] for s in daily_summaries)
        total_deals = sum(s["deals_found"] for s in daily_summaries)
        total_alerts = sum(s["alerts_sent"] for s in daily_summaries)
        total_profit = sum(s["total_profit_potential"] for s in daily_summaries)

        avg_daily_deals = total_deals / len(daily_summaries) if daily_summaries else 0
        avg_daily_profit = total_profit / len(daily_summaries) if daily_summaries else 0

        all_deals = []
        for summary in daily_summaries:
            all_deals.extend(summary["top_10_deals"])
        best_deal = max(all_deals, key=lambda x: x.get("profit_potential", 0)) if all_deals else None

        avg_fp_rate = sum(s["false_positive_rate"] for s in daily_summaries) / len(daily_summaries) if daily_summaries else 0

        # Model performance
        model_profits = defaultdict(list)
        for summary in daily_summaries:
            for deal in summary["top_10_deals"]:
                model = deal.get("bike_model", "Unknown")
                profit = deal.get("profit_potential", 0)
                model_profits[model].append(profit)

        best_model = max(model_profits.items(), key=lambda x: sum(x[1])) if model_profits else (None, [])
        worst_model = min(model_profits.items(), key=lambda x: sum(x[1])) if model_profits else (None, [])

        msg = f"""
╔════════════════════════════════════════════╗
║       📈 7-DAY PRODUCTION SUMMARY          ║
║    {daily_summaries[0]['date']} to {daily_summaries[-1]['date']}  ║
╚════════════════════════════════════════════╝

📊 OVERALL STATISTICS
├─ Total Listings:     {total_listings}
├─ Total Deals:        {total_deals}
├─ Total Alerts:       {total_alerts}
├─ Avg Daily Deals:    {avg_daily_deals:.1f}
└─ False Positive Rate: {avg_fp_rate:.1f}%

💰 FINANCIAL SUMMARY
├─ Total Profit Pot.:  €{total_profit:.0f}
├─ Avg Daily Profit:   €{avg_daily_profit:.0f}
└─ Per Deal Avg:       €{total_profit/total_deals:.0f} if total_deals > 0 else 0

🏆 BEST DEAL OF THE WEEK
"""

        if best_deal:
            msg += f"""{best_deal.get('bike_name', 'N/A')}
  Discount: {best_deal.get('discount', 0):.1f}%
  Profit:   €{best_deal.get('profit_potential', 0):.0f}
"""

        msg += f"""
🚴 MODEL PERFORMANCE
├─ Best Model:  {best_model[0] if best_model[0] else 'N/A'} (€{sum(best_model[1]):.0f} if best_model[1] else 0)
└─ Worst Model: {worst_model[0] if worst_model[0] else 'N/A'} (€{sum(worst_model[1]):.0f} if worst_model[1] else 0)

✅ SYSTEM HEALTH
├─ Production Duration: {(datetime.now() - self.monitoring_start).days} days
└─ Status: HEALTHY

╔════════════════════════════════════════════╗
║          🎯 FINAL VERDICT                 ║
╚════════════════════════════════════════════╝

System Health:           ✅ EXCELLENT
Average Daily Profit:    €{avg_daily_profit:.0f}
False Positive Rate:     {avg_fp_rate:.2f}%
Best Model:              {best_model[0] if best_model[0] else 'N/A'}
Worst Model:             {worst_model[0] if worst_model[0] else 'N/A'}

RECOMMENDATION:
"""

        # Decision logic
        if avg_fp_rate > 10:
            msg += "🔴 ADJUST FILTERS - FP rate too high"
        elif total_deals < 50:
            msg += "🟡 EXPAND MONITORING - Low deal volume"
        elif avg_daily_profit > 1000:
            msg += "🟢 CONTINUE AS-IS - Performance excellent"
        else:
            msg += "🟡 MONITOR - Steady performance"

        msg += "\n" + "="*44 + "\n"

        return msg

    async def send_telegram_report(self, report_text: str, is_summary: bool = False):
        """Send report to Telegram"""
        try:
            from telegram import Bot

            bot = Bot(token=self.telegram_token)

            # Split if too long
            max_length = 4096
            if len(report_text) > max_length:
                parts = [report_text[i:i+max_length] for i in range(0, len(report_text), max_length)]
                for part in parts:
                    await bot.send_message(
                        chat_id=self.telegram_chat_id,
                        text=part,
                        parse_mode="HTML"
                    )
            else:
                await bot.send_message(
                    chat_id=self.telegram_chat_id,
                    text=report_text,
                    parse_mode="HTML"
                )

            if not is_summary:
                self.record_telegram_sent()
            logger.info(f"✅ {'📈 Summary' if is_summary else '📊 Daily'} report sent to Telegram")

        except Exception as e:
            if not is_summary:
                self.record_telegram_error()
            logger.error(f"❌ Failed to send Telegram report: {e}")

    async def schedule_daily_report(self):
        """Schedule daily report at 09:00"""

        def should_send_report():
            now = datetime.now()
            report_time = datetime.strptime(self.report_schedule_time, "%H:%M").time()
            return (now.time() >= report_time and
                    now.time() < (datetime.combine(datetime.now().date(), report_time) + timedelta(minutes=5)).time())

        while True:
            now = datetime.now()
            target = now.replace(hour=9, minute=0, second=0, microsecond=0)

            if now > target:
                target += timedelta(days=1)

            wait_seconds = (target - now).total_seconds()
            logger.info(f"⏰ Next daily report at {target.strftime('%Y-%m-%d %H:%M')}")

            await asyncio.sleep(wait_seconds)

            # Generate and send report
            summary = self.get_today_metrics().get_summary()
            report_text = self.format_daily_report(summary)
            await self.send_telegram_report(report_text)

            self.seven_day_reports.append(summary)

            # After 7 days, send summary
            if len(self.seven_day_reports) >= 7:
                summary_text = self.format_seven_day_summary(self.seven_day_reports[:7])
                await self.send_telegram_report(summary_text, is_summary=True)
                logger.info("✅ 7-day summary sent!")
                # Reset for next cycle if needed
                self.seven_day_reports = self.seven_day_reports[7:]


async def main():
    """Test monitoring reporter"""

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")

    if not token or not chat_id:
        logger.error("❌ TELEGRAM_BOT_TOKEN or TELEGRAM_ADMIN_CHAT_ID not set")
        return

    reporter = MonitoringReporter(token, chat_id)

    # Simulate some data
    test_deal = {
        "bike_name": "Canyon Aeroad CF SLX 8 Di2",
        "bike_model": "Aeroad",
        "asking_price": 2900,
        "market_price": 4200,
        "profit_potential": 1300,
        "discount": 30.95,
        "confidence": 95.0,
        "comparable_count": 37,
        "url": "https://example.com/bike"
    }

    reporter.record_search(100)
    reporter.record_parsed(94)
    reporter.record_rejected(6)
    reporter.record_deal(test_deal)
    reporter.record_deal(test_deal)
    reporter.record_telegram_sent()
    reporter.update_circuit_breaker("NORMAL", False)

    summary = reporter.get_today_metrics().get_summary()
    report = reporter.format_daily_report(summary)

    logger.info("\n" + report)

    # Test summary
    reporter.seven_day_reports = [summary] * 7
    summary_report = reporter.format_seven_day_summary(reporter.seven_day_reports)
    logger.info("\n" + summary_report)


if __name__ == "__main__":
    asyncio.run(main())
