# ⚡ Telegram Бот - Быстрый Старт

Минимум информации для начала использования Telegram бота.

## 🚀 За 5 минут

### 1. Создать бота (2 мин)

- Откройте Telegram → найдите `@BotFather`
- Отправьте `/newbot`
- Выберите имя и username
- Скопируйте токен

### 2. Установить на Railway (2 мин)

- Railway Dashboard → Variables
- Добавьте: `TELEGRAM_BOT_TOKEN = ваш_токен`
- Сохраните (перестарт автоматический)

### 3. Проверить (1 мин)

- Откройте Telegram
- Напишите боту `/start`
- Если ответил - готово! ✅

---

## 🎮 Основные команды

| Команда | Что делает | Пример |
|---------|-----------|--------|
| `/start` | Запуск бота | `/start` |
| `/help` | Справка | `/help` |
| `/status` | Статус системы | `/status` |
| `/stats` | Статистика рынка | `/stats` |
| `/deals` | Дешевые велосипеды | `/deals Canyon` |
| `/add_search` | Мониторить | `/add_search Canyon Aeroad` |
| `/list_searches` | Мои поиски | `/list_searches` |
| `/remove_search` | Удалить поиск | `/remove_search 1` |

---

## 💡 Примеры

### Найти дешевый Canyon

```
/add_search Canyon
↓ (ждем уведомления о новых объявлениях)
/deals Canyon
↓ (смотрим лучшие предложения)
```

### Мониторить Specialized

```
/add_search Specialized Tarmac
↓ (теперь каждый новый Tarmac → уведомление)
/list_searches
↓ (видим что уже мониторим)
/price_analysis Specialized
↓ (видим тренды цен)
```

### Удалить ненужный поиск

```
/list_searches
↓ (видим ID поиска который не нужен)
/remove_search 2
↓ (удалено)
```

---

## 🔔 Автоматические уведомления

Бот сам отправляет:

**🆕 Новое объявление**
```
Найден новый велосипед из вашего поиска
[Кнопка "Посмотреть"]
```

**📉 Цена упала**
```
Canyon Aeroad упал в цене на €500!
[Кнопка "Посмотреть"]
```

Уведомления приходят автоматически когда:
- Появляется новое объявление
- Цена падает на сумму больше чем порог (по умолчанию €50)

---

## 📱 Мой ID в Telegram

Чтобы узнать свой ID:
1. Откройте Telegram
2. Найдите `@userinfobot`
3. Отправьте `/start`
4. Видите `Your user ID: 123456789`

Он нужен для REST API (если будете использовать программно).

---

## 🔗 REST API

Если хотите управлять ботом программно:

```bash
# Добавить поиск
curl -X POST "http://api.example.com/monitoring/add-search?user_id=123456&search_term=Canyon"

# Список поисков
curl "http://api.example.com/monitoring/searches?user_id=123456"

# Удалить поиск
curl -X DELETE "http://api.example.com/monitoring/searches/1"

# Статус мониторинга
curl "http://api.example.com/monitoring/status"
```

---

## 🆘 Что-то не работает?

### Бот не отвечает
- Проверьте что токен установлен на Railway
- Перезагрузите приложение: Railway → Deploy

### Нет уведомлений
- Проверьте список поисков: `/list_searches`
- Дождитесь 5 минут (проверка каждые 5 мин)
- Проверьте что объявления есть: `/deals`

### Ошибка при добавлении поиска
- Проверьте что название написано правильно
- Убедитесь что на Wallapop есть такие объявления

---

## 📚 Где найти помощь?

- **Все команды:** `/help`
- **Полная документация:** [TELEGRAM_BOT_GUIDE.md](./TELEGRAM_BOT_GUIDE.md)
- **Настройка:** [TELEGRAM_SETUP.md](./TELEGRAM_SETUP.md)
- **GitHub:** https://github.com/investgio7-max/bike-scraper

---

## 🎯 Типичный flow

```
День 1:
  /add_search Canyon Aeroad
  /add_search Specialized Tarmac

День 2:
  📬 Получаю уведомление: "Новый Canyon!"
  /deals Canyon
  😊 Нашел хороший велосипед!

День 7:
  /stats
  📊 Анализирую рынок
  /price_analysis Specialized
  📈 Вижу что цены падают
```

---

**Готово к использованию! Напишите боту и начните мониторить велосипеды! 🚴**
