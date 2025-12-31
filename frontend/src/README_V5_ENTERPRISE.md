# 🚀 Empire Trading Hub - V5 Enterprise Edition

**Multi-Broker Trading Platform** | TradeLocker • Topstep • TruForex

[![Status](https://img.shields.io/badge/status-production--ready-brightgreen)]()
[![Version](https://img.shields.io/badge/version-5.0.0-blue)]()
[![License](https://img.shields.io/badge/license-proprietary-red)]()

---

## 📋 Table of Contents

1. [What's New in V5](#whats-new-in-v5)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Database Schema](#database-schema)
5. [API Reference](#api-reference)
6. [Deployment](#deployment)
7. [Security](#security)
8. [Monetization](#monetization)
9. [Support](#support)

---

## 🆕 What's New in V5

### Enterprise-Grade Features

✅ **Real-time Everything**
- Live P&L updates via Supabase Realtime
- Order status changes without polling
- System health monitoring

✅ **Advanced Risk Visualization**
- Risk Heatmap (position exposure treemap)
- Equity Curve (historical performance)
- Daily Drawdown Chart (intraday risk)

✅ **Bank-Level Security**
- AES-256-GCM credential encryption
- HMAC-SHA256 webhook signing
- 2FA/TOTP authentication
- Row-Level Security (RLS) policies

✅ **Test Alert Playground**
- Validate TradingView JSON before sending
- Visual order preview with SL/TP
- Real-time schema validation

✅ **Tiered Pricing**
- Starter: $29/mo (1 broker, 100 trades/mo)
- Pro: $79/mo (3 brokers, unlimited trades)
- Elite: $199/mo (white-label, API access)

✅ **Production Observability**
- Prometheus metrics endpoint
- NATS event streaming
- 90-day audit logs
- Health status banner

---

## ⚡ Quick Start

### Prerequisites

- Node.js 18+ / Bun
- Docker & Docker Compose
- Supabase account (cloud or self-hosted)
- Stripe account (for billing)

### 1. Clone & Install

```bash
git clone https://github.com/empire-trading/hub-v5.git
cd hub-v5
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env.local

# Edit .env.local with your credentials:
NEXT_PUBLIC_SUPABASE_URL=https://[project].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGci...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
```

### 3. Deploy Database Schema

```bash
# Using psql
psql $SUPABASE_DB_URL < supabase_schema_v5.sql

# Or using Supabase CLI
supabase db push
```

### 4. Run Development Server

```bash
npm run dev
# Open http://localhost:3000
```

### 5. Deploy to Production

```bash
# Using Docker Swarm
docker stack deploy -c stack_v5.yml empire

# Or using Vercel
vercel --prod
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     CLIENT (Browser)                     │
│  React + Tailwind + Supabase Realtime + Recharts       │
└────────────┬────────────────────────────────────────────┘
             │
             │ HTTPS
             ▼
┌─────────────────────────────────────────────────────────┐
│                   TRAEFIK (Reverse Proxy)                │
│           SSL Termination + Rate Limiting                │
└────────────┬────────────────────────────────────────────┘
             │
       ┌─────┴─────┐
       │           │
       ▼           ▼
┌────────────┐ ┌────────────────────────────────────────┐
│  Gateway   │ │     Supabase (Database + Auth)         │
│  (Next.js) │ │  - PostgreSQL with RLS                 │
│            │ │  - Realtime WebSocket Server           │
└──────┬─────┘ │  - Storage (encrypted credentials)     │
       │       └────────────────────────────────────────┘
       │
   ┌───┴──────────────┐
   │                  │
   ▼                  ▼
┌──────────┐    ┌──────────────────┐
│   NATS   │◄───┤  Broker Backends │
│ (Events) │    │ - TradeLocker    │
└──────────┘    │ - Topstep        │
                │ - TruForex       │
                └──────────────────┘
```

### Component Responsibilities

**Gateway (Next.js)**
- UI rendering (React)
- API endpoint aggregation
- Webhook ingestion
- Stripe integration

**Supabase**
- User authentication (JWT)
- Data persistence (PostgreSQL)
- Real-time updates (WebSocket)
- File storage (encrypted)

**NATS**
- Event streaming (pub/sub)
- Service coordination
- Health monitoring
- Log aggregation

**Broker Backends**
- TradeLocker API integration
- Topstep contract polling
- TruForex MT4/MT5 execution
- Order lifecycle management

---

## 🗄️ Database Schema

### Core Tables (11 total)

**profiles** - User accounts
```sql
id, email, name, role, plan_tier, trial_end, totp_secret, totp_enabled
```

**broker_accounts** - Connected brokers
```sql
id, user_id, broker, account_id, api_key, api_key_hash, 
credentials_encrypted, balance, equity, last_sync
```

**risk_settings** - Risk management
```sql
user_id, broker, max_daily_loss_usd, max_daily_loss_pct,
max_trades_per_day, max_open_trades, max_concurrent_positions
```

**trading_config** - SL/TP/lot size
```sql
user_id, broker, lot_size_mode, fixed_lot_size, sl_percentage,
tp_percentage, risk_reward_ratio, use_trailing_sl
```

**orders** - Order history
```sql
id, user_id, broker, symbol, side, type, qty, price, status, tag
```

**positions** - Open positions
```sql
id, user_id, broker, symbol, side, qty, entry_price, unrealized_pnl,
stop_loss, take_profit
```

**logs** - System logs
```sql
id, user_id, level, type, message, details (jsonb), correlation_id
```

**webhook_events** - Incoming webhooks
```sql
id, user_id, payload (jsonb), signature, signature_valid, processed
```

**subscriptions** - Stripe billing
```sql
user_id, stripe_customer_id, plan, status, trial_end, current_period_end
```

**admin_actions** - Audit trail
```sql
admin_user_id, action, target_user_id, details, ip_address
```

**equity_history** - Performance tracking
```sql
user_id, broker, equity, balance, unrealized_pnl, timestamp
```

### Row-Level Security (RLS)

**User Isolation**
```sql
-- Users see only their own data
CREATE POLICY "users_own_data" ON positions
  FOR SELECT USING (auth.uid() = user_id);
```

**Admin Access**
```sql
-- Admins bypass RLS
CREATE POLICY "admins_all_data" ON positions
  FOR SELECT USING ((auth.jwt() ->> 'role')::text = 'admin');
```

### Realtime Channels

- `positions:${userId}` → Live P&L updates
- `orders:${userId}` → Order status changes
- `logs:${userId}` → Log tail mode
- `health:system` → System status (broadcast)

---

## 📡 API Reference

### Base URL
```
https://api.empiretrading.io/api/unify/v1
```

### Authentication
```http
Authorization: Bearer YOUR_API_KEY
```

### Endpoints

#### Place Order
```http
POST /order
Content-Type: application/json

{
  "broker": "tradelocker",
  "side": "buy",
  "type": "market",
  "symbol": "EURUSD",
  "qty_mode": "risk_pct",
  "qty": 1.0,
  "sl": {"mode": "price", "value": 1.0950},
  "tp": {"mode": "rr", "value": 2.0},
  "tag": "EU_Breakout"
}
```

#### Get Positions
```http
GET /positions?broker=tradelocker&symbol=EURUSD
```

#### Update Risk Settings
```http
PUT /risk
Content-Type: application/json

{
  "max_daily_loss_usd": 500,
  "max_trades_per_day": 10,
  "max_open_trades": 5
}
```

#### Webhook Endpoint (TradingView)
```http
POST /webhook/tradelocker
X-Webhook-Signature: t=1697300000,v1=abc123...
Content-Type: application/json

{
  "version": "unify.v1",
  "source": "tradingview",
  "intent": { ... },
  "ts": "2025-10-14T14:30:00Z"
}
```

#### Health Check
```http
GET /health

Response:
{
  "status": "healthy",
  "brokers": {
    "tradelocker": "operational",
    "topstep": "operational",
    "truforex": "operational"
  },
  "latency_ms": 42
}
```

#### Prometheus Metrics
```http
GET /metrics

Response (text/plain):
orders_total{broker="tradelocker",status="filled"} 1247
rejects_total{reason="insufficient_margin"} 12
pnl_unrealized{broker="tradelocker",symbol="EURUSD"} 125.50
```

### Full OpenAPI Specification
See `openapi_v5.yaml` for complete API documentation.

---

## 🚀 Deployment

### Option 1: Docker Swarm (Recommended)

```bash
# 1. Initialize Swarm
docker swarm init

# 2. Create secrets
echo "your-jwt-secret" | docker secret create supabase_jwt_secret -
echo "your-stripe-secret" | docker secret create stripe_webhook_secret -
openssl rand -hex 32 | docker secret create encryption_key -

# 3. Label nodes for NATS cluster
docker node update --label-add nats-node=1 node1
docker node update --label-add nats-node=2 node2
docker node update --label-add nats-node=3 node3

# 4. Deploy stack
docker stack deploy -c stack_v5.yml empire

# 5. Verify
docker service ls
docker service logs -f empire_gateway
```

### Option 2: Kubernetes

```bash
# Apply manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployments.yaml
kubectl apply -f k8s/services.yaml
kubectl apply -f k8s/ingress.yaml

# Scale services
kubectl scale deployment gateway --replicas=5
```

### Option 3: Vercel (Frontend Only)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod

# Environment variables (set in Vercel dashboard)
NEXT_PUBLIC_SUPABASE_URL=https://[project].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
STRIPE_SECRET_KEY=...
```

### Post-Deployment Checklist

- [ ] SSL certificates active (Let's Encrypt)
- [ ] DNS records configured (app.*, api.*, metrics.*)
- [ ] Supabase schema deployed
- [ ] Secrets created (JWT, Stripe, encryption)
- [ ] NATS cluster healthy (3 nodes)
- [ ] Health endpoint returns 200
- [ ] Stripe webhooks configured
- [ ] Prometheus scraping metrics
- [ ] Log retention configured (90 days)

---

## 🔒 Security

### Threat Model

**Protected Against:**
- ✅ SQL injection (parameterized queries)
- ✅ XSS (React auto-escaping)
- ✅ CSRF (SameSite cookies)
- ✅ Credential theft (encrypted at rest)
- ✅ Webhook spoofing (HMAC signatures)
- ✅ Replay attacks (timestamp validation)
- ✅ Privilege escalation (RLS policies)
- ✅ Brute force (rate limiting)

### Encryption

**Credentials (AES-256-GCM)**
```typescript
import { encrypt, decrypt } from './utils/encryption';

// Before storing
const encrypted = encrypt(JSON.stringify(credentials));
await supabase.from('broker_accounts')
  .insert({ credentials_encrypted: encrypted });

// When retrieving
const { data } = await supabase.from('broker_accounts')
  .select('credentials_encrypted').single();
const credentials = JSON.parse(decrypt(data.credentials_encrypted));
```

**Webhook Signatures (HMAC-SHA256)**
```typescript
import { signWebhookPayload, verifyWebhookSignature } from './utils/webhook';

// Signing
const signature = signWebhookPayload(payload, secret);
headers['X-Webhook-Signature'] = signature;

// Verifying
const isValid = verifyWebhookSignature(body, signature, secret);
if (!isValid) return res.status(401).send('Invalid signature');
```

### 2FA/TOTP

```typescript
import { generateTOTPSecret, verifyTOTP } from './utils/totp';

// Enable 2FA
const secret = generateTOTPSecret(user.email);
const qrCode = await generateQRCode(secret.otpauth_url);
// User scans QR code with authenticator app

// Verify login
const isValid = verifyTOTP(token, user.totp_secret);
```

### Rate Limiting

**Plan-Based Limits**
- Starter: 100 requests/min
- Pro: 500 requests/min
- Elite: 2000 requests/min

**Enforcement**: Traefik middleware
```yaml
http:
  middlewares:
    rate-limit-starter:
      rateLimit:
        average: 100
        burst: 200
```

### Audit Logging

All admin actions logged to `admin_actions` table:
```sql
INSERT INTO admin_actions (admin_user_id, action, target_user_id, details, ip_address)
VALUES (current_user_id, 'user_suspended', target_id, '{"reason": "ToS violation"}', client_ip);
```

---

## 💰 Monetization

### Plan Comparison

| Feature | Starter ($29/mo) | Pro ($79/mo) | Elite ($199/mo) |
|---------|------------------|--------------|-----------------|
| Brokers | 1 | 3 | Unlimited |
| Trades/Month | 100 | Unlimited | Unlimited |
| API Rate Limit | 100/min | 500/min | 2000/min |
| Risk Heatmap | ❌ | ✅ | ✅ |
| Equity Curve | ❌ | ✅ | ✅ |
| 2FA | ❌ | ✅ | ✅ |
| Support | Email | Priority Email + Chat | Dedicated + Phone |
| White-Label | ❌ | ❌ | ✅ |
| API Access | Read-Only | Full | Full + WebSocket |
| SLA | - | - | 99.9% |

### Revenue Projections

**Baseline (V4)**
- ARPU: $49
- Conversion: 15%
- Daily revenue per 100 signups: $7.35

**Projected (V5)**
- Weighted ARPU: $89
- Conversion: 22%
- Daily revenue per 100 signups: **$19.58** (+166%)

**Annual Revenue (10K users)**
- Starter: 1,200 users × $29 = $34,800/mo
- Pro: 800 users × $79 = $63,200/mo
- Elite: 200 users × $199 = $39,800/mo
- **Total MRR: $137,800**
- **Total ARR: $1.65M**

### Stripe Integration

**Webhook Events**
```javascript
// Handle subscription events
stripe.webhooks.constructEvent(body, signature, secret);

switch (event.type) {
  case 'customer.subscription.created':
    // Provision user access
    break;
  case 'customer.subscription.updated':
    // Update plan tier
    break;
  case 'invoice.payment_failed':
    // Send dunning email
    break;
}
```

**Checkout Session**
```typescript
const session = await stripe.checkout.sessions.create({
  customer_email: user.email,
  mode: 'subscription',
  line_items: [{
    price: 'price_pro_monthly', // From Stripe dashboard
    quantity: 1
  }],
  success_url: 'https://app.empiretrading.io/billing/success',
  cancel_url: 'https://app.empiretrading.io/billing'
});
```

---

## 📞 Support

### Documentation

- **API Docs**: https://docs.empiretrading.io/api
- **User Guide**: https://docs.empiretrading.io/guide
- **Video Tutorials**: https://youtube.com/@empiretrading

### Community

- **Discord**: https://discord.gg/empiretrading
- **Forum**: https://community.empiretrading.io

### Commercial Support

- **Starter Plan**: Email support (24-48h response)
- **Pro Plan**: Priority email + chat (4-8h response)
- **Elite Plan**: Dedicated account manager + phone support

### Contact

- **Email**: support@empiretrading.io
- **Sales**: sales@empiretrading.io
- **Security**: security@empiretrading.io

---

## 📄 License

Proprietary. All rights reserved.

© 2025 Empire Trading Hub

---

## 🎯 Next Steps

1. ✅ Deploy Supabase schema
2. ✅ Configure environment variables
3. ✅ Deploy Docker stack
4. ✅ Set up Stripe webhooks
5. ✅ Configure DNS & SSL
6. ✅ Test health endpoint
7. ✅ Create first user account
8. ✅ Connect first broker
9. ✅ Place test order
10. ✅ Monitor Prometheus metrics

**Ready to scale to 10,000+ users!** 🚀

---

**Version**: 5.0.0  
**Last Updated**: 2025-10-14  
**Status**: ✅ Production Ready
