"""
Диагностический тест для сравнения разных URL через один прокси и Playwright
Без изменений в основной код
"""

import asyncio
import time
from playwright.async_api import async_playwright
from urllib.parse import urlparse

# Прокси из основного кода
PROXY_STRING = "http://knPTlBSAfKW37C8H:knPTlBSAfKW37C8H@37.143.131.235:12181"

# Парсим прокси в правильный формат для Playwright
parsed = urlparse(PROXY_STRING)
PROXY_DICT = {
    "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
    "username": parsed.username,
    "password": parsed.password
}

# URLs для теста
TEST_URLS = [
    "https://api.ipify.org?format=json",
    "https://google.com",
    "https://example.com",
    "https://es.wallapop.com/search?keywords=bicicleta+carretera&start=0",
]

async def test_url(url):
    """Тестировать один URL с полным логированием"""

    print(f"\n{'='*80}")
    print(f"TESTING: {url}")
    print(f"{'='*80}\n")

    # Инициализируем слушатели
    requests_list = []
    responses_list = []
    failed_list = []

    try:
        playwright = await async_playwright().start()

        browser = await playwright.chromium.launch(
            headless=True,
            proxy=PROXY_DICT
        )

        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            locale="es-ES",
            timezone_id="Europe/Madrid",
        )

        page = await context.new_page()

        # Настраиваем слушатели
        async def on_request(request):
            requests_list.append({
                'url': request.url,
                'method': request.method,
                'timestamp': time.time()
            })
            print(f"  [REQUEST] {request.method} {request.url[:80]}")

        async def on_response(response):
            responses_list.append({
                'url': response.url,
                'status': response.status,
                'timestamp': time.time()
            })
            print(f"  [RESPONSE] {response.status} {response.url[:80]}")

        async def on_request_failed(request):
            failed_list.append({
                'url': request.url,
                'failure': request.failure.error_text if request.failure else 'UNKNOWN',
                'timestamp': time.time()
            })
            print(f"  [REQUEST_FAILED] {request.url[:80]}")
            if request.failure:
                print(f"    ERROR: {request.failure.error_text}")

        page.on('request', on_request)
        page.on('response', on_response)
        page.on('requestfailed', on_request_failed)

        # Пытаемся загрузить страницу
        start_time = time.time()

        try:
            response = await page.goto(url, wait_until='networkidle', timeout=15000)
            load_time = time.time() - start_time

            status = response.status if response else "UNKNOWN"
            final_url = page.url
            page_title = await page.title()

        except asyncio.TimeoutError:
            load_time = time.time() - start_time
            status = "TIMEOUT"
            final_url = page.url
            page_title = await page.title()
            print(f"\n  ⏱️ TIMEOUT after {load_time:.2f}s (waiting for networkidle)")

        except Exception as e:
            load_time = time.time() - start_time
            status = f"ERROR: {type(e).__name__}"
            final_url = page.url
            try:
                page_title = await page.title()
            except:
                page_title = "ERROR"
            print(f"\n  ❌ ERROR: {str(e)[:100]}")

        # === RESULTS ===
        print(f"\n--- RESULTS ---")
        print(f"URL={url}")
        print(f"STATUS={status}")
        print(f"FINAL_URL={final_url}")
        print(f"PAGE_TITLE={page_title}")
        print(f"LOAD_TIME={load_time:.2f}s")

        print(f"\n--- NETWORK EVENTS ---")
        print(f"REQUEST_COUNT={len(requests_list)}")
        print(f"RESPONSE_COUNT={len(responses_list)}")
        print(f"REQUEST_FAILED_COUNT={len(failed_list)}")

        if failed_list:
            print(f"\n--- FAILED REQUESTS ---")
            for failed in failed_list:
                print(f"FAILED_URL={failed['url'][:100]}")
                print(f"ERROR_TEXT={failed['failure']}")

        # === WALLAPOP-SPECIFIC ANALYSIS ===
        if 'wallapop' in url.lower():
            print(f"\n--- WALLAPOP-SPECIFIC ANALYSIS ---")
            print(f"REQUESTS_CREATED={len(requests_list) > 0}")
            print(f"RESPONSES_RECEIVED={len(responses_list) > 0}")
            print(f"REQUESTS_FAILED={len(failed_list) > 0}")

            # Пытаемся определить DNS resolve
            if len(requests_list) > 0:
                print(f"DNS_RESOLVED=YES (first request created)")
            else:
                print(f"DNS_RESOLVED=UNKNOWN (no requests created)")

        await browser.close()
        await playwright.stop()

        return {
            'url': url,
            'status': status,
            'load_time': load_time,
            'request_count': len(requests_list),
            'response_count': len(responses_list),
            'failed_count': len(failed_list)
        }

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        return None


