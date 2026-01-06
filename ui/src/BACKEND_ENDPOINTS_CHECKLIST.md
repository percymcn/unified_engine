# TradeFlow Backend Endpoints Checklist

**Quick reference**: Mark ✅ when implemented, ⚠️ when partially implemented, ❌ when missing

---

## 🔐 Authentication (6 endpoints)

| Status | Method | Endpoint | Purpose | Backend |
|--------|--------|----------|---------|---------|
| [ ] | POST | `/auth/signup` | Create new user account | Supabase |
| [ ] | POST | `/auth/login` | User login, returns JWT | Supabase |
| [ ] | POST | `/auth/logout` | Invalidate session | Supabase |
| [ ] | POST | `/auth/reset-password` | Send password reset email | Supabase |
| [ ] | GET | `/auth/session` | Validate session, get user data | Supabase |
| [ ] | POST | `/auth/admin/login` | Admin authentication | Custom |

---

## 🏦 Broker Registration & Accounts (10 endpoints)

| Status | Method | Endpoint | Purpose | Backend |
|--------|--------|----------|---------|---------|
| [ ] | POST | `/register/tradelocker` | Register TradeLocker account + generate API key | TradeLocker |
| [ ] | POST | `/register/projectx` | Register Topstep/ProjectX account + API key | Topstep |
| [ ] | POST | `/register/mtx` | Register MT4/MT5 account + API key | MT4/MT5 |
| [ ] | GET | `/api/user/brokers` | List all connected accounts for user | Unified |
| [ ] | PATCH | `/api/accounts/{id}/toggle` | Enable/disable account | Unified |
| [ ] | PATCH | `/api/accounts/{id}` | Update account metadata (name, number) | Unified |
| [ ] | DELETE | `/api/accounts/{id}` | Delete account permanently | Unified |
| [ ] | POST | `/api/accounts/sync/{id}` | Manually sync account from broker API | Broker-specific |
| [ ] | GET | `/api/accounts/sync_results` | View sync history | Unified |
| [ ] | POST | `/api/accounts/switch` | Set active account for session | Unified |

---

## 🔑 API Key Management (6 endpoints)

| Status | Method | Endpoint | Purpose | Backend |
|--------|--------|----------|---------|---------|
| [ ] | N/A | *(Auto-generated)* | API key created on `/register/{broker}` | All brokers |
| [ ] | POST | `/api/accounts/{id}/regenerate-api-key` | Invalidate old key, generate new | Unified |
| [ ] | GET | `/api/user/api_keys` | List all user API keys | Unified |
| [ ] | POST | `/api/user/api_keys/generate` | Create custom API key with permissions | Unified |
| [ ] | DELETE | `/api/user/api_keys/{id}` | Revoke custom API key | Unified |
| [ ] | GET | `/api/admin/api_keys` | Admin view of all API keys (admin only) | Unified |

---

## 🪝 Webhooks (4 endpoints) - **MOST CRITICAL**

| Status | Method | Endpoint | Purpose | Backend |
|--------|--------|----------|---------|---------|
| [ ] | POST | `/api/unify/v1/webhook/tradelocker` | **Execute trade from TradingView alert** | TradeLocker |
| [ ] | POST | `/api/unify/v1/webhook/topstep` | **Execute trade from TradingView alert** | Topstep |
| [ ] | POST | `/api/unify/v1/webhook/truforex` | **Execute trade from TradingView alert** | MT4/MT5 |
| [ ] | GET | `/api/webhooks/logs` | View webhook execution history | Unified |

**Auth**: `Authorization: Bearer {api_key}` (from account registration)

---

## 📊 Trading & Orders (6 endpoints)

| Status | Method | Endpoint | Purpose | Backend |
|--------|--------|----------|---------|---------|
| [ ] | GET | `/api/positions` | Fetch open positions (all accounts or filtered) | Broker-specific |
| [ ] | POST | `/api/orders/close` | Close position at market price | Broker-specific |
| [ ] | GET | `/api/orders` | List orders (with filtering/pagination) | Broker-specific |
| [ ] | DELETE | `/api/orders/{id}` | Cancel pending order | Broker-specific |
| [ ] | GET | `/api/overview` | Dashboard metrics (P&L, win rate, etc.) | Unified |
| [ ] | POST | `/api/user/emergency_stop` | **Close ALL positions immediately** | Unified |

---

## 📈 Analytics & Reporting (3 endpoints)

| Status | Method | Endpoint | Purpose | Backend |
|--------|--------|----------|---------|---------|
| [ ] | GET | `/api/reports/pnl` | P&L report for date range | Unified |
| [ ] | GET | `/api/analytics/metrics` | Detailed performance metrics | Unified |
| [ ] | GET | `/api/analytics/trades` | Trade-by-trade history | Unified |

---

## 🛡️ Risk Management (3 endpoints)

| Status | Method | Endpoint | Purpose | Backend |
|--------|--------|----------|---------|---------|
| [ ] | GET | `/api/user/risk_config` | Fetch risk control settings | Unified |
| [ ] | PUT | `/api/user/risk_config` | Update risk controls | Unified |
| [ ] | POST | `/api/user/emergency_stop` | *(Duplicate - see Trading section)* | Unified |

