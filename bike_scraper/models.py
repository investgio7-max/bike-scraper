"""
SQLAlchemy модели для велосипедов и объявлений
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, BigInteger, DateTime, Text, Boolean, JSON, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid

Base = declarative_base()


class Bike(Base):
    """Модель велосипеда с нормализованными данными"""
    __tablename__ = 'bikes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Основные параметры
    brand = Column(String(100), index=True)
    model = Column(String(100), index=True)
    version = Column(String(100))
    bike_type = Column(String(50), index=True)  # road, gravel, etc.
    year = Column(Integer)

    # Компоненты
    frame_size = Column(String(20))  # см или дюймы
    groupset = Column(String(100))
    wheels = Column(String(100))
    brakes = Column(String(100))
    drivetrain = Column(String(50))

    # Характеристики
    weight = Column(Float)  # кг
    frame_material = Column(String(50))  # carbon, aluminum, steel
    color = Column(String(50))
    condition = Column(String(50))  # new, like_new, good, fair

    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_bike_brand_model', 'brand', 'model'),
        Index('idx_bike_type', 'bike_type'),
    )


class Listing(Base):
    """Модель объявления"""
    __tablename__ = 'listings'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Идентификаторы
    source = Column(String(50), index=True)  # wallapop, olx, etc.
    listing_id = Column(String(255), index=True)  # ID на платформе
    url = Column(Text, unique=True)

    # Информация о товаре
    title = Column(Text)
    description = Column(Text)

    # Цена
    price = Column(Float, index=True)
    currency = Column(String(3), default='EUR')

    # Продавец
    seller_name = Column(String(255), index=True)
    seller_id = Column(String(255))
    seller_rating = Column(Float)
    seller_reviews_count = Column(Integer)

    # Локация
    location = Column(String(255), index=True)
    country = Column(String(100), index=True)

    # Даты
    date_posted = Column(DateTime)
    date_collected = Column(DateTime, default=datetime.utcnow, index=True)
    date_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Изображения
    images = Column(JSON)  # JSON array с URL и локальными путями
    main_image_url = Column(Text)
    main_image_path = Column(String(255))

    # Нормализованные параметры велосипеда
    bike_id = Column(UUID(as_uuid=True))
    frame_size = Column(String(20))
    bike_type = Column(String(50), index=True)

    # Сырые данные
    raw_data = Column(JSONB)

    # Статус
    is_active = Column(Boolean, default=True, index=True)
    is_duplicate = Column(Boolean, default=False)
    original_listing_id = Column(UUID(as_uuid=True))  # Если дубликат, указывает на оригинал

    # Метаданные
    parser_version = Column(String(50))
    extraction_errors = Column(JSON)

    # Метаданные для анализа
    scrapy_quality_score = Column(Float, default=0.0)  # Оценка качества парсинга
    market_value_estimate = Column(Float)  # Оценка рыночной стоимости
    profit_potential = Column(Float)  # Потенциальная прибыль

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('source', 'listing_id', name='uq_source_listing_id'),
        Index('idx_listing_source_date', 'source', 'date_collected'),
        Index('idx_listing_price_bike_type', 'price', 'bike_type'),
        Index('idx_listing_is_active', 'is_active'),
        Index('idx_listing_seller', 'seller_name', 'country'),
    )


class ListingHistory(Base):
    """История изменения цен и статуса объявлений"""
    __tablename__ = 'listing_history'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    listing_id = Column(UUID(as_uuid=True), index=True)
    source = Column(String(50))
    source_listing_id = Column(String(255))

    # Изменения
    price_old = Column(Float)
    price_new = Column(Float)

    is_active_old = Column(Boolean)
    is_active_new = Column(Boolean)

    change_type = Column(String(50))  # price_changed, removed, reactivated, etc.

    checked_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_history_listing', 'listing_id'),
        Index('idx_history_date', 'checked_at'),
    )


class ScraperLog(Base):
    """Логи парсера"""
    __tablename__ = 'scraper_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    source = Column(String(50), index=True)
    search_term = Column(String(255))

    # Результаты
    total_found = Column(Integer)
    successfully_parsed = Column(Integer)
    errors_count = Column(Integer)

    # Время
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)

    # Логи
    log_message = Column(Text)
    errors = Column(JSON)

    # Статус
    status = Column(String(50))  # success, partial, failed

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('idx_log_source_date', 'source', 'created_at'),
    )


class SellerProfile(Base):
    """Профили продавцов"""
    __tablename__ = 'seller_profiles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    source = Column(String(50), index=True)
    seller_id = Column(String(255), index=True)
    seller_name = Column(String(255))

    # Рейтинг
    rating = Column(Float)
    reviews_count = Column(Integer)

    # Статистика
    total_listings = Column(Integer, default=0)
    active_listings = Column(Integer, default=0)
    sold_listings = Column(Integer, default=0)

    # Средние цены (для анализа)
    avg_price = Column(Float)
    min_price = Column(Float)
    max_price = Column(Float)

    # Профиль продавца
    joined_date = Column(DateTime)
    response_time = Column(String(100))
    ship_on_time = Column(Float)  # процент

    # Локация
    location = Column(String(255))
    country = Column(String(100), index=True)

    # Метаданные
    raw_profile = Column(JSONB)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('source', 'seller_id', name='uq_seller_source_id'),
        Index('idx_seller_country', 'country'),
    )


class PriceAnalysis(Base):
    """Анализ цен по брендам/моделям"""
    __tablename__ = 'price_analysis'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Что анализируем
    brand = Column(String(100), index=True)
    model = Column(String(100), index=True)
    bike_type = Column(String(50), index=True)

    # Статистика
    total_listings = Column(Integer)
    avg_price = Column(Float)
    median_price = Column(Float)
    min_price = Column(Float)
    max_price = Column(Float)
    std_dev = Column(Float)

    # Тренд
    price_trend = Column(String(20))  # up, down, stable
    price_change_percent = Column(Float)  # % изменение за период

    # Спрос
    listings_per_week = Column(Float)
    avg_time_to_sell = Column(Float)  # дни

    # Период анализа
    period_start = Column(DateTime)
    period_end = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('brand', 'model', 'bike_type', 'period_start', name='uq_analysis_period'),
    )


class MonitoringSearch(Base):
    """Активные поиски пользователей для мониторинга"""
    __tablename__ = 'monitoring_searches'

    id = Column(Integer, primary_key=True)

    # Пользователь (Telegram ID)
    user_id = Column(Integer, index=True)

    # Поисковый запрос
    search_term = Column(String(255), index=True)

    # Параметры уведомлений
    is_active = Column(Boolean, default=True, index=True)
    notify_new_listings = Column(Boolean, default=True)
    notify_price_drop = Column(Boolean, default=True)
    price_drop_threshold = Column(Float)  # Оповещение если цена упала на X EUR

    # Статистика
    listings_found = Column(Integer, default=0)
    last_listing_id = Column(UUID(as_uuid=True))  # ID последнего найденного объявления
    last_checked = Column(DateTime, default=datetime.utcnow)

    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_monitoring_user_active', 'user_id', 'is_active'),
        Index('idx_monitoring_search_term', 'search_term'),
    )


class ListingNotification(Base):
    """Отслеживание отправленных уведомлений"""
    __tablename__ = 'listing_notifications'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Уведомление
    user_id = Column(Integer, index=True)
    search_id = Column(Integer)
    listing_id = Column(UUID(as_uuid=True), index=True)
    notification_type = Column(String(50))  # new_listing, price_drop

    # Статус
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime)

    # Данные объявления при отправке
    title = Column(String(255))
    price = Column(Float)
    url = Column(Text)
    previous_price = Column(Float)  # Для price_drop уведомлений

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_notification_user', 'user_id'),
        Index('idx_notification_listing', 'listing_id'),
        Index('idx_notification_sent', 'is_sent'),
    )


class SentAlert(Base):
    """Track all Telegram alerts sent to prevent duplicates on restart"""
    __tablename__ = 'sent_alerts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identification
    listing_id = Column(String(255), unique=True, index=True, nullable=False)
    listing_url = Column(Text)

    # Deal information
    deal_grade = Column(String(20))  # A-Tier, B-Tier, etc.
    bike_name = Column(String(500))

    # Pricing
    asking_price = Column(Float)
    market_price = Column(Float)
    discount_percent = Column(Float)

    # Telegram tracking
    telegram_message_id = Column(BigInteger)

    # Timestamp
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('idx_sent_alerts_listing_id', 'listing_id'),
        Index('idx_sent_alerts_sent_at', 'sent_at'),
    )


class UserDealAction(Base):
    """Track user actions on deal alerts (bought, ignored, marked)

    Records when a user clicks a button on a deal alert message.
    Enables deduplication of button clicks and tracking deal fate.
    """
    __tablename__ = 'user_deal_actions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User identification
    user_id = Column(Integer, index=True)  # Telegram user ID

    # Deal identification
    listing_id = Column(String(255), index=True)
    telegram_message_id = Column(BigInteger)  # Links to sent_alerts.telegram_message_id

    # Action details
    action_type = Column(String(20), index=True)  # 'bought', 'ignored', 'marked'
    action_value = Column(String(255))  # Additional data (e.g., price paid)

    # Timestamp
    action_timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Prevent duplicate button clicks
    __table_args__ = (
        UniqueConstraint(
            'telegram_message_id',
            'action_type',
            name='uq_user_action_dedup'
        ),
        Index('idx_user_action', 'user_id', 'action_timestamp'),
        Index('idx_user_action_listing', 'listing_id', 'action_type'),
    )
