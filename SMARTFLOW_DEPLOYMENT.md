# SmartFlow Deployment Status

## ✅ Completed Integration

### 1. Code Integration into main.py

**Imports Added** (lines 73-74):
```python
from app.routers.smartflow import router as smartflow_router
from app.services.smartflow_service import smartflow_service
```

**Background Task Created** (lines 705-716):
```python
async def smartflow_background_loop():
    """
    Background task for SmartFlow Indicator - optional AI-driven flow sentiment analysis.

    Fetches FlowAlgo data from flow_confluence_proxy.py, computes sentiment scores,
    and generates buy/sell/close signals based on institutional options flow.
    """
    try:
        logger.info("🤖 Starting SmartFlow Indicator background task...")
        await smartflow_service.background_task()
    except Exception as e:
        logger.error(f"SmartFlow background task failed: {e}")
```

**Background Task Started** (line 146):
```python
asyncio.create_task(smartflow_background_loop())
```

**Router Included** (line 341):
```python
app.include_router(smartflow_router, prefix="/api/v1/smartflow", tags=["smartflow"])
```

### 2. Alembic Migration Created

**File**: `alembic/versions/6aba51c2624e_add_smartflow_tables.py`

Creates three tables:
- `smartflow_config` - User configuration and settings
- `smartflow_signal_logs` - Signal generation history
- `smartflow_score_history` - Sentiment score time series

### 3. All SmartFlow Modules Ready

- ✅ `app/services/smartflow_service.py` - Core sentiment scoring logic
- ✅ `app/models/smartflow_models.py` - Database models
- ✅ `app/routers/smartflow.py` - API endpoints
- ✅ `app/static/smartflow_dashboard.html` - Dashboard UI
- ✅ `SMARTFLOW_README.md` - Complete user documentation
- ✅ `SMARTFLOW_INTEGRATION.md` - Integration guide

---

## ⏳ Pending Tasks

### 1. Run Database Migration

The migration is ready but not yet applied because the database is running in Docker Swarm.

**To apply the migration:**

```bash
# On the machine where the database is accessible
cd /home/pharma5/unified_engine
DATABASE_URL="postgresql://trading_user:trading_password@DATABASE_HOST:5432/trading_db" python3 -m alembic upgrade head
```

**Replace `DATABASE_HOST` with:**
- Docker service name (e.g., `db` or `postgres`)
- Or the actual IP/hostname where PostgreSQL is running in the Swarm

**Verify migration:**
```bash
# Check current migration version
DATABASE_URL="postgresql://..." python3 -m alembic current

# Should show: 6aba51c2624e (head)
```

### 2. Restart the Application

After migration, restart the Unified Trading Engine:

```bash
# Using Docker Swarm
docker service update --force unified-engine_api

# Or traditional restart
systemctl restart unified-engine
```

**Look for this log message:**
```
🤖 Starting SmartFlow Indicator background task...
```

### 3. Test SmartFlow Integration

**Step 1: Get authentication token**
```bash
# Login and get JWT token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}' \
  | jq -r '.access_token')
```

**Step 2: Check SmartFlow config**
```bash
# This creates default config if not exists
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/smartflow/config
```

**Step 3: Enable SmartFlow**
```bash
curl -X PUT http://localhost:8000/api/v1/smartflow/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "webhook_urls": ["https://api.mytradeflow.app/webhooks/tradingview/z9HN9uV4kQPEeXaQZuWH_vWPYeV1wtWYQc07UqfYtgA"],
    "buy_threshold": 4.0,
    "sell_threshold": -4.0,
    "close_threshold": 1.0,
    "score_window_minutes": 5,
    "update_interval_seconds": 45
  }'
```

**Step 4: Monitor live status**
```bash
# Check real-time sentiment scores
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/smartflow/status

# View signal history
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/smartflow/signals?limit=10
```

**Step 5: Check application logs**
```bash
# Docker Swarm
docker service logs -f unified-engine_api | grep -i smartflow

# Or traditional logs
tail -f /var/log/unified-engine/app.log | grep -i smartflow
```

**Expected log output:**
```
🤖 Starting SmartFlow Indicator background task...
SmartFlow: Fetching flow data from http://localhost:9001/flows
SmartFlow: Processing 47 flows (SPY: 28, QQQ: 15, GLD: 4)
SmartFlow: SPY score: +2.5 (bullish: 18, bearish: 10)
SmartFlow: QQQ score: -1.0 (bullish: 7, bearish: 8)
SmartFlow: GLD score: +0.5 (bullish: 3, bearish: 1)
```

### 4. Verify FlowAlgo Proxy is Running

SmartFlow requires `flow_confluence_proxy.py` to be running:

```bash
# Check if it's running
ps aux | grep flow_confluence_proxy

# Check the PID file
cat /home/pharma5/unified_engine/flow_proxy.pid

# Test the endpoint
curl http://localhost:9001/flows
```

