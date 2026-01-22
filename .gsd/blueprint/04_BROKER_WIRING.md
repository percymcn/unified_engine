# Broker Wiring: Unified Trading Engine

## Overview

The system uses a hexagonal architecture for broker integrations:

```
Domain Layer (ports)     →     Infrastructure Layer (adapters)     →     Broker Layer (executors)
  BrokerPort interface          TradeLockerAdapter                        TradeLockerExecutor
                                TopstepAdapter                            ProjectXExecutor
                                MT4Adapter                                MT4Executor
                                MT5Adapter                                MT5Executor
                                TradovateAdapter                          TradovateExecutor
```

---

## TradeLocker Integration

### Files

| File | Purpose |
|------|---------|
| `app/infrastructure/adapters/tradelocker_adapter.py` | BrokerPort implementation |
| `app/brokers/tradelocker_executor.py` | Low-level API calls |
| `app/brokers/tradelocker_sdk_wrapper.py` | Async wrapper for SDK |

### Authentication Methods

**SDK Mode (Preferred):**
- Uses official `tradelocker` Python package
- Requires: `email`, `password`, `server`, `environment`
- SDK handles JWT refresh internally
- Wrapped with `ThreadPoolExecutor` for async

**Brand API Mode (Fallback):**
- Uses `httpx` for direct HTTP calls
- Requires: `brand_api_url`, `brand_id`, `api_key`
- Manual JWT token management

### Config Keys (Environment Variables)

```bash
TRADELOCKER_USERNAME=your-email@example.com    # SDK mode
TRADELOCKER_PASSWORD=your-password             # SDK mode
TRADELOCKER_SERVER=Demo Server                 # SDK mode (server name)
TRADELOCKER_ENVIRONMENT=https://demo.tradelocker.com  # SDK mode

TRADELOCKER_BRAND_API_URL=https://api.tradelocker.com  # Brand API mode
TRADELOCKER_BRAND_ID=your-brand-id                     # Brand API mode
```

### Credential Fields (Database)

Table: `trading_accounts`
```
broker = 'tradelocker'
api_key = <encrypted>           # For Brand API mode
api_secret = <encrypted>        # For Brand API mode
access_token = <encrypted>      # JWT token
refresh_token = <encrypted>     # Refresh token
token_expires_at = <timestamp>
```

Table: `credentials` (Fernet encrypted JSON)
```json
{
  "email": "user@example.com",
  "password": "...",
  "server": "Demo Server",
  "environment": "https://demo.tradelocker.com"
}
```

### Happy Path Sequence

```
1. UI: User clicks "Add TradeLocker Account"
   → POST /api/v1/accounts/test-connection

2. API: accounts.py:test_connection()
   → Creates TradeLockerExecutor with credentials
   → Calls executor.initialize()

3. Executor: tradelocker_executor.py:initialize()
   → If SDK available: Creates TradeLockerSDKWrapper
   → SDK wrapper: TLAPI(environment, username, password, server)
   → SDK authenticates, returns account info

4. API: Returns available accounts to UI
   → User selects account, clicks "Connect"
   → POST /api/v1/accounts/

5. API: accounts.py:create_account()
   → Encrypts credentials with Fernet
   → Stores in trading_accounts table
   → Returns account_id

6. Signal arrives: POST /api/v1/webhooks/signal/{key}

7. Signal Processor: signal_processor.py:process_signal()
   → Gets user's TradeLocker accounts (is_signal_enabled=True)
   → For each account: Gets executor from broker pool

8. Executor: tradelocker_executor.py:place_order()
   → SDK: wrapper.create_order(instrument_id, qty, side, type_)
   → Brand API: httpx POST to /v2/trade/orders

9. Response: Order ID, status, filled price
   → Stored in trades table
   → WebSocket push to UI
```

---

## ProjectX/TopStep Integration

### Files

| File | Purpose |
|------|---------|
| `app/infrastructure/adapters/topstep_adapter.py` | BrokerPort implementation |
| `app/brokers/projectx_executor.py` | Gateway API calls |
| `app/services/projectx_sdk_service.py` | SDK wrapper (deprecated) |

### Authentication Method

**Gateway API (Recommended for v1.2):**
- Direct HTTP calls via `httpx`
- Auth: `POST /api/Auth/loginKey` with `userName` + `apiKey`
- Returns JWT token (24h expiry)
- Manual token refresh required

**SDK Mode (Deprecated):**
- Uses `project-x-py` package
- Complex TradingSuite lifecycle
- v1.2 will remove this

### Config Keys (Environment Variables)

```bash
PROJECT_X_USERNAME=your-topstep-username
PROJECT_X_API_KEY=your-api-key
PROJECTX_GATEWAY_API_URL=https://gateway-api.s2f.projectx.com  # Live
# OR
PROJECTX_GATEWAY_API_URL=https://gateway-api-demo.s2f.projectx.com  # Demo
```

### Credential Fields (Database)

