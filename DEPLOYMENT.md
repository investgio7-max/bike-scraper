# Telegram Alert Module - Railway Deployment Guide

## Overview

The Telegram Alert Module sends real-time notifications about profitable bike listings to your Telegram account.

## Features

✅ **Automatic Deal Detection**
- Monitors listings 24/7
- Filters by confidence, comparables, discount, and profit potential

✅ **Smart Alerting**
- Rate-limited (max 20 messages/hour)
- Deduplication (no duplicate alerts)
- Inline buttons for quick actions (Buy/Ignore)

✅ **Daily Summaries**
- Top deals of the day
- Profit statistics

## Setup

### 1. Create Telegram Bot

```bash
# In Telegram:
1. Open BotFather chat: @BotFather
2. Send: /newbot
3. Name: "Bike Scraper Alerts" (or any name)
4. Username: "bike_scraper_alerts_bot" (must be unique)
5. Copy the token (starts with numbers:letters)
6. Send: /setcommands
7. Select bot
8. Send:
   deals - List today's deals
   stats - Show statistics
   help - Show help
```

### 2. Get Chat ID

```bash
# In Telegram:
1. Start bot: @bike_scraper_alerts_bot
2. Send any message
3. Visit: https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
4. Find "chat": {"id": YOUR_CHAT_ID}
5. Copy the chat ID
```

### 3. Deploy to Railway

```bash
# Initialize Railway
railway login
railway init

# Set environment variables
railway variables set TELEGRAM_BOT_TOKEN "your_token_here"
railway variables set TELEGRAM_CHAT_ID "your_chat_id_here"

# Deploy
git push

# Check logs
railway logs

# Monitor health
railway status
```

## Configuration

### Alert Criteria (Configurable)

Default settings in `telegram_alerts.py`:

```python
TelegramAlertService(
    min_confidence=85,      # Minimum 85% confidence
    min_comparables=20,     # At least 20 similar listings
    min_discount=15,        # At least 15% discount
    min_profit=500,         # At least €500 profit potential
)
```

### Rate Limit

Default: **20 messages per hour**

Prevents Telegram from rate-limiting your bot and avoids message spam.

## Message Format

```
🚨 A-TIER DEAL FOUND

🚴 Canyon Aeroad CF SLX 8 Di2 2022

💰 Price: €5,500
📈 Market: €8,000

🔥 Discount: 31.2%

💵 Potential Profit: €1,750

📏 Size: M
⚙️ Groupset: Ultegra Di2
📅 Year: 2022

🎯 Confidence: 96%
📊 Comparables: 35

🔗 [Listing URL]

[🌐 Open Listing] [✅ Bought] [❌ Ignore]
```

## Inline Buttons

- **🌐 Open Listing** - Opens the Wallapop listing
- **✅ Bought** - Mark deal as purchased
- **❌ Ignore** - Skip this deal

## Deduplication

The service tracks `listing_id` to prevent duplicate alerts:

- Each listing is stored in memory (`sent_listing_ids`)
- Prevents alerting about the same listing multiple times
- Optional: Connect to database for persistence across deployments

## Logging

All alerts are logged with:

```python
{
    "timestamp": "2026-06-07T14:30:00",
    "listing_id": "1234567890",
    "deal_grade": "A-Tier",
    "telegram_sent": true,
    "bike_name": "Canyon Aeroad CF SLX 8 Di2 2022",
    "profit_potential": 1750.00
}
```

## Environment Variables

```bash
# Required
TELEGRAM_BOT_TOKEN      # Bot token from BotFather
TELEGRAM_CHAT_ID        # Your chat ID

# Optional
LOG_LEVEL              # INFO, DEBUG, WARNING (default: INFO)
ENVIRONMENT            # production, development (default: production)
```

## Health Check

Railway includes a health check endpoint:

```bash
GET http://localhost:8000/health
```

Response: `{"status": "healthy"}`

## Monitoring

### Check Logs

```bash
railway logs --tail
```

### View Metrics

```bash
railway metrics
```

### Restart Service

```bash
railway down
railway up
```

## Troubleshooting

### Bot not sending messages

1. Check credentials:
   ```bash
   railway variables list
   ```

2. Test bot token:
   ```bash
   curl https://api.telegram.org/bot<TOKEN>/getMe
   ```

3. Check logs:
   ```bash
   railway logs | grep -i "telegram\|error"
   ```

### Rate limit exceeded

Messages are queued when rate limit is hit. Wait 1 hour for the queue to clear.

### Duplicates appearing

Ensure `sent_listing_ids` is properly maintained. For production, use database persistence.

## Advanced Configuration

### Custom Alert Criteria

Edit `telegram_alerts.py`:

```python
service = TelegramAlertService(
    min_confidence=90,      # More strict
    min_comparables=25,     # More comparables required
    min_discount=20,        # Higher discount needed
    min_profit=1000,        # Higher profit threshold
)
```

### Database Persistence (PostgreSQL)

Optional: Store `sent_listing_ids` in database for cross-deployment deduplication.

### Webhook Integration

Optional: Integrate with Wallapop scraper to push deals directly.

## Example Integration

```python
from bike_scraper.telegram_alerts import TelegramAlertService, DealAlert
from bike_scraper.e2e_validation_suite import ListingValidation

# Create service
alert_service = TelegramAlertService()

# Process listing
async def process_listing(validation: ListingValidation):
    deal = DealAlert(
        listing_id=validation.listing_id,
        bike_name=f"{validation.parsed_bike.brand} {validation.parsed_bike.model}",
        asking_price=validation.deal_evaluation.listing_price,
        market_price=validation.deal_evaluation.market_price,
        discount_percent=validation.deal_evaluation.discount_percent,
        profit_potential=validation.deal_evaluation.profit_potential,
        size=validation.parsed_bike.size,
        groupset=validation.parsed_bike.groupset,
        year=validation.parsed_bike.year,
        confidence=validation.market_comparison.confidence,
        comparable_count=validation.market_comparison.comparable_count,
        listing_url=validation.url,
        deal_grade=validation.deal_evaluation.grade.value,
    )
    
    await alert_service.send_deal_alert(deal)
```

## Statistics

Get alert statistics:

```python
stats = alert_service.get_statistics()
print(stats)
# {
#   "total_alerts_logged": 42,
#   "total_sent_message_count": 42,
#   "unique_listings_sent": 42,
#   "rate_limit": "18/20 (last hour)",
#   "avg_profit_per_alert": 1645.24
# }
```

## Support

For issues:
1. Check Railway logs
2. Verify environment variables
3. Test bot token with Telegram API
4. Review `telegram_alerts.py` configuration

---

**Happy hunting for deals! 🎯**
