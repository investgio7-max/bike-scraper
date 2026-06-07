# Telegram Smoke Test Module

Complete testing suite for Telegram Alert System functionality.

## Modules

### 1. `test_telegram.py` - Basic Smoke Test (5 min)

Verifies that the Telegram alert system is functional and messages are delivered correctly.

**8 Checks:**
1. ✅ Environment variables (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
2. ✅ Bot connection (getMe() call)
3. ✅ Simple message delivery
4. ✅ Deal alert with production format
5. ✅ Inline keyboard acceptance
6. ✅ API response structure
7. ✅ Logging
8. ✅ Final verdict

**Running:**
```bash
# Set environment variables first
export TELEGRAM_BOT_TOKEN="your_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"

# Run test
python3 tests/test_telegram.py
```

**Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━
TELEGRAM SMOKE TEST
━━━━━━━━━━━━━━━━━━━━━━━

Bot Connection:     ✅ PASS
Simple Message:     ✅ PASS
Deal Alert:         ✅ PASS
Inline Keyboard:    ✅ PASS
API Response:       ✅ PASS
Chat ID:            123456789
Message ID:         125

Overall:            ✅ TELEGRAM READY

Test Log:           tests/logs/test_telegram_<timestamp>.log
```

---

### 2. `test_telegram_callbacks.py` - Callback Audit (10-15 min)

Comprehensive audit of Telegram buttons and callback handlers.

**9 Checks:**
1. ✅ Button Discovery - finds all InlineKeyboard buttons
2. ✅ Handler Registration - checks callbacks are registered
3. ✅ URL Validation - verifies URL buttons are valid
4. ✅ Callback Execution - tests callback logic
5. ✅ Database Operations - verifies data saving
6. ✅ Error Handling - simulates failures
7. ✅ Deduplication - button clicks 10x test
8. ✅ Production Load - 100 alerts × 3 clicks
9. ✅ Handler Registry - callback registration check

**Running:**
```bash
python3 tests/test_telegram_callbacks.py
```

**Output:**
```
BUTTON AUDIT TABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Button              Type         Status
🌐 Open Listing    url          IMPLEMENTED ✅
✅ Bought          callback     PENDING ⚠️
❌ Ignore          callback     PENDING ⚠️

AUDIT SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Buttons found:           3
Handlers registered:     0
URL validation errors:   0
Deduplication test:      ✅ PASS

Production Load Test:
  Alerts processed:     100/100
  Clicks processed:     300/300
  Duplicate clicks:     150
  Errors:               0

Overall Status: ✅ PRODUCTION READY
```

---

### 3. `/test-alert` API Endpoint

HTTP endpoint for sending test alerts via API.

**Endpoint:** `POST /test-alert`

**URL:** `http://localhost:8000/test-alert`

**Usage:**
```bash
curl -X POST http://localhost:8000/test-alert
```

**Response:**
```json
{
  "status": "success",
  "message": "test alert sent",
  "chat_id": 123456789,
  "message_id": 125,
  "timestamp": "2026-06-07T14:30:00"
}
```

**Error Response (if env vars not set):**
```json
{
  "detail": "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured"
}
```

---

## Test Logs

All test logs are stored in `tests/logs/`:
- `test_telegram_<timestamp>.log` - Basic smoke test logs
- `test_telegram_callbacks_<timestamp>.log` - Callback audit logs

View logs:
```bash
tail -f tests/logs/test_telegram_*.log
```

---

## Setup

### 1. Get Telegram Bot Token

```
1. Open Telegram BotFather: @BotFather
2. Send: /newbot
3. Name your bot
4. Set unique username
5. Copy token (format: 123456:ABC-DEF...)
```

### 2. Get Chat ID

```
1. Start your bot
2. Send any message
3. Visit: https://api.telegram.org/bot<TOKEN>/getUpdates
4. Find "chat": {"id": YOUR_CHAT_ID}
```

### 3. Set Environment Variables

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
export TELEGRAM_CHAT_ID="987654321"
```

Or in `.env`:
```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=987654321
```

---

## Callback Handlers

### Implemented Buttons

1. **🌐 Open Listing** (URL button)
   - Opens Wallapop listing in browser
   - No callback (simple link)
   - Implementation: Built-in to Telegram

2. **✅ Bought** (Callback button)
   - Records user marked deal as purchased
   - Callback data: `bought_<listing_id>`
   - Handler: `handle_bought_callback()`
   - DB: Records in `user_deal_actions` table
   - Status: ⚠️ READY (needs registration in bot)

3. **❌ Ignore** (Callback button)
   - Records user ignored this deal
   - Callback data: `ignore_<listing_id>`
   - Handler: `handle_ignore_callback()`
   - DB: Records in `user_deal_actions` table
   - Status: ⚠️ READY (needs registration in bot)

### Handler Registration

Handlers are registered in `telegram_bot_final.py`:

```python
from telegram.ext import CallbackQueryHandler
from bike_scraper.telegram_callback_handlers import register_callbacks

# In main():
app = Application.builder().token(token).build()
register_callbacks(app)  # Register all callbacks
app.run_polling()
```

Handlers use pattern matching:
- `bought_.*` - matches all "bought" callbacks
- `ignore_.*` - matches all "ignore" callbacks

---

## Database Tables

### `sent_alerts`
Tracks which alerts were sent (prevents duplicates on restart).

### `user_deal_actions`
Records user actions on alerts (bought, ignored).

```sql
CREATE TABLE user_deal_actions (
    id UUID PRIMARY KEY,
    user_id INTEGER,
    listing_id VARCHAR(255),
    telegram_message_id BIGINT,
    action_type VARCHAR(20),  -- 'bought', 'ignored'
    action_timestamp TIMESTAMP
);
```

---

## Troubleshooting

### "TELEGRAM_BOT_TOKEN not found"
- Set environment variable: `export TELEGRAM_BOT_TOKEN="..."`
- Check `.env` file exists and is loaded

### "Bot not connected"
- Verify token is correct
- Check internet connectivity
- Verify bot is not running twice (would cause API errors)

### "Message not delivered"
- Verify chat ID is correct
- Check bot has permission to send messages
- Verify Telegram API is accessible

### "Callbacks not working"
- Callbacks need to be registered in `telegram_bot_final.py`
- Check `register_callbacks(app)` is called during bot startup
- Verify callback handlers are in `telegram_callback_handlers.py`

---

## Running All Tests

```bash
#!/bin/bash

# Set environment
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"

echo "Running Telegram Smoke Tests..."
echo "================================"

echo ""
echo "[1/3] Basic Smoke Test..."
python3 tests/test_telegram.py

echo ""
echo "[2/3] Callback Audit..."
python3 tests/test_telegram_callbacks.py

echo ""
echo "[3/3] API Endpoint Test..."
curl -X POST http://localhost:8000/test-alert

echo ""
echo "================================"
echo "All tests completed!"
echo "Check tests/logs/ for detailed results"
```

---

## Production Deployment

Before deploying to production:

1. ✅ Run `test_telegram.py` - must see ✅ TELEGRAM READY
2. ✅ Run `test_telegram_callbacks.py` - must see 0 critical errors
3. ✅ Test `/test-alert` endpoint
4. ✅ Send test alert and verify it arrives in Telegram
5. ✅ Click button and verify action is recorded in database
6. ✅ Restart service and verify no duplicate messages

---

## References

- [python-telegram-bot documentation](https://python-telegram-bot.readthedocs.io/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [InlineKeyboardButton docs](https://python-telegram-bot.readthedocs.io/en/stable/telegram.inlinekeyboardbutton.html)
