# SmartFlow Integration Guide

## Changes to app/main.py

Add these imports at the top of the file (after line 74):

```python
# SmartFlow imports
from app.routers.smartflow import router as smartflow_router
from app.services.smartflow_service import smartflow_service
```

Add this background task function (around line 240, near other background tasks):

```python
async def smartflow_background_loop():
    """Background task for SmartFlow Indicator"""
    try:
        logger.info("🤖 Starting SmartFlow background task...")
        await smartflow_service.background_task()
    except Exception as e:
        logger.error(f"SmartFlow background task failed: {e}")
```

Add SmartFlow background task to startup (line 143, after other create_task calls):

```python
        # Start background tasks
        asyncio.create_task(websocket_manager.start_heartbeat())
        asyncio.create_task(monitor_system_health())
        asyncio.create_task(tradovate_token_refresh_loop())
        asyncio.create_task(webhook_log_cleanup_loop())
        asyncio.create_task(smartflow_background_loop())  # ADD THIS LINE
```

Add SmartFlow router to router includes (after line 337):

```python
app.include_router(circuit_breaker_health_router, prefix="/api/v1", tags=["monitoring"])
app.include_router(smartflow_router, prefix="/api/v1", tags=["smartflow"])  # ADD THIS LINE
```

## Database Migration

Run this SQL to create SmartFlow tables:

```sql
-- SmartFlow Configuration Table
CREATE TABLE smartflow_config (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    webhook_urls JSON NOT NULL DEFAULT '[]',
    buy_threshold FLOAT NOT NULL DEFAULT 4.0,
    sell_threshold FLOAT NOT NULL DEFAULT -4.0,
    close_threshold FLOAT NOT NULL DEFAULT 1.0,
    score_window_minutes INTEGER NOT NULL DEFAULT 5,
    update_interval_seconds INTEGER NOT NULL DEFAULT 45,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- SmartFlow Signal Logs Table
CREATE TABLE smartflow_signal_logs (
    id SERIAL PRIMARY KEY,
    config_id INTEGER NOT NULL REFERENCES smartflow_config(id) ON DELETE CASCADE,
    ticker VARCHAR(10) NOT NULL,
    action VARCHAR(10) NOT NULL,
    score FLOAT NOT NULL,
    price FLOAT,
    bullish_flows INTEGER DEFAULT 0,
    bearish_flows INTEGER DEFAULT 0,
    total_premium FLOAT DEFAULT 0.0,
    webhooks_posted JSON NOT NULL DEFAULT '[]',
    post_successful BOOLEAN DEFAULT FALSE,
    post_errors TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_smartflow_logs_ticker ON smartflow_signal_logs(ticker);
CREATE INDEX idx_smartflow_logs_created ON smartflow_signal_logs(created_at);

-- SmartFlow Score History Table
CREATE TABLE smartflow_score_history (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    score FLOAT NOT NULL,
    bullish_flows INTEGER DEFAULT 0,
    bearish_flows INTEGER DEFAULT 0,
    total_premium FLOAT DEFAULT 0.0,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_smartflow_history_ticker ON smartflow_score_history(ticker);
CREATE INDEX idx_smartflow_history_timestamp ON smartflow_score_history(timestamp);
```

Or use Alembic migration (if using):

```bash
# Create migration
alembic revision --autogenerate -m "Add SmartFlow tables"

# Apply migration
alembic upgrade head
```

## Verification

After integration, verify SmartFlow is running:

1. Check logs for startup message:
   ```
   🤖 Starting SmartFlow background task...
   ```

2. Test API endpoints:
   ```bash
   # Get config (creates default if not exists)
   curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/smartflow/config

   # Get status
   curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/smartflow/status
   ```

3. Enable SmartFlow:
   ```bash
   curl -X PUT http://localhost:8000/api/v1/smartflow/config \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "enabled": true,
       "webhook_urls": ["https://api.mytradeflow.app/webhooks/tradingview/YOUR_KEY"]
     }'
   ```

## Notes

- SmartFlow is **completely optional** and disabled by default
- No impact on existing TradingView webhook routing
- Can be toggled on/off per user via API or dashboard
- Runs independently as a background task
- All logs go to `smartflow.log` (separate from main logs)
