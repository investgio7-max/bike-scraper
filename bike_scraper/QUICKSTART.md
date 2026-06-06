# 🚀 Bike Scraper - Quick Start

Начни за 5 минут!

## Вариант 1: С Docker (самый простой)

```bash
# 1. Запусти Docker
docker-compose up -d

# 2. Инициализируй БД
docker-compose exec scraper python init_project.py

# 3. Готово! Система работает
```

Проверь:
- 📊 API: http://localhost:8000/docs
- 📋 Данные: http://localhost:8000/bikes
- 📊 Статистика: http://localhost:8000/statistics

---

## Вариант 2: Локально (без Docker)

### Шаг 1: Подготовка

```bash
# Установи PostgreSQL (если еще не установлен)
# macOS:
brew install postgresql

# Linux:
sudo apt-get install postgresql postgresql-contrib

# Windows: скачай с https://www.postgresql.org/download/windows/
```

### Шаг 2: Создай БД

```bash
# Запусти PostgreSQL
pg_ctl -D /usr/local/var/postgres start  # macOS
# или
sudo service postgresql start  # Linux

# Создай БД
createdb bike_scraper

# Создай пользователя (опционально)
psql -c "CREATE USER bike_user WITH PASSWORD 'bike_password';"
psql -c "ALTER ROLE bike_user WITH CREATEDB;"
```

### Шаг 3: Настройка проекта

```bash
# Перейди в папку
cd bike_scraper

# Установи зависимости
pip install -r requirements.txt

# Инициализируй проект
python init_project.py

# Или создай .env вручную
cp .env.example .env
# Отредактируй .env с настройками БД
```

### Шаг 4: Запуск

```bash
# В одном терминале - парсер
python scheduler.py

# В другом - API
python api_main.py
```

---

## ⚡ Быстрые команды

```bash
# Проверить здоровье
curl http://localhost:8000/health

# Получить все велосипеды
curl http://localhost:8000/bikes | jq '.'

# Получить только road bikes
curl "http://localhost:8000/bikes?bike_type=road" | jq '.'

# Последние объявления
curl http://localhost:8000/new | jq '.'

# Статистика
curl http://localhost:8000/statistics | jq '.'

# API документация
open http://localhost:8000/docs
```

---

## 🔍 Просмотр логов

```bash
# Логи парсера
tail -f logs/scraper.log

# Или все логи
tail -f logs/*.log
```

---

## 🐛 Если что-то не работает

### PostgreSQL не подключается

```bash
# Проверь что postgres работает
psql -l

# Проверь CONNECTION STRING в .env
DATABASE_URL=postgresql://user:password@localhost:5432/bike_scraper

# Создай БД если нет
createdb bike_scraper
```

### API не запускается

```bash
# Проверь что порт 8000 свободен
lsof -i :8000

# Используй другой порт
API_PORT=8001 python api_main.py
```

### Парсер не находит объявления

```bash
# Проверь интернет
ping google.com

# Проверь логи
grep ERROR logs/scraper.log
```

---

## 📊 Первые шаги

### 1. Проверить данные

```python
from database import get_session
from models import Listing

db = get_session()
count = db.query(Listing).count()
print(f"Всего объявлений: {count}")
db.close()
```

### 2. Посмотреть новые объявления

```bash
curl http://localhost:8000/new?hours=24 | jq '.[] | {title, price, seller_name}'
```

### 3. Найти выгодные предложения

```bash
curl "http://localhost:8000/bikes?bike_type=road&min_price=300&max_price=1000" | jq '.[] | {title, price}'
```

### 4. Анализ цен

```bash
curl http://localhost:8000/price-analysis | jq '.'
```

---

## 🎯 Что дальше?

- 📖 Полная документация: [README.md](README.md)
- 📚 Примеры использования: [USAGE.md](USAGE.md)
- 🔧 Расширенная конфигурация: [config.py](config.py)

---

## 💡 Полезные советы

- Парсер запускается автоматически каждые 10 минут
- Первый парсинг может занять 1-2 минуты
- Изображения скачиваются автоматически в папку `images/`
- Все данные хранятся в PostgreSQL
- API документация доступна на `/docs`

---

## 📞 Быстрая помощь

| Проблема | Решение |
|----------|---------|
| БД не подключается | Проверь PostgreSQL и CONNECTION STRING |
| API не запускается | Убедись что порт 8000 свободен |
| Парсер не работает | Проверь интернет и логи в `logs/scraper.log` |
| Нет данных в БД | Подожди первый парсинг (5-10 минут) |

---

**Готово! Система работает 🚀**

API документация: http://localhost:8000/docs
Данные: http://localhost:8000/bikes
