"""
Подключение и управление БД
"""

from sqlalchemy import create_engine, pool, event
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import logging

from bike_scraper.config import DATABASE_URL, DEBUG
from bike_scraper.models import Base

logger = logging.getLogger(__name__)

# Создаем engine с пулингом соединений
engine = create_engine(
    DATABASE_URL,
    poolclass=pool.QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,  # Проверяем соединение перед использованием
    echo=DEBUG,
)

# Логируем SQL в debug режиме
if DEBUG:
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        logger.debug(f"SQL: {statement}")


# Factory для создания сессий
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def init_db():
    """Инициализирует все таблицы в БД"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        raise


def get_db() -> Session:
    """Получить сессию БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager для работы с БД"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Ошибка БД: {e}")
        raise
    finally:
        db.close()


def get_session() -> Session:
    """Создать новую сессию"""
    return SessionLocal()


def close_db():
    """Закрыть пул соединений"""
    engine.dispose()
    logger.info("📊 Соединение с БД закрыто")
