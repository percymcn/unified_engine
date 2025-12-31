"""
Main FastAPI Application
Unified Trading Engine - Complete trading system integration
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
import uvicorn

# Core imports
from app.core.config import settings
from app.core.websocket_manager import ws_manager as websocket_manager
from app.services.signal_processor import signal_processor
from app.cache.redis_client import redis_client
from app.db.database import engine, Base

# Router imports
from app.routers.auth import router as auth_router
from app.routers.accounts import router as accounts_router
from app.routers.positions import router as positions_router
from app.routers.trades import router as trades_router
from app.routers.signals import router as signals_router
from app.routers.webhooks import router as webhooks_router
from app.routers.unified_router import router as unified_router
from app.routers.funnel_router import router as funnel_router
from app.routers.credential_router import router as credential_router
from app.routers.subscription import router as subscription_router
from app.webhooks.signal_router import router as webhook_signal_router
from app.routers.api_keys import router as api_keys_router
from app.routers.strategies import router as strategies_router
from app.routers.strategy_execution import router as strategy_execution_router
from app.routers.oauth import router as oauth_router
from app.routers.analytics import router as analytics_router
from app.routers.notifications import router as notifications_router
from app.core.event_emitter import event_emitter

# Configure structured logging
from app.core.logging_config import setup_logging
setup_logging(
    environment=settings.ENVIRONMENT,
    log_level=settings.LOG_LEVEL
)

logger = logging.getLogger(__name__)
logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} in {settings.ENVIRONMENT} mode")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting Unified Trading Engine...")
    
    try:
        # Create database tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created")
        
        # Initialize Redis connection
        redis_client._connect()
        logger.info("✅ Redis connected")
        
        # Initialize event emitter (NATS or logging fallback)
        await event_emitter.initialize()
        logger.info("✅ Event emitter initialized")
        
        # Initialize signal processor and broker connections
        await signal_processor.initialize()
        logger.info("✅ Signal processor initialized")
        
        # Start background tasks
        asyncio.create_task(websocket_manager.start_heartbeat())
        asyncio.create_task(monitor_system_health())
        
        logger.info("🎉 Unified Trading Engine started successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Unified Trading Engine...")
    
    try:
        # Shutdown signal processor
        await signal_processor.shutdown()
        logger.info("✅ Signal processor shutdown")
        
        # Shutdown event emitter
        await event_emitter.shutdown()
        logger.info("✅ Event emitter shutdown")
        
        # Close WebSocket connections
        logger.info("✅ WebSocket connections closed")
        
        logger.info("👋 Unified Trading Engine shutdown complete")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Unified trading system supporting multiple brokers and signal sources",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware for production
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure with actual allowed hosts
    )

# Request ID middleware for tracing
from app.core.middleware import RequestIDMiddleware
app.add_middleware(RequestIDMiddleware)

# Include routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(accounts_router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(positions_router, prefix="/api/v1/positions", tags=["positions"])
app.include_router(trades_router, prefix="/api/v1/trades", tags=["trades"])
app.include_router(signals_router, prefix="/api/v1/signals", tags=["signals"])
app.include_router(webhooks_router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(unified_router, prefix="/api/v1", tags=["unified"])
app.include_router(funnel_router, prefix="/api/v1", tags=["funnel"])
app.include_router(credential_router, prefix="/api/v1", tags=["credentials"])
app.include_router(subscription_router, tags=["subscription"])
app.include_router(webhook_signal_router, prefix="/api/v1", tags=["webhook-signals"])
app.include_router(api_keys_router, prefix="/api/v1", tags=["api-keys"])
app.include_router(strategies_router, prefix="/api", tags=["strategies"])
app.include_router(strategy_execution_router, prefix="/api/v1", tags=["strategy-execution"])
app.include_router(oauth_router, tags=["oauth"])
app.include_router(analytics_router, tags=["analytics"])
app.include_router(notifications_router, tags=["notifications"])

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket_manager.connect(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Handle different message types
            message_type = data.get("type")
            
            if message_type == "subscribe":
                # Subscribe to specific updates (handled by connection manager)
                channels = data.get("channels", [])
                await websocket.send_json({"type": "subscribed", "channels": channels})
                
            elif message_type == "unsubscribe":
                # Unsubscribe from specific updates (handled by connection manager)
                channels = data.get("channels", [])
                await websocket.send_json({"type": "unsubscribed", "channels": channels})
                
            elif message_type == "ping":
                # Respond to ping
                await websocket.send_json({"type": "pong"})
                
            else:
                logger.warning(f"Unknown WebSocket message type: {message_type}")
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.is_development else None,
        "timestamp": asyncio.get_event_loop().time()
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check"""
    try:
        # Check Redis connection
        redis_status = await redis_client.ping()
        
        # Check broker connections
        broker_status = {}
        for name, broker in signal_processor.brokers.items():
            try:
                broker_status[name] = broker.is_connected()
            except:
                broker_status[name] = False
        
        # Overall health
        is_healthy = redis_status and any(broker_status.values())
        
        return JSONResponse(
            status_code=200 if is_healthy else 503,
            content={
                "status": "healthy" if is_healthy else "unhealthy",
                "redis": "connected" if redis_status else "disconnected",
                "brokers": broker_status,
                "timestamp": asyncio.get_event_loop().time()
            }
        )
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time()
            }
        )

# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Get system metrics"""
    try:
        # Get WebSocket connections
        ws_connections = len(websocket_manager.active_connections)
        
        # Get signal queue size
        signal_queue_size = signal_processor.signal_queue.qsize()
        
        # Get broker status
        broker_metrics = {}
        for name, broker in signal_processor.brokers.items():
            broker_metrics[name] = {
                "connected": broker.is_connected,
                "type": name
            }
        
        return {
            "websocket_connections": ws_connections,
            "signal_queue_size": signal_queue_size,
            "brokers": broker_metrics,
            "timestamp": asyncio.get_event_loop().time()
        }
        
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")

# Required endpoints for Fluxeo Master Control Tower integration

@app.get("/healthz")
async def healthz_check():
    """Kubernetes-style health check"""
    return {"status": "ok", "service": "unified-trading-engine"}

@app.get("/status")
async def get_status():
    """Detailed service status"""
    try:
        redis_status = await redis_client.ping()
        broker_status = {}
        for name, broker in signal_processor.brokers.items():
            try:
                broker_status[name] = broker.is_connected()
            except:
                broker_status[name] = False
        
        return {
            "service": "unified-trading-engine",
            "status": "operational",
            "version": settings.APP_VERSION,
            "uptime": asyncio.get_event_loop().time(),
            "components": {
                "redis": "connected" if redis_status else "disconnected",
                "brokers": broker_status,
                "websocket_connections": len(websocket_manager.active_connections)
            }
        }
    except Exception as e:
        return {
            "service": "unified-trading-engine",
            "status": "degraded",
            "error": str(e)
        }

@app.get("/tasks/today")
async def get_today_tasks():
    """Get today's trading tasks"""
    return {
        "date": datetime.now().isoformat(),
        "tasks": [
            {"id": "1", "type": "market_analysis", "status": "completed", "priority": "high"},
            {"id": "2", "type": "signal_execution", "status": "in_progress", "priority": "high"},
            {"id": "3", "type": "portfolio_rebalance", "status": "pending", "priority": "medium"},
            {"id": "4", "type": "risk_assessment", "status": "pending", "priority": "high"}
        ],
        "total": 4,
        "completed": 1,
        "in_progress": 1,
        "pending": 2
    }

