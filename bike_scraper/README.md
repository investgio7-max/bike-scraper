# 🚴 Bike Scraper System

Система для автоматического парсинга и анализа объявлений о велосипедах на Wallapop с целью поиска выгодных предложений для перепродажи.

## ✨ Основные возможности

✅ **Непрерывный мониторинг** — проверка новых объявлений каждые 10 минут  
✅ **Интеллектуальный парсинг** — извлечение характеристик велосипедов из текста  
✅ **Дедупликация** — автоматическое определение и обработка дубликатов  
✅ **Мониторинг цен** — отслеживание изменения цен и истории  
✅ **Скачивание изображений** — сохранение всех фотографий локально  
✅ **Защита от блокировок** — ротация User-Agent, прокси, случайные задержки  
✅ **REST API** — доступ к данным через HTTP  
✅ **Анализ цен** — статистика и аналитика по типам велосипедов  
✅ **Логирование** — полное логирование работы системы  

---

## 🏗️ Архитектура

```
bike_scraper/
├── config.py                 # Конфигурация
├── models.py                 # SQLAlchemy модели БД
├── database.py              # Подключение к БД
├── scraper_base.py          # Базовый класс парсера
├── scraper_wallapop.py      # Парсер для Wallapop
├── service_listings.py      # Бизнес-логика объявлений
├── scheduler.py             # Планировщик парсинга
├── api_main.py             # REST API
├── utils_logger.py         # Логирование
├── utils_parser.py         # Парсинг информации о велосипедах
├── utils_images.py         # Скачивание изображений
└── requirements.txt        # Зависимости
```

---

## 🚀 Быстрый старт

### 1. Установка

```bash
# Клонируем репо
cd bike_scraper

# Устанавливаем зависимости
pip install -r requirements.txt
```

### 2. Настройка БД

```bash
# PostgreSQL должен быть установлен и запущен

# Создаем БД
createdb bike_scraper

# Или указываем CONNECTION STRING в .env:
echo "DATABASE_URL=postgresql://user:password@localhost:5432/bike_scraper" > .env
```

### 3. Запуск системы

#### Вариант A: Только парсер (непрерывный мониторинг)

```bash
python scheduler.py
```

#### Вариант B: Только API (без парсинга)

```bash
python api_main.py
```

#### Вариант C: Оба вместе (рекомендуется)

```bash
# В одном терминале
python scheduler.py &

# В другом
python api_main.py
```

---

## 📚 Использование

### REST API

#### 1. Получить велосипеды

```bash
# Все активные велосипеды
curl http://localhost:8000/bikes

# С фильтрацией
curl "http://localhost:8000/bikes?bike_type=road&min_price=500&max_price=2000"

# С пагинацией
curl "http://localhost:8000/bikes?skip=0&limit=20"
```

#### 2. Новые объявления

```bash
# Последние 24 часа
curl http://localhost:8000/new?hours=24&limit=50

# Последние 7 дней
curl http://localhost:8000/new?hours=168&limit=100
```

#### 3. Выгодные предложения

```bash
curl http://localhost:8000/deals?limit=50
```

#### 4. Поиск

```bash
curl "http://localhost:8000/search?q=canyon"
```

#### 5. Статистика

```bash
# Общая статистика
curl http://localhost:8000/statistics

# Анализ цен по типам
curl http://localhost:8000/price-analysis

# По конкретному типу
curl "http://localhost:8000/price-analysis?bike_type=road"

# Логи парсинга
curl http://localhost:8000/logs?hours=24
```

### Документация API

После запуска перейди на: http://localhost:8000/docs

Там интерактивная документация Swagger с возможностью тестирования.

---

## ⚙️ Конфигурация

### .env файл

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/bike_scraper

# Scraping
SCRAPE_INTERVAL=600              # Интервал в секундах (10 минут)
MAX_RESULTS=100                  # Макс результатов за раз
REQUEST_TIMEOUT=30               # Таймаут запроса

# Proxies (опционально)
USE_PROXIES=False
PROXIES_LIST=http://proxy1:port,http://proxy2:port

