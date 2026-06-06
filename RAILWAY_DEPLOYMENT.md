# 🚀 Развертывание на Railway

Инструкция по развертыванию Bike Scraper на платформе Railway.

---

## 📋 Требования

- Railway аккаунт (https://railway.app)
- Railway CLI установлен (опционально)
- GitHub репозиторий (рекомендуется)

---

## 🚀 Способ 1: Через GitHub (рекомендуется)

### Шаг 1: Push в GitHub

```bash
git add .
git commit -m "Add bike scraper system"
git push origin main
```

### Шаг 2: Создать Railway проект

1. Перейди на https://railway.app
2. Нажми "New Project"
3. Выбери "Deploy from GitHub"
4. Подключи свой GitHub репозиторий
5. Выбери репозиторий `betbet`

### Шаг 3: Настроить сервисы

#### Основное приложение (Scraper)

1. Railway автоматически обнаружит Dockerfile
2. В "Settings" укажи:
   - **Builder:** Dockerfile
   - **Dockerfile path:** `bike_scraper/Dockerfile`
   - **Root directory:** `bike_scraper`

#### PostgreSQL база данных

1. Нажми "Add Service" → "Add from Marketplace"
2. Выбери "PostgreSQL"
3. Railway автоматически создаст инстанс

### Шаг 4: Переменные окружения

В Railway Dashboard добавь переменные:

```bash
DATABASE_URL=postgresql://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/bike_scraper
SCRAPE_INTERVAL=600
MAX_RESULTS=100
LOG_LEVEL=INFO
DOWNLOAD_IMAGES=True
DEBUG=False
PYTHONUNBUFFERED=1
```

#### Где взять переменные Postgres:

Railway автоматически создаст переменные для PostgreSQL:
- `${{Postgres.PGUSER}}`
- `${{Postgres.PGPASSWORD}}`
- `${{Postgres.PGHOST}}`
- `${{Postgres.PGPORT}}`

Они будут доступны в разделе "Variables"

### Шаг 5: Развертывание

1. Railway автоматически начнет деплой
2. Смотри логи в Dashboard
3. После успешного деплоя приложение будет доступно

---

## 🚀 Способ 2: Railway CLI (локально)

### Установка

```bash
# macOS
brew install railway

# Linux/Windows
npm install -g @railway/cli
```

### Логин

```bash
railway login
```

### Инициализация проекта

```bash
cd /Users/oleg/betbet
railway init
```

Выбери:
- Название проекта: `bike-scraper`
- Environment: `production`

### Добавить PostgreSQL

```bash
railway add
# Выбери PostgreSQL
```

### Развертывание

```bash
# Деплой приложения
railway up

# Или деплой сервиса
railway deploy --service scraper
```

### Просмотр логов

```bash
railway logs -f
```

### Переменные окружения

```bash
railway variables set DATABASE_URL=postgresql://...
railway variables set SCRAPE_INTERVAL=600
# И остальные
```

---

## 🔧 Конфигурация

### railway.json (в папке bike_scraper)

```json
{
  "build": {
    "builder": "dockerfile"
  },
  "deploy": {
    "startCommand": "python scheduler.py"
  },
  "env": {
    "PYTHONUNBUFFERED": "1"
  }
}
```

### Dockerfile

Уже готов в `bike_scraper/Dockerfile`

---

## 📊 Два варианта развертывания

### Вариант 1: Только Scraper (рекомендуется для начала)

- Парсер работает непрерывно
- Данные сохраняются в PostgreSQL
- Экономнее по ресурсам

```bash
# В railway.json указать:
"startCommand": "python scheduler.py"
```

### Вариант 2: Scraper + API

Два отдельных сервиса:

#### Сервис 1: Scraper

```json
{
  "startCommand": "python scheduler.py"
}
```

#### Сервис 2: API

```json
{
  "startCommand": "python api_main.py"
}
```

В этом случае нужно создать два сервиса в Railway Dashboard.

---

## 🔐 Переменные окружения (полный список)

```bash
# Database (ОБЯЗАТЕЛЬНО)
DATABASE_URL=postgresql://user:pass@host:5432/bike_scraper

# Scraping
SCRAPE_INTERVAL=600              # каждые 10 минут
MAX_RESULTS=100
REQUEST_TIMEOUT=30

# Images
DOWNLOAD_IMAGES=True
IMAGES_DIR=/tmp/images           # Railway ограничивает хранилище
MAX_IMAGE_SIZE_MB=10

# Logging
LOG_LEVEL=INFO
LOG_FILE=/tmp/logs/scraper.log

# System
PYTHONUNBUFFERED=1
DEBUG=False
HEADLESS_BROWSER=True

# API (если используешь)
API_HOST=0.0.0.0
API_PORT=8000
```

---

## ⚠️ Важно для Railway

### Хранилище изображений

Railway имеет эфемерное хранилище (исчезает при перезагрузке). Решения:

#### Вариант 1: Отключить скачивание изображений
```bash
DOWNLOAD_IMAGES=False
```

#### Вариант 2: Использовать Railway Volume

1. В Railway Dashboard
2. Add Volume
3. Mount path: `/app/images`
4. Size: 10GB

#### Вариант 3: S3 хранилище
```bash
# Добавить в config.py
USE_S3=True
S3_BUCKET=my-bike-scraper
S3_REGION=us-east-1
```

### Логи

Railway автоматически собирает логи из stdout/stderr. Проверяй в Dashboard.

### Дефолтный таймаут

Railway имеет таймаут на соединение. Убедись что:
- `REQUEST_TIMEOUT` достаточен
- `SCRAPE_INTERVAL` не слишком маленький

---

## ✅ Checklist развертывания

- [ ] GitHub репозиторий готов
- [ ] Dockerfile существует
- [ ] requirements.txt актуален
- [ ] DATABASE_URL настроена
- [ ] PostgreSQL добавлена
- [ ] Переменные окружения установлены
- [ ] Логи просматриваются в Dashboard
- [ ] Парсер успешно работает
- [ ] API доступен (если используется)

---

## 🐛 Troubleshooting

### "Module not found"

```
ModuleNotFoundError: No module named 'sqlalchemy'
```

**Решение:**
- Убедись что `requirements.txt` в корне проекта или в `bike_scraper/`
- Railway должен выполнить `pip install -r requirements.txt`

Если в подпапке:

```dockerfile
# В Dockerfile
WORKDIR /app/bike_scraper
COPY requirements.txt .
RUN pip install -r requirements.txt
```

### "Database connection failed"

```
psycopg2.OperationalError: could not connect to server
```

**Решение:**
- Проверь что PostgreSQL сервис запущен
- Проверь DATABASE_URL (особенно пароль)
- В Railway Variables используй правильный синтаксис

```bash
# ПРАВИЛЬНО
DATABASE_URL=postgresql://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:5432/bike_scraper

# НЕПРАВИЛЬНО
DATABASE_URL=postgresql://user:pass@localhost:5432/...
```

### "Application crashed"

Посмотри логи в Railway Dashboard:

```
railway logs -f
```

Ищи ошибки в последних строках.

### "Port already in use"

Если используешь API сервис:

```
Address already in use
```

**Решение:**
- В Dockerfile убедись что приложение слушает на правильном порту
- В railway.json укажи правильный порт

```json
{
  "env": {
    "PORT": "8000"
  }
}
```

---

## 📈 Мониторинг

### Логи в Railway

```bash
# Просмотр логов
railway logs -f

# Последние 100 строк
railway logs --limit 100

# Поиск ошибок
railway logs | grep ERROR
```

### Метрики

Railway Dashboard показывает:
- CPU использование
- Память
- Network трафик
- Статус приложения

### Уведомления

1. Railway Dashboard → Settings
2. Enable notifications
3. Выбери канал (Email, Slack, etc.)

---

## 🔄 CI/CD

Railway автоматически:
- Смотрит на изменения в GitHub
- При каждом push в main ветку
- Автоматически деплоит новую версию

Можно отключить в Railway Settings если нужно.

---

## 💰 Стоимость

Railway использует pay-as-you-go модель:
- Первые 5$ в месяц бесплатно
- PostgreSQL: ~$0.50/день
- Приложение: зависит от ресурсов
- Хранилище: ~$0.10/GB/месяц

**Для Bike Scraper:**
- Примерная стоимость: $10-20/месяц

---

## 🚀 Готово к развертыванию!

Начни с GitHub метода (способ 1) - это самый простой способ.

**Вопросы?** Посмотри документацию Railway: https://docs.railway.app

---

**Happy deploying! 🚀**
