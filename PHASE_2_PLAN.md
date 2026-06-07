# Phase 2: Market Analysis (Рыночный анализ)

## Overview
Implement market price analysis for each bike listing to identify profit opportunities.

## Steps to Implement

### STEP 6: Find Market Analogs
For each bike found in STEP 1, find similar bikes sold in the last 30 days:

1. **Matching criteria** (in priority order):
   - Same brand + model + year + size (exact match)
   - Same brand + model + year (allow size variation ±1)
   - Same brand + model (allow year variation ±2)
   - Same brand + type (fallback)

2. **Filters**:
   - Only include listings with `is_active=False` (completed/sold listings)
   - Date range: last 30 days (`date_posted >= NOW - 30 days`)
   - Minimum matches: 3 listings (need statistical significance)

3. **Data to extract**:
   - List of all matching listing prices
   - Seller location (if relevant for regional pricing)

### STEP 7: Calculate Market Baseline
For matching listings found in STEP 6:

1. **Price statistics**:
   - Median price (more robust than mean for outliers)
   - Mean price
   - Price range (min/max)
   - Price std deviation

2. **Market segment**:
   - Classify as: "Budget", "Mid-range", "Premium" based on quantiles
   - Regional variations (if applicable)

3. **Liquidity estimate**:
   - Days to sell (from historical data if available)
   - Turnover rate (listings per month in this segment)

## Database Updates Needed

### Models to Update
- `Listing` table needs new fields:
  - `market_price_median: Float` - median price of similar bikes
  - `market_price_mean: Float` - mean price of similar bikes
  - `market_analogs_count: Int` - how many similar bikes found
  - `price_discount_percent: Float` - discount from market price
  - `price_discount_euro: Float` - discount amount in €

### Queries to Create
```python
# Find similar bikes from last 30 days
def find_market_analogs(
    brand: str,
    model: str,
    year: Optional[int],
    size: Optional[str],
    days_back: int = 30
) -> List[Listing]:
    """Find similar bikes sold in market"""
    pass

# Calculate price statistics
def calculate_market_stats(
    listings: List[Listing]
) -> Dict[str, float]:
    """Return: median, mean, min, max, std dev"""
    pass

# Update listing with market analysis
def update_market_analysis(
    db: Session,
    listing: Listing
) -> bool:
    """Calculate and store market analysis for listing"""
    pass
```

## Integration Points

### Service Layer
Create `service_price_analysis.py`:
- `PriceAnalyzer` class with methods for finding analogs and calculating stats
- Integration point in `ListingService.get_or_create_listing()` to auto-calculate market analysis

### API Endpoints
Add to REST API:
- `GET /listings/{id}/market-analysis` - get market analysis for specific listing
- `GET /listings/deals?discount_min=10&discount_max=50` - filter by discount percentage

### Telegram Bot
Add to search results:
```
💰 €500 → Market: €650 (save €150, 23% discount)
⭐ Great deal!
```

### Scheduler
Hook into `analyze_prices()` task to recalculate market analysis periodically

## Testing Checklist
- [ ] Find market analogs correctly for exact matches
- [ ] Fall back gracefully when no exact matches found
- [ ] Handle edge cases (brand not in DB, new models, etc.)
- [ ] Verify median calculation with sample data
- [ ] Test discount percentage calculation
- [ ] Verify API returns correct data
- [ ] Test Telegram bot integration

## Performance Considerations
- Analog search can be expensive (full table scan)
- Implement caching for frequently searched bikes
- Consider materialized view for historical prices
- Add index on (brand, model, year, size, date_posted)

## Success Metrics
- Each listing has accurate market baseline price
- Discount percentage calculated for profit analysis (Phase 3)
- API endpoints return market analysis data
- Telegram users see deal quality indicators
