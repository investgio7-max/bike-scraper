# 🚀 START HERE - Велосипедный скрейпер готов!

## ⚡ Быстро начни за 5 минут

### Вариант 1: Docker (самый простой)
```bash
cd bike_scraper
docker-compose up -d
```
Готово! 🎉

### Вариант 2: Локально
```bash
cd bike_scraper
pip install -r requirements.txt
python init_project.py
python scheduler.py &
python api_main.py
```

---

## 🎯 Что дальше?

### 1️⃣ Проверь что работает
```bash
# Здоровье системы
curl http://localhost:8000/health

# Все велосипеды
curl http://localhost:8000/bikes | jq '.'

# Документация API
open http://localhost:8000/docs
```

### 2️⃣ Просмотри логи
```bash
tail -f logs/scraper.log
```

### 3️⃣ Подожди первый парсинг (5-10 минут)

---

## 📖 Документация (в порядке чтения)

1. **[QUICKSTART.md](QUICKSTART.md)** ⚡
   - Быстрый старт
   - Простые примеры

2. **[README.md](README.md)** 📚
   - Полная информация
   - Все возможности

3. **[USAGE.md](USAGE.md)** 📖
   - Примеры кода
   - API примеры
   - Советы

4. **[ARCHITECTURE.md](ARCHITECTURE.md)** 🏗️
   - Как всё устроено
   - Диаграммы
   - Data flow

5. **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** 📋
   - Обзор проекта
   - Список файлов

---

## 📦 Что это?

✅ **Система для парсинга объявлений о велосипедах** на Wallapop  
✅ **Непрерывный мониторинг** каждые 10 минут  
✅ **REST API** для доступа к данным  
✅ **PostgreSQL** для хранения данных  
✅ **Защита от блокировок** встроенная  
✅ **Готов к production** с Docker  

---

## 🗂️ Структура проекта

```
bike_scraper/
├── 🔧 Основной код (12 файлов)
│   ├── config.py              ⚙️ Конфигурация
│   ├── models.py              🗄️ База данных
│   ├── scraper_wallapop.py    🕷️ Парсер
│   ├── api_main.py            🌐 REST API
│   ├── scheduler.py           ⏱️ Расписание
│   └── utils_*.py             🔧 Утилиты
│
├── 📚 Документация (7 файлов)
│   ├── README.md              📖 Полное описание
│   ├── QUICKSTART.md          ⚡ Быстрый старт
│   ├── USAGE.md               📖 Примеры
│   ├── ARCHITECTURE.md        🏗️ Архитектура
│   ├── PROJECT_SUMMARY.md     📋 Обзор
│   ├── FILES_CREATED.md       📋 Список файлов
│   └── START_HERE.md          👈 ТЫ ЗДЕСЬ
│
└── 🐳 Docker (5 файлов)
    ├── docker-compose.yml
    ├── Dockerfile
    ├── .env.example
    ├── requirements.txt
    └── .gitignore
```

---

## 🎯 Основные возможности

### Парсинг
- Поиск велосипедов на Wallapop
- Извлечение параметров из текста
- Скачивание всех изображений

### Хранение
- PostgreSQL база данных
- 8 таблиц для организации данных
- История цен

### API
- 12+ эндпоинтов
- Фильтрация и поиск
- Статистика и анализ
- Swagger документация

### Защита
- curl_cffi для имитации браузера
- Ротация User-Agent
- Случайные задержки
- Поддержка прокси

---

## 🚀 Быстрые команды

```bash
# Запуск (выбери один)
docker-compose up -d                    # Docker (рекомендуется)
python scheduler.py & python api_main.py # Локально

# Проверка
curl http://localhost:8000/health       # Здоровье
curl http://localhost:8000/bikes        # Данные
curl http://localhost:8000/docs         # API документация

# Логи
tail -f logs/scraper.log                # Просмотр в реальном времени

# Остановка
docker-compose down                     # Docker
pkill -f scheduler                      # Локально
```

---

## ⚙️ Основные параметры (.env)

```bash
# БД (обязательно)
DATABASE_URL=postgresql://user:password@localhost:5432/bike_scraper

# Парсинг
SCRAPE_INTERVAL=600          # Каждые 10 минут
MAX_RESULTS=100              # Макс объявлений за раз

# API
API_HOST=0.0.0.0
API_PORT=8000

# Другое
LOG_LEVEL=INFO
DOWNLOAD_IMAGES=True
DEBUG=False
```

Полный список в: `.env.example`

---

## 🐛 Если что-то не работает

| Проблема | Решение |
|----------|---------|
| БД не подключается | Проверь PostgreSQL и CONNECTION STRING |
| API не запускается | Убедись что порт 8000 свободен |
| Нет данных | Подожди первый парсинг (5-10 минут) |
| Ошибки парсинга | Посмотри `logs/scraper.log` |

---

## 📊 Примеры использования

### Python
```python
from database import get_session
from models import Listing

db = get_session()
bikes = db.query(Listing).limit(10).all()
for bike in bikes:
    print(f"{bike.title} - €{bike.price}")
db.close()
```

### REST API
```bash
# Последние велосипеды
curl http://localhost:8000/new

# Road bikes дешевле 1000€
curl "http://localhost:8000/bikes?bike_type=road&max_price=1000"

# Поиск
curl "http://localhost:8000/search?q=canyon"
```

### SQL
```sql
-- Самые дешевые
SELECT title, price FROM listings 
WHERE is_active = TRUE 
ORDER BY price 
LIMIT 10;
```

---

## ✨ Основные файлы для изучения

1. **config.py** - все настройки
2. **models.py** - структура БД
3. **scraper_wallapop.py** - как парсит
4. **api_main.py** - API эндпоинты
5. **scheduler.py** - как планирует парсинг

---

## 🎓 Технологический стек

- **Python 3.11** — язык
- **PostgreSQL** — база данных
- **FastAPI** — REST API
- **SQLAlchemy** — ORM
- **curl_cffi** — парсинг
- **Docker** — контейнеризация

---

## 📞 Помощь

- Документация: [README.md](README.md)
- Примеры: [USAGE.md](USAGE.md)
- Архитектура: [ARCHITECTURE.md](ARCHITECTURE.md)
- Быстрый старт: [QUICKSTART.md](QUICKSTART.md)

---

## 🎉 Готово!

Система полностью работоспособна и готова к использованию.

**Начни с Docker:**
```bash
docker-compose up -d
```

**Или локально:**
```bash
python init_project.py
python scheduler.py &
python api_main.py
```

**API документация:** http://localhost:8000/docs 📚

---

**Created with ❤️ by Claude Code** 🚀