**Note**: Risk controls are **enforced** in webhook handler before executing trades.

---

## ⚙️ Trading Configuration (2 endpoints)

| Status | Method | Endpoint | Purpose | Backend |
|--------|--------|----------|---------|---------|
| [ ] | GET | `/api/user/config` | Fetch trading config (SL/TP defaults, position size) | Unified |
| [ ] | PUT | `/api/user/config` | Update trading config | Unified |

---

## 💳 Billing & Subscription (8 endpoints)

| Status | Method | Endpoint | Purpose | Backend |
|--------|--------|----------|---------|---------|
| [ ] | GET | `/api/billing/status` | Get Stripe subscription status | Unified |
| [ ] | GET | `/api/billing/usage` | Get trial/plan usage (trades count, days left) | Unified |
| [ ] | POST | `/api/billing/checkout` | Create Stripe checkout session | Unified |
| [ ] | POST | `/api/billing/portal` | Create Stripe customer portal session | Unified |
| [ ] | POST | `/api/billing/cancel` | Cancel subscription at period end | Unified |
| [ ] | POST | `/api/billing/change_plan` | Upgrade/downgrade plan | Unified |
| [ ] | POST | `/api/billing/webhook` | **Handle Stripe webhook events** | Unified |
| [ ] | GET | `/api/billing/invoices` | List user invoices | Unified |

**Critical**: Webhook handler must update database on subscription events.

---

## 👑 Admin Panel (5 endpoints)

| Status | Method | Endpoint | Purpose | Backend |
|--------|--------|----------|---------|---------|
| [ ] | GET | `/api/admin/users` | List all users (with filters) | Unified |
| [ ] | GET | `/api/admin/stats` | Platform-wide metrics | Unified |
| [ ] | GET | `/api/admin/accounts` | View all broker accounts (all users) | Unified |
| [ ] | POST | `/api/admin/impersonate` | Generate token to view as user | Unified |
| [ ] | GET | `/api/admin/logs` | System-wide logs | Unified |

**Auth**: Requires `role=admin` check.

---

## 📝 Logs & Monitoring (2 endpoints)

| Status | Method | Endpoint | Purpose | Backend |
|--------|--------|----------|---------|---------|
| [ ] | GET | `/api/logs` | User activity logs | Unified |
| [ ] | GET | `/api/webhooks/logs` | *(Duplicate - see Webhooks section)* | Unified |

---

## 🔔 Notifications (2 endpoints)

| Status | Method | Endpoint | Purpose | Backend |
|--------|--------|----------|---------|---------|
| [ ] | GET | `/api/notifications` | Fetch user notifications | Unified |
| [ ] | PATCH | `/api/notifications/{id}/read` | Mark notification as read | Unified |

---

## 🔒 Password & Settings (2 endpoints)

| Status | Method | Endpoint | Purpose | Backend |
|--------|--------|----------|---------|---------|
| [ ] | POST | `/api/user/change_password` | Update password (requires current password) | Unified |
| [ ] | PATCH | `/api/user/profile` | Update user profile (name, email, timezone) | Unified |

---

## 💬 Chatbot Support (1 endpoint) - Optional

| Status | Method | Endpoint | Purpose | Backend |
|--------|--------|----------|---------|---------|
| [ ] | POST | `/api/support/chat` | Send message to AI chatbot | Unified |

---

## ⚠️ Missing or Unclear Features

| Feature | Suggested Endpoint | Priority | Notes |
|---------|-------------------|----------|-------|
| Real-time position updates | `WebSocket /ws/positions` | High | For live P&L without polling |
| EA heartbeat (MT4/MT5) | `GET /api/accounts/{id}/ea_status` | High | Check if EA is connected |
| Fluxeo strategies | `GET /api/strategies`, `POST /api/strategies/activate` | Medium | Pro/Elite plans |
| News calendar lockout | `GET /api/calendar/events` | Low | For news_lockout feature |
| Trade export | `GET /api/export/trades?format=csv` | Low | User may want CSV export |
| Performance benchmarking | `GET /api/analytics/benchmark` | Low | Compare to market average |
| White-label config | `GET/PUT /api/user/whitelabel` | Low | Elite plan feature |

---

## 📊 Implementation Progress

**Total Unique Endpoints**: 67 (excluding duplicates)

### By Category:
- Authentication: 6
- Broker Registration: 10
- API Keys: 6
- Webhooks: 4 (**CRITICAL**)
- Trading & Orders: 6
- Analytics: 3
- Risk Management: 3
- Trading Config: 2
- Billing: 8 (**HIGH PRIORITY**)
- Admin: 5
- Logs: 2
- Notifications: 2
- Settings: 2
- Chatbot: 1 (optional)
- Missing/Unclear: 7

---

## ✅ Minimum Viable Product (MVP) Checklist

**Must have for launch:**

