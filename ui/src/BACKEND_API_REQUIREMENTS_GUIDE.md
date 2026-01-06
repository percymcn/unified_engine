# TradeFlow Backend API Requirements Guide

## 📋 Overview

This document accompanies `BACKEND_API_REQUIREMENTS.json` which contains a **complete extraction of all UI elements and their expected backend interactions** for the TradeFlow by Fluxeo trading SaaS dashboard.

**Purpose**: Enable you to diff this specification against your existing FastAPI backends (TradeLocker, Topstep/ProjectX, MT4/MT5) and generate patch files for missing routes.

---

## 🎯 What's Included

The JSON file contains:

1. **Complete endpoint catalog** - 70+ unique API endpoints
2. **Request/Response schemas** - Inputs, outputs, error states for each route
3. **UI-to-Backend mapping** - Which screen/button triggers which API call
4. **Data flow documentation** - How data moves from registration → first trade
5. **Priority rankings** - What to build first (MVP vs nice-to-have)
6. **Gap analysis** - Features in UI but missing backend support

---

## 📂 JSON Structure

```json
{
  "meta": { ... },                               // App metadata, URLs, broker list
  "pricing_tiers": { ... },                      // Plan limits (Starter/Pro/Elite)
  "authentication": [ ... ],                     // Login, signup, password reset
  "broker_registration_and_accounts": [ ... ],  // Connect brokers, manage accounts
  "api_key_management": [ ... ],                 // Generate, regenerate, delete API keys
  "webhook_templates_and_execution": [ ... ],    // TradingView webhook handling
  "trading_and_orders": [ ... ],                 // Positions, orders, close trades
  "analytics_and_reporting": [ ... ],            // P&L reports, trade analytics
  "risk_management": [ ... ],                    // Risk controls, emergency stop
  "trading_configuration": [ ... ],              // SL/TP settings, position sizing
  "billing_and_subscription": [ ... ],           // Stripe integration, trials
  "admin_panel": [ ... ],                        // Admin oversight, impersonation
  "logs_and_monitoring": [ ... ],                // Activity logs, webhook logs
  "chatbot_support": [ ... ],                    // AI chatbot (optional)
  "notifications": [ ... ],                      // User alerts
  "onboarding": [ ... ],                         // New user flow
  "password_and_settings": [ ... ],              // Profile, password changes
  "theme_settings": [ ... ],                     // UI themes (client-side)
  "missing_or_unclear_endpoints": [ ... ],       // Features needing clarification
  "endpoints_summary": { ... },                  // Stats and categorization
  "data_flow_notes": { ... },                    // Step-by-step user journeys
  "ui_to_backend_matching": { ... },             // What's covered vs missing
  "recommended_backend_priorities": { ... }      // Build order (Phase 1-4)
}
```

---

## 🔍 How to Use This Document

### Step 1: Load Your Backend Routes

For each of your 3 FastAPI backends, extract all existing routes:

**TradeLocker backend:**
```bash
grep -rn "@app.post\|@app.get\|@app.put\|@app.delete" tradelocker_main.py > tradelocker_routes.txt
```

**Topstep/ProjectX backend:**
```bash
grep -rn "@app.post\|@app.get\|@app.put\|@app.delete" projectx_main.py > projectx_routes.txt
```

**MT4/MT5 backend:**
```bash
grep -rn "@app.post\|@app.get\|@app.put\|@app.delete" mtx_main.py > mtx_routes.txt
```

### Step 2: Compare Against JSON Spec

Open `BACKEND_API_REQUIREMENTS.json` and cross-reference each endpoint:

**Example:**
```json
{
  "screen": "Connect Broker Page",
  "element": "TradeLocker Registration Form",
  "expected_backend_route": "POST /register/tradelocker",
  "inputs": ["email", "password", "server", "mode"],
  "outputs": ["id", "broker", "email", "status", "balance", "api_key"],
  "notes": "Must connect to TradeLocker API, validate credentials, return API key"
}
```

**Check your `tradelocker_main.py`:**
- ✅ **If route exists**: Verify it returns all required outputs (especially `api_key`)
- ⚠️ **If route missing**: Add to your "TODO" list
- ❌ **If route exists but output incomplete**: Needs patching

