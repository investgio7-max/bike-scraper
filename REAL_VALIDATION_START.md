# 🚀 REAL MARKET VALIDATION RUN

## Objective

**Prove that the system finds real profitable bikes on Wallapop using real data.**

Not demo data.  
Not sample bikes.  
Not mock listings.

**Real Wallapop searches. Real results. Real validation.**

---

## What Will Happen

### Duration: 60 Minutes
- Searches Wallapop every 10 minutes
- Real API calls (not mocked)
- Real bike parsing (AI model detection)
- Real price analysis (market comparison)
- Real filtering (confidence ≥90%, discount ≥20%)
- Real Telegram alerts (if credentials set)

### What Gets Searched
```
Search Queries:
  • "bicicleta carretera" (road bikes)
  • "bicicleta montaña" (mountain bikes)
  • "bicicleta gravel" (gravel bikes)
  • "bicicleta ruta" (route bikes)
  • "road bike" (English)
  • "mountain bike" (English)

Max Results: 20 per query per cycle
Total Per Cycle: ~120 real listings
```

### Filters Applied
```
Confidence Threshold:     ≥90%
Discount Threshold:       ≥20%
Comparable Listings:      ≥25
```

---

## What You'll See

### During Run (Every 15 Minutes)
```
📊 PERIODIC REPORT - 15 MINUTES ELAPSED
Found Listings:           124
Parsed Successfully:      118
Price Validated:          115
Market Compared:          98
Filters Passed:           24
Telegram Alerts Sent:     24
Rejected:                 100
Conversion Rate:          19.4%
```

### For Each Alert Sent
```
🚴 Trek Domane AL 3

ID: wallapop_12345
Price: €1200 → Market: €1800
Discount: 33.3%
Confidence: 92%
Comparables: 42
URL: https://es.wallapop.com/item/12345
Time: 2026-06-08T12:30:45
```

---

## Prerequisites

### 1. Wallapop Scraper Working
✅ Already verified in demo run

### 2. AI Parser Working
✅ Already verified (91% confidence)

### 3. Price Analyzer Working
✅ Already verified

### 4. Telegram Optional
- If NOT set: Alerts tracked in logs/JSON only
- If SET: Alerts sent to Telegram in real-time

To set credentials:
```bash
railway variable set TELEGRAM_BOT_TOKEN=<token> --service bike-scraper-api
railway variable set TELEGRAM_ADMIN_CHAT_ID=<id> --service bike-scraper-api
railway restart --service bike-scraper-api
```

---

## Start the Run

### Command
```bash
cd /Users/oleg/bike-scraper
python3 real_market_validation.py
```

### What Happens Next
```
🚀 REAL MARKET VALIDATION RUN - 60 MINUTES
⚠️  USING REAL WALLAPOP DATA - NO MOCKS, NO SAMPLES

📍 SEARCH CONFIGURATION:
  Start Time: 2026-06-08 12:00:00
  Duration: 60 minutes
  Search Queries: bicicleta carretera, bicicleta montaña, ...

🎯 FILTER THRESHOLDS:
  Confidence: ≥90%
  Discount: ≥20%
  Comparables: ≥25

⏱️  REPORTING: Every 15 minutes + final report

🔄 SEARCH CYCLE #1
🔍 Searching Wallapop: 'bicicleta carretera'
✅ Found 20 real listings for 'bicicleta carretera'
...
```

---

## During the Run

### What to Monitor

**Real-Time Alerts:**
- Each found deal appears in logs
- `✅ ALERT SENT:` lines = Telegram notifications

**Statistics:**
- Every 15 minutes: Progress report
- Current conversion rate, deal count, etc.

**Output Files:**
- `/tmp/real_validation_*.log` - Full logs
- `/tmp/real_validation_*.json` - Structured data

---

## After 60 Minutes

### You'll Get
```
📊 FINAL VALIDATION REPORT

📈 PIPELINE STATISTICS:
  Listings Found:           612
  Parsed Successfully:      580
  Price Validated:          568
  Market Compared:          450
  Filters Passed:           78
  Telegram Alerts Sent:     78

❌ REJECTION BREAKDOWN:
  low_comparables: 156
  confidence_low: 89
  discount_insufficient: 45
  ...

✅ QUALITY METRICS:
  Conversion Rate:          12.7%
  Parse Success Rate:       94.8%
  Listings Per Hour:        10.2
  Avg Processing Time:      1250ms

📲 ALL 78 SENT ALERTS:
  [1] Canyon Aeroad CF SLX 8
      Price: €2900 → Market: €4200
      Discount: 30.9%
      Confidence: 95%
      Comparables: 28
      URL: https://...
      Time: 2026-06-08T12:10:45
  
  [2] Trek Domane AL 3
      Price: €1200 → Market: €1800
      Discount: 33.3%
      ...
  
  ... [all 78 alerts listed]

🏆 BEST DEALS:
  By Discount: Trek Domane AL 3 (33.3%)
  By Confidence: Specialized Tarmac SL7 (96%)
  Average Discount: 27.5%

🎯 FINAL VERDICT:
✅ MVP VALIDATED = YES
   System found 78 real high-quality deals
   Conversion rate: 12.7%
   All deals from REAL Wallapop data
```

---

## Manual Verification

### You Should Check

For **first 10 alerts**, verify:

1. **Link Opens** ✓
   - Click each Wallapop URL
   - Page loads without 404

