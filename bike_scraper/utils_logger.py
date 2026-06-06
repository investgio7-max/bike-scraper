"""
Логирование для скрейпера
"""

import logging
import logging.handlers
from pathlib import Path
from bike_scraper.config import LOG_LEVEL, LOG_FILE

# Создаем папку для логов
log_dir = Path(LOG_FILE).parent
log_dir.mkdir(parents=True, exist_ok=True)

# Основной логгер
logger = logging.getLogger('bike_scraper')
logger.setLevel(getattr(logging, LOG_LEVEL))

# Format для логов
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Handler для файла (ротирующийся)
file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE,
    maxBytes=10 * 1024 * 1024,  # 10 МБ
    backupCount=5
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Handler для консоли
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Подавляем verbose логи от библиотек
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)


def get_logger(name: str = None) -> logging.Logger:
    """Получить логгер для модуля"""
    if name:
        return logging.getLogger(f'bike_scraper.{name}')
    return logger
