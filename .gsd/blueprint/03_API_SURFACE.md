# API Surface: Unified Trading Engine

## OpenAPI Specification

Backend exposes OpenAPI at: `http://localhost:8765/openapi.json`

## API Groups

### Authentication (`/api/v1/auth`)

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| POST | `/register` | `auth.py:register` | User registration |
| POST | `/login` | `auth.py:login` | JWT login |
| GET | `/me` | `auth.py:get_current_user` | Current user info |
| POST | `/logout` | `auth.py:logout` | Invalidate session |
| POST | `/refresh` | `auth.py:refresh` | Refresh JWT token |
| POST | `/change-password` | `auth.py:change_password` | Update password |
| GET | `/sessions` | `auth.py:list_sessions` | Active sessions |
| DELETE | `/sessions/{session_id}` | `auth.py:revoke_session` | Revoke session |

### Accounts (`/api/v1/accounts`)

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| GET | `/` | `accounts.py:list_accounts` | List user accounts |
| POST | `/` | `accounts.py:create_account` | Add broker account |
| POST | `/test-connection` | `accounts.py:test_connection` | Test broker credentials |
| GET | `/available/{broker_type}` | `accounts.py:get_available_accounts` | List broker accounts |
| POST | `/{account_id}/select` | `accounts.py:select_account` | Set active account |
| POST | `/sync-all` | `accounts.py:sync_all_accounts` | Refresh all balances |
| GET | `/{account_id}` | `accounts.py:get_account` | Get account details |
| PUT | `/{account_id}` | `accounts.py:update_account` | Update account |
| DELETE | `/{account_id}` | `accounts.py:delete_account` | Remove account |
| POST | `/{account_id}/sync` | `accounts.py:sync_account` | Sync single account |
| GET | `/{account_id}/balance` | `accounts.py:get_balance` | Get current balance |
| GET | `/{account_id}/settings` | `accounts.py:get_settings` | Account risk settings |
| PUT | `/{account_id}/settings` | `accounts.py:update_settings` | Update settings |

### Positions (`/api/v1/positions`)

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| GET | `/` | `positions.py:list_positions` | All open positions |
| GET | `/{position_id}` | `positions.py:get_position` | Position details |
| POST | `/{position_id}/close` | `positions.py:close_position` | Close position |
| GET | `/account/{account_id}` | `positions.py:account_positions` | Positions by account |

### Trades (`/api/v1/trades`)

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| GET | `/` | `trades.py:list_trades` | Trade history |
| GET | `/{trade_id}` | `trades.py:get_trade` | Trade details |
| GET | `/account/{account_id}` | `trades.py:account_trades` | Trades by account |

### Signals (`/api/v1/signals`)

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| GET | `/` | `signals.py:list_signals` | Signal history |
| GET | `/{signal_id}` | `signals.py:get_signal` | Signal details |
| POST | `/{signal_id}/cancel` | `signals.py:cancel_signal` | Cancel pending |
| GET | `/history` | `signals.py:signal_history` | Historical signals |
| GET | `/active` | `signals.py:active_signals` | Currently processing |
| POST | `/execute` | `signals.py:manual_execute` | Manual signal |

### Webhooks (`/api/v1/webhooks`)

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| POST | `/tradingview` | `webhooks.py:tradingview_webhook` | TradingView alerts |
| POST | `/trailhacker` | `webhooks.py:trailhacker_webhook` | Trailhacker alerts |
| POST | `/signal/{webhook_key}` | `signal_router.py:handle_signal` | Generic signal |
| GET | `/logs` | `webhooks.py:webhook_logs` | Webhook history |
| POST | `/test` | `webhooks.py:test_webhook` | Test webhook |

### Webhook Config (`/api/v1/webhook-configs`)

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| GET | `/` | `webhook_config.py:list_configs` | List webhooks |
| POST | `/` | `webhook_config.py:create_config` | Create webhook |
| GET | `/{config_id}` | `webhook_config.py:get_config` | Get config |
| PUT | `/{config_id}` | `webhook_config.py:update_config` | Update config |
| DELETE | `/{config_id}` | `webhook_config.py:delete_config` | Delete config |
| POST | `/{config_id}/regenerate-key` | `webhook_config.py:regenerate` | New webhook key |