2. **Bike Really Exists** ✓
   - Model matches what was parsed
   - Photos show complete bike

3. **Price Matches** ✓
   - Listed price = what we found
   - Same currency (EUR)

4. **Is Bike, Not Parts** ✓
   - Full bike (not just frame)
   - Not "wheels only" or similar

5. **Not "Looking For"** ✓
   - "Se vende" (for sale)
   - Not "Busco" (looking for)

6. **Not Damaged** ✓
   - No crash damage visible
   - All parts intact

7. **Not Obvious Scam** ✓
   - Seller has reviews/history
   - Price seems reasonable
   - Photos are real (not stock photos)

### For Each: Mark PASS or FAIL

```
Alert 1: Trek Domane AL 3 - PASS ✅
Alert 2: Canyon Aeroad CF - PASS ✅
Alert 3: Specialized Tarmac - PASS ✅
...
Alert 10: Giant TCR - FAIL ❌ (damaged)

False Positive Rate: 1/10 = 10%
```

---

## Expected Results

### Conservative Estimate (60 min real search)
```
Listings Found:           500-700
Alerts Sent:              50-100
False Positive Rate:      0-10%
Best Deal Discount:       25%+
```

### Quality Check
```
Parser Success:           90%+
Confidence Average:       92%+
Comparable Count Avg:     30+
```

---

## Success Criteria

System is **MVP VALIDATED** if:

✅ **At least 10 real alerts sent**
- From real Wallapop data
- Not mock or sample

✅ **False positive rate < 10%**
- Most deals are legit
- Occasional misidentifications OK

✅ **Best deals make sense**
- >25% discount typical for good deals
- Prices reasonable for bike type

✅ **Pipeline works end-to-end**
- Search finds listings
- Parser identifies bikes
- Analyzer calculates prices
- Filters apply correctly

---

## What to Do With Results

### If MVP VALIDATED = YES
1. **Celebrate** 🎉
2. **Deploy to production**
   - Enable 24/7 scheduler
   - Push code to Railway
   - Monitor for 48 hours
3. **Optimize filters**
   - Adjust confidence threshold
   - Adjust discount threshold
   - Fine-tune based on results

### If MVP VALIDATED = INCONCLUSIVE
1. **Adjust filters**
   - Lower confidence threshold (85% instead of 90%)
   - Lower discount threshold (15% instead of 20%)
2. **Run again**
   - See if more deals found
3. **Check Wallapop availability**
   - Maybe few bikes matching criteria

### If MVP VALIDATED = NO
1. **Debug**
   - Check logs for errors
   - Verify API access
   - Test individual components
2. **Adjust strategy**
   - Expand search queries
   - Relax filters
   - Check data quality

---

## Files Generated

```
Logs:
  /tmp/real_validation_<timestamp>.log
  └─ Full execution log with all details

JSON Report:
  /tmp/real_validation_<timestamp>.json
  └─ Structured data (all alerts, statistics)

Screenshots to Save:
  1. Start output (search config)
  2. 15-min report
  3. 30-min report
  4. 45-min report
  5. Final report with verdict
```

---

## Troubleshooting

### Error: "TELEGRAM_BOT_TOKEN not set"
```
This is OK! System still works, just logs instead of sending.
Check logs for: "would send: [bike_name]"
```

### Error: "Wallapop search failed"
```
May be rate limit or server issue.
Check: Is Wallapop website working?
System will retry next cycle.
```

### Error: "Parse failed for listing"
```
Normal for some listings (ads, spam, etc)
System counts these as rejections.
This is expected behavior.
```

### Too Few Alerts (< 5 in 60 min)
```
Options:
1. Lower confidence: 85% instead of 90%
2. Lower discount: 15% instead of 20%
3. Run longer: Extend to 120 minutes
4. Check Wallapop: Maybe few deals available
```

---

## Important Notes

### Real Data Only
- **NO** mock data
- **NO** sample listings
- **NO** simulated results
- All results from actual Wallapop API

### No Cheating
- System must find real deals
- Must pass real filters
- Must show real statistics
- Must output real alerts

### This Is The Real Test
- Previous demos were "proof of concept"
- This is actual production validation
- Results determine MVP readiness

---

## Timeline

```
T+0 min:    Start real_market_validation.py
T+10 min:   First results appearing in logs
T+15 min:   First periodic report
T+20 min:   First alerts likely sent
T+30 min:   Second periodic report
T+45 min:   Third periodic report
T+60 min:   Final comprehensive report
T+70 min:   Manual verification of 10 alerts
T+80 min:   Final verdict: MVP VALIDATED YES/NO
```

---

## Next Steps (Based on Results)

### If PASS
```
1. ✅ Review final report
2. ✅ Spot-check 10 deals manually
3. ✅ Deploy to 24/7 production
4. ✅ Enable automatic scheduling
5. ✅ Monitor for 48 hours
6. ✅ Production ready!
```

### If INCONCLUSIVE
```
1. ⚠️  Lower filter thresholds
2. ⚠️  Run validation again
3. ⚠️  Check if more deals found
4. ⚠️  Adjust and iterate
```

### If FAIL
```
1. ❌ Debug system issues
2. ❌ Check component functionality
3. ❌ Expand search criteria
4. ❌ Run diagnostic tests
```

---

## Ready?

```bash
cd /Users/oleg/bike-scraper
python3 real_market_validation.py
```

**System is set to prove itself with REAL data.**

No more demos. This is the real deal.

🚀 Let's go!
