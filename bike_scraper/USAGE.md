# 📖 Руководство по использованию Bike Scraper

## 🚀 Быстрый старт

### 1. Установка и инициализация

```bash
# Перейди в папку проекта
cd bike_scraper

# Запусти инициализацию
python init_project.py

# Установи зависимости (если еще не установлены)
pip install -r requirements.txt
```

### 2. Запуск системы

```bash
# Вариант A: Только парсер (непрерывный мониторинг)
python scheduler.py

# Вариант B: Только API
python api_main.py

# Вариант C: Оба в background
python scheduler.py > logs/scheduler.log 2>&1 &
python api_main.py > logs/api.log 2>&1 &
```

---

## 🔍 Примеры использования

### Парсинг одного поиска

```python
from scraper_wallapop import create_wallapop_scraper
from database import get_session
from service_listings import ListingService

# Создаем парсер
scraper = create_wallapop_scraper()

# Ищем велосипеды
listings = scraper.search("bicicleta carretera", max_results=50)
print(f"Найдено {len(listings)} объявлений")

# Сохраняем в БД
db = get_session()
for listing_data in listings:
    listing, is_new = ListingService.get_or_create_listing(db, listing_data)
    if is_new:
        print(f"✨ Новое: {listing.title} - €{listing.price}")

db.commit()
db.close()
scraper.close()
```

### Получение данных из БД

```python
from database import get_session
from models import Listing
from sqlalchemy import desc

db = get_session()

# Последние 10 новых объявлений
new = db.query(Listing).filter(
    Listing.is_active == True
).order_by(desc(Listing.created_at)).limit(10).all()

for listing in new:
    print(f"{listing.title} - €{listing.price} ({listing.location})")

db.close()
```

### Анализ цен

```python
from database import get_session
from models import Listing
from sqlalchemy import func

db = get_session()

# Статистика по типам велосипедов
stats = db.query(
    Listing.bike_type,
    func.count(Listing.id).label('count'),
    func.avg(Listing.price).label('avg_price'),
    func.min(Listing.price).label('min'),
    func.max(Listing.price).label('max'),
).filter(
    Listing.is_active == True
).group_by(Listing.bike_type).all()

for stat in stats:
    print(f"{stat.bike_type}:")
    print(f"  Объявлений: {stat.count}")
    print(f"  Средняя цена: €{stat.avg_price:.0f}")
    print(f"  Min: €{stat.min} / Max: €{stat.max}")

db.close()
```

### Мониторинг цен

```python
from database import get_session
from models import ListingHistory
from datetime import datetime, timedelta

db = get_session()

# История изменения цен за последний день
cutoff = datetime.utcnow() - timedelta(days=1)

changes = db.query(ListingHistory).filter(
    ListingHistory.checked_at >= cutoff
).order_by(ListingHistory.checked_at.desc()).all()

for change in changes:
    price_change = change.price_new - change.price_old
    direction = "⬆️" if price_change > 0 else "⬇️"
    print(f"{direction} €{change.price_old} → €{change.price_new} ({price_change:+.0f}€)")

db.close()
```

### Выгодные предложения

```python
from database import get_session
from models import Listing
from sqlalchemy import and_, func

db = get_session()

# Road bikes дешевле чем средняя цена
avg_road_price = db.query(func.avg(Listing.price)).filter(
    Listing.bike_type == 'road',
    Listing.is_active == True
).scalar()

cheap_roads = db.query(Listing).filter(
    and_(
        Listing.bike_type == 'road',
        Listing.price < avg_road_price * 0.8,  # На 20% дешевле средней
        Listing.is_active == True
    )
).all()

print(f"Средняя цена road bike: €{avg_road_price:.0f}")
print(f"Дешевые предложения (< €{avg_road_price * 0.8:.0f}):")

for listing in cheap_roads:
    discount = (avg_road_price - listing.price) / avg_road_price * 100
    print(f"  {listing.title}")
    print(f"    €{listing.price} (скидка {discount:.0f}%)")
    print(f"    {listing.seller_name} ({listing.seller_rating}⭐)")
    print()

db.close()
```

### Анализ продавца

```python
from database import get_session
from models import Listing

db = get_session()

# Информация о продавце
seller_name = "Juan García"

listings = db.query(Listing).filter(
    Listing.seller_name == seller_name,
    Listing.is_active == True
).all()

if listings:
    prices = [l.price for l in listings]
    avg_price = sum(prices) / len(prices)

    print(f"Продавец: {seller_name}")
    print(f"Рейтинг: {listings[0].seller_rating}⭐")
    print(f"Объявлений: {len(listings)}")
    print(f"Средняя цена: €{avg_price:.0f}")
    print(f"От €{min(prices)} до €{max(prices)}")
    print()
    print("Объявления:")
    for listing in listings:
        print(f"  - {listing.title} - €{listing.price}")

db.close()
```

---

## 🌐 REST API - Примеры

### Получить список велосипедов

