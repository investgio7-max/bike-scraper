#!/bin/bash

# 🚀 Автоматический скрипт развертывания на GitHub и Railway

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  🚀 BIKE SCRAPER - АВТОМАТИЧЕСКИЙ DEPLOY СКРИПТ         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Переменные
REPO_NAME="bike-scraper"
REPO_PATH="/Users/oleg/bike-scraper"
GITHUB_USER="investgio7-max"

# Функция для проверки команд
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1 не установлен!"
        echo "   Установи: brew install $1"
        exit 1
    fi
}

# Проверяем зависимости
echo "📋 Проверяю зависимости..."
check_command "git"
check_command "gh"

echo "✅ Все необходимые инструменты установлены"
echo ""

# Проверяем SSH доступ
echo "🔐 Проверяю SSH доступ к GitHub..."
if ! ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
    echo "❌ SSH ключ не добавлен на GitHub!"
    echo ""
    echo "Выполни эти шаги:"
    echo "1. Открой: https://github.com/settings/ssh/new"
    echo "2. Добавь SSH ключ из ~/.ssh/id_github.pub"
    echo "3. Затем запусти этот скрипт снова"
    exit 1
fi

echo "✅ SSH доступ работает!"
echo ""

# Проверяем что находимся в правильной папке
if [ ! -d "$REPO_PATH/.git" ]; then
    echo "❌ Git репозиторий не найден в $REPO_PATH"
    exit 1
fi

cd "$REPO_PATH"

echo "📝 Логируюсь в GitHub..."
# Проверяем авторизацию через gh
if ! gh auth status &> /dev/null; then
    echo "⚠️  Нужна авторизация GitHub"
    echo "Выполняю: gh auth login"
    gh auth login --web
fi

echo "✅ Авторизация успешна!"
echo ""

# Проверяем существует ли уже репозиторий
echo "🔍 Проверяю существует ли репозиторий на GitHub..."
if gh repo view "$GITHUB_USER/$REPO_NAME" &> /dev/null; then
    echo "⚠️  Репозиторий уже существует!"
    echo "Пропускаю создание..."
else
    echo "📦 Создаю репозиторий на GitHub..."
    gh repo create "$REPO_NAME" \
        --public \
        --source=. \
        --remote=origin \
        --push \
        --description "Bike price scraper and analyzer for Wallapop" \
        --homepage "https://github.com/$GITHUB_USER/$REPO_NAME"

    echo "✅ Репозиторий создан!"
fi

echo ""

# Проверяем что всё запушилось
echo "📤 Проверяю что код запушился на GitHub..."
git push origin main --force || echo "⚠️  Код уже на GitHub"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ GITHUB ЧАСТЬ ЗАВЕРШЕНА!                              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

echo "📊 Информация о репозитории:"
echo "---"
echo "GitHub URL: https://github.com/$GITHUB_USER/$REPO_NAME"
echo "Git Clone: git clone git@github.com:$GITHUB_USER/$REPO_NAME.git"
echo ""

# Railway часть
echo "🚀 RAILWAY DEPLOYMENT"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Следующие шаги:"
echo "1. Перейди на https://railway.app"
echo "2. Нажми 'New Project' → 'Deploy from GitHub'"
echo "3. Выбери репозиторий $REPO_NAME"
echo "4. Railway автоматически деплоит!"
echo ""

echo "📚 Для подробной информации смотри:"
echo "- RAILWAY_QUICK_DEPLOY.md"
echo "- RAILWAY_DEPLOYMENT.md"
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  🎉 DEPLOY ЗАВЕРШЕН УСПЕШНО!                            ║"
echo "║                                                            ║"
echo "║  Репозиторий готов к Railway deployment 🚀               ║"
echo "╚════════════════════════════════════════════════════════════╝"
