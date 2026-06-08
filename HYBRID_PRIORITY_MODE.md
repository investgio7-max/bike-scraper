# 🔥 HYBRID PRIORITY MODE IMPLEMENTATION

**Status:** ✅ DEPLOYED  
**Date:** 2026-06-08  
**Mode:** Two-tier prioritization system (no hard whitelist)

---

## Overview

Smart two-tier system that prioritizes high-profit models while maintaining flexibility to catch rare deals from lesser-known brands.

**Key Principle:** Different alert thresholds for different model tiers, allowing lower-threshold alerts for premium models while maintaining high standards for others.

---

## Tier 1: HIGH PRIORITY (🔥)

**10 Premium Models** with **lower thresholds**

### Models
```
Canyon Aeroad          → Most common, highest profit margin
Canyon Ultimate        → Climbing specialist, reliable profit
Specialized Tarmac     → Road performance, premium quality
Scott Addict RC        → Excellent deals, consistent profit
Pinarello Dogma        → Italian premium, high margin
Trek Madone            → Road power, consistent value
Trek Emonda            → Climbing focus, good profit
Cervelo S5             → Premium road, strong market
Giant TCR              → Common, good conversion rate
BMC Roadmachine        → Premium engineering, high margin
```

### Thresholds
```
Confidence    >= 90%   (AI model confidence)
Comparables   >= 20    (minimum market listings)
Discount      >= 15%   (profit margin threshold)
```

### Alert Example (TIER 1)
```
Model: Canyon Aeroad
Confidence: 92%
Comparables: 22
Discount: 17%

Thresholds:  92% >= 90% ✅
            22 >= 20 ✅
            17% >= 15% ✅

Result: ✅ ALERT SENT (Priority: TIER 1 🔥)
```

---

## Tier 2: NORMAL PRIORITY

**All Other Models** with **standard thresholds**

### Models
```
All models NOT in Tier 1 list (25+ additional models)
Examples: Merida Reacto, Focus Izalco, Lapierre Aircode, etc.
```

### Thresholds
```
Confidence    >= 90%   (AI model confidence)
Comparables   >= 25    (minimum market listings)
Discount      >= 25%   (profit margin threshold - higher!)
```

### Alert Example (TIER 2 - FAIL)
```
Model: Merida Reacto
Confidence: 92%
Comparables: 22
Discount: 17%

Thresholds:  92% >= 90% ✅
            22 >= 25 ❌ (INSUFFICIENT MARKET DATA)
            17% >= 25% ❌ (INSUFFICIENT DISCOUNT)

Result: ❌ ALERT NOT SENT
Reason: LOW_COMPARABLES + LOW_DISCOUNT
```

### Alert Example (TIER 2 - PASS)
```
Model: Merida Reacto
Confidence: 92%
Comparables: 30
Discount: 28%

Thresholds:  92% >= 90% ✅
            30 >= 25 ✅
            28% >= 25% ✅

Result: ✅ ALERT SENT (Priority: TIER 2)
```

---

## Code Implementation

### 1. Configuration File

**File:** `hybrid_priority_config.py`  
**Lines:** Complete module

```python
TIER_1_MODELS = {
    'aeroad', 'ultimate', 'tarmac', 'addict rc', 'dogma',
    'madone', 'emonda', 's5', 'tcr', 'roadmachine'
}

TIER_1_MIN_CONFIDENCE = 90
TIER_1_MIN_COMPARABLES = 20
TIER_1_MIN_DISCOUNT = 15

TIER_2_MIN_CONFIDENCE = 90
TIER_2_MIN_COMPARABLES = 25
TIER_2_MIN_DISCOUNT = 25

def should_send_alert(model, confidence, comparables, discount):
    """Determine if alert should be sent based on tier"""
    tier = get_model_tier(model)
    thresholds = get_tier_thresholds(tier)
    
    # Check thresholds and return decision
```

**Function:** `should_send_alert()`
- Input: model name, confidence, comparables, discount
- Output: (should_send: bool, reason: str, tier: str)

### 2. Integration into first_live_run.py

