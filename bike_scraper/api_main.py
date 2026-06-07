"""
REST API для системы парсинга велосипедов
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID
import json

from bike_scraper.database import init_db, get_db, get_session
from bike_scraper.models import Listing, ScraperLog, SellerProfile, MonitoringSearch
from bike_scraper.service_listings import ListingService
from bike_scraper.config import API_HOST, API_PORT
from bike_scraper.utils_logger import get_logger

logger = get_logger('api')

app = FastAPI(
    title="Bike Scraper API",
    description="API для системы парсинга велосипедов на Wallapop",
    version="1.0.0"
)


# =====================
# INITIALIZATION
# =====================

@app.on_event("startup")
async def startup():
    """Инициализация при запуске"""
    logger.info("🚀 Запускаю API...")
    init_db()
    logger.info("✅ API инициализирован")


@app.on_event("shutdown")
async def shutdown():
    """Очистка при остановке"""
    logger.info("⏹️  Останавливаю API...")


# =====================
# MODELS (Pydantic)
# =====================

from pydantic import BaseModel
from typing import Optional, List


class ListingResponse(BaseModel):
    """Модель ответа для объявления"""
    id: UUID
    source: str
    listing_id: str
    url: str
    title: str
    price: float
    currency: str
    seller_name: str
    seller_rating: Optional[float]
    location: str
    country: str
    date_posted: Optional[datetime]
    date_collected: datetime
    bike_type: Optional[str]
    frame_size: Optional[str]
    is_active: bool
    images_count: int

    class Config:
        from_attributes = True

    @property
    def images_count(self) -> int:
        if isinstance(self.images, list):
            return len(self.images)
        return 0


class StatisticsResponse(BaseModel):
    """Модель ответа для статистики"""
    total_listings: int
    active_listings: int
    duplicate_listings: int
    price_stats: dict
    bike_types: dict


class ScraperLogResponse(BaseModel):
    """Модель ответа для логов"""
    source: str
    search_term: str
    total_found: int
    successfully_parsed: int
    errors_count: int
    duration_seconds: float
    status: str
    created_at: datetime


# =====================
# ROUTES - LISTINGS
# =====================

@app.get("/bikes", response_model=List[ListingResponse], tags=["Listings"])
async def get_bikes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    bike_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    country: Optional[str] = "Spain",
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Получить список велосипедов с фильтрацией"""
    query = db.query(Listing)

    if active_only:
        query = query.filter(Listing.is_active == True)

    if bike_type:
        query = query.filter(Listing.bike_type == bike_type)

    if min_price:
        query = query.filter(Listing.price >= min_price)

    if max_price:
        query = query.filter(Listing.price <= max_price)

    if country:
        query = query.filter(Listing.country == country)

    listings = query.offset(skip).limit(limit).all()
    return listings


@app.get("/bike/{listing_id}", response_model=ListingResponse, tags=["Listings"])
async def get_bike(
    listing_id: UUID,
    db: Session = Depends(get_db)
):
    """Получить информацию о конкретном велосипеде"""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()

    if not listing:
        raise HTTPException(status_code=404, detail="Объявление не найдено")

    return listing


