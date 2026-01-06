# 🚀 TradeFlow Backend Analysis - START HERE

**Generated**: 2025-10-19  
**Purpose**: Complete UI → Backend requirements extraction for TradeFlow by Fluxeo

---

## 📚 What You Have Now

I've extracted **every UI element, screen, button, and interaction** from your TradeFlow application and mapped them to their expected backend API routes. You now have **4 comprehensive documents** to compare against your existing FastAPI backends:

### 1. **BACKEND_API_REQUIREMENTS.json** (Primary Reference)
   - **What**: Complete JSON specification of all 70+ API endpoints
   - **Format**: Structured data with request/response schemas
   - **Use Case**: Machine-readable format for automated diff tools
   - **Best For**: Generating patches, API testing, documentation generation

### 2. **BACKEND_API_REQUIREMENTS_GUIDE.md** (Implementation Guide)
   - **What**: Human-readable guide on how to use the JSON spec
   - **Includes**: Step-by-step instructions, code examples, testing checklist
   - **Use Case**: For your backend developers to implement missing routes
   - **Best For**: Understanding the "how" and "why" behind each endpoint

### 3. **BACKEND_ENDPOINTS_CHECKLIST.md** (Quick Reference)
   - **What**: Checkbox-style table of all endpoints by category
   - **Format**: Markdown tables with status checkboxes
   - **Use Case**: Track implementation progress, sprint planning
   - **Best For**: Daily development work, team standups

### 4. **SYSTEM_ARCHITECTURE_DIAGRAM.md** (Visual Overview)
   - **What**: ASCII diagrams showing data flow and system architecture
   - **Includes**: User journeys, webhook flow, emergency stop, billing
   - **Use Case**: Onboarding new developers, architectural decisions
   - **Best For**: Understanding how all pieces fit together

---

## 🎯 Your Next Steps

### STEP 1: Load Your Existing Backend Routes

For each of your 3 FastAPI backends, extract current routes:

```bash
# TradeLocker Backend
cd /path/to/tradelocker-backend
grep -rn "@app\.(get|post|put|delete|patch)" main.py routes/ > /tmp/tradelocker_routes.txt

# Topstep/ProjectX Backend
cd /path/to/projectx-backend
grep -rn "@app\.(get|post|put|delete|patch)" main.py routes/ > /tmp/projectx_routes.txt

# MT4/MT5 Backend
cd /path/to/mtx-backend
grep -rn "@app\.(get|post|put|delete|patch)" main.py routes/ > /tmp/mtx_routes.txt
```

### STEP 2: Compare Against Specification

Open `BACKEND_ENDPOINTS_CHECKLIST.md` and go through each section:

**For each endpoint:**
1. ✅ **Exists and complete** → Check the box, move on
2. ⚠️ **Exists but incomplete** → Note what's missing (e.g., missing `api_key` in response)
3. ❌ **Missing entirely** → Add to your TODO list

**Example comparison:**

| Spec Says | Your Backend | Action Needed |
|-----------|--------------|---------------|
| `POST /register/tradelocker` must return `api_key` | Returns `{ id, broker, email, status }` | ⚠️ Add `api_key` generation |
| `POST /api/unify/v1/webhook/tradelocker` | Doesn't exist | ❌ Implement webhook handler |
| `GET /api/positions` | Exists, returns correct schema | ✅ No action needed |

### STEP 3: Prioritize Implementation

Follow the **Phase 1-4 breakdown** in `BACKEND_ENDPOINTS_CHECKLIST.md`:

#### **Week 1: MVP Critical** (Can't launch without these)
- [ ] Webhook handler (`POST /webhook/{broker}`)
- [ ] API key generation (in `/register/{broker}` response)
- [ ] Account listing (`GET /api/user/brokers`)
- [ ] Position viewing (`GET /api/positions`)

#### **Week 2: Core Features**
- [ ] Account management (toggle, sync, delete)
- [ ] Billing basics (status, usage, checkout)
- [ ] Close positions (`POST /api/orders/close`)

#### **Week 3: Safety & Analytics**
- [ ] Risk controls enforcement (in webhook handler)
- [ ] Emergency stop button
- [ ] Dashboard metrics & reports

