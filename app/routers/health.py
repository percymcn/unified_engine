"""
Health Check Router
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.database import get_db
from app.cache.redis_client import redis_client

router = APIRouter(tags=["health"])

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Check database
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    try:
        # Check Redis
        redis_client._connect()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
    
    overall_status = "healthy" if db_status == "healthy" and redis_status == "healthy" else "unhealthy"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "checks": {
            "database": db_status,
            "redis": redis_status
        }
    }
