"""
Диагностика передачи прокси с авторизацией в браузер
"""

import asyncio
import json
import requests
from urllib.parse import urlparse

PROXIES = [
    "http://ZdeODemWWNu9JVR3:ZdeODemWWNu9JVR3@107.174.114.18:14109",
    "http://knPTlBSAfKW37C8H:knPTlBSAfKW37C8H@37.143.131.235:12181",
    "http://y1gG6aKEG56SPffZ:y1gG6aKEG56SPffZ@185.186.76.222:10584",
]

TEST_URL = "https://api.ipify.org?format=json"

async def test_proxy_config(proxy_url):
    """Test proxy configuration and transmission to browser"""

    print(f"\n{'='*80}")
    print(f"PROXY CONFIGURATION TEST")
    print(f"{'='*80}\n")

    # 1. Show proxy string
    print(f"1. PROXY STRING FROM CONFIG:")
    print(f"   {proxy_url}\n")

    # 2. Parse proxy
    parsed = urlparse(proxy_url)
    print(f"2. PARSED PROXY COMPONENTS:")
    print(f"   scheme={parsed.scheme}")
    print(f"   username={parsed.username}")
    print(f"   password={parsed.password}")
    print(f"   hostname={parsed.hostname}")
    print(f"   port={parsed.port}\n")

    # Show how it's passed to Playwright
    print(f"3. HOW PROXY IS PASSED TO PLAYWRIGHT:")
    print(f"   browser = await playwright.chromium.launch(")
    print(f"       headless=True,")
    print(f"       proxy={{'server': '{proxy_url}'}}")
    print(f"   )\n")

    # 4. Test with proxy via requests
    print(f"4. DIRECT REQUEST WITH PROXY (via requests library):")
    try:
        proxies_dict = {'https': proxy_url}
        response = requests.get(TEST_URL, proxies=proxies_dict, timeout=5)
        print(f"   WITH_PROXY_STATUS={response.status_code}")

        try:
            data = response.json()
            print(f"   WITH_PROXY_IP={data.get('ip', 'ERROR')}")
        except:
            print(f"   WITH_PROXY_IP=PARSE_ERROR")
            print(f"   Response body: {response.text[:500]}")
    except Exception as e:
        print(f"   WITH_PROXY_STATUS=ERROR")
        print(f"   Error: {str(e)[:100]}")

    print()

    # 5. Test without proxy
    print(f"5. DIRECT REQUEST WITHOUT PROXY (via requests library):")
    try:
        response = requests.get(TEST_URL, timeout=5)
        print(f"   WITHOUT_PROXY_STATUS={response.status_code}")

        try:
            data = response.json()
            print(f"   WITHOUT_PROXY_IP={data.get('ip', 'ERROR')}")
        except:
            print(f"   WITHOUT_PROXY_IP=PARSE_ERROR")
    except Exception as e:
        print(f"   WITHOUT_PROXY_STATUS=ERROR")
        print(f"   Error: {str(e)[:100]}")

    print()

    # 6. Test with Playwright
    print(f"6. BROWSER REQUEST WITH PROXY (via Playwright):")
    try:
        from playwright.async_api import async_playwright

        playwright = await async_playwright().start()

        # Test with proxy
        browser = await playwright.chromium.launch(
            headless=True,
            proxy={"server": proxy_url}
        )

        print(f"   Browser launched with proxy config:")
        print(f"   proxy={{'server': '{proxy_url}'}}")
        print()

        context = await browser.new_context()
        page = await context.new_page()

        try:
            response = await page.goto(TEST_URL, wait_until='networkidle', timeout=15000)
            print(f"   WITH_PROXY_STATUS={response.status if response else 'UNKNOWN'}")

            # Try to get JSON
            try:
                content = await page.content()
                # Extract IP from JSON response
                if 'ip' in content:
                    # Simple extraction
                    import re
                    match = re.search(r'"ip":"([^"]+)"', content)
                    if match:
                        print(f"   WITH_PROXY_IP={match.group(1)}")
                    else:
                        print(f"   WITH_PROXY_IP=PARSE_ERROR")
                else:
                    print(f"   WITH_PROXY_IP=NO_IP_IN_RESPONSE")
                    print(f"   Response content: {content[:500]}")
            except Exception as e:
                print(f"   WITH_PROXY_IP=ERROR: {str(e)[:50]}")

        except Exception as e:
            print(f"   WITH_PROXY_STATUS=ERROR")
            print(f"   Error: {str(e)[:100]}")

        await browser.close()
        await playwright.stop()

    except Exception as e:
        print(f"   ❌ Failed to test with Playwright: {str(e)[:100]}")

    print()

    # 7. Show proxy object details
    if response and response.status == 407:
        print(f"7. PROXY OBJECT DETAILS (407 ERROR DETECTED):")
        print(f"   Full proxy object passed to browser:")
        print(f"   {{'server': '{proxy_url}'}}")
        print(f"   ")
        print(f"   Note: If credentials are in URL, they should be:")
        print(f"   - Extracted by browser during proxy.server parsing")
        print(f"   - OR passed separately as proxy.username/proxy.password")
        print()


async def main():
    print(f"\n{'='*80}")
    print(f"PROXY AUTHENTICATION TEST")
    print(f"Checking if username/password are properly transmitted to browser")
    print(f"{'='*80}\n")

    for i, proxy_url in enumerate(PROXIES, 1):
        print(f"\n{'#'*80}")
        print(f"# PROXY #{i}")
        print(f"{'#'*80}")

        try:
            await test_proxy_config(proxy_url)
        except Exception as e:
            print(f"\n❌ Error testing proxy {i}: {str(e)[:200]}\n")


if __name__ == "__main__":
    asyncio.run(main())