#### **Week 4: Admin & Polish**
- [ ] Admin panel endpoints
- [ ] Advanced billing (plan changes, portal)
- [ ] Logs and monitoring

### STEP 4: Generate Patch Files

For each missing or incomplete endpoint, create a patch file:

**Example: `/patches/add_api_key_to_registration.patch`**

```python
# File: tradelocker_backend/routes/register.py
# Description: Add API key generation to registration endpoint

import secrets

@app.post("/register/tradelocker")
async def register_tradelocker(payload: TradeLockerRegister, db: Database):
    # ... existing validation and account creation code ...
    
    # NEW: Generate API key for webhook authentication
    api_key = f"tradelocker_{account_id[:8]}_{secrets.token_urlsafe(16)}"
    
    # NEW: Store API key in database
    await db.execute(
        """
        INSERT INTO api_keys (account_id, key, created_at)
        VALUES ($1, $2, NOW())
        """,
        account_id, api_key
    )
    
    # NEW: Return API key in response
    return {
        "id": account_id,
        "broker": "tradelocker",
        "email": payload.email,
        "server": payload.server,
        "mode": payload.mode,
        "status": "active",
        "balance": account_balance,
        "equity": account_equity,
        "api_key": api_key  # ← NEW FIELD
    }
```

### STEP 5: Test Critical Paths

Use the data flow examples in `SYSTEM_ARCHITECTURE_DIAGRAM.md` to test:

**Test 1: Registration → API Key**
```bash
curl -X POST https://unified.fluxeo.net/api/unify/v1/register/tradelocker \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {user_token}" \
  -d '{
    "email": "test@example.com",
    "password": "demo123",
    "server": "demo.tradelocker.com",
    "mode": "demo"
  }'

# Expected response MUST include:
# {
#   ...
#   "api_key": "tradelocker_acc12345_xyz789abc"
# }
```

**Test 2: Webhook Execution**
```bash
curl -X POST https://unified.fluxeo.net/api/unify/v1/webhook/tradelocker \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer tradelocker_acc12345_xyz789abc" \
  -d '{
    "version": "unify.v1",
    "intent": {
      "broker": "tradelocker",
      "side": "buy",
      "type": "market",
      "symbol": "EURUSD",
      "qty": 1,
      "sl": { "mode": "price", "value": 1.0850 },
      "tp": { "mode": "rr", "value": 2.0 }
    }
  }'

# Expected response:
# {
#   "success": true,
#   "order_id": "ord_123456",
#   "message": "Market buy order executed for EURUSD"
# }
```

**Test 3: View Positions**
```bash
curl -X GET https://unified.fluxeo.net/api/unify/v1/api/positions \
  -H "Authorization: Bearer {user_token}"

# Expected: Array of positions with current_price, pnl, etc.
```

---

## 🚨 Critical Gaps to Address Immediately

Based on the UI analysis, these are **MUST-HAVE** features that may be missing:

### 1. **API Key Generation** (CRITICAL)
**Status**: ⚠️ Likely missing  
**Why**: UI displays API keys in Accounts Manager and Webhook Templates  
**Action**: Add to `/register/{broker}` response  
**Priority**: 🔴 BLOCKING

### 2. **Webhook Execution Handler** (CRITICAL)
**Status**: ⚠️ May exist but needs validation  
**Why**: Core functionality - receives TradingView alerts and executes trades  
**Action**: Implement `POST /api/unify/v1/webhook/{broker}` with:
  - API key authentication
  - Risk control enforcement
  - Trade execution
  - Event logging  
**Priority**: 🔴 BLOCKING

### 3. **Trial Tracking** (HIGH)
**Status**: ❌ Likely missing  
**Why**: UI shows trial banner with "X trades remaining" and "X days left"  
**Action**: 
  - Track `trades_count` in database
  - Increment on webhook execution
  - Block trades when `trades_count >= 100` OR `days_since_signup >= 3`  
**Priority**: 🟠 HIGH

### 4. **Billing Integration** (HIGH)
**Status**: ⚠️ Partial (Stripe checkout exists?)  
**Why**: UI has full billing portal with plan selection and upgrade flows  
**Action**:
  - `GET /api/billing/status` - Stripe subscription status
  - `GET /api/billing/usage` - Trial progress
  - `POST /api/billing/webhook` - Handle Stripe events  