Table: `trading_accounts`
```
broker = 'projectx' OR 'topstep'
account_number = <TopStep account ID>
api_key = <encrypted API key>
access_token = <encrypted JWT>
token_expires_at = <24h from auth>
```

### Happy Path Sequence

```
1. UI: User clicks "Add TopStep Account"
   → POST /api/v1/accounts/test-connection

2. API: accounts.py:test_connection()
   → Creates ProjectXExecutor(username, api_key)
   → Calls executor.initialize()

3. Executor: projectx_executor.py:_initialize_httpx()
   → POST /api/Auth/loginKey { userName, apiKey }
   → Receives JWT token
   → Stores in Authorization header
   → POST /api/Account/search {} → Returns available accounts

4. API: Returns accounts to UI
   → User selects account, clicks "Connect"

5. Signal arrives: POST /api/v1/webhooks/signal/{key}

6. Signal Processor: Routes to ProjectXExecutor

7. Executor: projectx_executor.py:_place_order_httpx()
   → POST /api/Contract/search { symbol } → Get contract_id
   → POST /api/Order/place { accountId, contractId, side, type, size }

8. Response: Order confirmation → stored in trades table
```

### Gateway API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/Auth/loginKey` | POST | Authenticate, get JWT |
| `/api/Account/search` | POST | List accounts |
| `/api/Contract/search` | POST | Find contract by symbol |
| `/api/Contract/available` | POST | List available contracts |
| `/api/Order/place` | POST | Place order |
| `/api/Order/cancel` | POST | Cancel order |
| `/api/Order/modify` | POST | Modify order |
| `/api/Order/searchOpen` | POST | List pending orders |
| `/api/Position/searchOpen` | POST | List open positions |
| `/api/Position/closeContract` | POST | Close position |

---

## MT4/MT5 Integration

### Files

| File | Purpose |
|------|---------|
| `app/infrastructure/adapters/mt4_adapter.py` | BrokerPort implementation |
| `app/infrastructure/adapters/mt5_adapter.py` | BrokerPort implementation |
| `app/brokers/mt4_executor.py` | Manager API calls |
| `app/brokers/mt5_executor.py` | Manager API calls |

### Authentication Method

Uses MetaTrader Manager API (REST bridge):
- Requires running MT4/MT5 Manager API server
- Auth via manager login/password

### Config Keys

```bash
MT4_MANAGER_API_URL=http://localhost:4444
MT4_MANAGER_LOGIN=1
MT4_MANAGER_PASSWORD=your-mt4-manager-password

MT5_MANAGER_API_URL=http://localhost:4445
MT5_MANAGER_LOGIN=1
MT5_MANAGER_PASSWORD=your-mt5-manager-password
```

---

## Tradovate Integration

### Files

| File | Purpose |
|------|---------|
| `app/infrastructure/adapters/tradovate_adapter.py` | BrokerPort implementation |
| `app/brokers/tradovate_executor.py` | REST + WebSocket |
| `app/routers/tradovate_oauth.py` | OAuth flow |

### Authentication Method

**OAuth 2.0 Flow:**
1. User redirected to Tradovate authorization
2. Callback receives authorization code
3. Exchange code for access_token + refresh_token
4. Tokens stored encrypted in database

### Config Keys

```bash
TRADOVATE_API_URL=https://demo.tradovate.com  # or live.tradovate.com
TRADOVATE_WS_URL=wss://demo.tradovate.com/ws
TRADOVATE_CLIENT_ID=your_client_id
TRADOVATE_CLIENT_SECRET=your_client_secret
TRADOVATE_OAUTH_REDIRECT_URI=https://tradeflow.fluxeo.net/api/auth/tradovate/callback
TRADOVATE_OAUTH_ENVIRONMENT=demo  # or live
```

---

## Broker Adapter Summary

| Broker | Auth Method | Credentials | Token Expiry |
|--------|-------------|-------------|--------------|
| TradeLocker | SDK (email/pass) or Brand API | email, password, server | SDK handles |
| ProjectX/TopStep | Gateway API (username/apiKey) | username, api_key | 24 hours |
| MT4/MT5 | Manager API | manager_login, manager_password | Session |
| Tradovate | OAuth 2.0 | client_id, client_secret | Refresh token |

---

## Credential Storage

All credentials are stored with Fernet encryption:

```python
# app/services/credential_service.py
from cryptography.fernet import Fernet

CREDENTIAL_ENCRYPTION_KEY = settings.CREDENTIAL_ENCRYPTION_KEY

def encrypt_credential(data: dict) -> str:
    f = Fernet(CREDENTIAL_ENCRYPTION_KEY)
    return f.encrypt(json.dumps(data).encode()).decode()

def decrypt_credential(encrypted: str) -> dict:
    f = Fernet(CREDENTIAL_ENCRYPTION_KEY)
    return json.loads(f.decrypt(encrypted.encode()).decode())
```

Environment variable: `CREDENTIAL_ENCRYPTION_KEY` (32-byte base64)

---
*Generated: 2026-01-22*
