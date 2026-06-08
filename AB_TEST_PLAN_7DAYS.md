# 🧪 7-DAY A/B TEST PLAN

**Whitelist vs No Whitelist: Real Data Collection & Analysis**

---

## 📋 Test Overview

Instead of immediately deploying the whitelist, we'll run a **7-day controlled A/B test** to collect real production data and make an informed decision.

**Why this approach?**
- ✅ Real data > predictions
- ✅ No assumptions about profitability
- ✅ Data-driven decision making
- ✅ Minimize risk of poor choices
- ✅ Identify unexpected patterns

---

## 🎯 Test Configuration

### MODE A: No Whitelist (Current System)
```
Configuration:  All 38 known models allowed
Filtering:      Standard 5 filters (URL, frame, parts, model, boost)
Confidence:     No modifications
Expected:       Current baseline ~45 alerts/day, 32% profit
```

### MODE B: Priority Whitelist
```
Configuration:  All models still allowed
Filtering:      Standard 5 filters + whitelist logic
Confidence:     TOP-10 models get +10% confidence boost
Strategy:       Prefer high-profit models without excluding others
Expected:       Shift toward better models, maintain volume
```

**Key Difference:** MODE B doesn't exclude models, it prioritizes them.

---

## 📊 Metrics to Collect (Both Modes)

### Listing & Deal Metrics
- [ ] Total listings found per day
- [ ] Parse success rate
- [ ] Total deals identified
- [ ] Total alerts sent
- [ ] Conversion rate (deals / listings)

### Quality Metrics
- [ ] Average confidence score
- [ ] Average discount %
- [ ] Average profit margin
- [ ] Average market price
- [ ] Average asking price

### Accuracy Metrics
- [ ] Manual verifications performed
- [ ] True positives count
- [ ] False positives count
- [ ] True positive rate %
- [ ] False positive rate %

### Model Distribution
- [ ] Top 10 models found
- [ ] Top 10 brands found
- [ ] Whitelist hits (MODE B only)
- [ ] Non-whitelist hits

### Bike Type Distribution
- [ ] Road bikes
- [ ] Gravel bikes
- [ ] Mountain bikes

### Price Segment Distribution
- [ ] Alerts under €2,000
- [ ] Alerts €2,000-€5,000
- [ ] Alerts €5,000-€10,000
- [ ] Alerts over €10,000

---

## 📅 7-Day Test Schedule

### Day 1: Setup & Baseline
```
Tasks:
  ✓ Deploy MODE A in production
  ✓ Verify statistics collection working
  ✓ Manual verification of 10 alerts
  ✓ Document baseline metrics
  
Check:
  - All alerts arriving to Telegram ✓
  - Statistics logging correctly ✓
  - No errors in logs ✓
```

### Days 2-6: Data Collection
```
Daily:
  ✓ Monitor alerts in Telegram
  ✓ Manual verify 5-10 alerts per day
  ✓ Record statistics
  ✓ Check for anomalies
  
Weekly:
  ✓ Generate daily comparison report
  ✓ Update aggregated statistics
```

### Day 7: Analysis & Decision
```
Tasks:
  ✓ Finalize all 7-day data
  ✓ Calculate final statistics
  ✓ Compare MODE A vs MODE B
  ✓ Analyze profitability differences
  ✓ Review accuracy metrics
  ✓ Make final decision
  
Decision Points:
  → Full Whitelist (only TOP-10)
  → Priority Whitelist (MODE B continues)
  → No Whitelist (keep MODE A)
```

---

## 🔍 Daily Verification Protocol

### For Each Alert Sent:
1. **Check URL**
   - [ ] Listing still exists (not 404)
   - [ ] Price matches (or close)
   - [ ] Description matches listing

2. **Verify Bike**
   - [ ] Model matches (e.g., Aeroad is Aeroad)
   - [ ] Brand correct (e.g., Canyon for Aeroad)
   - [ ] Bike type correct (road/gravel/mountain)

3. **Verify Deal Quality**
   - [ ] Market price reasonable
   - [ ] Discount calculation correct
   - [ ] Not parts-only listing
   - [ ] Not frame-only listing

4. **Mark Result**
   - ✅ TRUE POSITIVE: Real deal
   - ❌ FALSE POSITIVE: Mistake/removed/wrong

### Daily Quota
- **Days 1-3:** Verify 10 alerts per day (30 total)
- **Days 4-6:** Verify 5 alerts per day (30 total)
- **Day 7:** Verify 10 alerts (final check)
- **Total:** 100 verifications for 7-day period

---

## 📈 Expected Outcome

### If MODE A (No Whitelist) Performs Better:
- ✅ **Decision:** Keep current system
- ✅ **Reason:** More listings = more opportunities
- ✅ **Action:** Continue as-is, optimize filters

### If MODE B (Priority Whitelist) Performs Better:
- ✅ **Decision:** Deploy priority whitelist
- ✅ **Reason:** Better quality alerts, higher profit
- ✅ **Action:** Implement confidence boost, continue

### If Results are Equivalent:
- ✅ **Decision:** Use MODE B (priority)
- ✅ **Reason:** Same quality, better resource usage
- ✅ **Action:** Deploy priority whitelist for efficiency

---

## 📊 Sample Daily Report (Mode Comparison)