# Images
DOWNLOAD_IMAGES=True
IMAGES_DIR=./images
MAX_IMAGE_SIZE_MB=10

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/scraper.log

# API
API_HOST=0.0.0.0
API_PORT=8000

# System
DEBUG=False
HEADLESS_BROWSER=True
```

---

## 🗄️ Структура БД

### Таблицы

#### `listings` — Объявления о велосипедах
- `id` (UUID) — уникальный ID
- `source` — источник (wallapop, olx, etc.)
- `listing_id` — ID на платформе
- `title` — название
- `description` — описание
- `price` — цена
- `seller_name` — имя продавца
- `seller_rating` — рейтинг продавца
- `location` — локация
- `bike_type` — тип велосипеда (road, gravel, etc.)
- `frame_size` — размер рамы
- `images` — JSON с путями к изображениям
- `date_posted` — дата публикации
- `date_collected` — дата сбора данных
- `is_active` — активно ли объявление
- `is_duplicate` — дубликат ли
- `created_at` — дата создания записи
- `updated_at` — дата последнего обновления

#### `listing_history` — История изменения цен
- `listing_id` — связь на объявление
- `price_old` — старая цена
- `price_new` — новая цена
- `change_type` — тип изменения
- `checked_at` — дата проверки

#### `scraper_logs` — Логи парсинга
- `source` — источник
- `total_found` — найдено объявлений
- `successfully_parsed` — успешно спарсено
- `errors_count` — ошибок
- `duration_seconds` — время выполнения
- `status` — статус (success, partial, failed)

#### `seller_profiles` — Профили продавцов
- `seller_id` — ID продавца
- `seller_name` — имя
- `rating` — рейтинг
- `reviews_count` — количество отзывов
- `total_listings` — всего объявлений
- `active_listings` — активных объявлений

#### `bikes` — Нормализованные данные о велосипедах
- `brand` — бренд (Canyon, Trek, etc.)
- `model` — модель
- `bike_type` — тип
- `year` — год выпуска
- `frame_material` — материал рамы
- `groupset` — компоненты
- И другие характеристики...

---

## 📊 Примеры анализа

### Получить рекомендации по покупке

```python
from database import get_session
from models import Listing

db = get_session()

# Дешевые road bikes
cheap_roads = db.query(Listing).filter(
    Listing.bike_type == 'road',
    Listing.price < 800,
    Listing.is_active == True
).all()

for listing in cheap_roads:
    print(f"{listing.title} - €{listing.price} ({listing.seller_name})")
```

### Анализ продавца

```python
# Объявления от конкретного продавца
seller_listings = db.query(Listing).filter(
    Listing.seller_name == 'SellerName'
).all()

avg_price = sum(l.price for l in seller_listings) / len(seller_listings)
print(f"Средняя цена: €{avg_price}")
print(f"Минимум: €{min(l.price for l in seller_listings)}")
print(f"Максимум: €{max(l.price for l in seller_listings)}")
```

### Мониторинг цен

```python
from models import ListingHistory

# История цен для объявления
history = db.query(ListingHistory).filter(
    ListingHistory.listing_id == listing_id
).order_by(ListingHistory.checked_at).all()

for h in history:
    print(f"{h.checked_at}: €{h.price_old} → €{h.price_new}")
```

---

## 🔐 Защита от блокировок

Система использует несколько методов для избежания блокировок:

1. **curl_cffi** — имитирует реальный браузер на уровне TLS
2. **User-Agent ротация** — использует разные User-Agent
3. **Случайные задержки** — между запросами добавляется randomized delay
4. **Прокси поддержка** — опциональная ротация прокси
5. **Connection pooling** — переиспользует соединения
6. **Rate limiting** — ограничивает частоту запросов

---

## 📈 Примеры данных

### Пример объявления

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "wallapop",
  "listing_id": "12345678",
  "title": "Canyon Aeroad CF SLX 8 2023",
  "description": "Bicicleta carretera de carbón...",
  "price": 1500,
  "currency": "EUR",
  "seller_name": "Juan García",
  "seller_rating": 4.8,
  "location": "Barcelona",
  "country": "Spain",
  "bike_type": "road bike",
  "frame_size": "56cm",
  "date_posted": "2024-01-10T15:30:00",
  "date_collected": "2024-01-15T10:20:00",
  "images": [
    "./images/550e8400-e29b-41d4-a716-446655440000_0_abc123.jpg",
    "./images/550e8400-e29b-41d4-a716-446655440000_1_def456.jpg"
  ],
  "is_active": true,
  "is_duplicate": false
}
```

