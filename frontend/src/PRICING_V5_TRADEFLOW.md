# TradeFlow by Fluxeo - Pricing & Plan Structure

## 🎯 Plan Tiers

### Starter - $20/month
**Perfect for individual traders getting started**

**Features:**
- ✅ Connect 1 broker (TradeLocker/ProjectX/MT4/MT5)
- ✅ BYO (Bring Your Own) strategy
- ✅ TradingView webhooks
- ✅ Basic risk controls
- ✅ Email support
- ✅ Order management
- ✅ Position monitoring

**Limits:**
- Brokers: 1
- Fluxeo Strategies: 0 (BYO only)
- Webhooks: 1

**Trial:** 3 days or 100 trades (whichever comes first)

---

### Pro - $40/month ⭐ Most Popular
**Best for active traders wanting premium strategies**

**Features:**
- ✅ Connect 2 brokers
- ✅ 1 Fluxeo strategy/indicator access
- ✅ Priority execution
- ✅ Advanced risk controls
- ✅ Unlimited TradingView webhooks
- ✅ Priority support
- ✅ Real-time notifications
- ✅ Risk heatmap
- ✅ Equity curve chart

**Limits:**
- Brokers: 2
- Fluxeo Strategies: 1
- Webhooks: Unlimited

**Trial:** 3 days or 100 trades (whichever comes first)

---

### Elite - $60/month 🚀
**Premium for professionals needing custom solutions**

**Features:**
- ✅ Connect 3 brokers
- ✅ Up to 3 Fluxeo strategies/indicators
- ✅ Custom build service
- ✅ Advanced risk tools
- ✅ Full API access
- ✅ Priority execution
- ✅ Dedicated support
- ✅ Custom integrations
- ✅ Multi-account management
- ✅ Advanced analytics
- ✅ Daily drawdown tracking

**Limits:**
- Brokers: 3
- Fluxeo Strategies: 3
- Webhooks: Unlimited
- API: Full access

**Trial:** 3 days or 100 trades (whichever comes first)

---

## 📊 Trial System

**All plans include the same trial:**
- **3 days OR 100 trades** (whichever comes first)
- Full access to plan features during trial
- No credit card required to start
- Auto-converts to paid after trial if payment method added
- No charges during trial period

**Trial Counter Logic:**
- Starts on account registration
- Tracks: `trial_start_date` + `trial_trades_count`
- Expires when: `NOW() - trial_start_date > 3 days` OR `trial_trades_count >= 100`
- Warning shown at 80% of either limit (2.4 days or 80 trades)

---

## 💳 Payment & Billing

**Accepted Payment Methods:**
- Credit/Debit Cards (Visa, Mastercard, Amex)
- Processed securely via Stripe

**Billing Cycle:**
- Monthly subscriptions
- Billed on the same day each month
- Pro-rated upgrades/downgrades

**Cancellation:**
- Cancel anytime from billing portal
- Access continues until end of billing period
- No refunds for partial months

---

## 🔄 Plan Comparison Table

| Feature | Starter | Pro | Elite |
|---------|---------|-----|-------|
| **Price/Month** | $20 | $40 | $60 |
| **Brokers** | 1 | 2 | 3 |
| **Fluxeo Strategies** | 0 (BYO) | 1 | 3 |
| **TradingView Webhooks** | 1 | Unlimited | Unlimited |
| **Risk Controls** | Basic | Advanced | Advanced |
| **Priority Execution** | ❌ | ✅ | ✅ |
| **API Access** | ❌ | ❌ | ✅ Full |
| **Custom Builds** | ❌ | ❌ | ✅ |
| **Support** | Email | Priority | Dedicated |
| **Risk Heatmap** | ❌ | ✅ | ✅ |
| **Equity Curve** | ❌ | ✅ | ✅ |
| **Daily Drawdown** | ❌ | ❌ | ✅ |
| **Trial** | 3d/100 trades | 3d/100 trades | 3d/100 trades |

---

## 📈 Revenue Projections

**Monthly Recurring Revenue (MRR) Model:**

Assuming 1,000 active users:
- Starter (40%): 400 users × $20 = $8,000/mo
- Pro (45%): 450 users × $40 = $18,000/mo
- Elite (15%): 150 users × $60 = $9,000/mo

**Total MRR: $35,000**
**Total ARR: $420,000**

**Conversion Rate Targets:**
- Trial → Starter: 20%
- Starter → Pro: 30% (after 2 months)
- Pro → Elite: 15% (after 3 months)

**Churn Target:** < 5% monthly

---

## 🎁 Fluxeo Strategies/Indicators

**What are Fluxeo Strategies?**
- Proprietary trading algorithms developed by Fluxeo
- Pre-built TradingView Pine scripts
- Optimized for multi-broker execution
- Includes: Entry/Exit signals, SL/TP management, position sizing

**Strategy Tiers:**
- **Pro Plan (1 strategy):** Choose from 3 core strategies
  - Trend Following Suite
  - Mean Reversion System
  - Breakout Scanner

- **Elite Plan (3 strategies):** All Pro strategies + advanced:
  - Multi-Timeframe Confluence
  - Smart Money Concepts
  - Volume Profile Analysis
  - **PLUS:** Custom strategy building service

**Custom Build Service (Elite Only):**
- 1-on-1 consultation with Fluxeo team
- Custom strategy development based on your requirements
- Includes: Backtesting, optimization, deployment
- Turnaround: 2-4 weeks
- Unlimited revisions during development

---

## 🔒 Fair Use Policy

**Trade Limits:**
- No hard limits on number of trades per month (post-trial)
- Rate limiting: Max 10 webhook requests per second
- Position limits based on broker constraints

**API Usage (Elite Plan):**
- 5,000 API calls per day
- WebSocket connections: Up to 10 concurrent

**Support Response Times:**
- Starter: 24-48 hours (business days)
- Pro: 4-8 hours (business days)
- Elite: < 2 hours (24/7)

---

## 📞 Contact Sales

For enterprise/institutional needs:
- **Custom broker integrations**
- **White-label solutions**
- **Volume discounts** (50+ users)
- **On-premise deployment**

Contact: sales@fluxeo.com

---

**Last Updated:** 2025-10-14  
**Version:** TradeFlow V5