### Step 3: Generate Patch Files

For each missing or incomplete route, create a patch:

**Example Patch (missing `api_key` in response):**
```python
# PATCH: Add API key generation to /register/tradelocker

@app.post("/register/tradelocker")
async def register_tradelocker(payload: TradeLockerRegister):
    # ... existing validation code ...
    
    # NEW: Generate API key for webhooks
    api_key = f"tradelocker_{account_id[:8]}_{secrets.token_urlsafe(16)}"
    
    # Store API key in database
    await db.execute(
        "INSERT INTO api_keys (account_id, key, created_at) VALUES ($1, $2, NOW())",
        account_id, api_key
    )
    
    return {
        "id": account_id,
        "broker": "tradelocker",
        "email": payload.email,
        "status": "active",
        "balance": account_balance,
        "api_key": api_key  # NEW
    }
```

### Step 4: Prioritize Implementation

Follow the **recommended_backend_priorities** section:

#### **Phase 1: MVP Critical** (Must have for basic functionality)
1. `POST /auth/signup, /auth/login, /auth/logout`
2. `POST /register/tradelocker, /register/projectx, /register/mtx`
3. `GET /api/user/brokers`
4. **`POST /api/unify/v1/webhook/{broker}`** ← MOST IMPORTANT
5. `GET /api/positions`, `POST /api/orders/close`
6. `GET /api/billing/status, /api/billing/usage`
7. `POST /api/billing/checkout` (Stripe)

#### **Phase 2: Core Features** (Essential for production)
- Account management (toggle, delete, sync, switch)
- API key regeneration
- Risk controls (GET/PUT `/api/user/risk_config`)
- Emergency stop button
- Webhook logs

#### **Phase 3: Analytics** (User insights)
- Dashboard overview metrics
- P&L reports
- Trade analytics

#### **Phase 4: Admin & Advanced** (Optional but valuable)
- Admin panel (user oversight, impersonation)
- Advanced billing (plan changes, portal)
- Notifications system

---

## 🚨 Critical Endpoints Requiring Immediate Attention

### 1. **Webhook Execution** (The Heart of the System)
```
POST /api/unify/v1/webhook/{broker}
```
- **Why Critical**: This receives TradingView alerts and executes trades
- **Must Do**:
  - Validate `Authorization: Bearer {api_key}` header
  - Map API key → user account
  - Check if account is enabled (`enabled: true`)
  - Apply risk controls (max daily loss, trading hours, etc.)
  - Execute trade via broker API
  - Log event to database
  - Return success/error to TradingView

**Current Status**: UI generates webhook templates, but backend must handle incoming POST requests.

---

### 2. **API Key Generation on Account Registration**
```
POST /register/{broker}
```
- **Why Critical**: Users need API keys to authenticate webhooks
- **Must Do**:
  - Generate unique API key on account creation
  - Store securely in database (hashed or encrypted)
  - Return API key in response
  - Display in UI with copy button

**Current Status**: Your backends may register accounts but might not generate webhook API keys.

---

### 3. **Billing & Trial Management**
```
GET /api/billing/status
GET /api/billing/usage
POST /api/billing/checkout
POST /api/billing/webhook (Stripe webhook handler)
```
- **Why Critical**: Trial ends after 3 days OR 100 trades
- **Must Do**:
  - Track `trades_count` per user
  - Calculate `trial_trades_remaining = 100 - trades_count`
  - Calculate `days_remaining` from signup date
  - Block trading when trial expires unless upgraded
  - Handle Stripe webhook events (subscription.created, subscription.updated)

**Current Status**: Needs Stripe integration. Webhook execution must increment `trades_count`.

---

## 📊 Gap Analysis

### ✅ **Fully Covered (UI + Backend Planned)**
- User authentication (Supabase)
- Broker registration (all 3 brokers)
- Account management (list, toggle, sync, delete)
- Position & order display
- Webhook templates (UI generates JSON)
- Risk controls UI
- Billing UI (plan selection)

