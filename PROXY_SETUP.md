# Proxy Configuration Guide

## Proxies Added

```
PROXY_1: ZdeODemWWNu9JVR3:ZdeODemWWNu9JVR3@107.174.114.18:14109
PROXY_2: knPTlBSAfKW37C8H:knPTlBSAfKW37C8H@37.143.131.235:12181
PROXY_3: y1gG6aKEG56SPffZ:y1gG6aKEG56SPffZ@185.186.76.222:10584
```

## Installation

### Option 1: Local Development (with .env file)

Create `.env` file in project root:

```bash
PROXY_1=ZdeODemWWNu9JVR3:ZdeODemWWNu9JVR3@107.174.114.18:14109
PROXY_2=knPTlBSAfKW37C8H:knPTlBSAfKW37C8H@37.143.131.235:12181
PROXY_3=y1gG6aKEG56SPffZ:y1gG6aKEG56SPffZ@185.186.76.222:10584
```

Then load with dotenv:

```python
from dotenv import load_dotenv
load_dotenv()
```

### Option 2: Production (Railway Environment Variables)

```bash
# Set all proxies at once
railway variable set \
  PROXY_1="ZdeODemWWNu9JVR3:ZdeODemWWNu9JVR3@107.174.114.18:14109" \
  PROXY_2="knPTlBSAfKW37C8H:knPTlBSAfKW37C8H@37.143.131.235:12181" \
  PROXY_3="y1gG6aKEG56SPffZ:y1gG6aKEG56SPffZ@185.186.76.222:10584" \
  --service bike-scraper-api

# Or set individually:
railway variable set PROXY_1="ZdeODemWWNu9JVR3:ZdeODemWWNu9JVR3@107.174.114.18:14109" --service bike-scraper-api
railway variable set PROXY_2="knPTlBSAfKW37C8H:knPTlBSAfKW37C8H@37.143.131.235:12181" --service bike-scraper-api
railway variable set PROXY_3="y1gG6aKEG56SPffZ:y1gG6aKEG56SPffZ@185.186.76.222:10584" --service bike-scraper-api

# Restart service
railway restart --service bike-scraper-api
```

## Features

### Automatic Proxy Rotation

The system automatically rotates through available proxies:

- **Cycle 1**: PROXY_1
- **Cycle 2**: PROXY_2
- **Cycle 3**: PROXY_3
- **Cycle 4**: PROXY_1 (repeats)

```python
# Each search cycle uses next proxy in rotation
scraper = WallapopScraper(use_proxy=True)
await scraper.search_async("bicicleta carretera", max_results=100)
```

### Logging

Proxy usage is logged:

```
✅ Загружен proxy 1: 107.174.114.18:14109
✅ Загружен proxy 2: 37.143.131.235:12181
✅ Загружен proxy 3: 185.186.76.222:10584
📍 Используется proxy: 1/3
```

## Usage

### With Proxy (Default)

```python
from bike_scraper.scraper_wallapop import WallapopScraper

# Automatic proxy rotation enabled
scraper = WallapopScraper(use_proxy=True)
listings = await scraper.search_async("bicicleta carretera")
```

### Without Proxy

```python
# Direct connection (no proxy)
scraper = WallapopScraper(use_proxy=False)
listings = await scraper.search_async("bicicleta carretera")
```

## Testing

### Test Proxy Configuration

```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()

for i in range(1, 4):
    proxy = os.getenv(f'PROXY_{i}')
    if proxy:
        print(f'✅ PROXY_{i}: {proxy}')
    else:
        print(f'❌ PROXY_{i}: Not set')
"
```

### Test Scraper with Proxies

```bash
python3 -c "
import asyncio
from bike_scraper.scraper_wallapop import WallapopScraper

async def test():
    scraper = WallapopScraper(use_proxy=True)
    listings = await scraper.search_async('bicicleta', max_results=1)
    print(f'✅ Found {len(listings)} listings')
    if listings:
        print(f'   Title: {listings[0].title}')

asyncio.run(test())
"
```

## Benefits

✅ **Rate Limiting Prevention** - Distributes requests across proxies  
✅ **IP Ban Avoidance** - Rotates IPs to avoid blocking  
✅ **Increased Reliability** - Falls back if one proxy fails  
✅ **Better Scraping Speed** - Parallel requests possible  
✅ **Geographic Distribution** - Access from different locations  

## Troubleshooting

### Issue: Proxy not detected

**Check:**
```bash
# Verify environment variables
echo $PROXY_1
echo $PROXY_2
echo $PROXY_3
```

### Issue: Connection timeout with proxy

**Check:**
- Proxy IP and port are correct
- Username and password are correct
- Proxy is not blocked by Wallapop
- Network connectivity

### Issue: Slow performance with proxy

- Try without proxy (`use_proxy=False`)
- Check proxy server latency
- Rotate to different proxy

## Configuration in Code

If you want to enable/disable proxies globally:

```python
# bike_scraper/config.py
USE_PROXIES = True  # Set to False to disable

# Usage
scraper = WallapopScraper(use_proxy=USE_PROXIES)
```

## Security

⚠️ **Important**:
- Never commit proxy credentials to git
- Use environment variables (Railway or .env)
- Don't share proxy URLs publicly
- Rotate credentials periodically

## Next Steps

1. ✅ Set proxies in Railway (or .env for local testing)
2. ✅ Restart service: `railway restart --service bike-scraper-api`
3. ✅ Test with: `python3 quick_e2e_demo.py`
4. ✅ Run validation: `python3 real_market_validation.py`

---

**Ready to use proxies for improved scraping performance! 🚀**
