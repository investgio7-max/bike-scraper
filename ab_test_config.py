"""
A/B TEST FRAMEWORK: Whitelist vs No Whitelist
Collect real data for 7 days to determine optimal configuration
"""

import os
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import logging

logger = logging.getLogger("ab_test")

# =====================
# A/B TEST MODES
# =====================

class ABTestMode(Enum):
    """A/B Test Configuration"""
    MODE_A = "no_whitelist"      # Current system - all models allowed
    MODE_B = "priority_whitelist"  # TOP-10 models get +10% confidence boost


# =====================
# TOP-10 WHITELIST MODELS
# =====================

TOP_10_WHITELIST = {
    'madone',           # Trek
    'aeroad',           # Canyon
    'tarmac',           # Specialized
    'addict rc',        # Scott
    'dogma',            # Pinarello
    'tcr',              # Giant
    's5',               # Cervelo
    'grail',            # Canyon
    'emonda',           # Trek
    'roadmachine',      # BMC
}


# =====================
# A/B TEST STATISTICS TRACKER
# =====================

class ABTestStats:
    """Track statistics for both modes"""

    def __init__(self, mode: ABTestMode):
        self.mode = mode
        self.start_time = datetime.now()
        self.stats = {
            "mode": mode.value,
            "start_time": self.start_time.isoformat(),
            "end_time": None,
            "duration_hours": 0,

            # Listing statistics
            "total_listings_found": 0,
            "total_listings_parsed": 0,
            "parse_success_rate": 0.0,

            # Deal statistics
            "total_deals_found": 0,
            "total_alerts_sent": 0,
            "conversion_rate": 0.0,

            # Quality metrics
            "average_confidence": 0.0,
            "average_discount": 0.0,
            "average_profit": 0.0,
            "average_market_price": 0.0,
            "average_asking_price": 0.0,

            # Accuracy metrics
            "manual_verifications": 0,
            "true_positives": 0,
            "false_positives": 0,
            "true_positive_rate": 0.0,
            "false_positive_rate": 0.0,

            # Model distribution
            "top_models": {},
            "top_brands": {},
            "whitelist_hits": 0,
            "non_whitelist_hits": 0,

            # Alerts by category
            "road_bikes": 0,
            "gravel_bikes": 0,
            "mountain_bikes": 0,

            # Price distribution
            "alerts_under_2000": 0,
            "alerts_2000_5000": 0,
            "alerts_5000_10000": 0,
            "alerts_over_10000": 0,

            # Hourly distribution
            "hourly_distribution": {},
            "daily_distribution": {},
        }
        self.all_alerts = []
        self.all_listings = []

    def add_listing(self, listing: Dict):
        """Track a found listing"""
        self.stats["total_listings_found"] += 1
        self.all_listings.append(listing)

    def add_parsed_listing(self, bike_data: Dict):
        """Track successfully parsed listing"""
        self.stats["total_listings_parsed"] += 1

    def add_alert(self, alert: Dict):
        """Track sent alert"""
        self.stats["total_alerts_sent"] += 1
        self.all_alerts.append(alert)

        # Track model
        model = alert.get('model', 'unknown').lower()
        self.stats["top_models"][model] = \
            self.stats["top_models"].get(model, 0) + 1

        # Track brand
        brand = alert.get('brand', 'unknown').lower()
        self.stats["top_brands"][brand] = \
            self.stats["top_brands"].get(brand, 0) + 1

        # Track whitelist hits
        if model in TOP_10_WHITELIST:
            self.stats["whitelist_hits"] += 1
        else:
            self.stats["non_whitelist_hits"] += 1

        # Track bike type
        bike_type = alert.get('bike_type', 'unknown').lower()
        if 'road' in bike_type or 'carretera' in bike_type:
            self.stats["road_bikes"] += 1
        elif 'gravel' in bike_type or 'grava' in bike_type:
            self.stats["gravel_bikes"] += 1
        elif 'mountain' in bike_type or 'montaña' in bike_type:
            self.stats["mountain_bikes"] += 1

        # Track price distribution
        asking_price = alert.get('asking_price', 0)
        if asking_price < 2000:
            self.stats["alerts_under_2000"] += 1
        elif asking_price < 5000:
            self.stats["alerts_2000_5000"] += 1
        elif asking_price < 10000:
            self.stats["alerts_5000_10000"] += 1
        else:
            self.stats["alerts_over_10000"] += 1

    def add_verification(self, is_correct: bool):
        """Track manual verification"""
        self.stats["manual_verifications"] += 1
        if is_correct:
            self.stats["true_positives"] += 1
        else:
            self.stats["false_positives"] += 1

    def calculate_stats(self):
        """Calculate derived statistics"""
        # Parse rate
        if self.stats["total_listings_found"] > 0:
            self.stats["parse_success_rate"] = \
                round(self.stats["total_listings_parsed"] /
                      self.stats["total_listings_found"] * 100, 1)

        # Conversion rate
        if self.stats["total_listings_parsed"] > 0:
            self.stats["conversion_rate"] = \
                round(self.stats["total_alerts_sent"] /
                      self.stats["total_listings_parsed"] * 100, 1)

        # Accuracy rates
        if self.stats["manual_verifications"] > 0:
            self.stats["true_positive_rate"] = \
                round(self.stats["true_positives"] /
                      self.stats["manual_verifications"] * 100, 1)
            self.stats["false_positive_rate"] = \
                round(self.stats["false_positives"] /
                      self.stats["manual_verifications"] * 100, 1)

        # Average metrics
        if self.all_alerts:
            confidences = [a.get('confidence', 0) for a in self.all_alerts]
            discounts = [a.get('discount', 0) for a in self.all_alerts]
            profits = [a.get('profit', 0) for a in self.all_alerts]
            market_prices = [a.get('market_price', 0) for a in self.all_alerts]
            asking_prices = [a.get('asking_price', 0) for a in self.all_alerts]

            self.stats["average_confidence"] = \
                round(sum(confidences) / len(confidences), 1)
            self.stats["average_discount"] = \
                round(sum(discounts) / len(discounts), 1)
            self.stats["average_profit"] = \
                round(sum(profits) / len(profits), 1)
            self.stats["average_market_price"] = \
                round(sum(market_prices) / len(market_prices), 1)
            self.stats["average_asking_price"] = \
                round(sum(asking_prices) / len(asking_prices), 1)

        # Duration
        duration = datetime.now() - self.start_time
        self.stats["duration_hours"] = round(duration.total_seconds() / 3600, 1)
        self.stats["end_time"] = datetime.now().isoformat()

    def get_summary(self) -> Dict:
        """Get summary statistics"""
        self.calculate_stats()
        return self.stats

    def save_to_file(self, filename: str):
        """Save statistics to JSON file"""
        self.calculate_stats()
        with open(filename, 'w') as f:
            json.dump(self.stats, f, indent=2, default=str)


