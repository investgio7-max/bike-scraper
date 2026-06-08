# 🚀 Quick Start - 5 Minute Setup

> **Everything is ready!** Just set Telegram credentials and go.

## What You Need

1. Telegram bot token (from @BotFather)
2. Chat ID where you want alerts (from @userinfobot)
3. 2 minutes to set environment variables

## Go!

### Step 1: Get Your Telegram IDs (2 min)

**Get Bot Token:**
1. Open Telegram
2. Find @BotFather
3. Send: `/newbot`
4. Follow instructions
5. Copy your token (long string starting with numbers)

**Get Chat ID:**
1. Open Telegram
2. Find @userinfobot
3. Send: `/start`
4. Copy your User ID (just numbers)

### Step 2: Set Environment Variables (1 min)

```bash
# Replace YOUR_TOKEN and YOUR_CHAT_ID with actual values
export BOT_TOKEN="YOUR_TOKEN"
export CHAT_ID="YOUR_CHAT_ID"

# Set in Railway
railway variable set TELEGRAM_BOT_TOKEN=$BOT_TOKEN --service bike-scraper-api
railway variable set TELEGRAM_ADMIN_CHAT_ID=$CHAT_ID --service bike-scraper-api

# Restart
railway restart --service bike-scraper-api
```

### Step 3: Start Validation (60 seconds)

Wait 30 seconds for restart, then:

```bash
cd /Users/oleg/bike-scraper
python3 mvp_launcher.py
```

**What happens:**
- Every 10 minutes: Searches for bikes on Wallapop
- Analyzes prices and quality
- Sends alerts to your Telegram
- Runs for 60 minutes total

**Watch for:**
- Telegram notifications with deals
- Best deals highlighted

### Done!

You'll get Telegram alerts that look like:

```
🚴 Trek Domane AL 3

💰 Price: €1200
📊 Market: €1800
✅ Discount: 33.3%
📈 Confidence: 92%
🔗 https://es.wallapop.com/item/12345
```

---

## Quick Commands Reference

```bash
# Health check
python3 mvp_status.py

# Quick demo (1 minute)
python3 validation_runner.py

# Full run (60 minutes)
python3 mvp_launcher.py

# Watch API logs
railway logs --service bike-scraper-api --follow
```

---

## Troubleshooting

**No alerts?**
- Check Telegram credentials are set: `railway variable list --service bike-scraper-api | grep TELEGRAM`
- Verify credentials: `curl https://api.telegram.org/bot${BOT_TOKEN}/getMe`

**502 Bad Gateway?**
- Wait 2 minutes for restart to complete
- Check port: `railway variable list --service bike-scraper-api | grep PORT`

**Too few/many alerts?**
- Edit filters in `mvp_launcher.py`
- Lower confidence for more alerts
- Raise confidence for quality

---

## That's It!

System is running. Monitor Telegram. Done. 🎉

For details, see MVP_LAUNCH_GUIDE.md