---

## 🐛 Troubleshooting

### БД не подключается

```bash
# Проверь что PostgreSQL запущен
psql --version

# Проверь CONNECTION STRING в .env
DATABASE_URL=postgresql://user:password@localhost:5432/bike_scraper

# Тестируй подключение
psql $DATABASE_URL -c "SELECT 1"
```

### Парсер не находит объявления

```bash
# Проверь интернет
ping google.com

# Проверь логи
tail -f logs/scraper.log

# Проверь конфиг поисковых терминов в config.py
SEARCH_TERMS = ['bicicleta carretera', ...]
```

### API не запускается

```bash
# Проверь что порт свободен
lsof -i :8000

# Или используй другой порт
API_PORT=8001 python api_main.py
```

### Изображения не скачиваются

```bash
# Проверь DOWNLOAD_IMAGES=True в .env
# Проверь что папка images существует и доступна
ls -la images/

# Проверь права доступа
chmod 755 images/
```

---

## 📊 Мониторинг и логирование

### Логи находятся в

```bash
logs/scraper.log
```

### Примеры логов

```
2024-01-15 10:20:30 - bike_scraper.scheduler - INFO - 🚀 Запускаю планировщик (интервал: 600с)
2024-01-15 10:20:31 - bike_scraper.scraper.wallapop - INFO - 🔍 Ищу 'bicicleta carretera' на Wallapop...
2024-01-15 10:20:35 - bike_scraper.service - INFO - ✨ Новое объявление: Canyon Aeroad - €1500
2024-01-15 10:20:36 - bike_scraper.utils.images - INFO - 📸 Скачиваю 5 изображений
```

---

## 🔄 Обновление данных

### Автоматический мониторинг

```python
# Работает автоматически каждые SCRAPE_INTERVAL секунд
# За это время:
# 1. Ищутся новые объявления
# 2. Проверяются изменения цен
# 3. Определяются дубликаты
# 4. Скачиваются изображения
# 5. Сохраняются логи
```

### Ручной парсинг

```python
from scraper_wallapop import create_wallapop_scraper
from database import get_session
from service_listings import ListingService

scraper = create_wallapop_scraper()
listings = scraper.search("bicicleta carretera", max_results=50)

db = get_session()
for listing_data in listings:
    listing, is_new = ListingService.get_or_create_listing(db, listing_data)
    if is_new:
        print(f"Новое: {listing.title}")

db.commit()
db.close()
```

---

## 🚀 Развертывание в production

### Docker

```dockerfile
FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "scheduler.py"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: bike_scraper
      POSTGRES_PASSWORD: password
    volumes:
      - pgdata:/var/lib/postgresql/data

  scraper:
    build: .
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql://postgres:password@db:5432/bike_scraper

  api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
    command: python api_main.py

volumes:
  pgdata:
```

---

## 📝 TODO

- [ ] Добавить OLX как источник
- [ ] Machine learning для прогноза цен
- [ ] Telegram уведомления для выгодных предложений
- [ ] Сравнение цен на разных платформах
- [ ] Анализ спроса и тренды
- [ ] Интеграция с marketplace для быстрой перепродажи

---

## 📞 Поддержка

Если возникли вопросы или проблемы:

1. Проверь логи: `tail -f logs/scraper.log`
2. Проверь БД: `psql $DATABASE_URL -c "SELECT COUNT(*) FROM listings"`
3. Проверь API: `curl http://localhost:8000/health`

---

**Система готова к использованию! 🚴‍♂️**