### Risk Management (`/api/v1/risk`)

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| GET | `/settings` | `risk.py:get_risk_settings` | User risk settings |
| PUT | `/settings` | `risk.py:update_risk_settings` | Update settings |
| GET | `/daily-pnl` | `risk.py:get_daily_pnl` | Today's P&L |
| GET | `/rejected-signals` | `risk.py:rejected_signals` | Rejection log |

### Credentials (`/api/v1/credentials`)

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| GET | `/` | `credential_router.py:list_credentials` | List credentials |
| POST | `/` | `credential_router.py:create_credential` | Store credential |
| GET | `/{credential_id}` | `credential_router.py:get_credential` | Get (decrypted) |
| DELETE | `/{credential_id}` | `credential_router.py:delete_credential` | Remove credential |
| POST | `/{credential_id}/rotate` | `credential_router.py:rotate` | Rotate credential |

### Unified API (`/api/v1/unified`)

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| GET | `/health` | `unified_router.py:health` | System health |
| GET | `/status` | `unified_router.py:status` | Detailed status |
| GET | `/accounts` | `unified_router.py:accounts` | All accounts |
| GET | `/positions` | `unified_router.py:positions` | All positions |
| GET | `/orders` | `unified_router.py:orders` | All orders |
| GET | `/signals` | `unified_router.py:signals` | Recent signals |
| GET | `/trades` | `unified_router.py:trades` | Recent trades |
| GET | `/symbols` | `unified_router.py:symbols` | Available symbols |
| GET | `/brokers` | `unified_router.py:brokers` | Broker status |
| GET | `/brokers/{broker_name}/status` | `unified_router.py:broker_status` | Single broker |

### Billing (`/api/v1/billing`)

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| POST | `/create-checkout` | `billing.py:create_checkout` | Stripe checkout |
| POST | `/create-portal` | `billing.py:create_portal` | Billing portal |
| GET | `/subscription` | `billing.py:get_subscription` | Current plan |

### OAuth (`/api/v1/oauth`)

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| GET | `/tradovate/authorize` | `tradovate_oauth.py:authorize` | Start OAuth |
| GET | `/tradovate/callback` | `tradovate_oauth.py:callback` | OAuth callback |
| POST | `/tradovate/disconnect` | `tradovate_oauth.py:disconnect` | Revoke OAuth |

### Health (`/health`)

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| GET | `/health` | `health.py:health_check` | Basic health |
| GET | `/api/v1/health/detailed` | `health.py:detailed_health` | Full status |

## Key Request/Response Schemas

### Account Creation
```json
POST /api/v1/accounts/
{
  "broker": "tradelocker",
  "account_type": "demo",
  "account_number": "12345",
  "account_name": "My Demo Account",
  "api_key": "...",  // Optional - stored encrypted
  "api_secret": "..."  // Optional - stored encrypted
}
```

### Test Connection
```json
POST /api/v1/accounts/test-connection
{
  "broker_type": "tradelocker",
  "credentials": {
    "email": "user@example.com",
    "password": "...",
    "server": "Demo Server",
    "environment": "https://demo.tradelocker.com"
  }
}
Response: { "success": true, "accounts": [...] }
```

### Webhook Signal
```json
POST /api/v1/webhooks/signal/{webhook_key}
{
  "symbol": "EURUSD",
  "action": "buy",
  "qty": 0.1,
  "price": 1.0850,
  "stop_loss": 1.0800,
  "take_profit": 1.0950
}
```

### Signal Response
```json
{
  "signal_id": "abc123",
  "status": "executed",
  "executed_accounts": 2,
  "failed_accounts": 0,
  "results": [
    {
      "account_id": 1,
      "broker": "tradelocker",
      "status": "success",
      "order_id": "12345"
    }
  ]
}
```

---
*Generated: 2026-01-22*
