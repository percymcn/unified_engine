# Backend Integration Guide - TradeFlow v6.0

This guide explains how to integrate the new TradeFlow v6.0 frontend with your existing FastAPI backend at `https://unified.fluxeo.net/api/unify/v1`.

---

## 🔗 API Endpoint Mapping

### Current Frontend Routes → Your Backend Routes

#### 1. Broker Registration

**Frontend expects:**
```typescript
POST /register/tradelocker
POST /register/projectx  
POST /register/mtx
```

**Your backend has:**
```
POST https://unified.fluxeo.net/api/unify/v1/register/tradelocker
POST https://unified.fluxeo.net/api/unify/v1/register/projectx
POST https://unified.fluxeo.net/api/unify/v1/register/mtx
```

**Payload format:**
```json
{
  "username": "user123",
  "password": "secure_password",
  "server": "live.tradelocker.com" // Optional for some brokers
}
```

**Expected response:**
```json
{
  "success": true,
  "apiKey": "generated-api-key-here",
  "accountId": "account-123",
  "message": "Broker connected successfully"
}
```

#### 2. Analytics & Metrics

**Frontend expects:**
```typescript
GET /metrics
GET /reports/pnl
GET /analytics/trades
GET /analytics/strategies
```

**Your backend should return:**

`GET /metrics`:
```json
{
  "totalTrades": 1248,
  "activeUsers": 189,
  "totalPnL": 45230.50,
  "winRate": 67.8,
  "timeRange": "7d"
}
```

`GET /reports/pnl`:
```json
{
  "daily": [
    { "date": "2025-10-10", "profit": 2250, "loss": 1000, "net": 1250 },
    { "date": "2025-10-11", "profit": 3890, "loss": 2000, "net": 1890 }
  ],
  "total": { "profit": 125000, "loss": 50000, "net": 75000 }
}
```

#### 3. Billing & Subscriptions

**Frontend calls Stripe directly**, but needs backend support for:

```typescript
POST /billing/create-checkout-session
POST /billing/create-portal-session
POST /billing/webhook
GET /billing/usage
```

**Implementation example:**
```python
from fastapi import APIRouter
import stripe

router = APIRouter()

@router.post("/billing/create-checkout-session")
async def create_checkout_session(plan: str, user_email: str):
    """Create Stripe Checkout session"""
    
    price_ids = {
        "starter": "price_starter_monthly",
        "pro": "price_pro_monthly",
        "elite": "price_elite_monthly"
    }
    
    session = stripe.checkout.Session.create(
        customer_email=user_email,
        payment_method_types=["card"],
        line_items=[{
            "price": price_ids[plan],
            "quantity": 1,
        }],
        mode="subscription",
        success_url="https://yourdomain.com/dashboard?checkout=success",
        cancel_url="https://yourdomain.com/billing?checkout=cancel",
    )
    
    return {"url": session.url}

@router.post("/billing/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        
        # Handle different event types
        if event["type"] == "checkout.session.completed":
            # Update user subscription in database
            session = event["data"]["object"]
            # ... your logic here
            
        elif event["type"] == "customer.subscription.deleted":
            # Handle cancellation
            # ... your logic here
            
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}, 400
```

---

## 🔧 Update API Client

Update `/utils/api-client.ts` to use your actual backend:

```typescript
const API_BASE_URL = 'https://unified.fluxeo.net/api/unify/v1';

// Change this to false to use real backend
const USE_MOCK_BACKEND = false;
```

---

## 🔐 Authentication Flow

### Current Supabase Auth Flow

1. User signs up → Supabase creates auth user
2. Frontend calls your backend `/auth/signup` to create profile
3. Backend creates user in your database
4. User logs in → Gets Supabase access token
5. Access token sent to your backend for authorization

### Update Your Backend Auth Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException
from supabase import create_client

router = APIRouter()

@router.post("/auth/signup")
async def signup(email: str, password: str, name: str, plan: str):
    """Create user profile after Supabase auth"""
    
    # Create user in Supabase (server-side)
    supabase = create_client(supabase_url, service_role_key)
    
    auth_response = supabase.auth.admin.create_user({
        "email": email,
        "password": password,
        "user_metadata": {"name": name},
        "email_confirm": True  # Auto-confirm since no email server
    })
    
    if auth_response.user:
        # Create profile in your database
        user_profile = {
            "id": auth_response.user.id,
            "email": email,
            "name": name,
            "plan": plan,
            "role": "user",
            "created_at": datetime.now()
        }
        # Save to your database
        
        return {"success": True, "user": user_profile}
    
    raise HTTPException(status_code=400, detail="Signup failed")

@router.get("/user/profile")
async def get_profile(user_id: str = Depends(get_current_user)):
    """Get user profile"""
    # Fetch from your database
    user = db.get_user(user_id)
    return user
```

---

## 📊 Analytics Data Structure

### Database Schema for Analytics

```sql
-- Trades table
CREATE TABLE trades (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    broker VARCHAR(50),
    symbol VARCHAR(20),
    side VARCHAR(10),
    entry_price DECIMAL(10, 2),
    exit_price DECIMAL(10, 2),
    pnl DECIMAL(10, 2),
    opened_at TIMESTAMP,
    closed_at TIMESTAMP
);

-- User metrics (pre-aggregated for performance)
CREATE TABLE user_metrics (
    user_id UUID PRIMARY KEY,
    total_trades INTEGER,
    win_rate DECIMAL(5, 2),
    total_pnl DECIMAL(12, 2),
    updated_at TIMESTAMP
);

