# SmartFlow Indicator - User Guide

## Overview

**SmartFlow Indicator** is an optional AI-powered signal source that enhances your TradeFlow application by generating trading signals from live institutional options flow data scraped from FlowAlgo.

### Key Features

✅ **Non-Destructive**: Runs alongside TradingView webhooks without interfering
✅ **Toggleable**: Enable/disable per user via dashboard
✅ **Sentiment-Based**: Computes real-time Flow Sentiment Scores
✅ **Auto-Posting**: Sends signals to your existing webhook URLs
✅ **Dashboard**: Beautiful monitoring interface with live scores and signal log

---

## How It Works

### 1. **Flow Data Source**

SmartFlow connects to your running `flow_confluence_proxy.py` (on port 9001) which scrapes FlowAlgo for:
- **Tickers**: SPY, QQQ, GLD options flow
- **Types**: Sweeps and Blocks only
- **Minimum Premium**: $50,000+
- **Update Frequency**: Every 30-60 seconds

### 2. **Sentiment Scoring Algorithm**

SmartFlow computes a **Flow Sentiment Score** for each ticker every 45 seconds:

```
Score Calculation (5-minute rolling window):
- Bullish call sweep/block:
  * Premium $50K-$100K:  +1.0 (+1.5 for sweeps)
  * Premium $100K-$500K: +2.0 (+2.5 for sweeps)
  * Premium $500K+:      +3.0 (+3.5 for sweeps)

- Bearish put sweep/block:
  * Same thresholds but NEGATIVE scores

Net Score = Sum of all flows in window
```

### 3. **Signal Generation**

Signals are generated when sentiment crosses thresholds:

| Score Range | Signal | Action |
|-------------|--------|--------|
| **> +4.0** | BUY | Opens long position |
| **< -4.0** | SELL | Opens short position |
| **Near 0 after extreme** | CLOSE | Closes existing position |

### 4. **Signal Routing**

When a signal is generated:
1. Mapped ticker is used (SPY→MES, QQQ→NQ, GLD→GC)
2. Current market price is fetched from broker
3. Signal is POST'd to your configured webhook URLs
4. Same format as TradingView alerts:
   ```json
   {
     "ticker": "MES",
     "action": "buy",
     "price": 5855.50,
     "source": "SmartFlow",
     "score": 6.5,
     "timestamp": "2026-03-05T10:30:00Z"
   }
   ```

---

## Installation & Setup

### Step 1: Install Database Tables

Run the SQL migration:

```bash
cd /home/pharma5/unified_engine
psql -U your_db_user -d your_db_name -f migrations/smartflow_tables.sql
```

Or with Alembic:

```bash
alembic revision --autogenerate -m "Add SmartFlow tables"
alembic upgrade head
```

### Step 2: Integrate into main.py

Follow the instructions in `SMARTFLOW_INTEGRATION.md`:

1. Add imports
2. Add background task function
3. Register background task in startup
4. Include SmartFlow router

### Step 3: Restart Application

```bash
# If running with systemd
sudo systemctl restart unified-engine

# If running manually
pkill -f "uvicorn app.main:app"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Step 4: Verify Installation

Check logs for startup message:
```
🤖 SmartFlow background task started
```

Test API endpoint:
```bash
curl http://localhost:8000/api/v1/smartflow/status
```

---

## Configuration

### Via API

**Get Configuration:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/smartflow/config
```

**Enable SmartFlow:**
```bash
curl -X PUT http://localhost:8000/api/v1/smartflow/config \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "webhook_urls": [
      "https://api.mytradeflow.app/webhooks/tradingview/YOUR_KEY"
    ],
    "buy_threshold": 4.0,
    "sell_threshold": -4.0,
    "close_threshold": 1.0,
    "score_window_minutes": 5,
    "update_interval_seconds": 45
  }'
```

**Disable SmartFlow:**
```bash
curl -X PUT http://localhost:8000/api/v1/smartflow/config \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false, "webhook_urls": []}'
```

### Via Dashboard

Access the SmartFlow Monitor UI:
```
http://localhost:8000/static/smartflow_dashboard.html
```

Features:
- **Toggle Switch**: Enable/disable with one click
- **Live Scores**: Real-time sentiment for SPY/QQQ/GLD
- **Signal Log**: Last 20 signals with timestamps
- **Configuration**: Edit thresholds and webhook URLs

---

## API Endpoints

### `GET /api/v1/smartflow/config`
Get user's SmartFlow configuration (creates default if not exists).

