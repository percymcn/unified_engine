# Broker Credential Schemas

**Single Source of Truth** for broker credential field mappings, endpoints, and storage locations.

**Generated:** 2026-01-22  
**Source:** Backend code analysis (`app/routers/accounts.py`, `app/application/use_cases/test_connection.py`, broker executors)

---

## Overview

This document maps:
- **UI field names** (camelCase) → **Backend API field names** (snake_case)
- **Required vs Optional** fields per broker
- **Test Connection** endpoint
- **Create Account** endpoint
- **Storage locations** (trading_accounts table vs credentials table)

---

## TradeLocker

### Authentication Modes
1. **SDK Mode (Preferred)**: Uses username/password/server
2. **Brand API Mode (Fallback)**: Uses API key

### Required Fields

| UI Field | Backend Field | Type | Storage Location | Storage Column |
|----------|---------------|------|------------------|----------------|
| `username` | `username` | string | `credentials` | `encrypted_data` (JSON) |
| `password` | `password` | string | `credentials` | `encrypted_data` (JSON) |
| `server` | `server` | string | `credentials` | `encrypted_data` (JSON) |

### Optional Fields

| UI Field | Backend Field | Type | Storage Location | Storage Column |
|----------|---------------|------|------------------|----------------|
| `environment` | `environment` | string | `credentials` | `encrypted_data` (JSON) |
| `apiKey` | `api_key` | password | `trading_accounts` | `api_key` (encrypted) |

### Endpoints

- **Test Connection**: `POST /api/v1/accounts/test-connection`
  - Request body: `{ "broker": "tradelocker", "credentials": { "username": "...", "password": "...", "server": "..." } }`
  
- **Create Account**: `POST /api/v1/accounts/`
  - Request body: `{ "broker": "tradelocker", "account_type": "demo", "account_id": "...", "broker_config": { "username": "...", "password": "...", "server": "..." } }`

### Storage Details

- **Credentials table**: Stores encrypted JSON with `email`, `password`, `server`, `environment`
- **Trading_accounts table**: Stores `api_key`, `api_secret` (Brand API mode), `access_token`, `refresh_token`, `token_expires_at`, `oauth_environment`

### Notes

- Provide either `(username, password, server)` for SDK mode OR `(api_key)` for Brand API mode
- SDK mode is preferred and handles JWT refresh automatically
- Environment defaults to `https://demo.tradelocker.com` if not specified

---

## ProjectX / TopStep

### Authentication Method
Gateway API authentication with username + API key

### Required Fields

| UI Field | Backend Field | Type | Storage Location | Storage Column |
|----------|---------------|------|------------------|----------------|
| `username` | `username` | string | `credentials` | `encrypted_data` (JSON) |
| `apiKey` | `api_key` | password | `trading_accounts` | `api_key` (encrypted) |

### Optional Fields
None

### Endpoints

- **Test Connection**: `POST /api/v1/accounts/test-connection`
  - Request body: `{ "broker": "projectx", "credentials": { "username": "...", "api_key": "..." } }`
  
- **Create Account**: `POST /api/v1/accounts/`
  - Request body: `{ "broker": "projectx", "account_type": "evaluation", "account_id": "...", "broker_config": { "username": "...", "api_key": "..." } }`

### Storage Details

- **Credentials table**: Stores encrypted JSON with `username`, `api_key`
- **Trading_accounts table**: Stores `api_key` (encrypted), `access_token` (JWT token after auth), `token_expires_at` (24h expiry)

### Notes

- API key is stored encrypted in `trading_accounts.api_key`
- JWT token obtained via `POST /api/Auth/loginKey` and stored in `access_token`
- Token expires after 24 hours and must be refreshed

---

## Tradovate

### Authentication Modes
1. **OAuth 2.0 (Preferred)**: Uses OAuth flow (redirect-based)
2. **Password Mode (Fallback)**: Uses username/password

### Required Fields

| UI Field | Backend Field | Type | Storage Location | Storage Column |
|----------|---------------|------|------------------|----------------|
| `userId` | `user_id` | string | `credentials` | `encrypted_data` (JSON) |
| `password` | `password` | string | `credentials` | `encrypted_data` (JSON) |

### Optional Fields

| UI Field | Backend Field | Type | Storage Location | Storage Column |
|----------|---------------|------|------------------|----------------|
| `environment` | `environment` | select (demo/live) | `trading_accounts` | `oauth_environment` |
| `appId` | `app_id` | string | `credentials` | `encrypted_data` (JSON) |
| `cid` | `cid` | string | `credentials` | `encrypted_data` (JSON) |
| `sec` | `sec` | password | `credentials` | `encrypted_data` (JSON) |

### Endpoints

- **Test Connection**: `POST /api/v1/accounts/test-connection`
  - Request body: `{ "broker": "tradovate", "credentials": { "user_id": "...", "password": "...", "environment": "demo" } }`
  
