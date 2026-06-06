# 🚀 РАЗВЕРТЫВАНИЕ НА RAILWAY

## ✅ СТАТУС

✅ Code: Все коммиты запушены на GitHub  
✅ Repository: https://github.com/investgio7-max/bike-scraper  
✅ Branch: main  
✅ Ready: YES

---

## 📋 ШАГ 1: Войти в Railway

```bash
railway login
```

Это откроет браузер для авторизации на https://railway.app

---

## 📋 ШАГ 2: Создать/Выбрать Проект

### Вариант A: Через Railway Dashboard (рекомендуется)

1. Перейти на https://railway.app/dashboard
2. Нажать "New Project"
3. Выбрать "Deploy from GitHub repo"
4. Выбрать `investgio7-max/bike-scraper`
5. Выбрать branch `main`
6. Нажать "Deploy"

### Вариант B: Через Railway CLI

```bash
railway project list
railway project link <project_id>
```

---

## 📋 ШАГ 3: Настроить Environment Variables

В Railway Dashboard перейти в Settings → Variables и добавить:

```
WALLAPOP_KEYWORDS=Canyon Aeroad CF SLX
SCRAPE_INTERVAL=600
LOG_LEVEL=INFO
CLAUDE_API_KEY=<optional, для image analysis>
```

PostgreSQL DATABASE_URL автоматически добавляется Railway!

---

## 📋 ШАГ 4: Добавить PostgreSQL Database

1. В Railway Dashboard нажать "Add Service"
2. Выбрать "Database"
3. Выбрать "PostgreSQL"
4. Railway автоматически добавит DATABASE_URL

---

## 📋 ШАГ 5: Развернуть

### Через Dashboard:
- Просто нажать "Deploy" в Railway Dashboard
- Система автоматически:
  - Читает `railway.toml` и `railway.json`
  - Собирает Docker образ
  - Запускает контейнеры
  - Инициализирует БД

### Через CLI:
```bash
cd /Users/oleg/bike-scraper
railway up
```

---

## 📊 ЧТО ПРОИЗОЙДЕТ ПРИ DEPLOYMENT

1. **Build Phase** (~2 минуты)
   - Собирается Docker образ
   - Устанавливаются зависимости из requirements.txt
   - Проверяются переменные окружения

2. **Database Phase** (~1 минута)
   - Инициализируется PostgreSQL
   - Создаются 8 таблиц
   - Добавляются индексы

3. **Startup Phase** (~30 сек)
   - Запускается Scheduler (скрейпинг каждые 10 мин)
   - Запускается FastAPI API на port 3000
   - CloakBrowser инициализируется

4. **Ready** (~30 сек)
   - Система готова
   - API доступен по URL: `https://<your-project>.railway.app`

---

## 🎯 ПРОВЕРИТЬ DEPLOYMENT

```bash
# Лайвные логи
railway logs -f

# Или через Dashboard → Logs
```

Ищите эти логи:

```
✅ CloakBrowser (stealth) запущен
✅ Страница браузера инициализирована
📋 Найдено X объявлений на странице 1
✅ Найдено X объявлений
💾 Подключено к PostgreSQL
✨ Сервис API запущен на :3000
```

---

## 🌐 ПРОВЕРИТЬ API

```bash
# Health check
curl https://<your-project>.railway.app/health

# Get all bikes
curl https://<your-project>.railway.app/bikes

# Get new listings
curl https://<your-project>.railway.app/new

# Search
curl "https://<your-project>.railway.app/search?q=Dura-Ace"

# Statistics
curl https://<your-project>.railway.app/statistics
```

---

## 🔧 TROUBLESHOOTING

### API не ответил
```bash
# Проверить логи
railway logs -f

# Проверить статус
railway status
```

### DATABASE_URL отсутствует
1. Railway Dashboard → Services
2. Проверить что PostgreSQL добавлена
3. Перезапустить: `railway restart`

### Скрейпер не находит объявления
1. Проверить WALLAPOP_KEYWORDS переменную
2. Проверить логи для CloakBrowser errors
3. Может потребоваться прокси (see config.py)

### Port уже занят
Railway автоматически выбирает free port
Проверить в логах: `запущен на :3000`

---

## 📈 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ

### После первого запуска (5 минут):
- ✅ API работает
- ✅ PostgreSQL инициализирован
- ✅ Первое объявление распарсено

### Через 10 минут:
- ✅ Первый цикл скрейпинга завершен
- ✅ 50-100 объявлений в БД
- ✅ API возвращает данные

### Через 1 час:
- ✅ 200+ объявлений
- ✅ Дедупликация работает
- ✅ Цены отслеживаются

### Через 1 день:
- ✅ 500-1000 объявлений
- ✅ Готова к анализу
- ✅ Market trends видны

---

## 💡 PRO TIPS

1. **Мониторинг**: Use Railway Dashboard → Metrics
2. **Масштабирование**: Railway → Services → Scale (если нужны ресурсы)
3. **Custom domain**: Railway → Settings → Domains
4. **Email alerts**: Railway → Settings → Notifications

---

## ✅ DEPLOYMENT CHECKLIST

- [ ] GitHub token работает
- [ ] Code запушен на GitHub
- [ ] Railway CLI установлен (`railway --version`)
- [ ] Авторизация на Railway (`railway login`)
- [ ] PostgreSQL будет добавлена (автоматически)
- [ ] Environment variables добавлены
- [ ] Deployment запущен
- [ ] API отвечает на запросы
- [ ] Логи показывают скрейпинг
- [ ] Данные в БД

---

## 🎉 ГОТОВО!

**Система запущена и работает 24/7 на Railway!** 🚀

Объявления парсятся каждые 10 минут.  
API доступен по уникальному URL.  
Данные сохраняются в PostgreSQL.

---

**Next:** Monitor via Railway Dashboard or `railway logs -f`
