"""
Конфигурация для системы парсинга велосипедов
"""

import os
from dotenv import load_dotenv

load_dotenv()

# =====================
# DATABASE
# =====================
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://user:password@localhost:5432/bike_scraper'
)

# =====================
# SCRAPING
# =====================
# Интервал проверки новых объявлений (секунды)
SCRAPE_INTERVAL = int(os.getenv('SCRAPE_INTERVAL', 600))  # 10 минут

# Максимум товаров за раз
MAX_RESULTS = int(os.getenv('MAX_RESULTS', 100))

# Таймаут запроса
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 30))

# =====================
# PROXIES
# =====================
USE_PROXIES = os.getenv('USE_PROXIES', 'False') == 'True'
PROXIES_LIST = os.getenv('PROXIES_LIST', '').split(',') if os.getenv('PROXIES_LIST') else []

# User-Agents для ротации
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
]

# =====================
# IMAGE DOWNLOAD
# =====================
IMAGES_DIR = os.getenv('IMAGES_DIR', './images')
MAX_IMAGE_SIZE_MB = int(os.getenv('MAX_IMAGE_SIZE_MB', 10))
DOWNLOAD_IMAGES = os.getenv('DOWNLOAD_IMAGES', 'True') == 'True'

# =====================
# LOGGING
# =====================
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', './logs/scraper.log')

# =====================
# REDIS (для очередей)
# =====================
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# =====================
# API
# =====================
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', 8000))
API_WORKERS = int(os.getenv('API_WORKERS', 4))

# =====================
# WALLAPOP CONFIG
# =====================
WALLAPOP_BASE_URL = 'https://es.wallapop.com'
WALLAPOP_SEARCH_URL = f'{WALLAPOP_BASE_URL}/search'

# Поисковые термины для велосипедов
SEARCH_TERMS = [
    'bicicleta carretera',
    'bicicleta gravel',
    'road bike',
    'gravel bike',
    'bicicleta ciclismo',
    'carretera bici',
]

# Фильтры
MIN_PRICE = int(os.getenv('MIN_PRICE', 100))  # EUR
MAX_PRICE = int(os.getenv('MAX_PRICE', 5000))  # EUR
LOCATIONS = os.getenv('LOCATIONS', 'Spain').split(',')

# =====================
# BIKE PARSER CONFIG
# =====================
BIKE_BRANDS = [
    'Canyon', 'Trek', 'Specialized', 'Giant', 'Scott', 'Orbea', 'Focus',
    'Cube', 'Merida', 'Bianchi', 'Colnago', 'Pinarello', 'Cervelo',
    'Cannondale', 'Felt', 'Kona', 'BMC', 'Wilier', 'Lapierre',
    'LaPierre', 'Norco', 'Polygon', 'Gt', 'Fuji', 'Ridley'
]

BIKE_GROUPSETS = [
    'Ultegra', 'Dura-Ace', '105', 'Tiagra',
    'Sram', 'Force', 'Rival', 'Apex',
    'Shimano', 'Claris', 'Tourney'
]

BIKE_TYPES = [
    'road bike',
    'gravel bike',
    'cyclocross',
    'endurance road',
    'aero road',
    'climbing bike',
    'carretera',
    'grava',
    'ciclocross',
    'endurance',
    'aero'
]

# =====================
# SYSTEM
# =====================
DEBUG = os.getenv('DEBUG', 'False') == 'True'
HEADLESS_BROWSER = os.getenv('HEADLESS_BROWSER', 'True') == 'True'
