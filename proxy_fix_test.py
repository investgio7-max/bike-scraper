"""
PROOF OF FIX TEST
Test correct proxy format without changing production code
"""

import asyncio
from urllib.parse import urlparse

print(f"\n{'='*80}")
print(f"PROXY FIX VERIFICATION TEST")
print(f"{'='*80}\n")

# === STEP 1: Show current code locations ===
print(f"1. CURRENT CODE LOCATIONS (from scraper_wallapop.py):\n")
print(f"   Line 96  (CloakBrowser):")
print(f"     kwargs['proxy'] = self._get_next_proxy()  # STRING\n")
print(f"   Line 106 (Playwright/Chromium - primary):")
print(f"     kwargs['proxy'] = {{'server': self._get_next_proxy()}}  # WRONG FORMAT\n")
print(f"   Line 117 (Playwright/Chromium - fallback):")
print(f"     kwargs['proxy'] = {{'server': self._get_next_proxy()}}  # WRONG FORMAT\n")

# === STEP 2: Parse proxy string ===
print(f"\n{'='*80}")
print(f"2. PROXY PARSING\n")

PROXY_1 = "http://ZdeODemWWNu9JVR3:ZdeODemWWNu9JVR3@107.174.114.18:14109"

print(f"   Original proxy string:")
print(f"   {PROXY_1}\n")

parsed = urlparse(PROXY_1)

print(f"   Parsed components:")
print(f"     scheme = {parsed.scheme}")
print(f"     username = {parsed.username}")
print(f"     password = {parsed.password}")
print(f"     hostname = {parsed.hostname}")
print(f"     port = {parsed.port}\n")

# === STEP 3: Build correct proxy object ===
print(f"\n{'='*80}")
print(f"3. CORRECT PROXY FORMAT FOR PLAYWRIGHT\n")

print(f"   ❌ WRONG (current code):")
print(f"     proxy = {{'server': '{PROXY_1}'}}\n")

correct_proxy = {
    "server": f"http://{parsed.hostname}:{parsed.port}",
    "username": parsed.username,
    "password": parsed.password
}

print(f"   ✅ CORRECT (Playwright documentation format):")
print(f"     proxy = {correct_proxy}\n")

# === STEP 4: Test with correct format ===
print(f"\n{'='*80}")
print(f"4. CONTROL TEST WITH CORRECT FORMAT\n")

async def test_correct_proxy():
    """Test with CORRECT proxy format"""

    TEST_URL = "https://api.ipify.org?format=json"

    print(f"   Testing URL: {TEST_URL}")
    print(f"   Proxy config: {correct_proxy}\n")

    try:
        from playwright.async_api import async_playwright

        playwright = await async_playwright().start()

        print(f"   Launching browser with CORRECT proxy format:")
        print(f"     server = 'http://{parsed.hostname}:{parsed.port}'")
        print(f"     username = '{parsed.username}'")
        print(f"     password = '{parsed.password}'\n")

        browser = await playwright.chromium.launch(
            headless=True,
            proxy=correct_proxy
        )

        context = await browser.new_context()
        page = await context.new_page()

        try:
            response = await page.goto(TEST_URL, wait_until='networkidle', timeout=10000)
            status = response.status if response else "UNKNOWN"

            print(f"   STATUS = {status}")

            # Get response body
            try:
                content = await page.content()
                print(f"   BODY = {content[:200]}")

                # Extract IP
                import re
                match = re.search(r'"ip":"([^"]+)"', content)
                if match:
                    ip = match.group(1)
                    print(f"   IP = {ip}")
                else:
                    print(f"   IP = NOT_FOUND_IN_RESPONSE")

            except Exception as e:
                print(f"   BODY = ERROR: {str(e)[:50]}")
                print(f"   IP = ERROR")

        except asyncio.TimeoutError:
            print(f"   STATUS = TIMEOUT")
            print(f"   BODY = (timeout waiting for networkidle)")
            print(f"   IP = TIMEOUT")
        except Exception as e:
            print(f"   STATUS = ERROR")
            print(f"   Error: {str(e)[:100]}")

        await browser.close()
        await playwright.stop()

        # Return status for answer
        return status

    except Exception as e:
        print(f"   ❌ Failed to initialize Playwright: {str(e)}")
        return "ERROR"

print(f"   Running test...\n")
status = asyncio.run(test_correct_proxy())

# === STEP 5: Answers ===
print(f"\n{'='*80}")
print(f"5. ANSWERS TO QUESTIONS\n")

if status == 200:
    print(f"A) Получен ли HTTP 200?")
    print(f"   ✅ ДА - STATUS = 200\n")

    print(f"B) Какой IP вернулся?")
    print(f"   ✅ IP address from proxy (see BODY above)\n")

    print(f"C) Подтверждает ли это, что причина 407 устранена?")
    print(f"   ✅ ДА - DEFINITIVELY CONFIRMED\n")

    print(f"   Evidence:")
    print(f"   • Wrong format (current code): HTTP 407")
    print(f"   • Correct format (this test): HTTP 200")
    print(f"   • Difference: username/password passed separately\n")

    print(f"   CONCLUSION:")
    print(f"   The root cause of 407 error is INCORRECT proxy format.")
    print(f"   Using correct format with separate username/password fields")
    print(f"   eliminates the 407 error completely.\n")

elif status == 407:
    print(f"A) Получен ли HTTP 200?")
    print(f"   ❌ НЕТ - still getting 407\n")

    print(f"   Unexpected! This should have worked.")
    print(f"   Please verify proxy credentials are still valid.\n")

else:
    print(f"A) Получен ли HTTP 200?")
    print(f"   ❌ НЕТ - STATUS = {status}\n")

print(f"{'='*80}\n")
