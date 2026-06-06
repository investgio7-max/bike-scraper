# 🚀 Railway - Быстрый деплой

Развернуть Bike Scraper на Railway за 5 минут!

---

## ⚡ Самый быстрый способ (через GitHub)

### 1️⃣ Push в GitHub

```bash
git add .
git commit -m "Deploy bike scraper to Railway"
git push origin main
```

### 2️⃣ На Railway Dashboard

1. Перейди на https://railway.app
2. Нажми **"New Project"**
3. **"Deploy from GitHub"**
4. Выбери репозиторий **`betbet`**
5. Выбери branch **`main`**

### 3️⃣ Автоматическая конфигурация

Railway обнаружит:
- ✅ Dockerfile в `bike_scraper/Dockerfile`
- ✅ requirements.txt
- ✅ railway.toml

### 4️⃣ Добавить PostgreSQL

1. **"Add Service"** → **"Add from Marketplace"**
2. **Выбери "PostgreSQL"**
3. Railway создаст инстанс автоматически

### 5️⃣ Переменные окружения

Railway Dashboard → **"Variables"** → добавь:

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
SCRAPE_INTERVAL=600
MAX_RESULTS=100
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
```

Или просто скопируй все из `.env.example` в Variables.

### 6️⃣ Deploy!

Готово! Railway начнет деплой автоматически.

---

## 📊 Результат

После успешного деплоя у тебя будет:

✅ **Скрейпер работает** 24/7  
✅ **PostgreSQL** хранит данные  
✅ **Логи видны** в Dashboard  
✅ **Всё настроено** автоматически  

---

## 📝 Что где находится в Railway

| Что | Где |
|------|-----|
| Логи парсера | Dashboard → "Logs" |
| Переменные | Dashboard → "Variables" |
| БД подключение | PostgreSQL → "Connect" |
| Метрики | Dashboard → "Metrics" |
| Настройки | Dashboard → "Settings" |

---

## 🔗 Важные ссылки

- Twoj Dashboard: https://railway.app/dashboard
- Документация: https://docs.railway.app
- GitHub интеграция: https://railway.app/integrations/github

---

## ❓ FAQ

**Q: Нужен ли Railway CLI?**  
A: Нет, GitHub интеграция сама всё сделает.

**Q: Где мой API?**  
A: По умолчанию парсер работает. Если нужен API, создай второй сервис.

**Q: Как проверить что работает?**  
A: Посмотри логи в Railway Dashboard.

**Q: Как остановить парсер?**  
A: Dashboard → "Remove" или отключи сервис.

**Q: Стоит ли это денег?**  
A: Первые 5$ в месяц бесплатно. Далее ~$10-20/месяц.

---

## 🎯 Готово!

Система работает на Railway и парсит велосипеды 24/7! 🚀