**Priority**: 🟠 HIGH

### 5. **Account Enable/Disable Toggle** (MEDIUM)
**Status**: ❌ Likely missing  
**Why**: Accounts Manager has toggle switch for each account  
**Action**: `PATCH /api/accounts/{id}/toggle`  
**Priority**: 🟡 MEDIUM

### 6. **Risk Controls Enforcement** (MEDIUM)
**Status**: ❌ Likely missing  
**Why**: UI has Risk Controls page with max daily loss, trading hours, etc.  
**Action**: 
  - `GET/PUT /api/user/risk_config`
  - Apply checks in webhook handler before executing trades  
**Priority**: 🟡 MEDIUM

### 7. **Emergency Stop** (MEDIUM)
**Status**: ❌ Likely missing  
**Why**: UI has red "Emergency Stop" button in dashboard  
**Action**: `POST /api/user/emergency_stop` - Close all positions immediately  
**Priority**: 🟡 MEDIUM

---

## 📊 Gap Analysis Summary

### ✅ **Likely Already Implemented**
- User authentication (Supabase)
- Broker registration (TradeLocker, Topstep, MT4/MT5 account creation)
- Position fetching (from broker APIs)
- Order fetching
- Basic account sync

### ⚠️ **Partially Implemented (Needs Enhancement)**
- Registration endpoints (exist but may not return `api_key`)
- Webhook endpoints (may exist but missing risk enforcement)
- Billing (Stripe checkout exists but usage tracking may be missing)

### ❌ **Likely Missing Entirely**
- API key management (generation, regeneration, display)
- Trial tracking (trades count, days remaining)
- Account enable/disable toggle
- Risk controls (GET/PUT config, enforcement in webhook)
- Emergency stop
- Analytics endpoints (P&L reports, metrics)
- Admin panel endpoints
- Webhook event logging
- Notifications system

---

## 🔐 Security Checklist

Before launching, ensure:

### API Key Security
- [ ] API keys are generated with cryptographically secure randomness (`secrets` module)
- [ ] API keys are stored hashed or encrypted in database (not plain text)
- [ ] Webhook handler validates API key on EVERY request
- [ ] Invalid API key returns `401 Unauthorized` (not `403` or `500`)
- [ ] API keys can be regenerated (invalidates old key immediately)

### Rate Limiting
- [ ] Webhook endpoint has rate limit (e.g., 100 requests/minute per API key)
- [ ] Authentication endpoints have rate limit (prevent brute force)
- [ ] Admin endpoints require additional authentication

### Input Validation
- [ ] Webhook payload is validated against schema (reject malformed JSON)
- [ ] Symbol names are sanitized (prevent SQL injection)
- [ ] Quantity and price values are validated (must be > 0, reasonable limits)

### Data Privacy
- [ ] Users can only see their own accounts (unless admin)
- [ ] Admin actions are logged (who, what, when)
- [ ] Passwords are never logged or returned in API responses
- [ ] Sensitive fields (API keys) are masked in logs

---

## 🛠️ Development Workflow

### Recommended Approach

1. **Day 1-2**: Review all 4 documents, compare against existing backends
2. **Day 3-5**: Implement Phase 1 (MVP Critical) endpoints
3. **Day 6-10**: Test critical path (signup → register → webhook → trade)
4. **Day 11-15**: Implement Phase 2 (Core Features)
5. **Day 16-20**: Implement Phase 3 (Analytics & Safety)
6. **Day 21-25**: Implement Phase 4 (Admin & Polish)
7. **Day 26-30**: Integration testing, bug fixes, documentation

### Daily Checklist Template

```markdown
## [Date] Backend Development Log

### Completed Today
- [ ] Endpoint: `POST /register/tradelocker` - Added API key generation
- [ ] Endpoint: `POST /webhook/tradelocker` - Basic implementation (no risk checks yet)

### Testing
- [ ] Test 1: Registration returns API key ✅
- [ ] Test 2: Webhook accepts valid API key ✅
- [ ] Test 3: Webhook rejects invalid API key ✅

### Blocked/Issues
- Need Stripe test keys for billing integration
- TradeLocker API documentation unclear on order types

### Tomorrow's Plan
- [ ] Add risk control enforcement to webhook handler
- [ ] Implement `GET /api/positions` endpoint
- [ ] Set up database tables for webhooks_log
```