### Phase 1: Core Flow (Week 1)
- [ ] `POST /auth/signup` - User registration
- [ ] `POST /auth/login` - User login
- [ ] `POST /register/tradelocker` - Register broker account
- [ ] `POST /register/projectx` - Register Topstep account
- [ ] `POST /api/unify/v1/webhook/tradelocker` - **Execute trades**
- [ ] `POST /api/unify/v1/webhook/topstep` - **Execute trades**
- [ ] `GET /api/user/brokers` - List connected accounts
- [ ] `GET /api/positions` - View open positions

### Phase 2: Account Management (Week 2)
- [ ] `PATCH /api/accounts/{id}/toggle` - Enable/disable accounts
- [ ] `POST /api/accounts/sync/{id}` - Refresh account data
- [ ] `POST /api/orders/close` - Close positions
- [ ] `DELETE /api/accounts/{id}` - Delete accounts
- [ ] `POST /api/accounts/{id}/regenerate-api-key` - Regenerate API keys

### Phase 3: Billing & Trial (Week 2-3)
- [ ] `GET /api/billing/status` - Check subscription status
- [ ] `GET /api/billing/usage` - Track trial usage (trades count, days left)
- [ ] `POST /api/billing/checkout` - Stripe checkout
- [ ] `POST /api/billing/webhook` - Handle Stripe events

### Phase 4: Risk & Safety (Week 3)
- [ ] `POST /api/user/emergency_stop` - Emergency stop button
- [ ] `GET /api/user/risk_config` - Fetch risk settings
- [ ] `PUT /api/user/risk_config` - Update risk settings
- [ ] Risk enforcement in webhook handler (max daily loss, trading hours, etc.)

### Phase 5: Analytics (Week 4)
- [ ] `GET /api/overview` - Dashboard metrics
- [ ] `GET /api/reports/pnl` - P&L reports
- [ ] `GET /api/webhooks/logs` - Webhook history

---

## 🚨 Critical Path Dependencies

```
User Signup (auth)
    ↓
Connect Broker (register/{broker})
    ↓
Get API Key (auto-generated in register response)
    ↓
Configure TradingView Alert (webhook/{broker})
    ↓
Receive Webhook → Execute Trade
    ↓
View Positions (GET /api/positions)
    ↓
Close Position (POST /api/orders/close)
```

**Bottleneck**: If webhook handler doesn't work, entire system fails.

---

## 🔍 Testing Checklist

### For Each Backend (TradeLocker, Topstep, MT4/MT5):

**Registration**
- [ ] POST `/register/{broker}` returns `api_key` in response
- [ ] API key is stored in database
- [ ] API key format: `{broker}_{account_id_prefix}_{random}`
- [ ] Account status is `active` after registration

**Webhook Execution**
- [ ] POST `/webhook/{broker}` accepts `Authorization: Bearer {api_key}`
- [ ] Invalid API key returns `401 Unauthorized`
- [ ] Disabled account returns `403 Forbidden`
- [ ] Valid request executes trade via broker API
- [ ] Response includes `order_id` and `success: true`
- [ ] Event is logged to database (GET `/api/webhooks/logs` shows it)

**Account Management**
- [ ] GET `/api/user/brokers` returns all user's accounts
- [ ] PATCH `/api/accounts/{id}/toggle` updates `enabled` flag
- [ ] POST `/api/accounts/sync/{id}` updates `last_sync` timestamp
- [ ] DELETE `/api/accounts/{id}` cascades to positions, orders, API keys

**Risk Controls**
- [ ] Webhook rejects trades when `max_daily_loss` exceeded
- [ ] Webhook rejects trades outside `trading_hours` if enabled
- [ ] Webhook rejects trades for symbols in `denied_instruments`
- [ ] Emergency stop closes all positions immediately

**Billing**
- [ ] GET `/api/billing/usage` correctly counts trades
- [ ] Trial blocks trading after 100 trades OR 3 days
- [ ] Stripe webhook updates `user.plan` on subscription events
- [ ] Plan limits enforced (brokers_limit, accounts_per_broker)

---

## 📦 Deliverables for Backend Team

1. **API Endpoints**: All routes from this checklist
2. **Database Schema**: Users, accounts, api_keys, positions, orders, webhooks_log, billing_status
3. **Broker API Integration**: TradeLocker SDK, Topstep API, MT4/MT5 EA communication
4. **Stripe Integration**: Checkout, webhooks, customer portal
5. **Risk Engine**: Middleware to enforce risk controls on webhooks
6. **Logging**: All webhook events, errors, user actions
7. **Admin Panel**: Endpoints for user oversight
8. **Documentation**: OpenAPI spec, Postman collection

---

## 🎯 Success Criteria

**MVP is complete when:**
- [ ] User can signup/login
- [ ] User can connect TradeLocker account and receive API key
- [ ] User can send TradingView alert to webhook
- [ ] Webhook executes trade on TradeLocker account
- [ ] User can view position in UI
- [ ] User can close position via UI
- [ ] Trial tracking works (blocks after 3 days or 100 trades)
- [ ] User can upgrade to paid plan via Stripe
- [ ] Emergency stop closes all positions

---

**Last Updated**: 2025-10-19  
**Total Endpoints**: 67  
**Critical Endpoints**: 15  
**Estimated Implementation Time**: 3-4 weeks (MVP)