### ⚠️ **In UI But Missing Backend**
- **Real-time position price updates** → Need WebSocket `/ws/positions` or polling
- **EA heartbeat check (MT4/MT5)** → `GET /api/accounts/{id}/ea_status`
- **Fluxeo strategies management** → `GET /api/strategies`, `POST /api/strategies/activate`
- **News calendar lockout** → Integrate external API or `GET /api/calendar/events`
- **Trade export (CSV/JSON)** → `GET /api/export/trades?format=csv`
- **Performance benchmarking** → `GET /api/analytics/benchmark`
- **White-label config (Elite plan)** → `GET/PUT /api/user/whitelabel`

### ❌ **Potentially in Backend But Not Used by UI**
- Any internal admin endpoints not exposed in UI
- Rate limiting metadata (may exist but not displayed)
- Broker API health monitoring (backend-only)

---

## 🛠️ Recommended Backend Changes

### For TradeLocker Backend (`tradelocker_main.py`)

**Add/Verify:**
1. `POST /register/tradelocker` → Returns `api_key`
2. `GET /api/user/brokers?broker=tradelocker` → List user's TL accounts
3. `POST /api/unify/v1/webhook/tradelocker` → Execute trades from TradingView
4. `POST /api/accounts/sync/{id}` → Refresh account data
5. `GET /api/positions?broker=tradelocker` → Fetch open positions
6. `POST /api/orders/close` → Close position

---

### For Topstep/ProjectX Backend (`projectx_main.py`)

**Add/Verify:**
1. `POST /register/projectx` → Returns `api_key`
2. `GET /api/user/brokers?broker=topstep` → List user's Topstep accounts
3. `POST /api/unify/v1/webhook/topstep` → Execute trades
4. `POST /api/accounts/sync/{id}` → Sync with ProjectX API
5. `GET /api/positions?broker=topstep`
6. Daily profit target tracking (Topstep-specific)

---

### For MT4/MT5 Backend (`mtx_main.py`)

**Add/Verify:**
1. `POST /register/mtx` → Returns `api_key` + EA installation instructions
2. `GET /api/accounts/{id}/ea_status` → Check if EA is connected
3. `POST /api/unify/v1/webhook/truforex` → EA receives via HTTP requests
4. EA sends heartbeat every 30s → `POST /api/ea/heartbeat`
5. `GET /api/positions?broker=truforex`

**Special Note**: MT4/MT5 requires Expert Advisor (EA) installation. Backend must:
- Provide EA download link in `/register/mtx` response
- Accept EA heartbeat pings to confirm connection
- Queue trades if EA offline (or reject with error)

---

## 🔐 Security Considerations

### API Key Validation
```python
# Webhook handler must validate API key
async def validate_api_key(api_key: str) -> Account:
    account = await db.fetchrow(
        "SELECT * FROM accounts WHERE api_key = $1 AND enabled = TRUE",
        api_key
    )
    if not account:
        raise HTTPException(401, "Invalid or disabled API key")
    return account
```

### Rate Limiting
```python
# Prevent abuse on webhook endpoint
from slowapi import Limiter
limiter = Limiter(key_func=get_api_key)

@app.post("/api/unify/v1/webhook/{broker}")
@limiter.limit("100/minute")  # 100 requests per minute per API key
async def webhook_handler(broker: str, request: Request):
    # ...
```

### Risk Control Enforcement
```python
# Apply user's risk settings before executing trade
risk_config = await get_risk_config(user_id)

if risk_config["max_daily_loss"] and daily_loss >= risk_config["max_daily_loss"]:
    raise HTTPException(403, "Daily loss limit reached")

if risk_config["trading_hours_enabled"]:
    if not is_within_trading_hours(risk_config):
        raise HTTPException(403, "Outside allowed trading hours")
```

---

## 📞 Support & Next Steps

### Testing Your Backend

1. **Unit Tests**: Verify each endpoint returns correct schema
2. **Integration Tests**: Test full user flow (signup → register broker → webhook → close position)
3. **Postman Collection**: Create from JSON spec
4. **Mock TradingView**: Send webhook payloads manually

### Debugging Checklist

- [ ] All `/register/{broker}` endpoints return `api_key`
- [ ] Webhook endpoint validates `Authorization` header
- [ ] Webhook logs every request (success or failure) to database
- [ ] Billing usage increments `trades_count` on each webhook
- [ ] Emergency stop closes all positions immediately
- [ ] Sync endpoints update `last_sync` timestamp
- [ ] Admin endpoints require `role=admin` check

