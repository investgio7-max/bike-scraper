"""
Диагностический скрипт для тестирования всех 3 прокси
Не изменяет основной парсер
"""

import asyncio
import time
import json
from datetime import datetime
from playwright.async_api import async_playwright

PROXIES = [
    ("http://ZdeODemWWNu9JVR3:ZdeODemWWNu9JVR3@107.174.114.18:14109", "Proxy #1 (107.174.114.18)"),
    ("http://knPTlBSAfKW37C8H:knPTlBSAfKW37C8H@37.143.131.235:12181", "Proxy #2 (37.143.131.235)"),
    ("http://y1gG6aKEG56SPffZ:y1gG6aKEG56SPffZ@185.186.76.222:10584", "Proxy #3 (185.186.76.222)"),
]

URLS = [
    ("https://www.google.com", "GOOGLE"),
    ("https://es.wallapop.com", "WALLAPOP"),
]

async def test_proxy(proxy_url, proxy_name):
    """Test single proxy"""
    print(f"\n{'='*80}")
    print(f"Testing: {proxy_name}")
    print(f"{'='*80}\n")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True, proxy={"server": proxy_url})
    context = await browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        locale="es-ES",
        timezone_id="Europe/Madrid",
    )
    page = await context.new_page()
    page.set_default_timeout(30000)
    page.set_default_navigation_timeout(30000)

    for test_url, url_name in URLS:
        print(f"\n>>> Testing {url_name}: {test_url}")
        print("-" * 80)

        try:
            start_time = time.time()

            # Measure navigation timing
            response = await page.goto(test_url, wait_until='networkidle', timeout=30000)

            load_time = time.time() - start_time

            # Get page info
            http_status = response.status if response else "UNKNOWN"
            final_url = page.url
            page_title = await page.title()

            print(f"HTTP_STATUS={http_status}")
            print(f"FINAL_URL={final_url}")
            print(f"PAGE_TITLE={page_title}")
            print(f"LOAD_TIME={load_time:.2f}s")

            # Get resource counts
            images = await page.evaluate('document.images.length')
            scripts = await page.evaluate('document.scripts.length')
            stylesheets = await page.evaluate('document.styleSheets.length')

            print(f"RESOURCES: images={images}, scripts={scripts}, stylesheets={stylesheets}")

            # Take screenshot
            screenshot_path = f"/tmp/{proxy_name.replace(' ', '_').replace('(', '').replace(')', '')}_{url_name}.png"
            await page.screenshot(path=screenshot_path)
            print(f"SCREENSHOT={screenshot_path}")

            # Get page content (first 5000 chars)
            html = await page.content()
            print(f"HTML_SIZE={len(html)}")
            print(f"HTML_FIRST_2000={html[:2000]}\n")

        except asyncio.TimeoutError as e:
            print(f"⏱️ TIMEOUT_ERROR: {str(e)[:100]}")

            # Get partial info
            try:
                final_url = page.url
                page_title = await page.title()
                images = await page.evaluate('document.images.length')
                scripts = await page.evaluate('document.scripts.length')
                stylesheets = await page.evaluate('document.styleSheets.length')

                print(f"FINAL_URL={final_url}")
                print(f"PAGE_TITLE={page_title}")
                print(f"PARTIAL_RESOURCES: images={images}, scripts={scripts}, stylesheets={stylesheets}")

                # Get page content despite timeout
                try:
                    html = await page.content()
                    print(f"HTML_SIZE={len(html)}")
                    print(f"HTML_FIRST_5000={html[:5000]}\n")
                except:
                    print("Could not get page content after timeout\n")

            except Exception as e2:
                print(f"Could not get partial info: {e2}\n")

        except Exception as e:
            print(f"❌ ERROR: {str(e)[:150]}\n")

    await browser.close()
    await playwright.stop()

async def main():
    """Test all proxies"""
    print(f"\n{'='*80}")
    print(f"PROXY DIAGNOSTIC TEST - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")

    for proxy_url, proxy_name in PROXIES:
        try:
            await test_proxy(proxy_url, proxy_name)
        except Exception as e:
            print(f"\n❌ Failed to test {proxy_name}: {e}\n")

    print(f"\n{'='*80}")
    print("Test completed")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(main())