---

## 📞 Support & Resources

### Documentation Files in This Project
1. `BACKEND_API_REQUIREMENTS.json` - Complete spec (use for automation)
2. `BACKEND_API_REQUIREMENTS_GUIDE.md` - Implementation guide
3. `BACKEND_ENDPOINTS_CHECKLIST.md` - Checkbox tracker
4. `SYSTEM_ARCHITECTURE_DIAGRAM.md` - Visual diagrams

### External Resources
- **TradeLocker API Docs**: [your-tradelocker-docs-url]
- **Topstep/ProjectX API**: [your-topstep-docs-url]
- **MT4/MT5 EA Guide**: [your-mt4-docs-url]
- **Stripe API**: https://stripe.com/docs/api
- **FastAPI Docs**: https://fastapi.tiangolo.com/

### Questions to Ask Your Team
1. **Do all 3 backends share the same PostgreSQL database?**
   - Yes → Unified `/api/user/brokers` can query all accounts
   - No → Need aggregation layer or separate endpoints

2. **Where is the "unified" endpoint hosted?**
   - Option A: Single gateway routing to 3 backends
   - Option B: Each backend has its own `/webhook/{broker}` endpoint

3. **Do you have Stripe integration set up?**
   - Yes → Implement billing endpoints
   - No → Use mock data, billing is client-side only

4. **How are API keys stored?**
   - Plain text → 🚨 URGENT: Switch to hashed/encrypted
   - Hashed → Good
   - Encrypted → Best

---

## 🎯 Success Metrics

You'll know the backend is complete when:

### Basic Flow Works
- [ ] User can signup and login
- [ ] User can connect TradeLocker account
- [ ] User receives API key in response
- [ ] User can copy API key from UI
- [ ] TradingView webhook executes trade
- [ ] User sees position in dashboard
- [ ] User can close position

### Trial System Works
- [ ] New user has `plan: 'trial'` and `trades_count: 0`
- [ ] Each webhook execution increments `trades_count`
- [ ] Trial blocks trading after 100 trades
- [ ] Trial blocks trading after 3 days
- [ ] User can upgrade via Stripe checkout
- [ ] Stripe webhook updates user plan to 'pro'

### Safety Features Work
- [ ] Emergency stop closes all positions
- [ ] Risk controls block trades (daily loss, trading hours)
- [ ] Disabled accounts reject webhooks
- [ ] Invalid API keys return 401

### Admin Features Work
- [ ] Admin can view all users
- [ ] Admin can see platform stats
- [ ] Admin can impersonate users
- [ ] Admin can view all accounts and API keys

---

## 🚀 Quick Win: Implement This First

If you only have time for ONE thing, implement this:

### **Webhook Handler with API Key Validation**

**File**: `unified_backend/routes/webhooks.py`

