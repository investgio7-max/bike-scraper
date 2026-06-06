# 🏗️ Архитектура Bike Scraper System

## Общий обзор

```
┌─────────────────────────────────────────────────────────────┐
│                    BIKE SCRAPER SYSTEM                      │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  Wallapop   │  │    OLX      │  │   Others    │  (future)│
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
└─────────┼──────────────────┼──────────────┼────────────────┘
          │                  │              │
          └──────────────────┴──────────────┘
                       │
         ┌─────────────▼──────────────┐
         │   SCRAPER LAYER            │
         │  ┌────────────────────┐    │
         │  │ BaseScraper        │    │
         │  │  (curl_cffi based) │    │
         │  └─────────┬──────────┘    │
         │            │               │
         │  ┌─────────▼──────────┐    │
         │  │ WallapopScraper    │    │
         │  │ OLXScraper (future)│   │
         │  └────────────────────┘    │
         └────────────┬────────────────┘
                      │
         ┌────────────▼────────────┐
         │  PROCESSING LAYER       │
         │  ┌───────────────────┐  │
         │  │ BikeParser        │  │
         │  │ (извлечение инфо) │  │
         │  └───────────────────┘  │
         │  ┌───────────────────┐  │
         │  │ ImageDownloader   │  │
         │  │ (скачивание фото) │  │
         │  └───────────────────┘  │
         │  ┌───────────────────┐  │
         │  │ ListingService    │  │
         │  │ (дедупликация)    │  │
         │  └───────────────────┘  │
         └────────────┬────────────┘
                      │
         ┌────────────▼────────────┐
         │  PERSISTENCE LAYER      │
         │  ┌───────────────────┐  │
         │  │   PostgreSQL      │  │
         │  │   (Listings, etc) │  │
         │  └───────────────────┘  │
         │  ┌───────────────────┐  │
         │  │   File Storage    │  │
         │  │   (Images)        │  │
         │  └───────────────────┘  │
         └────────────┬────────────┘
                      │
       ┌──────────────┴──────────────┐
       │                             │
┌──────▼────────────┐      ┌────────▼──────────┐
│  SCHEDULER        │      │  REST API         │
│  (Continuous)     │      │  (FastAPI)        │
│  ┌──────────────┐ │      │  ┌──────────────┐ │
│  │ Run every    │ │      │  │ GET /bikes   │ │
│  │ SCRAPE_      │ │      │  │ GET /new     │ │
│  │ INTERVAL sec │ │      │  │ GET /stats   │ │
│  │              │ │      │  │ GET /search  │ │
│  │ Parse listings
│  │ Save to DB   │ │      │  │ ...          │ │
│  │ Download imgs│ │      │  └──────────────┘ │
│  │ Log results  │ │      │                    │
│  └──────────────┘ │      │  Port: 8000       │
│                   │      │                    │
└───────────────────┘      └────────────────────┘
        │                           │
        └──────────────┬────────────┘
                       │
              ┌────────▼──────────┐
              │   USER/EXTERNAL   │
              │   Applications    │
              └───────────────────┘
```

---

## 📦 Модули

### 1. Config Layer (`config.py`)

```
config.py
├── Database Settings
│   └── DATABASE_URL
├── Scraping Settings
│   ├── SCRAPE_INTERVAL
│   ├── MAX_RESULTS
│   └── REQUEST_TIMEOUT
├── Source Settings
│   ├── WALLAPOP_BASE_URL
│   ├── SEARCH_TERMS
│   └── BIKE_BRANDS/GROUPSETS
└── System Settings
    ├── LOG_LEVEL
    ├── API_PORT
    └── DEBUG
```

### 2. Database Layer

```
database.py
├── SQLAlchemy Engine
├── Connection Pooling
└── Session Management

models.py
├── Listing (main table)
├── ListingHistory (price tracking)
├── ScraperLog (audit trail)
├── SellerProfile (seller info)
├── Bike (normalized data)
└── PriceAnalysis (analytics)
```

