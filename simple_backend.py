#!/usr/bin/env python3
"""
Simple Mock Backend for Unified Trading Engine MVP
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime
import uvicorn

app = FastAPI(title="Unified Trading Engine API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Unified Trading Engine API", "status": "active"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "redis": "connected",
        "brokers": {
            "mt4": True,
            "mt5": True,
            "tradelocker": False,
            "tradovate": True,
            "projectx": True
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/metrics")
async def get_metrics():
    return {
        "websocket_connections": 5,
        "signal_queue_size": 12,
        "brokers": {
            "mt4": {"connected": True, "type": "mt4"},
            "mt5": {"connected": True, "type": "mt5"},
            "tradelocker": {"connected": False, "type": "tradelocker"},
            "tradovate": {"connected": True, "type": "tradovate"},
            "projectx": {"connected": True, "type": "projectx"}
        },
        "timestamp": datetime.utcnow().isoformat()
    }

# Required endpoints for Fluxeo Master Control Tower integration

@app.get("/healthz")
async def healthz_check():
    """Kubernetes-style health check"""
    return {"status": "ok", "service": "unified-trading-engine"}

@app.get("/status")
async def get_status():
    """Detailed service status"""
    return {
        "service": "unified-trading-engine",
        "status": "operational",
        "version": "1.0.0",
        "uptime": datetime.utcnow().isoformat(),
        "components": {
            "redis": "connected",
            "brokers": {
                "mt4": True,
                "mt5": True,
                "tradelocker": False,
                "tradovate": True,
                "projectx": True
            },
            "websocket_connections": 5
        }
    }

@app.get("/tasks/today")
async def get_today_tasks():
    """Get today's trading tasks"""
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
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
    """Recent errors. This demo process has no webhook log database."""
    from app.services.ops_status import empty_errors_payload
    return empty_errors_payload()

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
    """API key status. This demo process does not invent broker credentials."""
    from app.services.ops_status import empty_api_keys_payload
    return empty_api_keys_payload()

@app.get("/daily")
async def get_daily_summary():
    """Daily summary. This demo process has no trade history to invent."""
    from app.services.ops_status import empty_daily_summary
    return empty_daily_summary(datetime.now().strftime("%Y-%m-%d"))

# Mock trading endpoints
@app.get("/api/v1/accounts")
async def get_accounts():
    return {
        "accounts": [
            {"id": "1", "broker": "mt4", "balance": 10500.50, "equity": 10450.75, "status": "active"},
            {"id": "2", "broker": "mt5", "balance": 8750.25, "equity": 8725.50, "status": "active"},
            {"id": "3", "broker": "tradovate", "balance": 15000.00, "equity": 15125.75, "status": "active"}
        ]
    }

@app.get("/api/v1/positions")
async def get_positions():
    return {
        "positions": [
            {"id": "1", "symbol": "EURUSD", "type": "buy", "volume": 0.1, "profit": 25.50, "broker": "mt4"},
            {"id": "2", "symbol": "GBPUSD", "type": "sell", "volume": 0.05, "profit": -12.25, "broker": "mt5"},
            {"id": "3", "symbol": "XAUUSD", "type": "buy", "volume": 0.02, "profit": 45.75, "broker": "tradovate"}
        ]
    }

@app.get("/api/v1/trades")
async def get_trades():
    return {
        "trades": [
            {"id": "1", "symbol": "EURUSD", "type": "buy", "volume": 0.1, "profit": 25.50, "status": "closed"},
            {"id": "2", "symbol": "GBPUSD", "type": "sell", "volume": 0.05, "profit": -12.25, "status": "closed"},
            {"id": "3", "symbol": "XAUUSD", "type": "buy", "volume": 0.02, "profit": 45.75, "status": "open"}
        ]
    }

@app.get("/api/v1/signals")
async def get_signals():
    return {
        "signals": [
            {"id": "1", "symbol": "EURUSD", "type": "buy", "strength": 0.85, "timestamp": datetime.utcnow().isoformat()},
            {"id": "2", "symbol": "GBPUSD", "type": "sell", "strength": 0.72, "timestamp": datetime.utcnow().isoformat()},
            {"id": "3", "symbol": "XAUUSD", "type": "buy", "strength": 0.91, "timestamp": datetime.utcnow().isoformat()}
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)