```python
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class WebhookPayload(BaseModel):
    version: str
    source: str
    intent: dict
    user_context: dict = {}
    ts: str = None

@router.post("/api/unify/v1/webhook/{broker}")
async def webhook_handler(
    broker: str,
    payload: WebhookPayload,
    request: Request,
    authorization: str = Header(None)
):
    """
    CRITICAL ENDPOINT: Receives TradingView webhooks and executes trades.
    
    Auth: Authorization: Bearer {api_key}
    """
    
    # 1. Extract and validate API key
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    
    api_key = authorization.split("Bearer ")[1]
    
    # 2. Query database for account
    account = await db.fetchrow(
        """
        SELECT a.*, u.plan, u.trades_count
        FROM accounts a
        JOIN api_keys ak ON a.id = ak.account_id
        JOIN users u ON a.user_id = u.id
        WHERE ak.key = $1 AND a.broker = $2
        """,
        api_key, broker
    )
    
    if not account:
        logger.warning(f"Invalid API key attempt: {api_key[:10]}...")
        raise HTTPException(401, "Invalid API key")
    
    if not account['enabled']:
        raise HTTPException(403, "Account is disabled")
    
    # 3. Check trial limits
    if account['plan'] == 'trial':
        if account['trades_count'] >= 100:
            raise HTTPException(403, "Trial limit: 100 trades reached. Upgrade to continue.")
        
        # Check days since signup (implement this)
        # if days_since_signup(account['user_id']) >= 3:
        #     raise HTTPException(403, "Trial expired. Upgrade to continue.")
    
    # 4. Execute trade via broker API (implement broker-specific logic)
    try:
        if broker == "tradelocker":
            result = await execute_tradelocker_trade(account, payload.intent)
        elif broker == "topstep":
            result = await execute_topstep_trade(account, payload.intent)
        elif broker == "truforex":
            result = await execute_mtx_trade(account, payload.intent)
        else:
            raise HTTPException(400, f"Unknown broker: {broker}")
        
        # 5. Increment trades count
        await db.execute(
            "UPDATE users SET trades_count = trades_count + 1 WHERE id = $1",
            account['user_id']
        )
        
        # 6. Log webhook event
        await db.execute(
            """
            INSERT INTO webhooks_log (account_id, timestamp, method, path, status, payload, response)
            VALUES ($1, NOW(), $2, $3, 200, $4, $5)
            """,
            account['id'], request.method, request.url.path, 
            payload.dict(), result
        )
        
        return {
            "success": True,
            "order_id": result['order_id'],
            "message": f"{payload.intent['type'].title()} {payload.intent['side']} order executed"
        }
        
    except Exception as e:
        logger.error(f"Webhook execution failed: {e}")
        
        # Log error
        await db.execute(
            """
            INSERT INTO webhooks_log (account_id, timestamp, method, path, status, payload, error)
            VALUES ($1, NOW(), $2, $3, 500, $4, $5)
            """,
            account['id'], request.method, request.url.path,
            payload.dict(), str(e)
        )
        
        raise HTTPException(500, f"Trade execution failed: {str(e)}")
```

**This ONE endpoint unlocks:**
- Webhook execution ✅
- API key validation ✅
- Trial tracking ✅
- Event logging ✅
- Error handling ✅

**Once this works, everything else is enhancement.**

---

## 📝 Final Checklist

Before considering backend "complete":

### Phase 1: MVP
- [ ] Webhook handler implemented (all 3 brokers)
- [ ] API keys generated on registration
- [ ] Trial tracking working (blocks after 100 trades or 3 days)
- [ ] Positions can be viewed
- [ ] Positions can be closed

### Phase 2: Production-Ready
- [ ] Billing integration complete (Stripe checkout + webhook)
- [ ] Account management (toggle, sync, delete)
- [ ] Risk controls enforced in webhook handler
- [ ] Emergency stop functional
- [ ] Logs viewable in UI

### Phase 3: Full Feature Set
- [ ] Analytics endpoints (P&L, metrics, trades)
- [ ] Admin panel endpoints
- [ ] Notifications system
- [ ] All error states handled gracefully

### Phase 4: Polish
- [ ] OpenAPI spec generated
- [ ] Postman collection created
- [ ] API documentation published
- [ ] Rate limiting configured
- [ ] Monitoring/alerting set up

---

## 🎉 You're Ready!

You now have:
- ✅ Complete specification of all 70+ endpoints
- ✅ Request/response schemas for each
- ✅ Priority rankings (Phase 1-4)
- ✅ Implementation examples
- ✅ Testing instructions
- ✅ Security checklist
- ✅ Data flow diagrams

**Next step**: Open `BACKEND_ENDPOINTS_CHECKLIST.md` and start checking boxes!

---

**Questions?** Refer back to:
- `BACKEND_API_REQUIREMENTS_GUIDE.md` for "how to implement"
- `SYSTEM_ARCHITECTURE_DIAGRAM.md` for "how it all fits together"
- `BACKEND_API_REQUIREMENTS.json` for exact specs

**Good luck! 🚀**

---

**Generated**: 2025-10-19  
**Version**: 6.0  
**Author**: AI Assistant (Figma Make)  
**Project**: TradeFlow by Fluxeo