**If not running, restart it:**
```bash
cd /home/pharma5/unified_engine
source flow_venv/bin/activate
nohup python3 flow_confluence_proxy.py > flow_proxy.log 2>&1 &
echo $! > flow_proxy.pid
```

---

## 🎯 What SmartFlow Does

### Data Flow

```
FlowAlgo ──► flow_confluence_proxy.py ──► SmartFlow Service ──► Your Webhooks
           (scrapes export page)      (computes sentiment)    (generates signals)
                 Port 9001                   Port 8000
```

### Sentiment Scoring Algorithm

1. **Fetches flows every 45s** from http://localhost:9001/flows
2. **Filters SPY/QQQ/GLD** option flows (sweeps/blocks only)
3. **Scores each flow:**
   - Premium ≥ $500k: ±3 points
   - Premium ≥ $100k: ±2 points
   - Premium ≥ $50k: ±1 point
   - Sweeps get +0.5 bonus
   - Bullish calls: positive, Bearish puts: negative
4. **Computes net score** over 5-minute rolling window
5. **Generates signals:**
   - Score > +4.0 → BUY signal on mapped ticker (MES/MYM/NQ → SPY/QQQ/GLD)
   - Score < -4.0 → SELL signal
   - Score near 0 after extreme → CLOSE signal
6. **Posts to webhooks** in TradingView JSON format

### Example Signal

```json
{
  "ticker": "MES",
  "action": "buy",
  "strategy": "smartflow",
  "interval": "1m",
  "position_size": 1,
  "time": "2026-03-05T11:45:00Z",
  "meta": {
    "flow_score": 5.5,
    "bullish_flows": 23,
    "bearish_flows": 8,
    "total_premium": 4250000.0,
    "top_flows": [
      "SPY 565 call sweep $2.9M",
      "SPY 570 call block $1.2M"
    ]
  }
}
```

---

## 📊 Dashboard Access

Once deployed, access the SmartFlow dashboard:

**URL**: `http://your-domain.com/app/static/smartflow_dashboard.html`

**Features**:
- Real-time sentiment scores (SPY/QQQ/GLD)
- Enable/disable toggle
- Signal history log
- Configuration panel
- Auto-refreshes every 10 seconds

---

## 🔧 Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `false` | Master on/off switch |
| `webhook_urls` | `[]` | Array of webhook URLs to post signals |
| `buy_threshold` | `4.0` | Score required for buy signal |
| `sell_threshold` | `-4.0` | Score required for sell signal |
| `close_threshold` | `1.0` | Near-zero threshold for close signals |
| `score_window_minutes` | `5` | Rolling window for score calculation |
| `update_interval_seconds` | `45` | How often to fetch flows and compute scores |

---

## ❓ Troubleshooting

### SmartFlow not generating signals

**Check:**
1. Is `flow_confluence_proxy.py` running? (`ps aux | grep flow_confluence`)
2. Is it returning flows? (`curl http://localhost:9001/flows`)
3. Is SmartFlow enabled? (`curl .../api/v1/smartflow/config | jq .enabled`)
4. Are flows passing thresholds? (`curl .../api/v1/smartflow/status | jq .scores`)

### Webhook posting fails

**Check:**
1. Webhook URLs in config: `curl .../api/v1/smartflow/config | jq .webhook_urls`
2. Signal logs for errors: `curl .../api/v1/smartflow/signals | jq '.[0].post_errors'`
3. Application logs: `grep -i "smartflow" app.log`

### Database connection errors

**Symptoms**: SmartFlow crashes on startup with database errors

**Solution**: Run the migration first (see Pending Task #1)

---

## 🚀 Deployment Checklist

- [x] Code integrated into main.py
- [x] Alembic migration created
- [ ] Database migration applied (`alembic upgrade head`)
- [ ] Application restarted
- [ ] FlowAlgo proxy running (port 9001)
- [ ] SmartFlow config created and enabled
- [ ] First signal generated successfully
- [ ] Dashboard accessible and showing live data

---

## 📚 Documentation

- **User Guide**: `SMARTFLOW_README.md`
- **Integration Guide**: `SMARTFLOW_INTEGRATION.md`
- **API Reference**: `SMARTFLOW_README.md` (API section)
- **Service Code**: `app/services/smartflow_service.py`
- **Database Models**: `app/models/smartflow_models.py`
- **API Router**: `app/routers/smartflow.py`

---

## 🎉 Summary

SmartFlow Indicator is **fully integrated** and ready to deploy. It's a completely non-destructive, optional enhancement that:

- ✅ Adds AI-driven flow sentiment analysis
- ✅ Runs independently as background task
- ✅ Generates signals based on institutional options flow
- ✅ Posts to your existing webhooks (same format as TradingView)
- ✅ Includes beautiful dashboard UI
- ✅ Zero impact on existing functionality
- ✅ Can run alongside TradingView signals (hybrid mode)
- ✅ Per-user configuration and enable/disable

**Next Step**: Apply the database migration and restart the application!
