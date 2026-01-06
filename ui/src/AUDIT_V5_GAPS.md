# Empire Trading Hub - V4 to V5 Enterprise Upgrade Audit

## 📊 CURRENT STATE ASSESSMENT

### ✅ IMPLEMENTED (V4)
- [x] Multi-broker UI (TradeLocker, Topstep, TruForex)
- [x] Basic account registration flows
- [x] TradingView webhook templates with API key injection
- [x] SL/TP/Lot size sliders with 0.01 precision
- [x] Risk controls (max daily loss, max trades/day, max open trades)
- [x] Order and position viewing
- [x] API key generation and display
- [x] RBAC (admin/user roles via UserContext)
- [x] Basic logs viewer
- [x] Billing portal UI (Stripe plans)
- [x] Dark theme with #002b36 primary

### ❌ MISSING FOR ENTERPRISE (V5 UPGRADES NEEDED)

## 1️⃣ TRADING & RISK CONTROLS
- [ ] **Broker-specific constraints enforcement**
  - TradeLocker: min 0.01 lots, max 100 lots
  - Topstep: contract-based (1-50 contracts)
  - TruForex: 0.01 lots = 1,000 units
- [ ] **Risk Heatmap Component**
  - Color-coded exposure per broker
  - Symbol-level heat visualization
  - Real-time updates via Supabase
- [ ] **Equity Curve Chart**
  - Historical balance over time
  - Recharts line chart
  - Filter by broker/date range
- [ ] **Daily Drawdown Chart**
  - Max intraday drawdown tracking
  - Alert when approaching limits
- [ ] **Smart Defaults**
  - Auto-populate based on broker selection
  - Conservative initial settings

## 2️⃣ WEBHOOK & TRADINGVIEW
- [ ] **Test Alert Playground**
  - Parse TradingView JSON in real-time
  - Visual order preview with entry/SL/TP
  - Validation before sending
- [ ] **HMAC Signed Webhook URLs**
  - SHA-256 signature generation
  - Per-workspace unique secrets
  - Signature verification UI
- [ ] **Direct API Equivalents**
  - REST API examples for each template
  - cURL/Python/Node.js snippets

## 3️⃣ SUPABASE INTEGRATION
- [ ] **Database Schema**
  ```sql
  - profiles (user_id, name, email, role, plan_tier, created_at)
  - broker_accounts (id, user_id, broker, api_key_hash, credentials_encrypted, status)
  - risk_settings (user_id, broker, sl_pct, tp_pct, max_trades, rr_ratio)
  - orders (id, user_id, broker, symbol, side, qty, price, status, timestamp)
  - positions (id, user_id, broker, symbol, side, qty, entry_price, unrealized_pnl)
  - logs (id, user_id, broker, level, type, message, details, timestamp)
  - webhook_events (id, user_id, source, payload, signature, processed_at)
  - subscriptions (user_id, plan, stripe_id, status, trial_end, next_billing)
  ```
- [ ] **Row-Level Security (RLS) Policies**
  - Users see only their own data
  - Admins bypass RLS for monitoring
- [ ] **Realtime Channels**
  - `positions:user_id` for live P&L
  - `orders:user_id` for order updates
  - `health:system` for status banner
- [ ] **Encrypted Storage**
  - AES-256 for broker credentials
  - Separate key management table
  - Auto-rotation mechanism

## 4️⃣ SECURITY & COMPLIANCE
- [ ] **2FA/TOTP Integration**
  - Supabase Auth + TOTP library
  - QR code generation
  - Backup codes
- [ ] **Audit Trail Table**
  - admin_actions (user_id, action, target, timestamp, ip_address)
  - Immutable log with retention policy
- [ ] **HMAC Webhook Verification**
  - Server-side signature checking
  - Clock skew tolerance (5 min)
  - Nonce store to prevent replay
- [ ] **SOC-2 Prep**
  - 90-day log retention
  - Anomaly detection rules
  - Security event NATS topics

## 5️⃣ RBAC & ADMIN ENHANCEMENTS
- [ ] **Supabase JWT Claims**
  - role: 'admin' | 'user' | 'viewer'
  - plan_tier: 'starter' | 'pro' | 'elite'
- [ ] **Admin Dashboard Enhancements**
  - System-wide metrics (all users aggregated)
  - User impersonation (view-as feature)
  - Bulk operations (suspend, upgrade)
- [ ] **Viewer Role**
  - Read-only access
  - No trading permissions
  - Used for managers/auditors

## 6️⃣ BILLING & MONETIZATION
- [ ] **Plan Tiers**
  - **Starter**: $29/mo (100 trades/mo, 1 broker, basic risk)
  - **Pro**: $79/mo (unlimited trades, 3 brokers, advanced risk)
  - **Elite**: $199/mo (white-label, API access, priority support)