# =====================
# A/B TEST CONTROLLER
# =====================

class ABTestController:
    """Control A/B test execution"""

    def __init__(self):
        self.mode = ABTestMode[os.getenv('AB_TEST_MODE', 'MODE_A')]
        self.enabled = os.getenv('AB_TEST_ENABLED', 'True') == 'True'
        self.test_duration_days = int(os.getenv('AB_TEST_DURATION_DAYS', '7'))
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(days=self.test_duration_days)
        self.stats = ABTestStats(self.mode)

        logger.info(f"🧪 A/B TEST INITIALIZED")
        logger.info(f"   Mode: {self.mode.value}")
        logger.info(f"   Duration: {self.test_duration_days} days")
        logger.info(f"   Start: {self.start_time}")
        logger.info(f"   End: {self.end_time}")

    def is_running(self) -> bool:
        """Check if test is still running"""
        if not self.enabled:
            return False
        return datetime.now() < self.end_time

    def get_time_remaining(self) -> Dict:
        """Get remaining test time"""
        remaining = self.end_time - datetime.now()
        return {
            "remaining_days": remaining.days,
            "remaining_hours": (remaining.seconds // 3600),
            "remaining_minutes": ((remaining.seconds % 3600) // 60),
        }

    def should_boost_confidence(self, model: str) -> float:
        """Determine confidence boost based on mode"""
        if not self.enabled or self.mode == ABTestMode.MODE_A:
            return 0.0  # No boost in MODE A

        # MODE B: +10% confidence boost for TOP-10 models
        if model.lower() in TOP_10_WHITELIST:
            return 10.0

        return 0.0

    def process_alert(self, alert: Dict) -> Dict:
        """Process alert with A/B test logic"""
        if not self.enabled:
            return alert

        # Apply confidence boost if needed
        boost = self.should_boost_confidence(alert.get('model', ''))
        if boost > 0:
            original_confidence = alert.get('confidence', 0)
            alert['confidence'] = min(original_confidence + boost, 100)
            alert['confidence_boost'] = boost

        return alert

    def get_current_stats(self) -> Dict:
        """Get current A/B test statistics"""
        stats = self.stats.get_summary()
        stats['test_running'] = self.is_running()
        stats['time_remaining'] = self.get_time_remaining()

        # Add mode-specific info
        if self.mode == ABTestMode.MODE_B:
            whitelist_rate = 0
            if stats['total_alerts_sent'] > 0:
                whitelist_rate = round(
                    stats['whitelist_hits'] / stats['total_alerts_sent'] * 100, 1
                )
            stats['whitelist_hit_rate'] = whitelist_rate

        return stats


# =====================
# A/B TEST REPORTER
# =====================

class ABTestReporter:
    """Generate A/B test reports"""

    @staticmethod
    def generate_daily_report(stats_a: ABTestStats, stats_b: ABTestStats) -> str:
        """Generate daily comparison report"""

        stats_a.calculate_stats()
        stats_b.calculate_stats()

        report = f"""
╔════════════════════════════════════════════════════════════════╗
║                     A/B TEST DAILY REPORT                     ║
║                  {datetime.now().strftime('%Y-%m-%d %H:%M')}                          ║
╚════════════════════════════════════════════════════════════════╝

MODE A (No Whitelist) vs MODE B (Priority Whitelist)

LISTINGS & DEALS:
  Metric                  MODE A          MODE B        Difference
  ────────────────────────────────────────────────────────
  Listings Found          {stats_a.stats['total_listings_found']:>6}           {stats_b.stats['total_listings_found']:>6}         {stats_b.stats['total_listings_found'] - stats_a.stats['total_listings_found']:>+6}
  Parse Success Rate      {stats_a.stats['parse_success_rate']:>6.1f}%         {stats_b.stats['parse_success_rate']:>6.1f}%       {stats_b.stats['parse_success_rate'] - stats_a.stats['parse_success_rate']:>+6.1f}%
  Alerts Sent             {stats_a.stats['total_alerts_sent']:>6}           {stats_b.stats['total_alerts_sent']:>6}         {stats_b.stats['total_alerts_sent'] - stats_a.stats['total_alerts_sent']:>+6}
  Conversion Rate         {stats_a.stats['conversion_rate']:>6.1f}%         {stats_b.stats['conversion_rate']:>6.1f}%       {stats_b.stats['conversion_rate'] - stats_a.stats['conversion_rate']:>+6.1f}%

QUALITY METRICS:
  Average Confidence      {stats_a.stats['average_confidence']:>6.1f}%        {stats_b.stats['average_confidence']:>6.1f}%       {stats_b.stats['average_confidence'] - stats_a.stats['average_confidence']:>+6.1f}%
  Average Discount        {stats_a.stats['average_discount']:>6.1f}%        {stats_b.stats['average_discount']:>6.1f}%       {stats_b.stats['average_discount'] - stats_a.stats['average_discount']:>+6.1f}%
  Average Profit          {stats_a.stats['average_profit']:>6.1f}%        {stats_b.stats['average_profit']:>6.1f}%       {stats_b.stats['average_profit'] - stats_a.stats['average_profit']:>+6.1f}%

PRICES:
  Avg Market Price        €{stats_a.stats['average_market_price']:>7,.0f}        €{stats_b.stats['average_market_price']:>7,.0f}       €{stats_b.stats['average_market_price'] - stats_a.stats['average_market_price']:>+7,.0f}
  Avg Asking Price        €{stats_a.stats['average_asking_price']:>7,.0f}        €{stats_b.stats['average_asking_price']:>7,.0f}       €{stats_b.stats['average_asking_price'] - stats_a.stats['average_asking_price']:>+7,.0f}

ACCURACY:
  Verifications           {stats_a.stats['manual_verifications']:>6}           {stats_b.stats['manual_verifications']:>6}         {stats_b.stats['manual_verifications'] - stats_a.stats['manual_verifications']:>+6}
  True Positives          {stats_a.stats['true_positives']:>6}           {stats_b.stats['true_positives']:>6}         {stats_b.stats['true_positives'] - stats_a.stats['true_positives']:>+6}
  False Positives         {stats_a.stats['false_positives']:>6}           {stats_b.stats['false_positives']:>6}         {stats_b.stats['false_positives'] - stats_a.stats['false_positives']:>+6}
  TP Rate                 {stats_a.stats['true_positive_rate']:>6.1f}%        {stats_b.stats['true_positive_rate']:>6.1f}%       {stats_b.stats['true_positive_rate'] - stats_a.stats['true_positive_rate']:>+6.1f}%
  FP Rate                 {stats_a.stats['false_positive_rate']:>6.1f}%        {stats_b.stats['false_positive_rate']:>6.1f}%       {stats_b.stats['false_positive_rate'] - stats_a.stats['false_positive_rate']:>+6.1f}%

BIKE TYPES:
  Road Bikes              {stats_a.stats['road_bikes']:>6}           {stats_b.stats['road_bikes']:>6}         {stats_b.stats['road_bikes'] - stats_a.stats['road_bikes']:>+6}
  Gravel Bikes            {stats_a.stats['gravel_bikes']:>6}           {stats_b.stats['gravel_bikes']:>6}         {stats_b.stats['gravel_bikes'] - stats_a.stats['gravel_bikes']:>+6}
  Mountain Bikes          {stats_a.stats['mountain_bikes']:>6}           {stats_b.stats['mountain_bikes']:>6}         {stats_b.stats['mountain_bikes'] - stats_a.stats['mountain_bikes']:>+6}

PRICE SEGMENTS:
  Under €2,000            {stats_a.stats['alerts_under_2000']:>6}           {stats_b.stats['alerts_under_2000']:>6}         {stats_b.stats['alerts_under_2000'] - stats_a.stats['alerts_under_2000']:>+6}
  €2,000-€5,000           {stats_a.stats['alerts_2000_5000']:>6}           {stats_b.stats['alerts_2000_5000']:>6}         {stats_b.stats['alerts_2000_5000'] - stats_a.stats['alerts_2000_5000']:>+6}
  €5,000-€10,000          {stats_a.stats['alerts_5000_10000']:>6}           {stats_b.stats['alerts_5000_10000']:>6}         {stats_b.stats['alerts_5000_10000'] - stats_a.stats['alerts_5000_10000']:>+6}
  Over €10,000            {stats_a.stats['alerts_over_10000']:>6}           {stats_b.stats['alerts_over_10000']:>6}         {stats_b.stats['alerts_over_10000'] - stats_a.stats['alerts_over_10000']:>+6}

════════════════════════════════════════════════════════════════
"""
        return report


# =====================
# ENVIRONMENT VARIABLES
# =====================

"""
Set these environment variables to control A/B test:

AB_TEST_ENABLED=True          # Enable/disable A/B test
AB_TEST_MODE=MODE_A           # MODE_A (no whitelist) or MODE_B (priority)
AB_TEST_DURATION_DAYS=7       # How many days to run test

Example:
  export AB_TEST_ENABLED=True
  export AB_TEST_MODE=MODE_A
  export AB_TEST_DURATION_DAYS=7
"""


# =====================
# USAGE EXAMPLE
# =====================

if __name__ == "__main__":
    # Initialize controller
    controller = ABTestController()

    # Simulate some data
    controller.stats.add_listing({"id": 1, "title": "Test Bike"})
    controller.stats.add_parsed_listing({"model": "aeroad"})

    # Create test alert
    alert = {
        "model": "aeroad",
        "brand": "canyon",
        "confidence": 92,
        "discount": 30,
        "profit": 28,
        "asking_price": 3100,
        "market_price": 4700,
        "bike_type": "road"
    }

    # Process with A/B test logic
    alert = controller.process_alert(alert)
    controller.stats.add_alert(alert)

    # Get current stats
    stats = controller.get_current_stats()
    print(f"Test running: {stats['test_running']}")
    print(f"Mode: {stats['mode']}")
    print(f"Alerts sent: {stats['total_alerts_sent']}")