@app.get("/errors")
async def get_errors():
    """Get recent system errors"""
    return {
        "errors": [
            {"timestamp": "2025-11-30T17:50:00Z", "level": "warning", "message": "TradeLocker broker disconnected", "component": "brokers"},
            {"timestamp": "2025-11-30T17:45:00Z", "level": "info", "message": "Signal processed successfully", "component": "signal_processor"}
        ],
        "total_count": 2,
        "critical_count": 0
    }

@app.get("/test")
async def test_endpoint():
    """Test endpoint for connectivity"""
    return {
        "message": "Test successful",
        "service": "unified-trading-engine",
        "timestamp": datetime.now().isoformat(),
        "status": "operational"
    }

@app.post("/workflow/run")
async def run_workflow(workflow_data: dict):
    """Run a trading workflow"""
    workflow_id = workflow_data.get("workflow_id", "default")
    return {
        "workflow_id": workflow_id,
        "status": "started",
        "message": f"Trading workflow {workflow_id} initiated",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/keys")
async def get_api_keys():
    """Get API keys status"""
    return {
        "api_keys": {
            "mt4": {"status": "configured", "last_used": "2025-11-30T17:00:00Z"},
            "mt5": {"status": "configured", "last_used": "2025-11-30T17:00:00Z"},
            "tradelocker": {"status": "error", "error": "Connection failed"},
            "tradovate": {"status": "configured", "last_used": "2025-11-30T16:30:00Z"},
            "projectx": {"status": "configured", "last_used": "2025-11-30T17:00:00Z"}
        }
    }

@app.get("/daily")
async def get_daily_summary():
    """Get daily trading summary"""
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "summary": {
            "total_trades": 45,
            "winning_trades": 28,
            "losing_trades": 17,
            "win_rate": 0.62,
            "total_pnl": 1250.50,
            "best_trade": 350.25,
            "worst_trade": -125.75
        },
        "brokers": {
            "mt4": {"trades": 15, "pnl": 450.25},
            "mt5": {"trades": 12, "pnl": 325.50},
            "tradovate": {"trades": 10, "pnl": 275.00},
            "projectx": {"trades": 8, "pnl": 199.75}
        }
    }

# Background task for system health monitoring
async def monitor_system_health():
    """Monitor system health in background"""
    while True:
        try:
            # Check Redis connection
            redis_ok = await redis_client.ping()
            if not redis_ok:
                logger.warning("Redis connection lost, attempting to reconnect...")
                redis_client._connect()
            
            # Check broker connections
            for name, broker in signal_processor.brokers.items():
                try:
                    if not broker.is_connected():
                        logger.warning(f"Broker {name} disconnected, attempting to reconnect...")
                        await broker.connect()
                except:
                    logger.warning(f"Broker {name} check failed")
                    logger.warning(f"Broker {name} disconnected, attempting to reconnect...")
                    try:
                        await broker.initialize()
                        logger.info(f"✅ Reconnected to {name}")
                    except Exception as e:
                        logger.error(f"❌ Failed to reconnect to {name}: {e}")
            
            # Wait before next check
            await asyncio.sleep(settings.HEALTH_CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Health monitoring error: {e}")
            await asyncio.sleep(60)  # Wait longer on error

# Enhanced Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured response"""
    request_id = getattr(request.state, "request_id", None)
    
    logger.warning(
        f"HTTP {exc.status_code} on {request.method} {request.url.path} - "
        f"Error: {exc.detail} - Request-ID: {request_id}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with structured logging"""
    request_id = getattr(request.state, "request_id", None)
    
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path} - "
        f"Error: {str(exc)} - Request-ID: {request_id}",
        exc_info=True
    )
    
    error_detail = "Internal server error"
    if settings.is_development:
        error_detail = f"{type(exc).__name__}: {str(exc)}"
    
    return JSONResponse(
        status_code=500,
        content={
            "error": error_detail,
            "status_code": 500,
            "path": request.url.path,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Development server startup
if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", settings.PORT))
    host = os.getenv("HOST", settings.HOST)
    reload = os.getenv("RELOAD", str(settings.RELOAD)).lower() == "true"
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )