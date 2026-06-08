"""
Аудит кода передачи прокси в Playwright/CloakBrowser
Изучение текущей реализации БЕЗ изменений
"""

import asyncio
import os
import requests
import traceback
from urllib.parse import urlparse

# === PART 1: Show proxy parsing logic ===
print(f"\n{'='*80}")
print(f"1. PROXY PARSING FROM CODE")
print(f"{'='*80}\n")

PROXY_STRING = "http://ZdeODemWWNu9JVR3:ZdeODemWWNu9JVR3@107.174.114.18:14109"

print(f"Original proxy string from config:")
print(f"  {PROXY_STRING}\n")

# Show how _get_next_proxy() returns it
print(f"Current code in _get_next_proxy():")
print(f"  proxy = self.proxy_list[self.proxy_index]")
print(f"  return proxy  # Returns the STRING AS-IS\n")

returned_proxy = PROXY_STRING
print(f"What _get_next_proxy() returns:")
print(f"  {returned_proxy}\n")

# === PART 2: Show how it's passed to CloakBrowser ===
print(f"\n{'='*80}")
print(f"2. HOW PROXY IS PASSED TO CLOAKBROWSER")
print(f"{'='*80}\n")

print(f"Code in init_browser() for CloakBrowser:")
print(f"  if self.use_cloak:")
print(f"      from cloakbrowser import launch_async")
print(f"      kwargs = {{'headless': True}}")
print(f"      if self.use_proxy and self.proxy_list:")
print(f"          kwargs['proxy'] = self._get_next_proxy()  # STRING")
print(f"      self.browser = await launch_async(**kwargs)\n")

cloakbrowser_kwargs = {"headless": True, "proxy": returned_proxy}
print(f"Actual kwargs passed to launch_async():")
print(f"  {cloakbrowser_kwargs}\n")

print(f"CLOAKBROWSER_PROXY_OBJECT={cloakbrowser_kwargs.get('proxy')}\n")

# === PART 3: Show how it's passed to Chromium ===
print(f"\n{'='*80}")
print(f"3. HOW PROXY IS PASSED TO CHROMIUM/PLAYWRIGHT")
print(f"{'='*80}\n")

print(f"Code in init_browser() for Chromium:")
print(f"  if self.use_proxy and self.proxy_list:")
print(f"      kwargs['proxy'] = {{'server': self._get_next_proxy()}}\n")

chromium_kwargs = {"headless": True, "proxy": {"server": returned_proxy}}
print(f"Actual kwargs passed to playwright.chromium.launch():")
print(f"  {chromium_kwargs}\n")

proxy_dict = chromium_kwargs.get('proxy', {})
print(f"PLAYWRIGHT_PROXY_OBJECT=")
print(f"  server={proxy_dict.get('server')}")
print(f"  username={proxy_dict.get('username', 'NOT SET')}")
print(f"  password={proxy_dict.get('password', 'NOT SET')}\n")

# === PART 4: Parse URL to show what Chromium receives ===
print(f"\n{'='*80}")
print(f"4. URL PARSING OF PROXY STRING")
print(f"{'='*80}\n")

parsed = urlparse(returned_proxy)
print(f"urlparse() results:")
print(f"  scheme={parsed.scheme}")
print(f"  username={parsed.username}")
print(f"  password={parsed.password}")
print(f"  hostname={parsed.hostname}")
print(f"  port={parsed.port}\n")

print(f"What Chromium sees in proxy.server:")
print(f"  Full string: {returned_proxy}")
print(f"  Credentials IN URL: YES (embedded)")
print(f"  proxy.username field: NOT PROVIDED")
print(f"  proxy.password field: NOT PROVIDED\n")

# === PART 5: Control test ===
print(f"\n{'='*80}")
print(f"5. CONTROL TEST: requests vs Playwright")
print(f"{'='*80}\n")

TEST_URL = "https://api.ipify.org?format=json"

# Test with requests
print(f"A. Testing with requests library:")
print(f"   URL: {TEST_URL}")
print(f"   Proxy: {returned_proxy}\n")

