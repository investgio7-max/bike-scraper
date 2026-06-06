# 📝 Подключение к GitHub

Инструкция по добавлению репозитория на GitHub.

---

## 1️⃣ Создать репозиторий на GitHub

1. Перейди на https://github.com/new
2. Введи название: `bike-scraper`
3. Описание (опционально): "Bike price scraper and analyzer for Wallapop"
4. Выбери **Public** или **Private**
5. **Не** инициализируй README/gitignore (они уже есть)
6. Нажми **"Create repository"**

---

## 2️⃣ Добавить remote и push

```bash
cd /Users/oleg/bike-scraper

# Добавить remote
git remote add origin https://github.com/YOUR_USERNAME/bike-scraper.git

# Или через SSH (если SSH ключи настроены)
git remote add origin git@github.com:YOUR_USERNAME/bike-scraper.git

# Push в GitHub
git branch -M main
git push -u origin main
```

Замени `YOUR_USERNAME` на свой GitHub username.

---

## 3️⃣ Проверить на GitHub

Перейди на https://github.com/YOUR_USERNAME/bike-scraper

Должны быть видны:
- ✅ Папка `bike_scraper/`
- ✅ Файл `README.md`
- ✅ Файл `RAILWAY_QUICK_DEPLOY.md`
- ✅ railway.toml конфиг

---

## 🚀 Теперь готов для Railway!

1. Перейди на https://railway.app
2. **"New Project"** → **"Deploy from GitHub"**
3. Подключи GitHub
4. Выбери **`bike-scraper`** репозиторий
5. Railway автоматически деплоит!

---

## 🔄 GitHub URLs

После создания репозитория:

- **HTTPS:** `https://github.com/YOUR_USERNAME/bike-scraper.git`
- **SSH:** `git@github.com:YOUR_USERNAME/bike-scraper.git`
- **GitHub:** `https://github.com/YOUR_USERNAME/bike-scraper`

---

## 💡 Полезные команды

```bash
# Проверить remote
git remote -v

# Изменить remote
git remote set-url origin NEW_URL

# Синхронизироваться с GitHub
git pull origin main

# Отправить изменения
git push origin main
```

---

## ✅ Готово!

Теперь ты имеешь:
- ✅ Локальный git репозиторий на машине
- ✅ GitHub репозиторий в облаке
- ✅ Готовность к Railway deployment

**Следующий шаг:** [RAILWAY_QUICK_DEPLOY.md](RAILWAY_QUICK_DEPLOY.md)
