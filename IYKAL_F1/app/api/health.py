"""
Health check برای مانیتورینگ
"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
import redis

from app.database import get_db
from app.config import settings
from app.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """بررسی سلامت API، دیتابیس و Redis"""
    db_status = "ok"
    redis_status = "ok"

    # تست دیتابیس
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {type(e).__name__}"

    # تست Redis
    try:
        r = redis.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
    except Exception as e:
        redis_status = f"error: {type(e).__name__}"

    overall = "healthy" if db_status == "ok" and redis_status == "ok" else "degraded"

    return HealthResponse(
        status=overall,
        phase=1,
        module="Lead Harvester & AI Analyzer",
        database=db_status,
        redis=redis_status,
        timestamp=datetime.utcnow(),
    )