async def main():
    print(f"\n{'='*80}")
    print(f"DIAGNOSTIC TEST - Playwright + Proxy + Multiple URLs")
    print(f"{'='*80}")
    print(f"\nPROXY: {PROXY_DICT['server']}")
    print(f"USERNAME: {PROXY_DICT['username']}")
    print(f"\nTesting URLs:")
    for url in TEST_URLS:
        print(f"  • {url}")

    results = []
    for url in TEST_URLS:
        result = await test_url(url)
        if result:
            results.append(result)

    # === SUMMARY ===
    print(f"\n\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}\n")

    for result in results:
        print(f"URL: {result['url'][:60]}")
        print(f"  STATUS={result['status']} | LOAD_TIME={result['load_time']:.2f}s")
        print(f"  REQUESTS={result['request_count']} | RESPONSES={result['response_count']} | FAILED={result['failed_count']}")
        print()

    # === ANSWERS ===
    print(f"\n{'='*80}")
    print(f"ANSWERS TO QUESTIONS")
    print(f"{'='*80}\n")

    # A) Работают ли через этот прокси другие сайты в Playwright?
    other_sites = [r for r in results if 'wallapop' not in r['url'].lower()]
    working_other_sites = [r for r in other_sites if r['response_count'] > 0]

    print(f"A) Работают ли через этот прокси другие сайты в Playwright?")
    if working_other_sites:
        print(f"   ✅ ДА - {len(working_other_sites)}/{len(other_sites)} сайтов работают")
        for r in working_other_sites:
            print(f"      • {r['url'][:60]} - STATUS={r['status']}")
    else:
        print(f"   ❌ НЕТ - никакие сайты не работают")

    # B) Проблема только у Wallapop или у всех сайтов?
    wallapop_results = [r for r in results if 'wallapop' in r['url'].lower()]
    if wallapop_results:
        wallapop = wallapop_results[0]

        print(f"\nB) Проблема только у Wallapop или у всех сайтов?")
        if wallapop['response_count'] == 0 and len(working_other_sites) > 0:
            print(f"   ✅ ТОЛЬКО У WALLAPOP")
            print(f"      • Wallapop: RESPONSES={wallapop['response_count']}")
            print(f"      • Другие сайты: RESPONSES={working_other_sites[0]['response_count'] if working_other_sites else 'N/A'}")
        elif wallapop['response_count'] == 0 and len(working_other_sites) == 0:
            print(f"   ❓ У ВСЕХ САЙТОВ")
            print(f"      • Ни один сайт не получил ответ")
        else:
            print(f"   ✅ РАБОТАЕТ И WALLAPOP")
            print(f"      • Wallapop: RESPONSES={wallapop['response_count']}")

    # C) Есть ли requestfailed события?
    total_failed = sum(r['failed_count'] for r in results)
    print(f"\nC) Есть ли requestfailed события?")
    if total_failed > 0:
        print(f"   ✅ ДА - всего {total_failed} failed requests")
        for r in results:
            if r['failed_count'] > 0:
                print(f"      • {r['url'][:60]} - {r['failed_count']} failed")
    else:
        print(f"   ❌ НЕТ - никаких failed requests")

    # D) Ошибки Chromium
    print(f"\nD) Конкретные ошибки Chromium (ERR_TUNNEL_CONNECTION_FAILED, ERR_PROXY_CONNECTION_FAILED и т.д.)?")
    # Это нужно будет вывести из предыдущих логов
    print(f"   (смотри детали в логах выше - ERROR_TEXT для каждого failed request)")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