**File:** `first_live_run.py`  
**Lines:** 55-57 (import), 120-137 (filtering logic)

```python
from hybrid_priority_config import should_send_alert as check_hybrid_alert

# In processing loop:
should_send, reason, tier = check_hybrid_alert(
    model=model,
    confidence=confidence,
    comparables=comparables,
    discount=discount
)

if not should_send:
    self.stats["rejection_reasons"][reason] += 1
    continue

# Add tier to alert
alert = {
    ...
    "tier": tier,  # "tier_1" or "tier_2"
    ...
}
```

### 3. Telegram Alert Format

**File:** `bike_scraper/telegram_alerts.py`  
**Lines:** 32-50 (DealAlert dataclass), 201-230 (_build_message)

```python
@dataclass
class DealAlert:
    ...
    tier: str = "tier_2"  # HYBRID PRIORITY MODE

def _build_message(self, alert: DealAlert) -> str:
    tier_badge = "🔥 TIER 1" if alert.tier == "tier_1" else "TIER 2"
    
    message = f"""...
    ⭐ Priority: {tier_badge}
    ..."""
```

**Output Example:**
```
🚨 A-TIER DEAL FOUND

🚴 Canyon Aeroad

💰 Price: €2,400
📈 Market: €4,200

🔥 Discount: 42.9%

💵 Potential Profit: €1,800

🎯 Confidence: 95%
📊 Comparables: 37

⭐ Priority: 🔥 TIER 1  ← Shows tier

🔗 [URL]
```

### 4. Daily Monitoring Reports

**File:** `monitoring_reporter.py`  
**Lines:** 245-253 (daily report formatting)

```
🔥 HYBRID PRIORITY MODE (Tier 1 vs Tier 2)
├─ Tier 1 Deals:       5
├─ Tier 1 Avg Profit:  €1,650
├─ Tier 2 Deals:       3
└─ Tier 2 Avg Profit:  €1,200
```

Daily reports now show:
- Tier 1 deals found separately
- Tier 1 average profit
- Tier 2 deals found separately
- Tier 2 average profit

---

## Verification

### 1. TIER 1 List Definition

**File:** `hybrid_priority_config.py` (Lines 9-18)

```python
TIER_1_MODELS = {
    'aeroad',       # Canyon
    'ultimate',     # Canyon
    'tarmac',       # Specialized
    'addict rc',    # Scott
    'dogma',        # Pinarello
    'madone',       # Trek
    'emonda',       # Trek
    's5',           # Cervelo
    'tcr',          # Giant
    'roadmachine',  # BMC
}
```

**Count:** 10 models

### 2. Filtering Logic Application

**File:** `first_live_run.py` (Lines 120-137)

```python
should_send, reason, tier = check_hybrid_alert(
    model=model,
    confidence=confidence,
    comparables=comparables,
    discount=discount
)
```

### 3. Example: Canyon Aeroad (TIER 1)

```
Input:
  Model: Canyon Aeroad
  Confidence: 92%
  Comparables: 22
  Discount: 17%

Processing:
  1. Get model tier → "tier_1"
  2. Get tier thresholds:
     - min_confidence: 90%
     - min_comparables: 20
     - min_discount: 15%
  3. Check thresholds:
     - 92% >= 90% ✅
     - 22 >= 20 ✅
     - 17% >= 15% ✅
  4. All pass → should_send = True, tier = "tier_1"

Output:
  ✅ ALERT SENT
  Message includes: "⭐ Priority: 🔥 TIER 1"
```

### 4. Example: Merida Reacto (TIER 2 - FAIL)

```
Input:
  Model: Merida Reacto
  Confidence: 92%
  Comparables: 22
  Discount: 17%

Processing:
  1. Get model tier → "tier_2"
  2. Get tier thresholds:
     - min_confidence: 90%
     - min_comparables: 25 ← HIGHER!
     - min_discount: 25% ← HIGHER!
  3. Check thresholds:
     - 92% >= 90% ✅
     - 22 >= 25 ❌ INSUFFICIENT MARKET DATA
     - 17% >= 25% ❌ INSUFFICIENT DISCOUNT
  4. Multiple failures → should_send = False

Output:
  ❌ ALERT NOT SENT
  Reason: LOW_COMPARABLES (22 < 25)
```