- [ ] **Trial Management**
  - 3-day free trial auto-start
  - Trial countdown badge
  - Auto-downgrade or suspend on expiry
- [ ] **Stripe Webhooks**
  - subscription.created → profiles.plan_tier
  - subscription.updated → NATS event
  - payment_failed → dunning email
- [ ] **Usage Tracking**
  - trades_used_this_month counter
  - Rate limiting per plan
  - Upgrade prompts at 80% usage

## 7️⃣ UI/UX ENHANCEMENTS
- [ ] **Theme Toggle**
  - Light mode support
  - Persist preference to localStorage
  - Update CSS variables dynamically
- [ ] **Health Status Banner**
  - Top-of-page alert bar
  - Green (healthy), Yellow (degraded), Red (down)
  - Live via Supabase Realtime
- [ ] **Real-time Updates**
  - Position P&L ticks live
  - Order status changes without refresh
  - Toast notifications for events
- [ ] **Mobile Responsive**
  - Sidebar collapses to drawer
  - Touch-friendly sliders
  - Simplified chart views
- [ ] **Copy Button Feedback**
  - Animate checkmark on copy
  - Timeout visual confirmation
- [ ] **Empty States**
  - No positions → prompt to connect account
  - No orders → link to webhook setup

## 8️⃣ OBSERVABILITY & MONITORING
- [ ] **/metrics Endpoint**
  ```
  orders_total{broker,side,status}
  rejects_total{reason}
  pnl_unrealized{broker,symbol}
  webhook_latency_ms{broker}
  api_requests_total{endpoint,status}
  ```
- [ ] **NATS Event Map**
  ```
  ai.trade.exec.order → order placed
  ai.trade.exec.reject → order rejected
  ai.risk.blocked.trade → risk limit hit
  ai.user.billing.status → subscription change
  ai.user.key.rotated → API key changed
  ai.ops.health.sweep → health check
  ai.log.error → critical error
  ```
- [ ] **Advanced Log Filters**
  - Correlation ID tracking
  - JSON pretty-print
  - Export to CSV
  - Real-time tail mode

## 9️⃣ API GATEWAY (NEW)
- [ ] **Unified /api/unify/v1/** namespace
  ```
  POST /api/unify/v1/order
  GET  /api/unify/v1/positions
  PUT  /api/unify/v1/risk
  POST /api/unify/v1/webhook/{broker}
  GET  /api/unify/v1/health
  ```
- [ ] **OpenAPI 3.0 Spec**
  - Request/response schemas
  - Authentication (Bearer token)
  - Error codes (4xx, 5xx)
- [ ] **Rate Limiting**
  - Starter: 100 req/min
  - Pro: 500 req/min
  - Elite: 2000 req/min

## 🔟 DEPLOYMENT STACK
- [ ] **Docker Swarm / Kubernetes**
  - Traefik reverse proxy
  - NATS cluster (3 nodes)
  - Redis cache
  - Supabase self-hosted or cloud
- [ ] **CI/CD Pipeline**
  - GitHub Actions
  - Automated tests
  - Blue-green deployments
- [ ] **Backup & DR**
  - Daily DB snapshots
  - Point-in-time recovery
  - Multi-region failover

---

## 📈 MONETIZATION IMPACT ANALYSIS

**Baseline (V4):**
- $49 ARPU
- 15% signup → paid conversion
- $7.35/day per 100 signups

**Projected (V5 with Elite tier):**
- $89 weighted ARPU (tiered pricing)
- 22% conversion (improved onboarding + trial)
- **$19.58/day per 100 signups** (+166% revenue)

**Enterprise Features Driving Upgrade:**
- Risk heatmap → 35% of users upgrade to Pro
- Multi-broker support → 15% to Elite
- 2FA + audit logs → compliance-required customers

---

## ✅ UPGRADE PRIORITY (SPRINT PLAN)

### SPRINT 1 (Week 1-2): Foundation
1. Supabase schema + RLS policies
2. Real-time channels setup
3. Encrypted credential storage
4. HMAC webhook signing

### SPRINT 2 (Week 3-4): Trading & Risk
5. Risk heatmap component
6. Equity curve chart
7. Broker constraint enforcement
8. Test Alert playground

### SPRINT 3 (Week 5-6): Security & Billing
9. 2FA/TOTP integration
10. Stripe webhook handlers
11. Audit trail logging
12. Admin dashboard enhancements

### SPRINT 4 (Week 7-8): UX & Observability
13. Theme toggle
14. Health status banner
15. /metrics endpoint
16. Mobile responsive polish

---

**Next Steps:**
Generate v5 JSON export, Supabase schema SQL, OpenAPI spec, and deployment manifests.