- **Create Account**: `POST /api/v1/accounts/`
  - Request body: `{ "broker": "tradovate", "account_type": "demo", "account_id": "...", "broker_config": { "user_id": "...", "password": "...", "environment": "demo" } }`

### Storage Details

- **Credentials table**: Stores encrypted JSON with `user_id`, `password`, `app_id`, `cid`, `sec`
- **Trading_accounts table**: Stores `access_token`, `refresh_token`, `token_expires_at`, `oauth_environment` (demo/live)

### Notes

- OAuth authentication is recommended for production (see `/api/v1/oauth/tradovate/authorize`)
- Password mode uses `POST /auth/accesstokenrequest` to get access token
- Access tokens stored in `trading_accounts.access_token` and `refresh_token`
- Environment must be specified: `demo` or `live`

---

## MT4 (MetaTrader 4)

### Authentication Modes
1. **MetaAPI SDK Mode (Preferred)**: Uses MetaAPI token + account ID
2. **Manager API Mode (Fallback)**: Uses manager login/password

### Required Fields

| UI Field | Backend Field | Type | Storage Location | Storage Column |
|----------|---------------|------|------------------|----------------|
| `metaapiToken` | `metaapi_token` | password | `credentials` | `encrypted_data` (JSON) |
| `metaapiAccountId` | `metaapi_account_id` | string | `trading_accounts` | `extra_metadata` (JSON) |

### Optional Fields

| UI Field | Backend Field | Type | Storage Location | Storage Column |
|----------|---------------|------|------------------|----------------|
| `managerLogin` | `manager_login` | string | `credentials` | `encrypted_data` (JSON) |
| `managerPassword` | `manager_password` | password | `credentials` | `encrypted_data` (JSON) |

### Endpoints

- **Test Connection**: `POST /api/v1/accounts/test-connection`
  - Request body: `{ "broker": "mt4", "credentials": { "metaapi_token": "...", "metaapi_account_id": "..." } }`
  
- **Create Account**: `POST /api/v1/accounts/`
  - Request body: `{ "broker": "mt4", "account_type": "demo", "account_id": "...", "broker_config": { "metaapi_token": "...", "metaapi_account_id": "..." } }`

### Storage Details

- **Credentials table**: Stores encrypted JSON with `metaapi_token`, `metaapi_account_id`, `manager_login`, `manager_password`
- **Trading_accounts table**: Stores `metaapi_account_id` in `extra_metadata` JSON field

### Notes

- Provide either `(metaapi_token, metaapi_account_id)` for MetaAPI mode OR `(manager_login, manager_password)` for Manager API mode
- MetaAPI SDK mode is preferred and handles connection management automatically
- Manager API mode requires running MT4 Manager API server

---

## MT5 (MetaTrader 5)

### Authentication Modes
1. **MetaAPI SDK Mode (Preferred)**: Uses MetaAPI token + account ID
2. **Manager API Mode (Fallback)**: Uses manager login/password

### Required Fields

| UI Field | Backend Field | Type | Storage Location | Storage Column |
|----------|---------------|------|------------------|----------------|
| `metaapiToken` | `metaapi_token` | password | `credentials` | `encrypted_data` (JSON) |
| `metaapiAccountId` | `metaapi_account_id` | string | `trading_accounts` | `extra_metadata` (JSON) |

### Optional Fields

| UI Field | Backend Field | Type | Storage Location | Storage Column |
|----------|---------------|------|------------------|----------------|
| `managerLogin` | `manager_login` | string | `credentials` | `encrypted_data` (JSON) |
| `managerPassword` | `manager_password` | password | `credentials` | `encrypted_data` (JSON) |

### Endpoints

- **Test Connection**: `POST /api/v1/accounts/test-connection`
  - Request body: `{ "broker": "mt5", "credentials": { "metaapi_token": "...", "metaapi_account_id": "..." } }`
  
- **Create Account**: `POST /api/v1/accounts/`
  - Request body: `{ "broker": "mt5", "account_type": "demo", "account_id": "...", "broker_config": { "metaapi_token": "...", "metaapi_account_id": "..." } }`

### Storage Details

- **Credentials table**: Stores encrypted JSON with `metaapi_token`, `metaapi_account_id`, `manager_login`, `manager_password`
- **Trading_accounts table**: Stores `metaapi_account_id` in `extra_metadata` JSON field

### Notes

- Provide either `(metaapi_token, metaapi_account_id)` for MetaAPI mode OR `(manager_login, manager_password)` for Manager API mode
- MetaAPI SDK mode is preferred and handles connection management automatically
- Manager API mode requires running MT5 Manager API server

---

## Database Schema Reference

