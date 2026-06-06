#!/usr/bin/env python3
"""
Скрипт инициализации проекта Bike Scraper
"""

import os
import sys
from pathlib import Path

def create_directories():
    """Создать необходимые директории"""
    dirs = [
        'images',
        'logs',
        'data',
    ]

    for dir_name in dirs:
        dir_path = Path(dir_name)
        dir_path.mkdir(exist_ok=True)
        print(f"✅ Создана директория: {dir_path}")


def create_env_file():
    """Создать .env файл из примера"""
    env_example = Path('.env.example')
    env_file = Path('.env')

    if env_file.exists():
        print(f"⚠️  Файл .env уже существует")
        return

    if not env_example.exists():
        print(f"❌ Не найден .env.example")
        return

    # Копируем
    with open(env_example, 'r') as f:
        content = f.read()

    with open(env_file, 'w') as f:
        f.write(content)

    print(f"✅ Создан .env файл (из .env.example)")
    print(f"   Отредактируй .env с правильными значениями!")


def init_database():
    """Инициализировать БД"""
    print("\n📊 Инициализирую БД...")

    try:
        from database import init_db
        init_db()
        print("✅ БД инициализирована")
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        print(f"   Убедись что PostgreSQL запущен")
        print(f"   И CONNECTION STRING правильный в .env")


def check_dependencies():
    """Проверить установлены ли зависимости"""
    print("\n📦 Проверяю зависимости...")

    required = [
        'fastapi',
        'sqlalchemy',
        'psycopg2',
        'curl_cffi',
        'beautifulsoup4',
    ]

    missing = []

    for package in required:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} НЕ установлен")
            missing.append(package)

    if missing:
        print(f"\n❌ Установи зависимости:")
        print(f"   pip install -r requirements.txt")
        return False

    return True


def test_database_connection():
    """Тестировать подключение к БД"""
    print("\n🔗 Тестирую подключение к БД...")

    try:
        from database import get_session
        db = get_session()
        db.execute("SELECT 1")
        db.close()
        print("✅ Подключение к БД работает")
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False


def main():
    """Главная функция"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║          🚴 BIKE SCRAPER - ИНИЦИАЛИЗАЦИЯ                 ║
╚═══════════════════════════════════════════════════════════╝

Этот скрипт подготовит проект к запуску.
    """)

    # 1. Создаем директории
    print("\n[1/4] Создание директорий...")
    create_directories()

    # 2. Создаем .env
    print("\n[2/4] Создание конфигурации...")
    create_env_file()

    # 3. Проверяем зависимости
    print("\n[3/4] Проверка зависимостей...")
    if not check_dependencies():
        print("\n❌ Установи зависимости перед продолжением")
        return

    # 4. Инициализируем БД
    print("\n[4/4] Инициализация БД...")
    if test_database_connection():
        init_database()
    else:
        print("\n⚠️  БД не подключена. Проверь конфигурацию PostgreSQL.")
        print("   Убедись что:")
        print("   1. PostgreSQL запущен")
        print("   2. БД 'bike_scraper' создана")
        print("   3. CONNECTION STRING правильный в .env")

    # Финал
    print(f"\n{'='*60}")
    print("✨ ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА!")
    print(f"{'='*60}")

    print("""
Что дальше:

1. 📝 Отредактируй .env файл с нужными значениями:
   - DATABASE_URL (PostgreSQL)
   - API_PORT (если нужен)
   - SCRAPE_INTERVAL (интервал парсинга)

2. 🚀 Запусти парсер:
   python scheduler.py

3. 📊 Или запусти API (в другом терминале):
   python api_main.py

4. 📖 Документация:
   http://localhost:8000/docs (после запуска API)

Логи находятся в: logs/scraper.log
    """)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Отменено")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
        sys.exit(1)
