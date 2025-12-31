"""
Demo FastAPI Application for Unified Trading Engine
Simplified version for testing and demonstration
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import uvicorn
import os
import redis
import asyncpg
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Unified Trading Engine - Demo",
    description="Simplified demo version for testing",
    version="1.0.0-demo"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Redis connection
try:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True
    )
    redis_client.ping()
    logger.info("Connected to Redis")
except Exception as e:
    logger.error(f"Redis connection failed: {e}")
    redis_client = None

# Database connection pool
db_pool = None

async def get_db_connection():
    """Get database connection"""
    global db_pool
    if db_pool is None:
        try:
            db_pool = await asyncpg.create_pool(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                database=os.getenv("POSTGRES_DB", "trading_db"),
                user=os.getenv("POSTGRES_USER", "trading_user"),
                password=os.getenv("POSTGRES_PASSWORD", "trading_password"),
                min_size=2,
                max_size=10
            )
            logger.info("Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise HTTPException(status_code=500, detail="Database connection failed")
    return db_pool

# Health endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0-demo",
        "services": {
            "redis": "connected" if redis_client else "disconnected",
            "database": "connected" if db_pool else "disconnected"
        }
    }

@app.get("/status", tags=["Health"])
async def status_check():
    """Detailed status check"""
    db_status = "disconnected"
    try:
        if db_pool:
            conn = await db_pool.acquire()
            await conn.execute("SELECT 1")
            await conn.release()
            db_status = "connected"
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
    
    redis_status = "disconnected"
    if redis_client:
        try:
            redis_client.ping()
            redis_status = "connected"
        except Exception as e:
            logger.error(f"Redis status check failed: {e}")
    
    return {
        "status": "operational" if db_status == "connected" and redis_status == "connected" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": db_status,
            "redis": redis_status
        },
        "uptime": "unknown"
    }

@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Basic metrics endpoint"""
    return {
        "http_requests_total": 42,
        "http_request_duration_seconds": 0.05,
        "database_connections_active": 2 if db_pool else 0,
        "redis_connected": 1 if redis_client else 0,
        "timestamp": datetime.utcnow().isoformat()
    }

# Authentication endpoints
@app.post("/api/auth/login", tags=["Authentication"])
async def login(username: str, password: str):
    """Simple login endpoint"""
    # Demo authentication - accept admin/admin123
    if username == "admin" and password == "admin123":
        return {
            "access_token": "demo-token-12345",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": 1,
                "username": "admin",
                "email": "admin@demo.com"
            }
        }
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/api/auth/validate", tags=["Authentication"])
async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Token validation endpoint"""
    if credentials.credentials == "demo-token-12345":
        return {"valid": True, "user_id": 1}
    return {"valid": False, "error": "Invalid token"}

# Trading endpoints
@app.get("/api/signals", tags=["Trading"])
async def get_signals():
    """Get trading signals"""
    return {
        "signals": [
            {
                "id": 1,
                "symbol": "EURUSD",
                "type": "BUY",
                "price": 1.0850,
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": 0.85
            },
            {
                "id": 2,
                "symbol": "GBPUSD",
                "type": "SELL",
                "price": 1.2650,
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": 0.72
            }
        ],
        "total": 2
    }

@app.get("/api/accounts", tags=["Trading"])
async def get_accounts():
    """Get broker accounts"""
    return {
        "accounts": [
            {
                "id": 1,
                "broker": "MT4",
                "account_id": "12345",
                "balance": 10000.0,
                "currency": "USD",
                "status": "active"
            },
            {
                "id": 2,
                "broker": "TradeLocker",
                "account_id": "TL67890",
                "balance": 5000.0,
                "currency": "USD",
                "status": "active"
            }
        ]
    }

@app.get("/api/trades", tags=["Trading"])
async def get_trades():
    """Get trades"""
    return {
        "trades": [
            {
                "id": 1,
                "symbol": "EURUSD",
                "type": "BUY",
                "volume": 0.1,
                "open_price": 1.0850,
                "current_price": 1.0875,
                "profit": 25.0,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "open"
            }
        ],
        "total": 1
    }

@app.get("/api/positions", tags=["Trading"])
async def get_positions():
    """Get open positions"""
    return {
        "positions": [
            {
                "id": 1,
                "symbol": "EURUSD",
                "type": "BUY",
                "volume": 0.1,
                "open_price": 1.0850,
                "current_price": 1.0875,
                "profit": 25.0,
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "total": 1
    }

# Webhook endpoints
@app.post("/api/webhooks/tradingview", tags=["Webhooks"])
async def tradingview_webhook(payload: Dict[str, Any]):
    """TradingView webhook endpoint"""
    logger.info(f"Received TradingView webhook: {payload}")
    return {
        "status": "received",
        "webhook_id": f"tv_{datetime.utcnow().timestamp()}",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/webhooks/signal", tags=["Webhooks"])
async def signal_webhook(payload: Dict[str, Any]):
    """Generic signal webhook endpoint"""
    logger.info(f"Received signal webhook: {payload}")
    return {
        "status": "processed",
        "signal_id": f"sig_{datetime.utcnow().timestamp()}",
        "timestamp": datetime.utcnow().isoformat()
    }

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Unified Trading Engine - Demo API",
        "version": "1.0.0-demo",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "metrics": "/metrics",
            "docs": "/docs",
            "api": "/api",
            "webhooks": "/api/webhooks"
        },
        "documentation": "http://localhost:8000/docs"
    }

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("Starting Unified Trading Engine Demo")
    await get_db_connection()  # Initialize database connection

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down Unified Trading Engine Demo")
    if db_pool:
        await db_pool.close()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )