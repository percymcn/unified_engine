# TradeFlow API Documentation

**Version:** 1.2  
**Base URL:** `http://localhost:8765` (development) / `https://api.tradeflow.fluxeo.net` (production)  
**Date:** January 22, 2026

## Table of Contents

1. [Authentication](#authentication)
2. [Webhook Endpoints](#webhook-endpoints)
3. [Signal Intelligence API](#signal-intelligence-api)
4. [Risk Management API](#risk-management-api)
5. [Error Codes](#error-codes)
6. [Setup Steps](#setup-steps)

## Authentication

All API endpoints (except public webhooks) require JWT authentication via Bearer token.

```bash
# Login to get token
curl -X POST http://localhost:8765/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user@example.com", "password": "password"}'

# Use token in subsequent requests
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8765/api/v1/accounts
```

## Webhook Endpoints

### POST /api/v1/webhooks/tradingview

Receive TradingView webhook signals.

**Request Body:**
```json
{
  "ticker": "EURUSD",
  "action": "buy",
  "quantity": 0.01,
  "price": 1.1000,
  "stop_loss": 1.0950,
  "take_profit": 1.1100,
  "comment": "Signal from strategy",
  "strategy_id": "strategy_123",
  "user_id": 1
}
```

**Response:**
```json
{
  "success": true,
  "signal_id": "uuid-here",
  "status": "executed",
  "executions": 1,
  "errors": [],
  "processing_time_ms": 45
}
```

**Guard Layer Responses:**
- `status: "skipped"` - Signal was stale or discarded
- `status: "paused"` - New entries paused (chop mode or exposure limit)
- `status: "warning_required"` - Momentum warning modal required

### POST /api/v1/webhooks/trailhacker

Receive TrailHacker webhook signals.

**Request Body:**
```json
{
  "symbol": "EURUSD",
  "signal": "buy",
  "size": 0.01,
  "entry": 1.1000,
  "stop": 1.0950,
  "target": 1.1100,
  "user_id": 1
}
```

### POST /api/v1/webhooks/signal/{webhook_key}

Receive routed signals via webhook configuration.

**URL Parameters:**
- `webhook_key`: Unique webhook key from webhook config

**Request Body:** Same as TradingView format

**Response:** Same format as TradingView endpoint

## Signal Intelligence API

### GET /api/v1/signal-intelligence/settings

Get user's momentum guard settings.

**Response:**
```json
{
  "user_id": 1,
  "warn_at": 6,
  "auto_breakeven": false,
  "pause_on_chop": true,
  "max_exposure": 5000.0,
  "auto_pause_on_exposure": true,
  "allow_hedge": false,
  "staleness_enabled": true,
  "staleness_seconds": 5,
  "force_old_signals": false,
  "discard_flush_interval": "24h",
  "created_at": "2026-01-22T12:00:00Z",
  "updated_at": "2026-01-22T12:00:00Z"
}
```

### PUT /api/v1/signal-intelligence/settings

Update momentum guard settings.

**Request Body:**
```json
{
  "warn_at": 8,
  "max_exposure": 10000.0,
  "staleness_seconds": 10
}
```

All fields are optional. Only provided fields will be updated.

### GET /api/v1/signal-intelligence/counters

Get all signal counters for user.

**Response:**
```json
[
  {
    "user_id": 1,
    "session_key": "1:EURUSD:strategy_123",
    "current_bias": "buy",
    "opposite_momentum": 3,
    "last_signal_ts": "2026-01-22T12:00:00Z",
    "last8_pattern": "BBBSBSBS",
    "chop_mode": false,
    "updated_at": "2026-01-22T12:00:00Z"
  }
]
```

### GET /api/v1/signal-intelligence/counters/{session_key}

Get specific signal counter.

**URL Parameters:**
- `session_key`: Format `{user_id}:{symbol}:{strategy_id}`

### POST /api/v1/signal-intelligence/counters/reset

Reset a signal counter.

**Request Body:**
```json
{
  "session_key": "1:EURUSD:strategy_123"
}
```

### POST /api/v1/signal-intelligence/modal-action

Handle guard modal actions.

**Request Body:**
```json
{
  "signal_id": "uuid-here",
  "action": "breakeven",  // or "close", "ignore", "hedge"
  "session_key": "1:EURUSD:strategy_123"
}
```

**Actions:**
- `breakeven`: Move SL to entry price
- `close`: Close position
- `ignore`: Reset counter and continue
- `hedge`: Create reverse order at 0.5x size

### GET /api/v1/signal-intelligence/discard-bin

Get discard bin entries.

**Query Parameters:**
- `limit`: Number of entries (default: 100)
- `reason`: Filter by reason (optional)

**Response:**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "received_at": "2026-01-22T12:00:00Z",
    "reason": "stale",
    "age_ms": 6000,
    "symbol": "EURUSD",
    "side": "buy",
    "broker_target": "mt4",
    "created_at": "2026-01-22T12:00:00Z"
  }
]
```

### POST /api/v1/signal-intelligence/discard-bin/flush

Flush old discard bin entries based on flush interval setting.

## Risk Management API

### GET /api/v1/risk/settings

Get global risk settings (existing endpoint).

### PUT /api/v1/risk/settings

Update global risk settings (existing endpoint).

## Error Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request - Invalid payload or parameters |
| 401 | Unauthorized - Missing or invalid token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 422 | Unprocessable Entity - Validation failed |
| 500 | Internal Server Error |
| 503 | Service Unavailable - Broker disconnected |

## Setup Steps

### 1. Database Migration

```bash
# Activate virtual environment
source venv/bin/activate

# Run migration
alembic upgrade head

# Verify tables created
psql -d unified_trading_db -c "\dt" | grep -E "(momentum_settings|signal_counters|discard_bin)"
```

### 2. Configure Webhook

1. Create webhook config via UI or API:
   ```bash
   POST /api/v1/webhook-configs
   {
     "name": "My Strategy",
     "source": "tradingview",
     "routing_strategy": "all_accounts"
   }
   ```

2. Get `webhook_key` from response

3. Configure TradingView webhook URL:
   ```
   https://api.tradeflow.fluxeo.net/api/v1/webhooks/signal/{webhook_key}
   ```

### 3. Configure Momentum Settings

1. Via UI: Go to Settings → Risk → Signal Intelligence Guard
2. Via API:
   ```bash
   PUT /api/v1/signal-intelligence/settings
   {
     "warn_at": 6,
     "max_exposure": 5000,
     "staleness_enabled": true,
     "staleness_seconds": 5
   }
   ```

### 4. Test Signal Processing

```bash
# Send test signal
curl -X POST http://localhost:8765/api/v1/webhooks/signal/YOUR_WEBHOOK_KEY \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "EURUSD",
    "action": "buy",
    "quantity": 0.01,
    "price": 1.1000
  }'

# Check counters
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8765/api/v1/signal-intelligence/counters

# Check discard bin
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8765/api/v1/signal-intelligence/discard-bin
```

## Webhook Formats

### TradingView Format

```json
{
  "ticker": "EURUSD",
  "action": "buy|sell|close",
  "quantity": 0.01,
  "price": 1.1000,
  "stop_loss": 1.0950,
  "take_profit": 1.1100,
  "comment": "Optional comment",
  "strategy_id": "strategy_123",
  "strategy_name": "My Strategy",
  "timestamp": "2026-01-22T12:00:00Z"
}
```

### TrailHacker Format

```json
{
  "symbol": "EURUSD",
  "signal": "buy|sell|close",
  "size": 0.01,
  "entry": 1.1000,
  "stop": 1.0950,
  "target": 1.1100,
  "strategy_id": "strategy_123"
}
```

## Guard Layer Behavior

The Signal Intelligence Guard Layer evaluates signals before execution:

1. **Staleness Check** (sg-002)
   - If signal age > `staleness_seconds` → SKIP
   - Respects `force_old_signals` toggle

2. **Momentum Guard** (sg-001)
   - Tracks directional bias per session
   - Increments counter on direction flips
   - If `opposite_momentum >= warn_at` → WARN_MODAL_REQUIRED
   - Detects chop mode (alternating pattern)
   - If chop detected and `pause_on_chop` → PAUSE_NEW_ENTRIES

3. **Exposure Guard** (sg-004)
   - Calculates total margin across positions
   - If `total_margin >= max_exposure` → PAUSE_NEW_ENTRIES

4. **Discard Bin** (sg-005)
   - All SKIP decisions logged to `discard_bin`
   - Auto-flush based on `discard_flush_interval`

## OpenAPI Specification

FastAPI automatically generates OpenAPI spec at:
- Development: `http://localhost:8765/docs`
- Production: `https://api.tradeflow.fluxeo.net/docs` (if enabled)

The spec includes all endpoints, request/response schemas, and examples.

## Rate Limiting

- Webhook endpoints: 100 requests/minute per IP
- API endpoints: 1000 requests/hour per user
- Guard layer: No additional rate limits (evaluates per signal)

## Support

For issues or questions:
- Check logs: `docker-compose logs -f api`
- Review discard bin for rejected signals
- Check signal counters for momentum state
- Verify settings via `/api/v1/signal-intelligence/settings`