@app.get("/new", response_model=List[ListingResponse], tags=["Listings"])
async def get_new_listings(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Получить новые объявления за последние N часов"""
    listings = ListingService.get_new_listings(db, hours=hours, limit=limit)
    return listings


@app.get("/deals", response_model=List[ListingResponse], tags=["Listings"])
async def get_good_deals(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Получить выгодные предложения (отсортировано по цене)"""
    listings = ListingService.get_good_deals(db, limit=limit)
    return listings


# =====================
# ROUTES - SOURCES
# =====================

@app.get("/source/{source_name}", response_model=List[ListingResponse], tags=["Sources"])
async def get_by_source(
    source_name: str,
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Получить объявления с определенного источника"""
    query = db.query(Listing).filter(Listing.source == source_name.lower())

    if active_only:
        query = query.filter(Listing.is_active == True)

    listings = query.offset(skip).limit(limit).all()
    return listings


# =====================
# ROUTES - ANALYTICS
# =====================

@app.get("/statistics", tags=["Analytics"])
async def get_statistics(db: Session = Depends(get_db)):
    """Получить статистику по объявлениям"""
    stats = ListingService.get_statistics(db)
    return stats


@app.get("/logs", response_model=List[ScraperLogResponse], tags=["Analytics"])
async def get_scraper_logs(
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Получить логи парсинга"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    logs = db.query(ScraperLog).filter(
        ScraperLog.created_at >= cutoff
    ).order_by(ScraperLog.created_at.desc()).limit(limit).all()

    return logs


@app.get("/sellers/{source}", tags=["Analytics"])
async def get_sellers(
    source: str,
    limit: int = Query(50, ge=1, le=200),
    min_rating: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Получить лучших продавцов"""
    query = db.query(SellerProfile).filter(SellerProfile.source == source)

    if min_rating:
        query = query.filter(SellerProfile.rating >= min_rating)

    sellers = query.order_by(
        SellerProfile.rating.desc(),
        SellerProfile.reviews_count.desc()
    ).limit(limit).all()

    return sellers


@app.get("/price-analysis", tags=["Analytics"])
async def get_price_analysis(
    bike_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Получить анализ цен по типам велосипедов"""
    from sqlalchemy import func, and_

    query = db.query(
        Listing.bike_type,
        func.count(Listing.id).label('count'),
        func.avg(Listing.price).label('avg_price'),
        func.min(Listing.price).label('min_price'),
        func.max(Listing.price).label('max_price'),
    ).filter(
        and_(
            Listing.is_active == True,
            Listing.bike_type.isnot(None)
        )
    )

    if bike_type:
        query = query.filter(Listing.bike_type == bike_type)

    results = query.group_by(Listing.bike_type).all()

    analysis = {
        result.bike_type: {
            'count': result.count,
            'avg_price': float(result.avg_price) if result.avg_price else 0,
            'min_price': float(result.min_price) if result.min_price else 0,
            'max_price': float(result.max_price) if result.max_price else 0,
        }
        for result in results
    }

    return analysis


@app.get("/deals", tags=["Analytics"])
async def get_good_deals(
    min_profit: float = Query(10, ge=1, le=100),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """💰 Получить выгодные сделки (профит >= min_profit%)"""
    try:
        deals = ListingService.get_good_deals(db, limit=limit, min_profit_percent=min_profit)

        results = []
        for listing, analysis in deals:
            market = analysis.get('market_analysis', {})
            results.append({
                'id': str(listing.id),
                'title': listing.title,
                'url': listing.url,
                'price': listing.price,
                'bike': {
                    'brand': analysis.get('bike', {}).get('brand'),
                    'model': analysis.get('bike', {}).get('model'),
                    'year': analysis.get('bike', {}).get('year'),
                    'size': analysis.get('bike', {}).get('size')
                },
                'market_price': market.get('market_median'),
                'profit_euros': market.get('profit_euros'),
                'profit_percent': market.get('profit_percent'),
                'discount_percent': market.get('discount_percent'),
                'comparable_count': market.get('comparable_count'),
                'confidence': market.get('confidence')
            })

        return {
            'total_deals': len(results),
            'min_profit_percent': min_profit,
            'deals': results
        }

    except Exception as e:
        logger.error(f"❌ Ошибка получения выгодных сделок: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================
# ROUTES - SEARCH
# =====================

@app.get("/search", response_model=List[ListingResponse], tags=["Search"])
async def search_listings(
    q: str = Query(..., min_length=2),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Поиск велосипедов по названию или описанию"""
    search_pattern = f"%{q.lower()}%"

    listings = db.query(Listing).filter(
        Listing.is_active == True
    ).filter(
        (Listing.title.ilike(search_pattern)) |
        (Listing.description.ilike(search_pattern))
    ).limit(limit).all()

    return listings


# =====================
# ROUTES - MONITORING
# =====================

@app.post("/monitoring/add-search", tags=["Monitoring"])
async def add_monitoring_search(
    user_id: int,
    search_term: str,
    price_drop_threshold: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Добавить поиск для мониторинга"""
    try:
        # Проверяем что такого поиска еще нет
        existing = db.query(MonitoringSearch).filter(
            MonitoringSearch.user_id == user_id,
            MonitoringSearch.search_term == search_term,
            MonitoringSearch.is_active == True
        ).first()

        if existing:
            return {"status": "exists", "message": f"Поиск '{search_term}' уже активен"}

        # Создаем новый поиск
        search = MonitoringSearch(
            user_id=user_id,
            search_term=search_term,
            price_drop_threshold=price_drop_threshold or 50.0,
            is_active=True
        )
        db.add(search)
        db.commit()

        return {
            "status": "created",
            "search_id": search.id,
            "search_term": search.search_term,
            "message": f"Поиск '{search_term}' добавлен"
        }

    except Exception as e:
        logger.error(f"Error adding search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/monitoring/searches", tags=["Monitoring"])
async def list_monitoring_searches(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Получить список активных поисков пользователя"""
    searches = db.query(MonitoringSearch).filter(
        MonitoringSearch.user_id == user_id,
        MonitoringSearch.is_active == True
    ).all()

    return {
        "user_id": user_id,
        "searches": [
            {
                "id": s.id,
                "search_term": s.search_term,
                "listings_found": s.listings_found,
                "price_drop_threshold": s.price_drop_threshold,
                "created_at": s.created_at,
                "last_checked": s.last_checked
            }
            for s in searches
        ]
    }


@app.delete("/monitoring/searches/{search_id}", tags=["Monitoring"])
async def remove_monitoring_search(
    search_id: int,
    db: Session = Depends(get_db)
):
    """Удалить поиск для мониторинга"""
    try:
        search = db.query(MonitoringSearch).filter(
            MonitoringSearch.id == search_id
        ).first()

        if not search:
            raise HTTPException(status_code=404, detail="Поиск не найден")

        search.is_active = False
        db.commit()

        return {
            "status": "deleted",
            "search_term": search.search_term,
            "message": f"Поиск '{search.search_term}' удален"
        }

    except Exception as e:
        logger.error(f"Error removing search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/monitoring/status", tags=["Monitoring"])
async def monitoring_status(db: Session = Depends(get_db)):
    """Статус системы мониторинга"""
    active_searches = db.query(MonitoringSearch).filter(
        MonitoringSearch.is_active == True
    ).count()

    total_users = db.query(MonitoringSearch.user_id).distinct().count()

    return {
        "bot_status": "running",
        "active_searches": active_searches,
        "total_users": total_users,
        "timestamp": datetime.utcnow()
    }


# =====================
# ROUTES - TELEGRAM TESTING
# =====================

@app.post("/test-alert", tags=["Testing"])
async def send_test_alert(db: Session = Depends(get_db)):
    """Send test deal alert to configured Telegram chat

    Used for smoke testing that Telegram alert system works correctly.
    Returns message_id and chat_id for verification.

    Returns:
        {
            "status": "success",
            "message": "test alert sent",
            "chat_id": 123456789,
            "message_id": 125,
            "timestamp": "2026-06-07T14:30:00"
        }
    """
    import os
    import asyncio
    from bike_scraper.telegram_alerts import TelegramAlertService, DealAlert

    try:
        # Get Telegram credentials
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if not bot_token or not chat_id:
            raise HTTPException(
                status_code=400,
                detail="TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured"
            )

        # Create test deal
        test_deal = DealAlert(
            listing_id="test_deal_api",
            bike_name="Canyon Aeroad CF SLX 8 Di2 2022",
            asking_price=2900,
            market_price=4200,
            discount_percent=30.95,
            profit_potential=1300,
            size="M",
            groupset="Ultegra Di2",
            year=2022,
            confidence=95.0,
            comparable_count=37,
            listing_url="https://example.com/test-bike",
            deal_grade="A-Tier"
        )

        # Send alert
        from telegram import Bot
        bot = Bot(token=bot_token)

        alert_service = TelegramAlertService(
            bot_token=bot_token,
            chat_id=chat_id,
            db_session=db
        )

        message_text = alert_service._build_message(test_deal)
        keyboard = alert_service._build_keyboard(test_deal)

        # Send message
        message = await bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        logger.info(f"✅ Test alert sent: message_id={message.message_id}, chat_id={message.chat_id}")

        return {
            "status": "success",
            "message": "test alert sent",
            "chat_id": message.chat_id,
            "message_id": message.message_id,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to send test alert: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send test alert: {str(e)}"
        )


# =====================
# ROUTES - HEALTH
# =====================

@app.get("/health", tags=["System"])
async def health_check():
    """Проверка здоровья API"""
    db = get_session()
    try:
        # Проверяем подключение к БД
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "healthy", "timestamp": datetime.utcnow()}
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database connection failed")


@app.get("/", tags=["System"])
async def root():
    """Информация об API"""
    return {
        "name": "Bike Scraper API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# =====================
# MAIN
# =====================

if __name__ == "__main__":
    import uvicorn

    logger.info(f"🚀 Запускаю API на {API_HOST}:{API_PORT}")

    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        workers=1,
        log_level="info"
    )