### Questions to Answer

1. **Do your backends share a database?**
   - If yes: Unified `/api/user/brokers` can query all 3
   - If no: Frontend must aggregate from 3 separate endpoints

2. **How are API keys stored?**
   - Plain text (unsafe)
   - Hashed (SHA-256)
   - Encrypted (AES-256)

3. **Where is the webhook endpoint hosted?**
   - Option 1: Unified at `https://unified.fluxeo.net/api/unify/v1/webhook/{broker}`
   - Option 2: Separate for each broker (`/webhook/tradelocker`, `/webhook/topstep`, etc.)

4. **Do you have Stripe integration?**
   - If no: Billing endpoints are placeholders (use mock data)
   - If yes: Ensure webhook handler updates `user.plan` on subscription events

---

## 📄 File Exports

### Generate OpenAPI Spec from JSON

You can convert `BACKEND_API_REQUIREMENTS.json` to OpenAPI YAML:

```python
# Example: Convert to OpenAPI 3.0
import json
import yaml

with open('BACKEND_API_REQUIREMENTS.json') as f:
    spec = json.load(f)

# Build OpenAPI schema from spec
openapi = {
    "openapi": "3.0.0",
    "info": {
        "title": "TradeFlow API",
        "version": "1.0.0",
        "description": spec["meta"]["app_name"]
    },
    "servers": [
        {"url": spec["meta"]["backend_url"]}
    ],
    "paths": {}
    # ... map endpoints from JSON to OpenAPI format
}

with open('openapi_generated.yaml', 'w') as f:
    yaml.dump(openapi, f)
```

### Generate Postman Collection

```python
# Convert to Postman v2.1 format
postman_collection = {
    "info": {
        "name": "TradeFlow API",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": [
        {
            "name": "Authentication",
            "item": [
                # ... map from authentication section
            ]
        }
        # ... repeat for each category
    ]
}
```

---

## 🚀 Quick Start Verification

### Test TradeLocker Backend

```bash
# 1. Register account
curl -X POST https://unified.fluxeo.net/api/unify/v1/register/tradelocker \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "demo123",
    "server": "demo.tradelocker.com",
    "mode": "demo"
  }'

# Expected response:
# {
#   "id": "acc_123",
#   "broker": "tradelocker",
#   "api_key": "tradelocker_acc_123_xyz789"  ← MUST BE PRESENT
# }

# 2. Send webhook
curl -X POST https://unified.fluxeo.net/api/unify/v1/webhook/tradelocker \
  -H "Authorization: Bearer tradelocker_acc_123_xyz789" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "unify.v1",
    "intent": {
      "broker": "tradelocker",
      "side": "buy",
      "type": "market",
      "symbol": "EURUSD",
      "qty": 1
    }
  }'

# Expected response:
# {
#   "success": true,
#   "order_id": "ord_456",
#   "message": "Market buy order executed"
# }
```

---

## 📝 Summary

### What You Have
- **Complete UI** ✅ (Figma design + React implementation)
- **Frontend Context** ✅ (BrokerContext, UserContext, ThemeContext)
- **3 FastAPI Backends** ✅ (TradeLocker, Topstep, MT4/MT5)

### What You Need
- **API Key Generation** ⚠️ (on account registration)
- **Webhook Handler** ⚠️ (`POST /webhook/{broker}`)
- **Billing Integration** ⚠️ (Stripe webhooks, trial tracking)
- **Account Management** ⚠️ (toggle, sync, delete endpoints)
- **Risk Controls Enforcement** ⚠️ (in webhook handler)

### Priority Order
1. **Week 1**: Webhook execution + API key generation
2. **Week 2**: Account management + billing basics
3. **Week 3**: Risk controls + analytics
4. **Week 4**: Admin panel + polish

---

## 💬 Contact & Support

For questions about this specification:
- **Support Email**: support@fluxeo.net
- **Backend URL**: https://unified.fluxeo.net/api/unify/v1
- **UI Repository**: TradeFlow v6 (current project)

---

**Last Updated**: 2025-10-19  
**Version**: 6.0  
**Author**: AI Assistant (Figma Make)