-- System metrics (admin view)
CREATE TABLE system_metrics (
    date DATE PRIMARY KEY,
    active_users INTEGER,
    total_trades INTEGER,
    total_revenue DECIMAL(12, 2),
    mrr DECIMAL(12, 2)
);
```

### Analytics Aggregation Query

```python
@router.get("/metrics")
async def get_metrics(
    user_id: str = Depends(get_current_user),
    time_range: str = "7d",
    broker: str = "all"
):
    """Get analytics metrics"""
    
    # Determine if admin
    user = db.get_user(user_id)
    is_admin = user.role == "admin"
    
    if is_admin:
        # Return system-wide metrics
        metrics = db.query("""
            SELECT 
                COUNT(*) as total_trades,
                COUNT(DISTINCT user_id) as active_users,
                SUM(pnl) as total_pnl,
                AVG(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 100 as win_rate
            FROM trades
            WHERE created_at >= NOW() - INTERVAL :time_range
        """, time_range=time_range)
    else:
        # Return user-specific metrics
        metrics = db.query("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(pnl) as total_pnl,
                AVG(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 100 as win_rate
            FROM trades
            WHERE user_id = :user_id
            AND created_at >= NOW() - INTERVAL :time_range
        """, user_id=user_id, time_range=time_range)
    
    return metrics
```

---

## 🎯 Priority Integration Tasks

### Phase 1: Core Functionality (Week 1)
1. ✅ Update API_BASE_URL in api-client.ts
2. ✅ Test broker registration endpoints
3. ✅ Implement /user/profile endpoint
4. ✅ Test authentication flow

### Phase 2: Analytics (Week 2)
5. ✅ Implement /metrics endpoint
6. ✅ Implement /reports/pnl endpoint
7. ✅ Add analytics data aggregation
8. ✅ Test admin vs user views

### Phase 3: Billing (Week 3)
9. ✅ Set up Stripe account
10. ✅ Create products/prices in Stripe
11. ✅ Implement checkout session endpoint
12. ✅ Set up webhook handler
13. ✅ Test subscription flow

### Phase 4: Polish (Week 4)
14. ✅ Add error handling
15. ✅ Implement rate limiting
16. ✅ Add logging
17. ✅ Performance optimization
18. ✅ Security audit

---

## 🔒 Security Considerations

### 1. API Key Storage
```python
# Never return API keys directly - hash them
import hashlib

def generate_api_key(user_id: str) -> tuple[str, str]:
    """Generate API key and return both plain and hashed versions"""
    plain_key = secrets.token_urlsafe(32)
    hashed_key = hashlib.sha256(plain_key.encode()).hexdigest()
    
    # Store hashed version in database
    db.store_api_key(user_id, hashed_key)
    
    # Return plain version to user (only once!)
    return plain_key, hashed_key
```

### 2. Rate Limiting
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/register/tradelocker")
@limiter.limit("5/minute")  # Max 5 registrations per minute
async def register_tradelocker(request: Request, ...):
    # ... your code
```

### 3. Input Validation
```python
from pydantic import BaseModel, EmailStr, validator

class BrokerRegistration(BaseModel):
    username: str
    password: str
    server: Optional[str] = None
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username too short')
        return v
```

---

## 🧪 Testing

### Test Broker Registration
```bash
curl -X POST https://unified.fluxeo.net/api/unify/v1/register/tradelocker \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "username": "test_user",
    "password": "test_password",
    "server": "demo.tradelocker.com"
  }'
```

### Test Analytics
```bash
curl -X GET https://unified.fluxeo.net/api/unify/v1/metrics?time_range=7d \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 📝 Environment Variables

Add to your backend `.env`:

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Redis (for caching)
REDIS_URL=redis://localhost:6379

# API
API_SECRET_KEY=your-secret-key-here
CORS_ORIGINS=https://yourdomain.com,http://localhost:3000
```

---

## 🚀 Deployment Checklist

Before going live:

- [ ] Update all API URLs to production
- [ ] Set USE_MOCK_BACKEND = false
- [ ] Configure Stripe with live keys
- [ ] Set up webhook endpoints
- [ ] Test all broker connections
- [ ] Verify authentication flow
- [ ] Test analytics with real data
- [ ] Load test critical endpoints
- [ ] Set up monitoring (Datadog/Sentry)
- [ ] Configure CORS properly
- [ ] Enable rate limiting
- [ ] Add comprehensive logging
- [ ] Backup database
- [ ] Set up SSL certificates

---

## 💬 Common Issues & Solutions

### Issue 1: CORS Errors
**Solution:** Add frontend domain to backend CORS whitelist
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Issue 2: Auth Token Expired
**Solution:** Implement token refresh logic
```typescript
// In api-client.ts
if (response.status === 401) {
  // Refresh token
  const newToken = await refreshAuthToken();
  apiClient.setToken(newToken);
  // Retry request
  return apiClient.request(originalRequest);
}
```

### Issue 3: Slow Analytics Queries
**Solution:** Pre-aggregate data
```python
# Run this as a cron job every hour
def aggregate_metrics():
    db.execute("""
        INSERT INTO user_metrics (user_id, total_trades, win_rate, total_pnl)
        SELECT 
            user_id,
            COUNT(*) as total_trades,
            AVG(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 100 as win_rate,
            SUM(pnl) as total_pnl
        FROM trades
        WHERE updated_at > NOW() - INTERVAL '1 hour'
        GROUP BY user_id
        ON CONFLICT (user_id) DO UPDATE SET
            total_trades = EXCLUDED.total_trades,
            win_rate = EXCLUDED.win_rate,
            total_pnl = EXCLUDED.total_pnl,
            updated_at = NOW()
    """)
```

---

## 📞 Support

Need help with backend integration?
- Email: support@fluxeo.net
- Review: `/openapi_v5.yaml` for API spec
- Check: `/unified_blueprint_v5.json` for data structures

---

**Last Updated:** October 17, 2025  
**Version:** 6.0.0