### 5. Example: Merida Reacto (TIER 2 - PASS)

```
Input:
  Model: Merida Reacto
  Confidence: 92%
  Comparables: 30
  Discount: 28%

Processing:
  1. Get model tier → "tier_2"
  2. Get tier thresholds:
     - min_confidence: 90%
     - min_comparables: 25
     - min_discount: 25%
  3. Check thresholds:
     - 92% >= 90% ✅
     - 30 >= 25 ✅
     - 28% >= 25% ✅
  4. All pass → should_send = True, tier = "tier_2"

Output:
  ✅ ALERT SENT
  Message includes: "⭐ Priority: TIER 2"
```

---

## Final Status

### TIER 1 MODE ACTIVE

**YES** ✅

### Configuration Summary

```
Tier 1 Models:        10
Tier 2 Models:        25+
Total Models:         35+

Tier 1 Thresholds:
  Confidence:         >= 90%
  Comparables:        >= 20
  Discount:           >= 15%

Tier 2 Thresholds:
  Confidence:         >= 90%
  Comparables:        >= 25
  Discount:           >= 25%

Hybrid Mode Status:    🔥 ACTIVE
```

### Tier 1 Model List (10 total)

1. **Canyon Aeroad** - Most common premium model
2. **Canyon Ultimate** - Climbing specialist
3. **Specialized Tarmac** - Road performance
4. **Scott Addict RC** - Excellent deals
5. **Pinarello Dogma** - Italian premium
6. **Trek Madone** - Road power
7. **Trek Emonda** - Climbing focus
8. **Cervelo S5** - Premium road
9. **Giant TCR** - Common, good deals
10. **BMC Roadmachine** - Premium engineering

### Tier 2 Model List (25+ total)

All other models from the 35 monitored models:
- Canyon (Grail, Grizl, Endurace)
- Specialized (Roubaix, Crux, Diverge)
- Scott (Foil, Speedster)
- Cervelo (R5, Caledonia, Aspero)
- Pinarello (Prince, Gan)
- Trek (Checkpoint)
- Giant (Propel, Revolt)
- BMC (TeamElite, AlpenChallenge)
- Cannondale (SystemSix, SuperSix, Caad)
- Wilier (Cento10, Mortirolo)
- Colnago (V3RS, Act)
- All other brands' models

---

## Benefits

### ✅ For Premium Models (Tier 1)
- Lower thresholds = more alerts
- Faster deal discovery
- Prefer high-profit, common models
- 🔥 Badge identifies priority

### ✅ For Rare Models (Tier 2)
- Still monitored (no hard whitelist)
- Higher thresholds for quality
- Catch exceptional deals if they appear
- Better market data requirements

### ✅ For System
- Flexible prioritization without exclusion
- Better ROI on premium models
- Maintains diversity for rare finds
- Clear tier indicators in alerts
- Separate statistics per tier

---

## Monitoring & Reporting

### Daily Report Includes:
```
🔥 HYBRID PRIORITY MODE (Tier 1 vs Tier 2)
├─ Tier 1 Deals:       5
├─ Tier 1 Avg Profit:  €1,650
├─ Tier 2 Deals:       3
└─ Tier 2 Avg Profit:  €1,200
```

### 7-Day Summary Includes:
- Tier 1 performance metrics
- Tier 2 performance metrics
- Best model by tier
- ROI comparison between tiers

---

## Deployment

**Commit:** Latest (hybrid_priority_mode)  
**Files Changed:**
- `hybrid_priority_config.py` (NEW)
- `first_live_run.py` (MODIFIED - filtering logic)
- `bike_scraper/telegram_alerts.py` (MODIFIED - tier field + display)
- `monitoring_reporter.py` (MODIFIED - tier tracking)

**Status:** ✅ READY FOR PRODUCTION

---

**Last Updated:** 2026-06-08  
**Next Review:** After 7-day monitoring period