```
╔════════════════════════════════════════════════════════════════╗
║              A/B TEST DAILY REPORT - DAY 3                    ║
║                     2026-06-11                                 ║
╚════════════════════════════════════════════════════════════════╝

LISTINGS & DEALS:
  Metric                  MODE A          MODE B        Difference
  ────────────────────────────────────────────────────────
  Listings Found            247             247           0
  Parse Success Rate       94.7%           94.7%         0.0%
  Alerts Sent              45              52           +7 (+15%)
  Conversion Rate         19.2%           22.2%        +3.0%

QUALITY METRICS:
  Average Confidence      92.1%           94.3%        +2.2%
  Average Discount        32.5%           33.1%        +0.6%
  Average Profit          28.0%           29.5%        +1.5%

PRICES:
  Avg Market Price        €4,650          €4,700       +€50
  Avg Asking Price        €3,150          €3,180       +€30

ACCURACY:
  Verifications           10              10           0
  True Positives          10              10           0
  False Positives         0               0            0
  TP Rate                 100%            100%         0%
  FP Rate                 0%              0%           0%

BIKE TYPES:
  Road Bikes              28              32           +4
  Gravel Bikes            12              14           +2
  Mountain Bikes          5               6            +1

PRICE SEGMENTS:
  Under €2,000            8               7            -1
  €2,000-€5,000           22              28           +6
  €5,000-€10,000          12              14           +2
  Over €10,000            3               3            0

INSIGHTS DAY 3:
  ✓ MODE B generating +15% more alerts
  ✓ Better quality (avg confidence +2.2%)
  ✓ Higher profit margins (+1.5%)
  ✓ 100% accuracy maintained
  ✓ Focus on road bikes (better profit)
```

---

## 🎯 Decision Framework

After 7 days, analyze using this framework:

### Metric Weights
```
Profitability:        40%  (Average Profit %)
Quality:              30%  (True Positive Rate %)
Volume:               20%  (Alerts per day)
Efficiency:           10%  (Resource usage)
```

### Decision Tree
```
If MODE B.profit > MODE A.profit:
    If MODE B.TP_rate > 90%:
        → Deploy Full or Priority Whitelist
    Else:
        → Keep MODE A
Else If MODE B.profit ≈ MODE A.profit:
    If MODE B.volume > MODE A.volume:
        → Deploy Priority Whitelist
    Else:
        → Keep MODE A
Else:
    → Keep MODE A
```

---

## 🛑 Stopping Rules (Emergency)

Stop test immediately if:
- [ ] False positive rate > 25% (quality collapse)
- [ ] Telegram delivery failing > 10% (system issue)
- [ ] Database errors > 5% per day (infrastructure)
- [ ] Suspicious spikes in alerts (+200%+ in single hour)

---

## 📝 Final Report Template

After 7 days, generate final report with:

### Executive Summary
- Mode that performed better
- Key difference in metrics
- Recommendation (Full / Priority / No whitelist)
- Confidence level in recommendation

### Detailed Comparison
- Week-long statistics for both modes
- Trend analysis (improving/declining)
- Top models in each mode
- Best price segments

### Data-Driven Insights
- Most profitable models (real data)
- Models with best conversion
- Unexpected findings
- Seasonal patterns

### Implementation Plan
- Deployment steps if changing
- Rollback plan if needed
- Timeline for go-live

---

## 🔄 Running Both Modes Simultaneously

To run both modes at the same time (recommended):

### Split Testing Setup
```
Option 1: Split Traffic
  - 50% of alerts through MODE A
  - 50% of alerts through MODE B
  - Compare side-by-side
  
Option 2: Sequential Testing
  - Days 1-3: Run MODE A
  - Days 4-7: Run MODE B
  - Compare consecutive periods

Option 3: Separate Pipelines
  - Pipeline A: All listings
  - Pipeline B: All listings + boost
  - Independent statistics tracking
```

**Recommended:** Option 3 (separate pipelines) for cleanest data.

---

## 🔐 Data Integrity

### Ensure Clean Data
- [ ] Same filters applied to both modes
- [ ] Same time periods
- [ ] Same query terms
- [ ] Same proxies/IP sources
- [ ] Same verification process
- [ ] No mode switching mid-test

### Avoid Bias
- [ ] Don't manually adjust one mode
- [ ] Don't cherry-pick metrics
- [ ] Include all alerts (no filtering)
- [ ] Verify equally (same person if possible)
- [ ] Use automated statistics (not manual counts)

---

## 📊 Sample Prediction (Based on Previous Data)

Based on audit results, expected outcomes:

### MODE A Projection (No Whitelist)
- Alerts/day: ~45
- True Positive Rate: ~90%
- Average Profit: ~28%
- Quality Score: 92/100

### MODE B Projection (Priority Whitelist)
- Alerts/day: ~48-52
- True Positive Rate: ~95%
- Average Profit: ~30%
- Quality Score: 94/100

**Key Assumption:** +10% confidence boost shifts alerts toward TOP-10 models (higher profit).

---

## ✅ SUCCESS CRITERIA

Test is successful if:
1. ✅ 7 days of continuous data collection
2. ✅ 100+ manual verifications completed
3. ✅ No major system failures
4. ✅ Clear winner or equivalent result
5. ✅ Data quality issues <5%
6. ✅ Recommendation backed by data

---

## 🚀 Next Steps

1. **Day 1 Morning:** Deploy test configuration
2. **Day 1 Evening:** Verify data collection
3. **Days 2-6:** Maintain daily verification quota
4. **Day 7 Evening:** Generate final analysis
5. **Day 8:** Implement decision

**Timeline:** 8 days total (7 days test + 1 day implementation)

---

**Status:** Ready to deploy A/B test framework  
**Updated:** June 8, 2026  
**Decision Point:** June 15, 2026
