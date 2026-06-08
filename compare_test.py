"""
Сравнение LOCAL vs RAILWAY
Сбор фактов о версиях, параметрах и времени загрузки
"""

import asyncio
import time
from datetime import datetime
from playwright.async_api import async_playwright
from urllib.parse import urlparse

# Прокси
PROXY_STRING = "http://knPTlBSAfKW37C8H:knPTlBSAfKW37C8H@37.143.131.235:12181"
parsed = urlparse(PROXY_STRING)
PROXY_DICT = {
    "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
    "username": parsed.username,
    "password": parsed.password
}

# URL для тестирования
TEST_URL = "https://es.wallapop.com/search?keywords=bicicleta+carretera&start=0"

async def test_wallapop():
    """Тестировать Wallapop с полным измерением времени и версий"""

    print(f"\n{'='*80}")
    print(f"LOCAL ENVIRONMENT TEST")
    print(f"{'='*80}\n")

    # 1. Версии
    print(f"1. VERSIONS")
    print(f"{'='*80}\n")

    playwright = await async_playwright().start()

    # Версия Playwright
    try:
        from playwright import __version__ as pw_version
        print(f"LOCAL_PLAYWRIGHT_VERSION={pw_version}")
    except:
        print(f"LOCAL_PLAYWRIGHT_VERSION=UNKNOWN")

    # Версия Chromium (из браузера)
    try:
        temp_browser = await playwright.chromium.launch(headless=True)
        browser_version = await temp_browser.version
        print(f"LOCAL_CHROMIUM_VERSION={browser_version}")
        await temp_browser.close()
    except Exception as e:
        print(f"LOCAL_CHROMIUM_VERSION=ERROR: {e}")

    print()

    # 2. page.goto параметры
    print(f"2. PAGE.GOTO PARAMETERS")
    print(f"{'='*80}\n")

    GOTO_TIMEOUT = 30000
    GOTO_WAIT_UNTIL = 'networkidle'

    print(f"TEST_URL={TEST_URL}")
    print(f"PROXY_SERVER={PROXY_DICT['server']}")
    print(f"GOTO_TIMEOUT={GOTO_TIMEOUT}ms")
    print(f"GOTO_WAIT_UNTIL={GOTO_WAIT_UNTIL}")
    print()

    # 3. Запуск браузера и тестирование
    print(f"3. BROWSER LAUNCH AND PAGE LOAD")
    print(f"{'='*80}\n")

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
    page.set_default_timeout(GOTO_TIMEOUT)
    page.set_default_navigation_timeout(GOTO_TIMEOUT)

    # Слушатели для измерения времени
    page_load_events = {}

    async def on_domcontentloaded():
        page_load_events['domcontentloaded'] = time.time()

    async def on_load():
        page_load_events['load'] = time.time()

    page.on("domcontentloaded", on_domcontentloaded)
    page.on("load", on_load)

    # Слушатель для первого запроса
    first_request_time = None
    async def on_request(request):
        nonlocal first_request_time
        if first_request_time is None:
            first_request_time = time.time()
            print(f"[REQUEST] First request at T+{first_request_time - start_time:.3f}s: {request.url[:60]}")

    # Слушатель для первого ответа
    first_response_time = None
    async def on_response(response):
        nonlocal first_response_time
        if first_response_time is None:
            first_response_time = time.time()
            print(f"[RESPONSE] First response at T+{first_response_time - start_time:.3f}s: {response.status} {response.url[:60]}")

    page.on('request', on_request)
    page.on('response', on_response)

    # Начало тестирования
    start_time = time.time()
    print(f"GOTO_START_TIME={datetime.now().isoformat()}")
    print(f"GOTO_START_TIMESTAMP={start_time}\n")

    try:
        response = await page.goto(TEST_URL, wait_until=GOTO_WAIT_UNTIL, timeout=GOTO_TIMEOUT)

        goto_end_time = time.time()
        goto_duration = goto_end_time - start_time

        print(f"\n✅ GOTO SUCCESS")
        print(f"GOTO_END_TIME={datetime.now().isoformat()}")
        print(f"GOTO_DURATION={goto_duration:.3f}s\n")

        # Получить финальные данные
        final_url = page.url
        page_title = await page.title()
        html_content = await page.content()
        html_length = len(html_content)

        print(f"4. PAGE DETAILS AFTER LOAD")
        print(f"{'='*80}\n")

        print(f"FINAL_URL={final_url}")
        print(f"PAGE_TITLE={page_title}")
        print(f"HTML_LENGTH={html_length}")
        print()

        # Временные метки
        print(f"5. TIMING MEASUREMENTS")
        print(f"{'='*80}\n")

        print(f"T_GOTO_START={start_time:.3f}")

        if first_request_time:
            print(f"T_FIRST_REQUEST={first_request_time:.3f} (T+{first_request_time - start_time:.3f}s)")
        else:
            print(f"T_FIRST_REQUEST=NONE")

        if first_response_time:
            print(f"T_FIRST_RESPONSE={first_response_time:.3f} (T+{first_response_time - start_time:.3f}s)")
        else:
            print(f"T_FIRST_RESPONSE=NONE")

        if 'domcontentloaded' in page_load_events:
            t = page_load_events['domcontentloaded']
            print(f"T_DOMCONTENTLOADED={t:.3f} (T+{t - start_time:.3f}s)")
        else:
            print(f"T_DOMCONTENTLOADED=NOT FIRED")

        if 'load' in page_load_events:
            t = page_load_events['load']
            print(f"T_LOAD={t:.3f} (T+{t - start_time:.3f}s)")
        else:
            print(f"T_LOAD=NOT FIRED")

        print(f"T_NETWORKIDLE={goto_end_time:.3f} (T+{goto_duration:.3f}s)")
        print()

        # Ответы на вопросы
        print(f"6. ANSWERS")
        print(f"{'='*80}\n")

        print(f"A) Настройки page.goto одинаковые?")
        print(f"   LOCAL: timeout={GOTO_TIMEOUT}ms | wait_until={GOTO_WAIT_UNTIL}")
        print(f"   RAILWAY: timeout=30000ms | wait_until=networkidle (из логов)")
        print(f"   ✅ ОДИНАКОВЫЕ\n")

        print(f"B) Версии Chromium одинаковые?")
        print(f"   (сравнить с RAILWAY_CHROMIUM_VERSION)\n")

        print(f"C) На каком именно этапе Railway зависает?")
        print(f"   LOCAL: успешно загружается за {goto_duration:.3f}s")
        print(f"   RAILWAY: зависает на 30s (из логов - GOTO_START в 18:26:10, TIMEOUT в 18:26:40)\n")

        print(f"D) Получает ли Railway хоть один response до timeout?")
        print(f"   LOCAL: T_FIRST_REQUEST={first_request_time - start_time:.3f}s, T_FIRST_RESPONSE={first_response_time - start_time:.3f}s")
        if first_request_time and first_response_time:
            print(f"   RAILWAY: REQUESTS_CAPTURED_BEFORE_GOTO=0 (из логов) ❌ NO REQUESTS AT ALL\n")

    except asyncio.TimeoutError:
        timeout_time = time.time()
        timeout_duration = timeout_time - start_time

        print(f"\n❌ TIMEOUT after {timeout_duration:.3f}s")
        print(f"TIMEOUT_END_TIME={datetime.now().isoformat()}\n")

        final_url = page.url
        try:
            page_title = await page.title()
        except:
            page_title = "ERROR"

        try:
            html_content = await page.content()
            html_length = len(html_content)
        except:
            html_length = 0

        print(f"4. PAGE DETAILS AFTER TIMEOUT")
        print(f"{'='*80}\n")

        print(f"FINAL_URL={final_url}")
        print(f"PAGE_TITLE={page_title}")
        print(f"HTML_LENGTH={html_length}")
        print()

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)[:200]}")

    await browser.close()
    await playwright.stop()

    print(f"\n{'='*80}")
    print(f"LOCAL TEST COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(test_wallapop())
