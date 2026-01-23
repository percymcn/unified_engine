# Broker Contracts - Single Source of Truth

**Generated:** 2026-01-23
**Purpose:** Canonical reference for broker authentication requirements across backend, UI, and documentation.

---

## Overview

This document defines the **exact credentials required** for each supported broker. The UI and backend MUST use these contracts to ensure consistency.

---

## TradeLocker

**Official Docs:** [TradeLocker Public API](https://public-api.tradelocker.com/) | [Brand API](https://brand-docs.tradelocker.com/docs/getting-started)

### Authentication Modes

| Mode | When to Use | Required Credentials |
|------|-------------|---------------------|
| **SDK Mode** (preferred) | Individual traders | `username` (email), `password`, `server` |
| **Brand API Mode** | Brokers/White-label | `api_key` |

### Credential Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | SDK mode | TradeLocker account email |
| `password` | password | SDK mode | Account password |
| `server` | string | SDK mode | Server name (e.g., "Demo Server", "GATESFX") |
| `api_key` | password | Brand API | Brand API key from TradeLocker |
| `environment` | select | Optional | `demo` or `live` (default: demo) |

### Environment URLs

- Demo: `https://demo.tradelocker.com`
- Live: `https://live.tradelocker.com`

### Notes
- GATESFX and some other brokers **require Brand API mode** (SDK won't work)
- Backend detects this and returns `mode: brand_api_required` in test-connection response
- JWT token obtained from `/auth/jwt/token` endpoint

---

## ProjectX / TopStep

**Official Docs:** [ProjectX Gateway API](https://gateway.docs.projectx.com/) | [TopstepX API Access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)

### Authentication Mode

API Key authentication via `/api/Auth/loginKey`

### Credential Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | TopStep/ProjectX username |
| `api_key` | password | Yes | API key from ProjectX settings |

### Environment URLs

- Demo: `https://gateway-api-demo.s2f.projectx.com/api`
- Live: `https://gateway-api.s2f.projectx.com/api`
- TopstepX: `https://gateway.topstepx.com/api`

### Notes
- API Access is $29/month (50% off with code "topstep")
- Must trade from own device (no VPS/VPN for TopStep rules)
- Session token returned grants full Gateway API access

---

## Tradovate

**Official Docs:** [Tradovate API](https://api.tradovate.com/) | [OAuth Example](https://github.com/tradovate/example-api-oauth)

### Authentication Modes

| Mode | When to Use | Required Credentials |
|------|-------------|---------------------|
| **OAuth** (preferred) | Interactive apps | OAuth flow (redirect) |
| **Password** | Direct auth | `user_id`, `password`, `app_id`, `cid`, `sec` |

### Credential Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | string | Yes | Tradovate username |
| `password` | password | Password mode | Account password |
| `environment` | select | Optional | `demo` or `live` |
| `app_id` | string | Optional | Application ID |
| `cid` | string | Optional | Client ID (from API key generation) |
| `sec` | password | Optional | Secret (from API key generation) |

### Environment URLs

- Demo: `https://demo.tradovate.com/v1`
- Live: `https://live.tradovate.com/v1`

### Notes
- OAuth is preferred for user-facing apps
- Password mode requires app_id + cid + sec for API key auth
- Access token stored after OAuth flow

---

## MetaTrader 4 (MT4)

**Official Docs:** [MetaApi Cloud SDK](https://github.com/metaapi/metaapi-python-sdk) | [MetaApi Auth](https://metaapi.cloud/docs/client/restApi/auth/)

### Authentication Modes

| Mode | When to Use | Required Credentials |
|------|-------------|---------------------|
| **MetaAPI SDK** (preferred) | Cloud-based | `metaapi_token`, `metaapi_account_id` |
| **Manager API** | Self-hosted | `manager_login`, `manager_password` |

### Credential Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `metaapi_token` | password | MetaAPI mode | MetaApi cloud token |
| `metaapi_account_id` | string | MetaAPI mode | MetaApi account ID |
| `manager_login` | string | Manager mode | MT4 Manager login |
| `manager_password` | password | Manager mode | MT4 Manager password |

### Notes
- MetaApi free tier available
- Token retrieved from https://app.metaapi.cloud
- Works with any MT4 broker

---

## MetaTrader 5 (MT5)

**Official Docs:** [MetaApi Cloud SDK](https://github.com/metaapi/metaapi-python-sdk) | [MetaApi Auth](https://metaapi.cloud/docs/client/restApi/auth/)

### Authentication Modes

| Mode | When to Use | Required Credentials |
|------|-------------|---------------------|
| **MetaAPI SDK** (preferred) | Cloud-based | `metaapi_token`, `metaapi_account_id` |
| **Manager API** | Self-hosted | `manager_login`, `manager_password` |

### Credential Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `metaapi_token` | password | MetaAPI mode | MetaApi cloud token |
| `metaapi_account_id` | string | MetaAPI mode | MetaApi account ID |
| `manager_login` | string | Manager mode | MT5 Manager login |
| `manager_password` | password | Manager mode | MT5 Manager password |

### Notes
- Identical to MT4 credential structure
- MetaApi handles both MT4 and MT5

---

## Environment Variables (Owner-Level)

These are set by the platform owner in `.env` or Docker secrets. Not per-user.

| Variable | Broker | Description |
|----------|--------|-------------|
| `TRADELOCKER_API_KEY` | TradeLocker | Brand API key (if platform-wide) |
| `PROJECT_X_API_KEY` | ProjectX | Platform API key (if shared) |
| `PROJECT_X_USERNAME` | ProjectX | Platform username (if shared) |
| `METAAPI_TOKEN` | MT4/MT5 | MetaApi token (if shared) |
| `TRADOVATE_CID` | Tradovate | OAuth Client ID |
| `TRADOVATE_SEC` | Tradovate | OAuth Client Secret |

---

## Field Mapping: UI → Backend

| UI Field (camelCase) | Backend Field (snake_case) | Notes |
|---------------------|---------------------------|-------|
| `username` | `username` | Direct |
| `password` | `password` | Direct |
| `server` | `server` | Direct |
| `apiKey` | `api_key` | Key mapped |
| `userId` | `user_id` | Key mapped |
| `metaapiToken` | `metaapi_token` | Key mapped |
| `metaapiAccountId` | `metaapi_account_id` | Key mapped |
| `managerLogin` | `manager_login` | Key mapped |
| `managerPassword` | `manager_password` | Key mapped |
| `environment` | `environment` | Direct |
| `appId` | `app_id` | Key mapped |
| `cid` | `cid` | Direct |
| `sec` | `sec` | Direct |

---

## Sources

- [TradeLocker Public API](https://public-api.tradelocker.com/)
- [TradeLocker Brand API](https://brand-docs.tradelocker.com/docs/getting-started)
- [ProjectX Gateway API](https://gateway.docs.projectx.com/)
- [TopstepX API Access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)
- [Tradovate API](https://api.tradovate.com/)
- [MetaApi Python SDK](https://github.com/metaapi/metaapi-python-sdk)
- [MetaApi Auth Docs](https://metaapi.cloud/docs/client/restApi/auth/)

---

*Generated: 2026-01-23*