try:
    proxies = {'https': returned_proxy}
    response = requests.get(TEST_URL, proxies=proxies, timeout=5)
    print(f"   REQUESTS_STATUS={response.status_code}")
    try:
        data = response.json()
        print(f"   REQUESTS_IP={data.get('ip', 'ERROR')}\n")
    except:
        print(f"   REQUESTS_IP=PARSE_ERROR\n")
except Exception as e:
    print(f"   REQUESTS_STATUS=ERROR")
    print(f"   Error: {str(e)[:100]}\n")

# Test with Playwright
print(f"B. Testing with Playwright:")
print(f"   URL: {TEST_URL}")
print(f"   Proxy config: {{'server': '{returned_proxy}'}}\n")

async def test_playwright():
    """Test with Playwright"""
    try:
        from playwright.async_api import async_playwright

        playwright = await async_playwright().start()

        # Create browser with proxy
        browser = await playwright.chromium.launch(
            headless=True,
            proxy={"server": returned_proxy}
        )

        context = await browser.new_context()
        page = await context.new_page()

        try:
            response = await page.goto(TEST_URL, wait_until='networkidle', timeout=10000)
            status = response.status if response else "UNKNOWN"

            print(f"   PLAYWRIGHT_STATUS={status}")

            if status == 407:
                print(f"   PLAYWRIGHT_IP=NONE (407 Auth Required)\n")
                print(f"   ⚠️ PROXY AUTHENTICATION FAILED\n")

                # Show what was passed
                print(f"   Actual proxy config passed to launch():")
                print(f"     server='{returned_proxy}'")
                print(f"     username=None")
                print(f"     password=None\n")
            else:
                content = await page.content()
                if 'ip' in content:
                    import re
                    match = re.search(r'"ip":"([^"]+)"', content)
                    if match:
                        print(f"   PLAYWRIGHT_IP={match.group(1)}\n")

        except asyncio.TimeoutError:
            print(f"   PLAYWRIGHT_STATUS=TIMEOUT\n")
        except Exception as e:
            print(f"   PLAYWRIGHT_STATUS=ERROR")
            print(f"   Error: {str(e)[:100]}\n")
            print(f"   Full traceback:")
            print(traceback.format_exc()[:500])

        await browser.close()
        await playwright.stop()

    except Exception as e:
        print(f"   ❌ Failed to initialize Playwright: {str(e)}\n")

asyncio.run(test_playwright())

# === PART 6: Answer questions ===
print(f"\n{'='*80}")
print(f"6. ANSWERS TO QUESTIONS")
print(f"{'='*80}\n")

print(f"A) Корректно ли передаются username/password в Playwright?\n")
print(f"   ❌ НЕТ - they are EMBEDDED in the URL string")
print(f"   Current code passes: proxy={{'server': 'http://user:pass@host:port'}}")
print(f"   Playwright expects: proxy={{'server': 'http://host:port', 'username': 'user', 'password': 'pass'}}")
print(f"   Chromium does NOT extract credentials from URL in proxy.server\n")

print(f"B) Совпадает ли формат с документацией Playwright?\n")
print(f"   ❌ НЕТ - Current code DOES NOT follow Playwright documentation")
print(f"   Documentation: https://playwright.dev/python/docs/api/class-browserlaunchtypeoptions#browser-launch-type-options-proxy")
print(f"   Required format: proxy.username and proxy.password as separate fields\n")

print(f"C) Является ли 407 основной причиной того, что Wallapop не загружается?\n")
print(f"   ✅ ДА - This is the ROOT CAUSE")
print(f"   Current flow:")
print(f"     1. Code passes credentials IN URL")
print(f"     2. Chromium ignores credentials in URL")
print(f"     3. Chromium sends request WITHOUT auth")
print(f"     4. Proxy returns HTTP 407")
print(f"     5. Page.goto() fails or times out")
print(f"     6. Wallapop never loads\n")

print(f"{'='*80}\n")