### trading_accounts Table

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INTEGER | Primary key |
| `user_id` | INTEGER | Foreign key to users |
| `broker` | ENUM | Broker type (tradelocker, tradovate, projectx, topstep, mt4, mt5) |
| `account_type` | ENUM | Account type (live, demo, funded, evaluation) |
| `account_number` | VARCHAR(100) | Broker's account ID |
| `account_name` | VARCHAR(255) | Display name |
| `api_key` | VARCHAR(500) | Encrypted API key (ProjectX, TradeLocker Brand API) |
| `api_secret` | VARCHAR(500) | Encrypted API secret (TradeLocker Brand API) |
| `access_token` | TEXT | Encrypted OAuth/JWT access token |
| `refresh_token` | TEXT | Encrypted OAuth refresh token |
| `token_expires_at` | TIMESTAMP | Token expiration time |
| `oauth_environment` | VARCHAR(10) | OAuth environment (demo/live) |
| `extra_metadata` | JSON | Additional broker-specific data (e.g., metaapi_account_id) |

### credentials Table

| Column | Type | Purpose |
|--------|------|---------|
| `id` | VARCHAR(36) | UUID primary key |
| `user_id` | INTEGER | Foreign key to users |
| `name` | VARCHAR(255) | Credential name |
| `type` | VARCHAR(50) | Credential type (api_key, password, token, oauth) |
| `service` | VARCHAR(50) | Service name (mt4, mt5, tradelocker, tradovate, projectx) |
| `encrypted_data` | TEXT | Fernet-encrypted JSON with credential fields |
| `description` | TEXT | Optional description |
| `expires_at` | TIMESTAMP | Credential expiration |
| `is_active` | BOOLEAN | Active status |

---

## Field Name Mapping Reference

### UI → Backend Mapping

| Broker | UI Field | Backend Field | Notes |
|--------|----------|---------------|-------|
| TradeLocker | `username` | `username` | Email/username |
| TradeLocker | `password` | `password` | Account password |
| TradeLocker | `server` | `server` | Server name |
| TradeLocker | `environment` | `environment` | Environment URL |
| TradeLocker | `apiKey` | `api_key` | Brand API key |
| ProjectX/TopStep | `username` | `username` | TopStep username |
| ProjectX/TopStep | `apiKey` | `api_key` | API key |
| Tradovate | `userId` | `user_id` | User ID/username |
| Tradovate | `password` | `password` | Password |
| Tradovate | `environment` | `environment` | demo/live |
| Tradovate | `appId` | `app_id` | App ID (optional) |
| Tradovate | `cid` | `cid` | Client ID (optional) |
| Tradovate | `sec` | `sec` | Secret (optional) |
| MT4/MT5 | `metaapiToken` | `metaapi_token` | MetaAPI token |
| MT4/MT5 | `metaapiAccountId` | `metaapi_account_id` | MetaAPI account ID |
| MT4/MT5 | `managerLogin` | `manager_login` | Manager API login |
| MT4/MT5 | `managerPassword` | `manager_password` | Manager API password |

---

## Implementation Notes

### Credential Encryption

- All credentials stored in `credentials` table are encrypted using Fernet encryption
- Encryption key: `CREDENTIAL_ENCRYPTION_KEY` environment variable (32-byte base64)
- Fields in `trading_accounts` table (api_key, api_secret, access_token, refresh_token) are also encrypted

### Test Connection Flow

1. UI sends credentials to `POST /api/v1/accounts/test-connection`
2. Backend creates executor instance with credentials
3. Executor calls `initialize()` method
4. Backend returns success/failure with optional symbol format detection

### Create Account Flow

1. UI sends account data + credentials to `POST /api/v1/accounts/`
2. Backend encrypts credentials and stores in `credentials` table
3. Backend creates `TradingAccount` record
4. Backend stores broker-specific tokens in `trading_accounts` table
5. Returns account ID

### Credential Storage Strategy

- **Credentials table**: Stores all raw credential fields as encrypted JSON
- **Trading_accounts table**: Stores tokens, API keys, and metadata needed for runtime operations
- Both tables are linked via `user_id` and `service`/`broker` fields

---

## Quick Reference: Endpoints

| Broker | Test Connection | Create Account |
|--------|----------------|----------------|
| TradeLocker | `POST /api/v1/accounts/test-connection` | `POST /api/v1/accounts/` |
| ProjectX | `POST /api/v1/accounts/test-connection` | `POST /api/v1/accounts/` |
| TopStep | `POST /api/v1/accounts/test-connection` | `POST /api/v1/accounts/` |
| Tradovate | `POST /api/v1/accounts/test-connection` | `POST /api/v1/accounts/` |
| MT4 | `POST /api/v1/accounts/test-connection` | `POST /api/v1/accounts/` |
| MT5 | `POST /api/v1/accounts/test-connection` | `POST /api/v1/accounts/` |

---

*This document is generated from backend code analysis. Update when backend credential handling changes.*