### 3. Scraper Layer

```
scraper_base.py (Abstract)
├── BaseScraper
├── Session Management (curl_cffi)
├── User-Agent Rotation
├── Proxy Rotation
└── Rate Limiting

scraper_wallapop.py (Concrete)
├── WallapopScraper
├── search()
├── _parse_listing_element()
└── get_listing_details()
```

### 4. Processing Layer

```
utils_parser.py
├── BikeParser
├── extract_brand()
├── extract_frame_size()
├── extract_groupset()
├── parse_listing()
└── normalize_price()

utils_images.py
├── ImageDownloader
├── download_images()
├── cleanup_unused_images()
└── get_image_stats()

service_listings.py
├── ListingService
├── get_or_create_listing() [дедупликация]
├── check_for_duplicates()
├── mark_as_duplicate()
├── save_scraper_log()
└── calculate_price_analysis()
```

### 5. Logging Layer

```
utils_logger.py
├── get_logger()
├── File Handler (rotating)
└── Console Handler
```

### 6. Orchestration Layer

```
scheduler.py
├── BikeScraperScheduler
├── start() [main loop]
├── run_scraping()
├── cleanup()
├── analyze_prices()
└── get_stats()
```

### 7. API Layer

```
api_main.py (FastAPI)
├── Startup/Shutdown Events
├── GET /bikes [filtering]
├── GET /bike/{id}
├── GET /new [recent]
├── GET /deals [good offers]
├── GET /search [full-text]
├── GET /statistics
├── GET /price-analysis
├── GET /logs
├── GET /health
└── Swagger Docs
```

---

## 🔄 Основной workflow

### Парсинг

```
1. scheduler.run_scraping()
   ├── Для каждого search_term в SEARCH_TERMS
   │   ├── scraper.search(term)
   │   │   ├── curl_cffi GET request
   │   │   ├── BeautifulSoup parse HTML
   │   │   └── return [ListingData, ...]
   │   │
   │   ├── Для каждого listing
   │   │   ├── ListingService.get_or_create_listing()
   │   │   │   ├── Проверяем дубликат в БД
   │   │   │   ├── Если новый - создаем
   │   │   │   ├── Если существует - обновляем цену
   │   │   │   └── Сохраняем историю цены
   │   │   │
   │   │   ├── BikeParser.parse_listing()
   │   │   │   ├── extract_brand()
   │   │   │   ├── extract_frame_size()
   │   │   │   ├── extract_groupset()
   │   │   │   └── return {normalized data}
   │   │   │
   │   │   └── ImageDownloader.download_images()
   │   │       ├── Параллельно скачиваем изображения
   │   │       └── Сохраняем пути в БД
   │   │
   │   └── db.commit()
   │
   ├── ListingService.save_scraper_log()
   │   └── Сохраняем статистику парсинга
   │
   └── Отправляем на следующий интервал
```

### Дедупликация

```
Когда находим новое объявление:

1. Генерируем уникальный ключ
   (source + listing_id)

2. Ищем в БД существующее
   WHERE source='wallapop' AND listing_id='123'

3. Если найдено:
   ├── Обновляем цену
   ├── Сохраняем в ListingHistory
   └── Обновляем date_collected

4. Если не найдено:
   ├── Создаем новое Listing
   ├── Парсим информацию о велосипеде
   ├── Скачиваем изображения
   └── Сохраняем в БД

5. Проверяем на дубликаты
   WHERE price=X AND seller=Y AND bike_type=Z
   └── Если найдено - отмечаем как duplicate
```

### API Request

```
curl /bikes?bike_type=road&min_price=500

1. api_main.py route handler
   └── Validates parameters

2. Database query
   ├── SELECT * FROM listings
   ├── WHERE bike_type = 'road'
   ├── AND price >= 500
   ├── AND is_active = True
   └── LIMIT 50

3. Serialize to JSON
   └── Pydantic ListingResponse model

4. Return to client
   └── 200 OK + JSON
```

---

## 📊 Data Flow