**Response:**
```json
{
  "id": 1,
  "user_id": 123,
  "enabled": true,
  "webhook_urls": ["https://..."],
  "buy_threshold": 4.0,
  "sell_threshold": -4.0,
  "close_threshold": 1.0,
  "score_window_minutes": 5,
  "update_interval_seconds": 45,
  "created_at": "2026-03-05T10:00:00Z",
  "updated_at": "2026-03-05T10:30:00Z"
}
```

### `PUT /api/v1/smartflow/config`
Update SmartFlow configuration.

**Request Body:**
```json
{
  "enabled": true,
  "webhook_urls": ["https://api.mytradeflow.app/webhooks/..."],
  "buy_threshold": 5.0,
  "sell_threshold": -5.0
}
```

### `GET /api/v1/smartflow/status`
Get current SmartFlow status and live scores.

**Response:**
```json
{
  "enabled": true,
  "latest_scores": {
    "SPY": {
      "score": 6.5,
      "bullish_flows": 12,
      "bearish_flows": 3,
      "total_premium": 2500000,
      "timestamp": "2026-03-05T10:30:00Z"
    },
    "QQQ": {...},
    "GLD": {...}
  },
  "last_signals": {
    "SPY": {
      "ticker": "MES",
      "action": "buy",
      "score": 6.5,
      "timestamp": "2026-03-05T10:29:00Z"
    }
  },
  "recent_signals": [...],
  "webhook_count": 1,
  "update_interval": 45
}
```

### `GET /api/v1/smartflow/signals`
Get signal history with optional filters.

**Query Parameters:**
- `limit` (default 50): Maximum signals to return
- `ticker` (optional): Filter by ticker (MES, NQ, GC)

**Response:**
```json
[
  {
    "id": 456,
    "ticker": "MES",
    "action": "buy",
    "score": 6.5,
    "price": 5855.50,
    "bullish_flows": 12,
    "bearish_flows": 3,
    "total_premium": 2500000,
    "created_at": "2026-03-05T10:29:00Z"
  },
  ...
]
```

### `GET /api/v1/smartflow/scores/history`
Get sentiment score history for charting.

**Query Parameters:**
- `ticker` (required): SPY, QQQ, or GLD
- `hours` (default 24): Hours of history to return

**Response:**
```json
[
  {
    "timestamp": "2026-03-05T09:30:00Z",
    "score": 2.5,
    "bullish_flows": 5,
    "bearish_flows": 2,
    "total_premium": 750000
  },
  ...
]
```

### `POST /api/v1/smartflow/test-signal`
Send a test signal (for debugging).

**Query Parameters:**
- `ticker`: MES, NQ, or GC
- `action`: buy, sell, or close

**Response:**
```json
{
  "status": "success",
  "message": "Test buy signal sent for MES",
  "webhooks_posted": 1
}
```

---

## Hybrid Mode (TradingView + SmartFlow)

SmartFlow runs **independently** of TradingView webhooks. You can use:

### **Option 1: TradingView Only**
- Keep SmartFlow disabled
- All signals come from TradingView alerts

### **Option 2: SmartFlow Only**
- Disable TradingView alerts
- All signals come from SmartFlow

### **Option 3: Hybrid Mode (Recommended)**
- Enable both TradingView and SmartFlow
- Configure SmartFlow to use **different** webhook URLs OR
- Use the **same** webhook URLs to let both sources send signals
- Your existing signal routing/filtering will handle both

**Example Hybrid Setup:**
```json
{
  "tradingview_webhooks": [
    "https://api.mytradeflow.app/webhooks/tradingview/TV_KEY"
  ],
  "smartflow_webhooks": [
    "https://api.mytradeflow.app/webhooks/tradingview/SMARTFLOW_KEY"
  ]
}
```

Or same webhook for both:
```json
{
  "both_sources_webhook": [
    "https://api.mytradeflow.app/webhooks/tradingview/SHARED_KEY"
  ]
}
```

SmartFlow signals include `"source": "SmartFlow"` for identification.

---

## Monitoring & Troubleshooting

### Check Logs

SmartFlow logs are in the main application logs:
```bash
tail -f logs/app.log | grep SmartFlow
```

Look for:
```
✅ SmartFlow enabled with 1 webhook(s)
🟢 SmartFlow BUY signal: SPY score=6.50
✅ SmartFlow signal forwarded to https://...
```

### Common Issues

**1. SmartFlow not generating signals**
- Check if flow_confluence_proxy.py is running on port 9001
- Verify FlowAlgo is scraping data: `curl http://localhost:9001/recent`
- Check if scores are being computed: `curl /api/v1/smartflow/status`

**2. Signals not reaching broker**
- Verify webhook URLs are correct in configuration
- Check webhook execution logs in TradeFlow dashboard
- Test webhook manually: `POST /api/v1/smartflow/test-signal`

**3. Incorrect sentiment scores**
- Verify FlowAlgo data quality
- Adjust score thresholds if too sensitive/insensitive
- Check score window (default 5 minutes might be too short/long)

### Performance Tuning

**Adjust sensitivity:**
```json
{
  "buy_threshold": 5.0,      // Higher = less frequent buys
  "sell_threshold": -5.0,    // Lower = less frequent sells
  "score_window_minutes": 10  // Longer = smoother scores
}
```

**Adjust update frequency:**
```json
{
  "update_interval_seconds": 60  // Check scores less frequently
}
```

---

## Example Scenarios

### Scenario 1: Strong Bullish Flow

```
FlowAlgo data (last 5 minutes):
- SPY 685 CALL sweep $486K   → +3.5 (sweep bonus)
- SPY 684 CALL sweep $192K   → +2.5
- SPY 685 CALL block $148K   → +2.0
- SPY 680 CALL sweep $96K    → +1.5
Net Score: +9.5 (> +4.0 threshold)

SmartFlow Action:
→ Generate BUY signal for MES
→ POST to webhook: {"ticker": "MES", "action": "buy", "score": 9.5}
```

### Scenario 2: Mixed Flow (No Signal)

```
FlowAlgo data (last 5 minutes):
- QQQ 610 CALL sweep $164K   → +2.5
- QQQ 612 PUT sweep $109K    → -2.0
- QQQ 607 CALL block $114K   → +2.0
Net Score: +2.5 (below +4.0 threshold)

SmartFlow Action:
→ No signal generated (neutral zone)
```

### Scenario 3: Fade to Close

```
Previous state: Long MES (from score +8.0)

FlowAlgo data (last 5 minutes):
- SPY 680 PUT sweep $157K    → -2.5
- SPY 682 PUT block $112K    → -2.0
Net Score: -4.5 → faded to +0.5

SmartFlow Action:
→ Generate CLOSE signal for MES
→ POST to webhook: {"ticker": "MES", "action": "close", "score": 0.5}
```

---

## Security Considerations

1. **Authentication**: All API endpoints require valid Bearer token
2. **User Isolation**: Each user has separate configuration and signal logs
3. **Webhook URLs**: Stored per user, not shared
4. **Rate Limiting**: Standard FastAPI rate limits apply
5. **Data Privacy**: Flow data is sourced from FlowAlgo proxy, not stored permanently

---

## Maintenance

### Database Cleanup

Score history can grow large. Recommended cleanup:

```sql
-- Delete score history older than 7 days
DELETE FROM smartflow_score_history
WHERE timestamp < NOW() - INTERVAL '7 days';

-- Delete signal logs older than 30 days
DELETE FROM smartflow_signal_logs
WHERE created_at < NOW() - INTERVAL '30 days';
```

Add to cron:
```bash
# Daily at 3 AM
0 3 * * * psql -U user -d db -c "DELETE FROM smartflow_score_history WHERE timestamp < NOW() - INTERVAL '7 days';"
```

### Monitoring

Key metrics to monitor:
- Signal generation rate (should be ~1-3 per hour normally)
- Webhook post success rate (should be >95%)
- Flow data freshness (check last_update timestamp)
- Background task health (check logs for errors)

---

## FAQ

**Q: Does SmartFlow affect my TradingView signals?**
A: No. SmartFlow is completely independent and posts to webhooks just like TradingView does.

**Q: Can I use SmartFlow without TradingView?**
A: Yes! You can disable TradingView and use only SmartFlow.

**Q: How much does SmartFlow cost?**
A: SmartFlow itself is free. You need a FlowAlgo subscription ($$$) for the data source.

**Q: What if FlowAlgo proxy goes down?**
A: SmartFlow will log errors but continue running. No signals will be generated until proxy recovers.

**Q: Can I customize the scoring algorithm?**
A: Yes, edit `app/services/smartflow_service.py` and adjust the `compute_sentiment_score()` method.

**Q: Does SmartFlow work with all brokers?**
A: Yes! Signals are posted to webhooks, which route to your broker via TradeFlow's existing execution system.

---

## Support

For issues or questions:
1. Check logs: `tail -f logs/app.log | grep SmartFlow`
2. Test endpoints with curl examples above
3. Verify flow_confluence_proxy.py is running
4. Check dashboard for configuration errors

---

**Happy Trading with SmartFlow! 🚀**