```bash
# Все велосипеды
curl http://localhost:8000/bikes

# JSON красиво
curl -s http://localhost:8000/bikes | jq '.'

# С фильтрацией по цене
curl "http://localhost:8000/bikes?min_price=500&max_price=1500"

# Road bikes
curl "http://localhost:8000/bikes?bike_type=road&limit=20"
```

### Новые объявления

```bash
# За последние 24 часа
curl http://localhost:8000/new?hours=24

# За последнюю неделю
curl http://localhost:8000/new?hours=168&limit=100
```

### Поиск

```bash
# Поиск по названию
curl "http://localhost:8000/search?q=canyon"

# Поиск с ограничением
curl "http://localhost:8000/search?q=trek&limit=30"
```

### Статистика

```bash
# Общая информация
curl http://localhost:8000/statistics | jq '.'

# Анализ цен
curl http://localhost:8000/price-analysis | jq '.'

# По конкретному типу
curl "http://localhost:8000/price-analysis?bike_type=gravel" | jq '.'
```

### Логи парсинга

```bash
# Последние логи
curl http://localhost:8000/logs

# За конкретное время
curl "http://localhost:8000/logs?hours=48&limit=20" | jq '.'
```

---

## 📊 Полезные SQL запросы

### Самые выгодные предложения

```sql
SELECT title, price, seller_name, seller_rating, location
FROM listings
WHERE is_active = TRUE
  AND bike_type IS NOT NULL
ORDER BY price ASC
LIMIT 20;
```

### Лучшие продавцы

```sql
SELECT seller_name, COUNT(*) as total,
       AVG(price) as avg_price,
       AVG(seller_rating) as avg_rating
FROM listings
WHERE is_active = TRUE
GROUP BY seller_name
HAVING COUNT(*) > 5
ORDER BY avg_rating DESC
LIMIT 20;
```

### История цен

```sql
SELECT l.title, l.price, lh.price_old, lh.price_new,
       lh.checked_at, (lh.price_new - lh.price_old) as change
FROM listing_history lh
JOIN listings l ON l.id = lh.listing_id
WHERE lh.change_type = 'price_changed'
ORDER BY lh.checked_at DESC
LIMIT 50;
```

### Спрос по типам

```sql
SELECT bike_type, COUNT(*) as count,
       AVG(price) as avg_price,
       MIN(price) as min_price,
       MAX(price) as max_price
FROM listings
WHERE is_active = TRUE
GROUP BY bike_type
ORDER BY count DESC;
```

---

## 🔧 Продвинутая конфигурация

### Использование прокси

```bash
# Добавь в .env
USE_PROXIES=True
PROXIES_LIST=http://proxy1:8080,http://proxy2:8080

# Парсер будет ротировать прокси между запросами
```

### Кастомные поисковые термины

```python
# Отредактируй config.py
SEARCH_TERMS = [
    'bicicleta carretera',
    'bicicleta gravel',
    'canyon',
    'trek',
    'specialized gravel',
]
```

### Более частый парсинг

```python
# config.py
SCRAPE_INTERVAL = 300  # 5 минут вместо 10
```

### Более медленный парсинг

```python
# config.py
SCRAPE_INTERVAL = 1800  # 30 минут
```

---

## 📈 Автоматизация

### Cron job для ежедневного запуска

```bash
# Добавь в crontab
0 8 * * * cd /path/to/bike_scraper && python scheduler.py

# Или с логированием
0 8 * * * cd /path/to/bike_scraper && python scheduler.py >> logs/cron.log 2>&1
```

### SystemD сервис

```ini
[Unit]
Description=Bike Scraper Service
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/bike_scraper
ExecStart=/usr/bin/python3 scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Включение:
```bash
sudo systemctl enable bike-scraper
sudo systemctl start bike-scraper
```

---

## 🧠 Идеи для расширения

### 1. Telegram уведомления

```python
from telegram import Bot

async def notify_good_deal(listing):
    bot = Bot(token="YOUR_TOKEN")
    message = f"🚴 Выгодное предложение!\n{listing.title}\n€{listing.price}\n{listing.url}"
    await bot.send_message(chat_id=YOUR_CHAT_ID, text=message)
```

### 2. Machine Learning для цен

```python
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression

# Предсказание цены на основе характеристик
def predict_price(brand, model, year, groupset):
    # ... модель обучения
    pass
```

### 3. OLX как источник

```python
# Создай scraper_olx.py с парсером для OLX
# Следуя же структуре как scraper_wallapop.py
```

### 4. Сравнение с историческими данными

```python
# Анализировать как цены менялись со временем
# Определять выгодные моменты для покупки/продажи
```

---

## 📞 Полезные команды

```bash
# Просмотр логов в реальном времени
tail -f logs/scraper.log

# Подсчет объявлений в БД
psql $DATABASE_URL -c "SELECT COUNT(*) FROM listings"

# Проверка API
curl http://localhost:8000/health

# Просмотр процессов
ps aux | grep python

# Остановка парсера
pkill -f "python scheduler.py"
```

---

**Удачи в анализе велосипедов! 🚴‍♂️**