```
Wallapop (HTML)
    ↓
curl_cffi (HTTP client)
    ↓
BeautifulSoup (HTML parser)
    ↓
ListingData (intermediate model)
    ↓
BikeParser (normalize bike info)
    ↓
ImageDownloader (fetch images)
    ↓
SQLAlchemy ORM
    ↓
PostgreSQL (persist)
    ↓
REST API (expose)
    ↓
Client Applications
```

---

## 🔐 Защита от блокировок

```
На каждом запросе:

1. curl_cffi
   └── Имитирует реальный браузер на уровне TLS

2. User-Agent ротация
   ├── Выбираем случайный из списка
   └── Отправляем в заголовке

3. Случайная задержка
   ├── random.uniform(min, max)
   └── time.sleep(delay)

4. Прокси (опционально)
   ├── Если USE_PROXIES=True
   └── Ротируем прокси между запросами

5. Connection pooling
   ├── Переиспользуем соединения
   └── Pool size = 20

6. Rate limiting
   ├── Между поисками: 5 сек
   ├── Между страницами: 2 сек
   └── Между всеми запросами: 1-3 сек
```

---

## 💾 Database Schema

```
listings
├── id (UUID, PK)
├── source (String, Index)
├── listing_id (String, Unique с source)
├── url (String, Unique)
├── title (Text)
├── description (Text)
├── price (Float, Index)
├── currency (String)
├── seller_name (String, Index)
├── seller_rating (Float)
├── location (String)
├── country (String, Index)
├── bike_type (String, Index)
├── frame_size (String)
├── images (JSON)
├── date_posted (DateTime)
├── date_collected (DateTime, Index)
├── is_active (Boolean, Index)
├── is_duplicate (Boolean)
├── original_listing_id (UUID, FK)
├── raw_data (JSONB)
├── created_at (DateTime)
└── updated_at (DateTime)

listing_history
├── id (UUID, PK)
├── listing_id (UUID, FK, Index)
├── source (String)
├── price_old (Float)
├── price_new (Float)
├── change_type (String)
└── checked_at (DateTime, Index)

scraper_logs
├── id (UUID, PK)
├── source (String, Index)
├── search_term (String)
├── total_found (Integer)
├── successfully_parsed (Integer)
├── errors_count (Integer)
├── duration_seconds (Float)
├── status (String)
├── log_message (Text)
├── errors (JSON)
└── created_at (DateTime, Index)
```

---

## 🚀 Масштабирование

### Текущая архитектура

```
┌─────────────────┐
│  Single Process │
├─────────────────┤
│  1 Scraper      │
│  1 API Server   │
│  1 DB Connection│
└─────────────────┘
```

### Будущее масштабирование

```
┌─────────────────────────────────────┐
│     Load Balancer (nginx)           │
└──────┬──────────────────────┬───────┘
       │                      │
┌──────▼──────┐       ┌──────▼──────┐
│  API Pod 1  │       │  API Pod 2  │
└─────┬────────┘       └──────┬──────┘
      │                       │
      └───────────┬───────────┘
                  │
        ┌─────────▼──────────┐
        │  PostgreSQL        │
        │  (replicated)      │
        └────────────────────┘
        
┌─────────────────────────────────────┐
│  Message Queue (Redis/RabbitMQ)     │
├─────────────────────────────────────┤
│  Scraper Task 1                     │
│  Scraper Task 2                     │
│  Scraper Task 3                     │
└─────────────────────────────────────┘
```

---

## 🔍 Мониторинг и метрики

```
Что отслеживается:

scheduler.stats
├── runs - количество запусков
├── listings_found - найдено объявлений
├── listings_new - новых объявлений
├── errors - ошибок
└── last_run - время последнего запуска

ScraperLog (в БД)
├── total_found
├── successfully_parsed
├── errors_count
├── duration_seconds
└── status

API metrics
├── Request count
├── Response time
├── Error rate
└── Database pool stats
```

---

**Architecture by: Claude Code** 🚀
