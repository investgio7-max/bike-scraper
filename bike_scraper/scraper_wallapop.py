"""
Парсер для Wallapop (Испания)
Использует CloakBrowser + Playwright для обработки JavaScript контента
"""

from typing import List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import re
import asyncio
import os
import time
from playwright.async_api import async_playwright

from bike_scraper.scraper_base import BaseScraper, ListingData
from bike_scraper.config import WALLAPOP_SEARCH_URL, MIN_PRICE, MAX_PRICE
from bike_scraper.utils_parser import BikeParser, normalize_price, parse_location
from bike_scraper.utils_logger import get_logger

logger = get_logger('wallapop')


class WallapopScraper(BaseScraper):
    """Парсер для Wallapop с поддержкой CloakBrowser + Playwright + Proxy rotation"""

    def __init__(self, use_cloak: bool = True, use_proxy: bool = True):
        super().__init__('wallapop')
        self.base_url = WALLAPOP_SEARCH_URL
        self.use_cloak = use_cloak
        self.use_proxy = use_proxy
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.proxy_list = self._load_proxies()
        self.proxy_index = 0

    def _load_proxies(self) -> List[str]:
        """Загрузить proxies из environment variables или использовать значения по умолчанию"""
        default_proxies = [
            "ZdeODemWWNu9JVR3:ZdeODemWWNu9JVR3@107.174.114.18:14109",
            "knPTlBSAfKW37C8H:knPTlBSAfKW37C8H@37.143.131.235:12181",
            "y1gG6aKEG56SPffZ:y1gG6aKEG56SPffZ@185.186.76.222:10584"
        ]

        proxies = []
        for i in range(1, 4):
            proxy_var = f"PROXY_{i}"
            proxy = os.getenv(proxy_var)

            # Если не найден в env, используем значение по умолчанию
            if not proxy and i <= len(default_proxies):
                proxy = default_proxies[i - 1]

            if proxy:
                # Format: user:pass@ip:port -> http://user:pass@ip:port
                if not proxy.startswith("http"):
                    proxy = f"http://{proxy}"
                proxies.append(proxy)
                ip_port = proxy.split('@')[1] if '@' in proxy else proxy[:30]
                logger.info(f"✅ Загружен proxy {i}: {ip_port}")

        if proxies:
            logger.info(f"🔄 Proxy rotation ENABLED ({len(proxies)} proxies)")
        else:
            logger.warning(f"⚠️ Proxy rotation DISABLED (no proxies configured)")

        return proxies

    def _get_next_proxy(self) -> Optional[str]:
        """Получить следующий proxy из списка (ротация) - для CloakBrowser"""
        if not self.proxy_list:
            logger.warning("⚠️ No proxy available - using direct connection")
            return None

        current_index = self.proxy_index % len(self.proxy_list)
        proxy = self.proxy_list[current_index]
        self.proxy_index += 1

        ip_port = proxy.split('@')[1] if '@' in proxy else proxy[:30]
        logger.info(f"📍 Using proxy: {current_index + 1}/{len(self.proxy_list)} ({ip_port})")
        return proxy

    def _get_next_proxy_dict(self) -> Optional[dict]:
        """Получить следующий proxy в формате Playwright (с отдельными username/password)"""
        if not self.proxy_list:
            return None

        current_index = self.proxy_index % len(self.proxy_list)
        proxy_str = self.proxy_list[current_index]
        self.proxy_index += 1

        # Parse proxy string: http://user:pass@host:port
        from urllib.parse import urlparse
        parsed = urlparse(proxy_str)

        proxy_dict = {
            "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
            "username": parsed.username,
            "password": parsed.password
        }

        ip_port = f"{parsed.hostname}:{parsed.port}"
        logger.info(f"📍 Using proxy: {current_index + 1}/{len(self.proxy_list)} ({ip_port}) with credentials")

        return proxy_dict

    async def init_browser(self):
        """Инициализировать браузер (CloakBrowser с humanize или Chromium)"""
        if self.page:
            return  # Уже инициализирован

        try:
            # Используем CloakBrowser Python пакет
            if self.use_cloak:
                from cloakbrowser import launch_async

                # Параметры для CloakBrowser с proxy
                kwargs = {"headless": True}
                if self.use_proxy and self.proxy_list:
                    kwargs["proxy"] = self._get_next_proxy()

                self.browser = await launch_async(**kwargs)
                logger.info("✅ CloakBrowser (stealth) запущен")
            else:
                self.playwright = await async_playwright().start()

                # Параметры для Chromium с proxy
                kwargs = {"headless": True}
                if self.use_proxy and self.proxy_list:
                    kwargs["proxy"] = self._get_next_proxy_dict()

                self.browser = await self.playwright.chromium.launch(**kwargs)
                logger.info("✅ Chromium запущен")

        except Exception as e:
            logger.warning(f"⚠️ CloakBrowser недоступен, используем Chromium: {e}")
            self.playwright = await async_playwright().start()

            kwargs = {"headless": True}
            if self.use_proxy and self.proxy_list:
                kwargs["proxy"] = self._get_next_proxy_dict()

            self.browser = await self.playwright.chromium.launch(**kwargs)

        # Создать страницу
        try:
            # Для CloakBrowser
            self.page = await self.browser.new_page()
        except:
            # Для обычного Chromium через Playwright
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                viewport={"width": 1920, "height": 1080},
                locale="es-ES",
                timezone_id="Europe/Madrid",
            )
            await self.context.set_extra_http_headers({
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            })
            self.page = await self.context.new_page()

        self.page.set_default_timeout(30000)
        self.page.set_default_navigation_timeout(30000)

        logger.info("✅ Страница браузера инициализирована")

    async def search_async(self, search_term: str, max_results: int = 100) -> List[ListingData]:
        """
        Асинхронный поиск велосипедов на Wallapop с использованием CloakBrowser
        """
        await self.init_browser()

        # === PROXY VERIFICATION (only once) ===
        if not hasattr(self, '_proxy_verified'):
            self._proxy_verified = True
            proxy_ip = self._get_next_proxy()
            if proxy_ip:
                proxy_ip_display = proxy_ip.split('@')[1] if '@' in proxy_ip else proxy_ip[:30]
                logger.info(f"🔐 PROXY_SELECTED={proxy_ip_display}")

                try:
                    # Check public IP via ipify
                    await self.page.goto('https://api.ipify.org?format=json', wait_until='networkidle', timeout=15000)
                    ipify_json_str = await self.page.evaluate('document.body.innerText')
                    import json
                    ipify_data = json.loads(ipify_json_str)
                    public_ip = ipify_data.get('ip', 'UNKNOWN')
                    logger.info(f"📍 PUBLIC_IP={public_ip}")
                except Exception as e:
                    logger.warning(f"⚠️ ipify check failed: {e}")
                    public_ip = 'ERROR'

                try:
                    # Check IP details via ipinfo.io
                    await self.page.goto('https://ipinfo.io/json', wait_until='networkidle', timeout=15000)
                    ipinfo_json_str = await self.page.evaluate('document.body.innerText')
                    import json
                    ipinfo_data = json.loads(ipinfo_json_str)

                    ip = ipinfo_data.get('ip', 'UNKNOWN')
                    country = ipinfo_data.get('country', 'UNKNOWN')
                    region = ipinfo_data.get('region', 'UNKNOWN')
                    city = ipinfo_data.get('city', 'UNKNOWN')
                    org = ipinfo_data.get('org', 'UNKNOWN')

                    logger.info(f"🌍 IP={ip}")
                    logger.info(f"🌎 COUNTRY={country}")
                    logger.info(f"🗺️ REGION={region}")
                    logger.info(f"🏙️ CITY={city}")
                    logger.info(f"🏢 ORG={org}")

                    if country:
                        logger.info(f"✅ PROXY_VERIFICATION_COMPLETE: {country} ({city})")
                except Exception as e:
                    logger.warning(f"⚠️ ipinfo check failed: {e}")

        logger.info(f"🔍 Ищу '{search_term}' на Wallapop (CloakBrowser)...")

        all_results = []
        seen_listing_ids = set()
        raw_items_processed = 0
        duplicates_skipped = 0
        page = 0
        consecutive_no_new_items = 0
        max_pages = 20  # Prevent infinite loops

        while len(all_results) < max_results and page < max_pages:
            try:
                # URL с параметрами поиска
                url = f"{self.base_url}?keywords={search_term.replace(' ', '+')}&start={page * 50}"

                logger.debug(f"📄 Загружаю страницу {page + 1}: {url}")

                # Загружаем страницу через браузер
                # Перехватываем все сетевые запросы
                requests_log = []
                json_responses = []
                requests_by_time = []  # Для отслеживания времени запросов
                start_goto_time = None

                async def on_request(request):
                    """Логируем каждый запрос с временем"""
                    nonlocal start_goto_time
                    if start_goto_time is None:
                        start_goto_time = time.time()

                    elapsed = time.time() - start_goto_time
                    resource_type = request.resource_type
                    req_url = request.url

                    requests_by_time.append({
                        'timestamp': elapsed,
                        'method': request.method,
                        'url': req_url,
                        'resource_type': resource_type,
                        'status': None  # Будет заполнено в on_response
                    })

                async def on_response(response):
                    nonlocal start_goto_time
                    if start_goto_time is None:
                        start_goto_time = time.time()

                    elapsed = time.time() - start_goto_time
                    try:
                        request = response.request
                        req_url = request.url
                        method = request.method
                        status = response.status
                        content_type = response.headers.get('content-type', '')
                        resource_type = request.resource_type

                        # Пытаемся получить размер ответа
                        try:
                            response_body = await response.text()
                            response_size = len(response_body)
                        except:
                            response_body = None
                            response_size = 0

                        requests_log.append({
                            'url': req_url,
                            'method': method,
                            'status': status,
                            'content_type': content_type,
                            'size': response_size,
                            'body': response_body,
                            'resource_type': resource_type,
                            'timestamp': elapsed
                        })

                        # Логируем JSON ответы с нужными ключевыми словами
                        keywords = ['api', 'search', 'items', 'listings', 'graphql', 'feed', 'catalog', 'ads', 'results']
                        if any(kw in req_url.lower() for kw in keywords):
                            if 'application/json' in content_type:
                                json_responses.append({
                                    'url': req_url,
                                    'status': status,
                                    'size': response_size,
                                    'body': response_body[:1000] if response_body else ''
                                })
                    except:
                        pass

                self.page.on('request', on_request)
                self.page.on('response', on_response)

                # === DIAGNOSTICS: Page load attempt ===
                start_goto_time = time.time()
                logger.info(f"📡 GOTO_ATTEMPT: {url}")
                logger.info(f"📡 GOTO_TIMEOUT=30000ms | WAIT_UNTIL=domcontentloaded")
                logger.info(f"📡 REQUESTS_CAPTURED_BEFORE_GOTO={len(requests_log)}")

                try:
                    await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    logger.info(f"✅ GOTO_SUCCESS")
                except TimeoutError as e:
                    logger.error(f"❌ GOTO_TIMEOUT: {str(e)[:200]}")

                    # === DETAILED NETWORK DIAGNOSTICS ===
                    total_requests = len(requests_log)
                    logger.info(f"📡 TOTAL_REQUESTS={total_requests}")

                    # Count responses by status
                    response_statuses = {}
                    for req in requests_log:
                        status = req.get('status')
                        if status not in response_statuses:
                            response_statuses[status] = 0
                        response_statuses[status] += 1

                    total_responses = sum(response_statuses.values())
                    logger.info(f"📡 TOTAL_RESPONSES={total_responses}")
                    logger.info(f"📡 RESPONSE_STATUSES={response_statuses}")

                    # Analyze resource types
                    resource_types = {}
                    for req in requests_log:
                        rt = req.get('resource_type', 'unknown')
                        if rt not in resource_types:
                            resource_types[rt] = 0
                        resource_types[rt] += 1
                    logger.info(f"📡 RESOURCE_TYPES={resource_types}")

                    # Find requests after 25 seconds
                    requests_after_25s = [r for r in requests_log if r.get('timestamp', 0) > 25.0]
                    logger.info(f"📡 REQUESTS_AFTER_25S={len(requests_after_25s)}")

                    if requests_after_25s:
                        logger.info(f"📡 URLS_GENERATING_REQUESTS_AFTER_25S:")
                        urls_after_25s = {}
                        for req in requests_after_25s:
                            url = req.get('url', 'unknown')
                            if url not in urls_after_25s:
                                urls_after_25s[url] = 0
                            urls_after_25s[url] += 1

                        for url, count in sorted(urls_after_25s.items()):
                            logger.info(f"  [{count}] {url[:150]}")

                    # Check for long-polling, websocket, eventsource, etc
                    suspicious_patterns = {
                        'websocket': [],
                        'eventsource': [],
                        'beacon': [],
                        'long_polling': [],
                        'graphql': [],
                        'analytics': [],
                        'tracking': []
                    }

                    for req in requests_log:
                        url_lower = req.get('url', '').lower()
                        rt = req.get('resource_type', '').lower()

                        if 'websocket' in rt or 'ws://' in url_lower or 'wss://' in url_lower:
                            suspicious_patterns['websocket'].append(req)
                        elif 'eventsource' in rt:
                            suspicious_patterns['eventsource'].append(req)
                        elif 'beacon' in rt or url_lower.endswith('/beacon'):
                            suspicious_patterns['beacon'].append(req)
                        elif 'graphql' in url_lower and req.get('timestamp', 0) > 25.0:
                            suspicious_patterns['graphql'].append(req)
                        elif 'analytics' in url_lower or 'tracking' in url_lower:
                            suspicious_patterns['analytics'].append(req)
                        elif any(x in url_lower for x in ['/poll', '/polling', '/long-poll', '/stream']):
                            suspicious_patterns['long_polling'].append(req)

                    for pattern, reqs in suspicious_patterns.items():
                        if reqs:
                            logger.info(f"📡 {pattern.upper()}_FOUND: {len(reqs)} requests")
                            for req in reqs[:5]:  # Log first 5
                                logger.info(f"  {req.get('method')} {req.get('url')[:100]} @ T+{req.get('timestamp', 0):.1f}s")

                    # Log last 50 requests before timeout
                    logger.info(f"📡 LAST_50_REQUESTS_BEFORE_TIMEOUT:")
                    last_requests = requests_log[-50:] if len(requests_log) > 50 else requests_log
                    for idx, req in enumerate(last_requests[-50:], start=max(1, len(requests_log)-49)):
                        logger.info(f"  [{idx}] {req.get('method')} {req.get('status')} {req.get('resource_type')} {req.get('url')[:100]} @ T+{req.get('timestamp', 0):.1f}s")

                    # Continue anyway to see what loaded
                    logger.warning(f"⚠️ Continuing despite timeout...")
                except Exception as e:
                    logger.error(f"❌ GOTO_ERROR: {type(e).__name__}: {str(e)[:200]}")

                    # === DETAILED NETWORK DIAGNOSTICS (if TimeoutError caught here) ===
                    if 'TimeoutError' in type(e).__name__:
                        total_requests = len(requests_log)
                        logger.info(f"📡 TOTAL_REQUESTS={total_requests}")

                        # Count responses by status
                        response_statuses = {}
                        for req in requests_log:
                            status = req.get('status')
                            if status not in response_statuses:
                                response_statuses[status] = 0
                            response_statuses[status] += 1

                        total_responses = sum(response_statuses.values())
                        logger.info(f"📡 TOTAL_RESPONSES={total_responses}")
                        logger.info(f"📡 RESPONSE_STATUSES={response_statuses}")

                        # Analyze resource types
                        resource_types = {}
                        for req in requests_log:
                            rt = req.get('resource_type', 'unknown')
                            if rt not in resource_types:
                                resource_types[rt] = 0
                            resource_types[rt] += 1
                        logger.info(f"📡 RESOURCE_TYPES={resource_types}")

                        # Find requests after 25 seconds
                        requests_after_25s = [r for r in requests_log if r.get('timestamp', 0) > 25.0]
                        logger.info(f"📡 REQUESTS_AFTER_25S={len(requests_after_25s)}")

                        if requests_after_25s:
                            logger.info(f"📡 URLS_GENERATING_REQUESTS_AFTER_25S:")
                            urls_after_25s = {}
                            for req in requests_after_25s:
                                url = req.get('url', 'unknown')
                                if url not in urls_after_25s:
                                    urls_after_25s[url] = 0
                                urls_after_25s[url] += 1

                            for url, count in sorted(urls_after_25s.items()):
                                logger.info(f"  [{count}] {url[:150]}")

                        # Check for long-polling, websocket, eventsource, etc
                        suspicious_patterns = {
                            'websocket': [],
                            'eventsource': [],
                            'beacon': [],
                            'long_polling': [],
                            'graphql': [],
                            'analytics': [],
                            'tracking': []
                        }

                        for req in requests_log:
                            url_lower = req.get('url', '').lower()
                            rt = req.get('resource_type', '').lower()

                            if 'websocket' in rt or 'ws://' in url_lower or 'wss://' in url_lower:
                                suspicious_patterns['websocket'].append(req)
                            elif 'eventsource' in rt:
                                suspicious_patterns['eventsource'].append(req)
                            elif 'beacon' in rt or url_lower.endswith('/beacon'):
                                suspicious_patterns['beacon'].append(req)
                            elif 'graphql' in url_lower and req.get('timestamp', 0) > 25.0:
                                suspicious_patterns['graphql'].append(req)
                            elif 'analytics' in url_lower or 'tracking' in url_lower:
                                suspicious_patterns['analytics'].append(req)
                            elif any(x in url_lower for x in ['/poll', '/polling', '/long-poll', '/stream']):
                                suspicious_patterns['long_polling'].append(req)

                        for pattern, reqs in suspicious_patterns.items():
                            if reqs:
                                logger.info(f"📡 {pattern.upper()}_FOUND: {len(reqs)} requests")
                                for req in reqs[:5]:  # Log first 5
                                    logger.info(f"  {req.get('method')} {req.get('url')[:100]} @ T+{req.get('timestamp', 0):.1f}s")

                        # Log last 50 requests before timeout
                        logger.info(f"📡 LAST_50_REQUESTS_BEFORE_TIMEOUT:")
                        last_requests = requests_log[-50:] if len(requests_log) > 50 else requests_log
                        for idx, req in enumerate(last_requests[-50:], start=max(1, len(requests_log)-49)):
                            logger.info(f"  [{idx}] {req.get('method')} {req.get('status')} {req.get('resource_type')} {req.get('url')[:100]} @ T+{req.get('timestamp', 0):.1f}s")
                    else:
                        logger.info(f"📡 REQUESTS_CAPTURED={len(requests_log)}")
                    raise

                # === WALLAPOP PAGE INFO ===
                wallapop_url = self.page.url
                page_title = await self.page.title()
                logger.info(f"WALLAPOP_FINAL_URL={wallapop_url}")
                logger.info(f"PAGE_TITLE={page_title}")

                # === PAGE AUDIT AFTER goto() ===
                read_state = await self.page.evaluate('document.readyState')
                logger.info(f"DOC_READY_STATE={read_state}")
                logger.info(f"NETWORK_AUDIT_T0_REQUESTS={len(requests_log)}")
                logger.info(f"NETWORK_AUDIT_T0_JSON={len(json_responses)}")

                # Wait 5 seconds and check
                await self.page.wait_for_timeout(5000)
                logger.info(f"NETWORK_AUDIT_T5_REQUESTS={len(requests_log)}")
                logger.info(f"NETWORK_AUDIT_T5_JSON={len(json_responses)}")

                # Wait 10 more seconds (15 total) and check
                await self.page.wait_for_timeout(10000)
                logger.info(f"NETWORK_AUDIT_T15_REQUESTS={len(requests_log)}")
                logger.info(f"NETWORK_AUDIT_T15_JSON={len(json_responses)}")

                # Wait 5 more seconds (20 total) and check
                await self.page.wait_for_timeout(5000)
                logger.info(f"NETWORK_AUDIT_T20_REQUESTS={len(requests_log)}")
                logger.info(f"NETWORK_AUDIT_T20_JSON={len(json_responses)}")

                # Check DOM elements
                main_count = await self.page.evaluate('document.querySelectorAll("main").length')
                main_role = await self.page.evaluate('document.querySelectorAll("[role=\'main\']").length')
                testid_count = await self.page.evaluate('document.querySelectorAll("[data-testid]").length')
                btn_count = await self.page.evaluate('document.querySelectorAll("button").length')
                walla_btn = await self.page.evaluate('document.querySelectorAll("walla-button").length')

                logger.info(f"DOM_MAIN={main_count} | DOM_ROLE_MAIN={main_role} | DOM_DATA_TESTID={testid_count}")
                logger.info(f"DOM_BUTTON={btn_count} | DOM_WALLA_BUTTON={walla_btn}")

                # Check for banners
                cookie_count = await self.page.evaluate('document.querySelectorAll("[class*=\'cookie\'],[id*=\'cookie\'],[class*=\'consent\'],[id*=\'consent\']").length')
                banner_text = await self.page.evaluate('''
                  Array.from(document.querySelectorAll("[class*='cookie'],[id*='cookie'],[class*='consent'],[id*='consent']"))
                    .map(e => e.textContent?.slice(0,100) || '')
                    .filter(t => t.length > 0)[0] || 'NONE'
                ''')
                logger.info(f"BANNER_COOKIE_CONSENT_COUNT={cookie_count}")
                logger.info(f"BANNER_TEXT_SAMPLE={banner_text}")

                # Get page text
                body_text = await self.page.evaluate('document.body.innerText.slice(0, 3000)')
                logger.info(f"BODY_TEXT_0_3000={body_text}")

                # === WALLAPOP PAGE FACTS (first page only) ===
                if page == 0:
                    # Collect facts
                    page_title = await self.page.title()
                    final_url = self.page.url
                    body_text_2000 = await self.page.evaluate('document.body.innerText.slice(0, 2000)')
                    has_nada_por_aqui = await self.page.evaluate('document.body.innerText.includes("Nada por aquí")')
                    has_nothing_here = await self.page.evaluate('document.body.innerText.includes("Nothing here") || document.body.innerText.includes("nothing here")')

                    logger.info(f"WALLAPOP_FINAL_URL={final_url}")
                    logger.info(f"WALLAPOP_PAGE_TITLE={page_title}")
                    logger.info(f"WALLAPOP_BODY_TEXT_0_2000={body_text_2000}")
                    logger.info(f"WALLAPOP_HAS_NADA_POR_AQUI={has_nada_por_aqui}")
                    logger.info(f"WALLAPOP_HAS_NOTHING_HERE={has_nothing_here}")

                    # Take screenshot
                    try:
                        screenshot = await self.page.screenshot(path='/tmp/wallapop_screenshot.png')
                        logger.info(f"📸 WALLAPOP_SCREENSHOT_TAKEN=/tmp/wallapop_screenshot.png")
                    except Exception as e:
                        logger.warning(f"⚠️ Screenshot failed: {e}")

                # Ждем загрузки контента (пробуем несколько селекторы)
                try:
                    await self.page.wait_for_selector('div[class*="ItemCard"]', timeout=10000)
                except:
                    await self.page.wait_for_selector('article', timeout=10000)

                # Получаем HTML
                html = await self.page.content()

                # DEBUG: Log page details on first page
                if page == 0:
                    page_title = await self.page.title()
                    final_url = self.page.url
                    html_length = len(html)
                    html_first_5000 = html[:5000]

                    logger.info(f"PAGE_TITLE={page_title}")
                    logger.info(f"FINAL_URL={final_url}")
                    logger.info(f"HTML_LENGTH={html_length}")
                    logger.info(f"HTML_FIRST_5000={html_first_5000}")

                    # Count keyword occurrences
                    count_itemcard = html.count('ItemCard')
                    count_item_card = html.count('item-card')
                    count_wallapop = html.count('wallapop')
                    count_cloudflare = html.count('cloudflare')
                    count_captcha = html.count('captcha')
                    count_cookie = html.count('cookie')
                    count_consent = html.count('consent')

                    logger.info(f"COUNT_ItemCard={count_itemcard}")
                    logger.info(f"COUNT_item_card={count_item_card}")
                    logger.info(f"COUNT_wallapop={count_wallapop}")
                    logger.info(f"COUNT_cloudflare={count_cloudflare}")
                    logger.info(f"COUNT_captcha={count_captcha}")
                    logger.info(f"COUNT_cookie={count_cookie}")
                    logger.info(f"COUNT_consent={count_consent}")

                    # Deep HTML diagnostics
                    logger.info("=== DEEP HTML DIAGNOSTICS ===")

                    # 1. Count specific tags
                    count_wallapop_item_card = html.count('<wallapop-item-card')
                    count_item_card_tag = html.count('<item-card')
                    count_article = html.count('<article')
                    count_section = html.count('<section')
                    count_main = html.count('<main')

                    logger.info(f"TAG_wallapop-item-card={count_wallapop_item_card}")
                    logger.info(f"TAG_item-card={count_item_card_tag}")
                    logger.info(f"TAG_article={count_article}")
                    logger.info(f"TAG_section={count_section}")
                    logger.info(f"TAG_main={count_main}")

                    # 2. Find first 20 links with /item/ or /search/
                    import re
                    href_pattern = r'href=["\']((?:/item/|/search/)[^\s"\']*)'
                    href_matches = re.findall(href_pattern, html)

                    logger.info(f"LINKS_WITH_ITEM_OR_SEARCH={len(href_matches)}")
                    for idx, href in enumerate(href_matches[:20]):
                        logger.info(f"LINK_{idx}={href}")

                    # 3. Analyze script tags
                    script_count = html.count('<script')
                    logger.info(f"SCRIPT_TAGS_TOTAL={script_count}")

                    # Find script tags with size > 1000
                    script_pattern = r'<script[^>]*>(.*?)</script>'
                    scripts = re.findall(script_pattern, html, re.DOTALL)

                    for idx, script in enumerate(scripts):
                        if len(script) > 1000:
                            script_type = 'unknown'
                            if 'type="application/json"' in html[max(0, html.find(script)-200):html.find(script)]:
                                script_type = 'json'
                            elif 'type="text/javascript"' in html[max(0, html.find(script)-200):html.find(script)]:
                                script_type = 'javascript'

                            logger.info(f"SCRIPT_{idx}_TYPE={script_type} | LENGTH={len(script)} | FIRST_500={script[:500]}")

                    # 4. Check for data formats
                    count_next_data = html.count('__NEXT_DATA__')
                    count_ld_json = html.count('application/ld+json')
                    count_initial_state = html.count('initialState')
                    count_apollo = html.count('apollo')
                    count_search_result = html.count('searchResult')
                    count_items = html.count('"items"')
                    count_listings = html.count('listings')

                    logger.info(f"NEXT_DATA={count_next_data}")
                    logger.info(f"LD_JSON={count_ld_json}")
                    logger.info(f"initialState={count_initial_state}")
                    logger.info(f"apollo={count_apollo}")
                    logger.info(f"searchResult={count_search_result}")
                    logger.info(f"items={count_items}")
                    logger.info(f"listings={count_listings}")

                    # 5. Extract NEXT_DATA if found
                    if count_next_data > 0:
                        next_data_pattern = r'<script id="__NEXT_DATA__"[^>]*type="application/json">(.*?)</script>'
                        next_data_match = re.search(next_data_pattern, html, re.DOTALL)
                        if next_data_match:
                            next_data_content = next_data_match.group(1)
                            logger.info(f"NEXT_DATA_LENGTH={len(next_data_content)}")
                            logger.info(f"NEXT_DATA_FIRST_3000={next_data_content[:3000]}")

                            # Parse JSON and search for listing-related keys
                            try:
                                import json
                                next_data_json = json.loads(next_data_content)
                                logger.info("=== NEXT_DATA JSON STRUCTURE ANALYSIS ===")

                                # Keys to search for
                                search_keys = ['listing', 'listings', 'item', 'items', 'search', 'searchResults', 'feed', 'cards', 'products']

                                def find_keys_recursive(obj, target_keys, path=''):
                                    """Recursively search for target keys in JSON structure"""
                                    results = []

                                    if isinstance(obj, dict):
                                        for key, value in obj.items():
                                            current_path = f"{path}.{key}" if path else key

                                            # Check if this key matches any target key
                                            if key.lower() in [tk.lower() for tk in target_keys]:
                                                obj_type = type(value).__name__
                                                count = len(value) if isinstance(value, (list, dict)) else 1
                                                results.append({
                                                    'path': current_path,
                                                    'type': obj_type,
                                                    'count': count,
                                                    'value': value
                                                })

                                            # Recurse into nested structures
                                            results.extend(find_keys_recursive(value, target_keys, current_path))

                                    elif isinstance(obj, list):
                                        for idx, item in enumerate(obj[:3]):  # Only check first 3 items
                                            results.extend(find_keys_recursive(item, target_keys, f"{path}[{idx}]"))

                                    return results

                                # Find all matching keys
                                matches = find_keys_recursive(next_data_json, search_keys)

                                # Log findings
                                for match in matches:
                                    path = match['path']
                                    obj_type = match['type']
                                    count = match['count']

                                    logger.info(f"FOUND_KEY: PATH={path} | TYPE={obj_type} | COUNT={count}")

                                    # If it's a list with objects, show first 3
                                    if isinstance(match['value'], list) and len(match['value']) > 0:
                                        for idx, item in enumerate(match['value'][:3]):
                                            if isinstance(item, dict):
                                                logger.info(f"  ITEM_{idx}={json.dumps(item)[:500]}")

                                # Check for required fields in listings arrays
                                logger.info("=== REQUIRED FIELDS CHECK ===")
                                required_fields = ['id', 'title', 'description', 'price', 'web_slug', 'slug', 'url', 'images', 'seller']

                                for match in matches:
                                    if isinstance(match['value'], list) and len(match['value']) > 0:
                                        first_item = match['value'][0]
                                        if isinstance(first_item, dict):
                                            found_fields = [f for f in required_fields if f in first_item]
                                            logger.info(f"PATH={match['path']} | FIELDS_FOUND={found_fields}")

                            except Exception as e:
                                logger.error(f"ERROR_PARSING_NEXT_DATA: {e}")

                # Парсим HTML
                soup = BeautifulSoup(html, 'html.parser')
                # Ищем карточки объявлений с фильтром: должна содержать ссылку на /item/
                all_items = soup.find_all('div', class_=lambda x: x and 'ItemCard' in x)
                logger.info(f"DEBUG_ALL_ITEMS={len(all_items)}")
                if all_items:
                    first_item = all_items[0]
                    first_link = first_item.find('a')
                    first_href = first_link.get('href', 'NO_HREF') if first_link else 'NO_LINK'
                    logger.info(f"DEBUG_ALL_ITEMS_FIRST: tag={first_item.name} | class={first_item.get('class', [])} | href={first_href}")

                listings = []
                for item in all_items:
                    # Проверяем что это реальное объявление (не реклама)
                    link = item.find('a', href=lambda x: x and '/item/' in x)
                    if link:
                        listings.append(item)

                logger.info(f"DEBUG_ITEM_LINKS={len(listings)} (из {len(all_items)})")
                if listings:
                    first_item = listings[0]
                    first_link = first_item.find('a', href=lambda x: x and '/item/' in x)
                    first_href = first_link.get('href', 'NO_HREF') if first_link else 'NO_LINK'
                    logger.info(f"DEBUG_ITEM_LINKS_FIRST: tag={first_item.name} | class={first_item.get('class', [])} | href={first_href}")

                if not listings and all_items:
                    # Fallback: если не нашли /item/, возьмём все ItemCard
                    logger.info("DEBUG_FALLBACK1_TRIGGERED")
                    listings = all_items

                if not listings:
                    logger.info("DEBUG_FALLBACK2_TRIGGERED")
                    listings = soup.find_all('article')
                    logger.info(f"DEBUG_ARTICLES={len(listings)}")
                    if listings:
                        first_item = listings[0]
                        first_link = first_item.find('a')
                        first_href = first_link.get('href', 'NO_HREF') if first_link else 'NO_LINK'
                        logger.info(f"DEBUG_ARTICLES_FIRST: tag={first_item.name} | class={first_item.get('class', [])} | href={first_href}")

                # Логируем сетевые запросы
                if page == 0 and requests_log:
                    logger.info("=== NETWORK REQUESTS AUDIT ===")
                    logger.info(f"TOTAL_REQUESTS={len(requests_log)}")

                    # Отфильтруем запросы с нужными ключевыми словами
                    keywords = ['api', 'search', 'items', 'listings', 'graphql', 'feed', 'catalog', 'ads', 'results']
                    filtered_requests = [r for r in requests_log if any(kw in r['url'].lower() for kw in keywords)]

                    logger.info(f"FILTERED_REQUESTS_WITH_KEYWORDS={len(filtered_requests)}")

                    for idx, req in enumerate(filtered_requests[:20]):
                        logger.info(f"REQ_{idx}: URL={req['url']} | METHOD={req['method']} | STATUS={req['status']} | TYPE={req['content_type']} | SIZE={req['size']}")

                    # Логируем JSON ответы
                    logger.info(f"JSON_RESPONSES_FOUND={len(json_responses)}")
                    for idx, resp in enumerate(json_responses[:10]):
                        logger.info(f"JSON_{idx}: URL={resp['url']} | STATUS={resp['status']} | SIZE={resp['size']}")
                        if resp['body']:
                            logger.info(f"JSON_{idx}_BODY[0:1000]={resp['body']}")

                    # Сортируем по размеру и логируем топ 20
                    sorted_by_size = sorted(requests_log, key=lambda x: x['size'], reverse=True)
                    logger.info("=== TOP 20 REQUESTS BY RESPONSE SIZE ===")
                    for idx, req in enumerate(sorted_by_size[:20]):
                        logger.info(f"SIZE_{idx}: {req['size']} bytes | URL={req['url'][:100]}")

                if not listings:
                    logger.debug(f"Страница {page + 1} пуста")
                    break

                logger.info(f"📋 Найдено {len(listings)} объявлений на странице {page + 1}")

                # Track if this page adds any new items
                items_before = len(all_results)

                # Парсим каждое объявление
                for idx, listing_elem in enumerate(listings):
                    if len(all_results) >= max_results:
                        break

                    try:
                        listing_data = self._parse_listing_element(listing_elem)
                        if listing_data:
                            raw_items_processed += 1
                            # DEDUP: Check if we've seen this listing_id before
                            already_seen = listing_data.listing_id in seen_listing_ids
                            current_seen_count = sum(1 for lid in seen_listing_ids if lid == listing_data.listing_id)

                            logger.warning(f"🔍 DEDUP_CHECK: listing_id={listing_data.listing_id} | title='{listing_data.title}' | already_seen={already_seen} | current_seen_count={current_seen_count}")

                            if not already_seen:
                                seen_listing_ids.add(listing_data.listing_id)
                                all_results.append(listing_data)
                            else:
                                duplicates_skipped += 1
                                logger.warning(f"🔍 DEDUP_SKIPPED: listing_id={listing_data.listing_id} | title='{listing_data.title}'")
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка парсинга объявления: {e}")
                        continue

                # DEDUP: Check if page added any new items
                items_after = len(all_results)
                if items_after == items_before:
                    consecutive_no_new_items += 1
                    if consecutive_no_new_items >= 3:
                        logger.warning(f"🔍 DEDUP_BREAK: No new items on last 3 pages, stopping scraper")
                        break
                else:
                    consecutive_no_new_items = 0

                page += 1

                # Задержка между страницами
                await asyncio.sleep(self.random_delay_seconds(2, 5))

            except Exception as e:
                logger.error(f"❌ Ошибка на странице {page}: {e}")
                break

        # DEDUP: Final summary
        logger.warning(f"🔍 FINAL_DEDUP_SUMMARY: raw_items_processed={raw_items_processed} | unique_listing_ids={len(seen_listing_ids)} | duplicates_skipped={duplicates_skipped} | final_results_returned={len(all_results)}")

        logger.info(f"✅ Найдено {len(all_results)} объявлений")
        return all_results

    def search(self, search_term: str, max_results: int = 100) -> List[ListingData]:
        """
        Синхронная обертка для асинхронного поиска
        """
        return asyncio.run(self.search_async(search_term, max_results))

    def _parse_listing_element(self, element) -> Optional[ListingData]:
        """Парсить элемент объявления из HTML (современная структура Wallapop)"""
        try:
            # Попробуем получить ID из разных атрибутов
            listing_id = None

            # 1. Попробуем найти link и извлечь ID
            links = element.find_all('a')
            for link in links:
                href = link.get('href', '')
                # /item/slug-text-123456 (new format) или /item/123456 (old format)
                # Try new format first: extract trailing numeric ID
                match = re.search(r'-(\d+)(?:\?|$)', href)
                if match:
                    listing_id = match.group(1)
                    break

            if not listing_id:
                logger.warning(f"PARSE FAILED: reason=NO_LISTING_ID | links_found={len(links)} | first_link_href={links[0].get('href', 'NONE') if links else 'NO_LINKS'}")
                return None

            # Название - ищем в разных местах
            title = ''

            # Попробуем найти span или div с классом, содержащим название
            title_candidates = element.find_all(['h2', 'h3', 'span', 'div'], limit=20)
            for candidate in title_candidates:
                text = candidate.text.strip()
                # Пропускаем короткие текст типа цены и фильтры
                if len(text) > 10 and len(text) < 200 and not text.startswith('€'):
                    # Проверяем что это не цена или другой сервисный текст
                    if text and ('/' not in text or 'Canyon' in text or 'Aeroad' in text):
                        title = text
                        break

            # Альтернативный способ - ищем в первой ссылке
            if not title:
                first_link = element.find('a')
                if first_link:
                    title = first_link.get('title', '') or first_link.text.strip()

            if not title or len(title) < 5:
                logger.warning(f"PARSE FAILED: reason=NO_TITLE | title_found={bool(title)} | title_length={len(title) if title else 0}")
                return None

            # Цена - ищем в названии в формате "310 €Название..."
            # Wallapop включает цену в начало названия
            price_text = ''
            price_match = re.match(r'^([\d.,]+)\s*€', title)
            if price_match:
                price_text = price_match.group(0)
                # Удаляем цену из названия
                title = re.sub(r'^([\d.,]+)\s*€\s*', '', title)

            # Если цены в названии не нашли, ищем в остальном тексте
            if not price_text:
                all_text = element.get_text()
                price_match = re.search(r'\b([\d.,]+)\s*€', all_text)
                if price_match:
                    price_text = price_match.group(0)

            # Очищаем название от артефактов
            title = re.sub(r'^\d+\s*/\s*\d+\s*', '', title)  # Удаляем "1 / 25"
            title = title.strip()

            # Ссылка
            url = ''
            if links:
                href = links[0].get('href', '')
                if href.startswith('/'):
                    url = 'https://es.wallapop.com' + href
                else:
                    url = href

            price = normalize_price(price_text)

            if not price or price < MIN_PRICE or price > MAX_PRICE:
                logger.warning(f"PARSE FAILED: reason=BAD_PRICE | price={price} | min={MIN_PRICE} | max={MAX_PRICE}")
                return None

            # Локация - обычно в конце объявления
            location = ''
            text_parts = all_text.split('\n')
            if len(text_parts) > 1:
                # Последний непустой текст часто - локация
                for part in reversed(text_parts):
                    part_clean = part.strip()
                    if part_clean and len(part_clean) < 50 and '€' not in part_clean:
                        location = part_clean
                        break

            # Продавец
            seller_name = 'Unknown'
            # Можно получить из других источников, но пока оставляем Unknown

            # Изображение
            image_url = ''
            img_elem = element.find('img')
            if img_elem:
                image_url = img_elem.get('src', '') or img_elem.get('data-src', '')

            # Собираем данные
            listing = ListingData(
                source='wallapop',
                listing_id=listing_id,
                url=url,
                title=title,
                description='',
                price=price,
                currency='EUR',
                seller_name=seller_name,
                location=location,
                country='Spain',
                date_posted=None,
                images=[image_url] if image_url else [],
                raw_data={'title': title, 'price': price_text}
            )

            return listing

        except Exception as e:
            logger.debug(f"Ошибка парсинга элемента: {e}")
            return None

    def get_listing_details(self, url: str) -> Optional[dict]:
        """
        Получить полную информацию о конкретном объявлении
        """
        try:
            logger.debug(f"📦 Получаю детали {url}")

            html = self.fetch_page(url)
            if not html:
                return None

            soup = BeautifulSoup(html, 'html.parser')

            # Полное описание
            description_elem = soup.find('div', class_='Description')
            description = description_elem.text.strip() if description_elem else ''

            # Все изображения
            images = []
            gallery = soup.find('div', class_='Gallery')
            if gallery:
                img_elements = gallery.find_all('img')
                images = [img.get('src', '') for img in img_elements if img.get('src')]

            # Информация о продавце
            seller_rating_elem = soup.find('span', class_='SellerRating')
            seller_rating = None
            if seller_rating_elem:
                try:
                    rating_text = seller_rating_elem.text.strip()
                    seller_rating = float(rating_text.replace(',', '.').split()[0])
                except:
                    pass

            return {
                'description': description,
                'images': images,
                'seller_rating': seller_rating,
            }

        except Exception as e:
            logger.warning(f"⚠️  Ошибка получения деталей: {e}")
            return None

    @staticmethod
    def _parse_date(date_text: str) -> Optional[datetime]:
        """
        Парсить дату из текста Wallapop
        Примеры: "2 hours ago", "1 day ago", "3 days ago"
        """
        if not date_text:
            return None

        try:
            date_text_lower = date_text.lower()
            now = datetime.now()

            # Часов назад
            match = re.search(r'(\d+)\s*hours?\s*ago', date_text_lower)
            if match:
                hours = int(match.group(1))
                from datetime import timedelta
                return now - timedelta(hours=hours)

            # Дней назад
            match = re.search(r'(\d+)\s*days?\s*ago', date_text_lower)
            if match:
                days = int(match.group(1))
                from datetime import timedelta
                return now - timedelta(days=days)

            # "1 day ago" vs "2 days ago"
            if 'ago' in date_text_lower:
                from datetime import timedelta
                return now - timedelta(hours=24)

            # Если это конкретная дата (DD/MM/YYYY)
            if '/' in date_text:
                return datetime.strptime(date_text, '%d/%m/%Y')

        except Exception as e:
            logger.debug(f"Ошибка парсинга даты '{date_text}': {e}")

        return None

    @staticmethod
    def random_delay_seconds(min_sec: float = 1, max_sec: float = 3) -> float:
        """Получить случайную задержку в секундах"""
        import random
        return random.uniform(min_sec, max_sec)

    async def close(self):
        """Закрыть браузер и контекст"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass  # Ignore errors during cleanup
        logger.info("✅ Браузер закрыт")

    def parse_listing(self, listing_data: dict) -> ListingData:
        """
        Реализация абстрактного метода
        """
        return ListingData(**listing_data)


def create_wallapop_scraper() -> WallapopScraper:
    """Factory для создания Wallapop скрейпера"""
    return WallapopScraper()
