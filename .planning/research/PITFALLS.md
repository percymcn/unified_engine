# Pitfalls Research: v1.1 Risks

**Researched:** 2026-01-20
**Domain:** Stripe Integration, Broker OAuth, SDK Migration, Subscription Gating, Landing Pages
**Confidence:** HIGH for Stripe/OAuth (official docs), MEDIUM for SDK migration (mixed sources)

## Executive Summary

Adding monetization to a working trading platform carries significant risk of breaking existing functionality. The three highest-risk areas are:

1. **Stripe webhook race conditions** - Out-of-order event delivery causing subscription state desync
2. **Broker OAuth token expiration** - Each broker has different token lifetimes and refresh behaviors
3. **Subscription gating scattered logic** - `if (user.plan === 'pro')` checks proliferating throughout codebase

The v1.1 milestone involves integrating with external systems (Stripe, broker OAuth) that operate asynchronously. **The core signal pipeline MUST remain isolated from subscription failures.**

---

## Stripe Integration Pitfalls

### Critical

#### P-STRIPE-01: Webhook Race Conditions

**What goes wrong:** Stripe does not guarantee delivery of events in the order they are generated. A `customer.subscription.updated` event can arrive before `customer.subscription.created`, or `invoice.paid` before `checkout.session.completed`. Your database shows "incomplete" status because that was the last event processed, even though payment succeeded.

**Real-world impact:** Users pay successfully but show as unpaid. They can't access features. Support tickets flood in.

**Warning signs:**
- Intermittent "subscription not found" errors in webhook handler logs
- Users reporting they paid but don't have access
- Database subscription status doesn't match Stripe dashboard

**Prevention strategy:**
1. Treat webhooks as notifications, not state machines
2. On any subscription-related webhook, fetch fresh state from Stripe API before updating local DB
3. Use idempotency keys for all Stripe API calls
4. Implement distributed locking (Redis) when processing webhooks for same customer

**Code pattern to avoid:**
```python
# BAD: Assumes events arrive in order
@webhook_handler("customer.subscription.created")
def handle_created(event):
    db.subscriptions.create(event.data)

@webhook_handler("customer.subscription.updated")
def handle_updated(event):
    db.subscriptions.update(event.data)  # Fails if created hasn't arrived
```

**Correct pattern:**
```python
# GOOD: Fetch fresh state, upsert
@webhook_handler("customer.subscription.*")
async def handle_subscription(event):
    subscription = await stripe.Subscription.retrieve(event.data.object.id)
    await db.subscriptions.upsert(subscription)
```

**Phase mapping:** Stripe Integration phase - webhook handler design

**Severity:** CRITICAL - Will cause paying users to lose access

**Sources:** [Stripe Webhooks Documentation](https://docs.stripe.com/webhooks), [Stripe Subscriptions Webhooks](https://docs.stripe.com/billing/subscriptions/webhooks)

---

#### P-STRIPE-02: Test/Live Mode Secret Mismatch

**What goes wrong:** Using test mode webhook signing secret (whsec_...) in production while Stripe sends live mode events. Signature verification fails on every request even though code is correct.

**Real-world impact:** All webhooks rejected. No subscription updates. Users upgrade but system doesn't know.

**Warning signs:**
- "Webhook signature verification failed" errors in production only
- Works perfectly in test mode
- Stripe dashboard shows webhooks being sent but failing

**Prevention strategy:**
1. Use separate environment variables: `STRIPE_WEBHOOK_SECRET_TEST`, `STRIPE_WEBHOOK_SECRET_LIVE`
2. Validate `livemode` property in webhook payload matches expected environment
3. Set up both test AND live webhook endpoints in Stripe dashboard
4. Add deployment checklist item to verify webhook secrets

**Phase mapping:** Stripe Integration phase - environment configuration

**Severity:** CRITICAL - Complete monetization failure in production

**Sources:** [Stripe Go-Live Checklist](https://docs.stripe.com/get-started/checklist/go-live), [Debugging Stripe Webhook Errors](https://dev.to/nerdincode/debugging-stripe-webhook-signature-verification-errors-in-production-1h7c)

---

#### P-STRIPE-03: Raw Body Manipulation

**What goes wrong:** Framework (FastAPI, Express) parses the request body before your webhook handler sees it. Stripe signature verification requires the raw, unmodified body. Any parsing breaks verification.

**Real-world impact:** All webhook signature verifications fail. Looks like "signature failed" error but actual cause is body modification.

**Warning signs:**
- Signature verification works with Stripe CLI but fails in production
- Adding logging or middleware breaks webhooks
- Works after disabling JSON parsing middleware

**Prevention strategy:**
```python
# FastAPI: Get raw body BEFORE any JSON parsing
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    raw_body = await request.body()  # Raw bytes
    sig_header = request.headers.get("stripe-signature")
    event = stripe.Webhook.construct_event(raw_body, sig_header, webhook_secret)
```

**Phase mapping:** Stripe Integration phase - webhook endpoint implementation

**Severity:** CRITICAL - Prevents all webhook processing

**Sources:** [Stripe Webhook Documentation](https://docs.stripe.com/webhooks)

---

### High

#### P-STRIPE-04: 72-Hour Invoice Finalization Delay

**What goes wrong:** If Stripe doesn't receive a successful response (2xx) to `invoice.created` webhook, it delays finalizing ALL invoices with automatic collection for up to 72 hours.

**Real-world impact:** Customers can't be billed for 3 days. Revenue delayed. Subscription activations stalled.

**Warning signs:**
- `invoice.created` webhook returning errors or timing out
- Invoices stuck in "draft" status
- Subscription activations delayed by days

**Prevention strategy:**
1. `invoice.created` handler must return 200 quickly (async queue processing)
2. Monitor webhook response times
3. Set up alerting for webhook failures
4. Don't do heavy processing synchronously in webhook handlers

**Phase mapping:** Stripe Integration phase - webhook handler architecture

**Severity:** HIGH - Delays all billing operations

**Sources:** [Stripe Subscriptions Webhooks](https://docs.stripe.com/billing/subscriptions/webhooks)

---

#### P-STRIPE-05: Idempotency Key Caching Gotcha

**What goes wrong:** Stripe caches the result of the first request for a given idempotency key, including errors. If you retry with the same key after fixing the error condition, you get the cached error response.

**Example:** Customer has 25 subscriptions (max). You try to create #26, get error, delete some subscriptions, retry with same idempotency key - still get the "max subscriptions" error.

**Prevention strategy:**
1. Generate new idempotency key after any error response
2. Only reuse keys for connection failures / timeouts
3. Use UUIDs that include operation + timestamp

**Phase mapping:** Stripe Integration phase - API client implementation

**Severity:** HIGH - Stuck operations, frustrated users

**Sources:** [Stripe Idempotent Requests](https://docs.stripe.com/api/idempotent_requests)

---

#### P-STRIPE-06: Checkout Session Subscription Timing (2025 API Change)

**What goes wrong:** As of 2025-03-31.basil API version, Checkout Sessions postpone subscription creation until AFTER payment completes. Old code expecting subscription to exist immediately after session creation breaks.

**Warning signs:**
- "Subscription not found" errors immediately after checkout
- Code that worked in 2024 fails in 2025
- Upgrade to stripe-python v18 breaks flows

**Prevention strategy:**
1. Check Stripe API changelog before upgrading SDK
2. Listen for `checkout.session.completed` before accessing subscription
3. Test checkout flow after any Stripe SDK upgrade

**Phase mapping:** Stripe Integration phase - Checkout implementation

**Severity:** HIGH - Breaks new customer onboarding

**Sources:** [Stripe Migration Guide v18](https://github.com/stripe/stripe-node/wiki/Migration-guide-for-v18)

---

### Medium

#### P-STRIPE-07: Synchronous Webhook Processing

**What goes wrong:** Processing webhooks synchronously. Stripe sends many events simultaneously during subscription lifecycle. Server becomes overloaded, requests timeout, webhooks marked as failed.

**Prevention strategy:**
1. Return 200 immediately after signature verification
2. Queue webhook payload for async processing (Redis queue, Celery)
3. Single worker pattern prevents race conditions
4. Implement dead letter queue for failed processing

**Phase mapping:** Stripe Integration phase - infrastructure design

**Severity:** MEDIUM - Scalability issues under load

**Sources:** [Stigg Best Practices](https://www.stigg.io/blog-posts/best-practices-i-wish-we-knew-when-integrating-stripe-webhooks)

---

#### P-STRIPE-08: Missing Trial End Payment Method Check

**What goes wrong:** User starts trial without payment method. Trial ends. `customer.subscription.trial_will_end` fires 3 days before. You don't prompt for payment method. Subscription fails to renew.

**Prevention strategy:**
1. Listen for `customer.subscription.trial_will_end`
2. Check if customer has valid payment method
3. Send email prompting to add payment method
4. Consider requiring payment method at signup (Stripe supports this)

**Phase mapping:** Stripe Integration phase - subscription lifecycle

**Severity:** MEDIUM - Trial conversion failure

**Sources:** [Stripe Subscriptions Webhooks](https://docs.stripe.com/billing/subscriptions/webhooks)

---

## Broker OAuth Pitfalls

### Critical

#### P-OAUTH-01: Token Expiration Variation

**What goes wrong:** Each broker has different token lifetimes. Code assumes "tokens last a while" without checking expiration. Trades fail at 3am when token expired overnight.

**Broker-specific lifetimes:**
| Broker | Access Token | Refresh Token | Notes |
|--------|-------------|---------------|-------|
| Tradovate | ~1 hour | ~7 days | Must refresh before expiry |
| Schwab | ~30 min | 7 days mandatory re-auth | Cannot be automated beyond 7 days |
| IBKR | ~24 hours | N/A - re-auth required daily | Manual login required |
| Questrade | 30 min | 3 days, single-use | Each refresh gives new refresh token |

**Warning signs:**
- Trades fail intermittently, especially overnight/weekends
- 401 errors appearing in broker logs
- Users reporting "disconnected" status

**Prevention strategy:**
1. Store token expiry timestamp in database
2. Proactive refresh: Refresh tokens when >50% lifetime used
3. Implement token refresh before EVERY trade, not on error
4. Alert users when refresh token approaching expiry (Schwab 7-day limit)

**Code pattern:**
```python
async def ensure_valid_token(account):
    if account.token_expires_at < (datetime.now() + timedelta(minutes=5)):
        await refresh_token(account)
    return account.access_token
```

**Phase mapping:** Broker OAuth phase - token management

**Severity:** CRITICAL - Silent trade failures

**Sources:** [Tradier OAuth](https://documentation.tradier.com/brokerage-api/oauth/refresh-token), [Questrade API Security](https://www.questrade.com/api/documentation/security), [Schwab OAuth Guide](https://developer.schwab.com/user-guides/apis-and-apps/oauth-restart-vs-refresh-token)

---

#### P-OAUTH-02: Schwab 7-Day Re-authentication

**What goes wrong:** Schwab Trader API (formerly TD Ameritrade) requires manual re-authentication every 7 days. No automation possible. Users must re-login weekly or trades fail.

**Real-world impact:** Users go on vacation, forget to re-auth, miss week of signals.

**Warning signs:**
- Schwab users reporting weekly disconnections
- Support tickets spike every Monday
- "Session expired" errors exactly 7 days after setup

**Prevention strategy:**
1. Track last authentication timestamp per account
2. Send email reminder at day 5 and day 6
3. Display prominent warning in dashboard when approaching expiry
4. Consider: Is Schwab integration worth the UX friction?

**Phase mapping:** Broker OAuth phase - Schwab-specific handling

**Severity:** CRITICAL - Architectural limitation, no workaround

**Sources:** [Schwab Developer Portal](https://developer.schwab.com/), [TD Ameritrade API Status](https://blog.traderspost.io/article/does-td-ameritrade-have-api)

---

### High

#### P-OAUTH-03: IBKR Daily Re-authentication

**What goes wrong:** Interactive Brokers requires authentication every 24 hours AND does a nightly system reset that disconnects all clients. Algorithmic trading systems that expect persistent connections fail.

**Warning signs:**
- IBKR connections failing daily at the same time
- "Gateway not connected" errors around midnight EST
- Users expecting 24/7 automation disappointed

**Prevention strategy:**
1. Document IBKR limitations clearly to users
2. Implement automatic reconnection after nightly reset
3. Queue signals received during reset, execute after reconnection
4. Consider if IBKR is suitable for signal routing use case

**Phase mapping:** Broker OAuth phase - IBKR-specific handling

**Severity:** HIGH - Daily disruption by design

**Sources:** [Electronic Trading Hub - Brokerages](https://electronictradinghub.com/brokerages-suck-navigating-the-challenges-of-live-algo-trading/)

---

#### P-OAUTH-04: Scope Revocation Cascade

**What goes wrong:** If user revokes a single scope in broker OAuth settings, the entire token may be invalidated. Or, a scope change requires complete re-authorization, invalidating existing tokens.

**Warning signs:**
- Token suddenly invalid without expiry
- "Insufficient permissions" errors
- User reports changing settings in broker account

**Prevention strategy:**
1. Request minimum necessary scopes upfront
2. Check scope validity on each API call
3. Graceful degradation when specific scopes revoked
4. Re-prompt for authorization when scope errors detected

**Phase mapping:** Broker OAuth phase - error handling

**Severity:** HIGH - Unexpected authentication failures

**Sources:** [OAuth 2.0 Token Revocation](https://curity.io/resources/learn/oauth-revoke/)

---

#### P-OAUTH-05: Refresh Token Single-Use (Questrade)

**What goes wrong:** Questrade refresh tokens are single-use. Using a refresh token returns a new refresh token. If you use an old refresh token (due to race condition or retry), you get invalid token error. Both tokens become invalid.

**Warning signs:**
- Intermittent auth failures with Questrade
- "Invalid refresh token" errors after retries
- Works sometimes, fails sometimes

**Prevention strategy:**
1. Atomic token refresh with database lock
2. Never retry refresh with same token
3. Store both old and new refresh tokens, mark old as "used"
4. If refresh fails, require user re-authentication

**Phase mapping:** Broker OAuth phase - Questrade-specific handling

**Severity:** HIGH - Race condition causes auth cascade failure

**Sources:** [Questrade API Documentation](https://www.questrade.com/api)

---

## SDK Migration Pitfalls

### Breaking Changes

#### P-SDK-01: Custom Client to Official SDK Authentication Differences

**What goes wrong:** Your custom broker clients use one authentication method. Official SDKs may use different methods, headers, or flows. Direct replacement breaks authentication.

**Current Tradeflow state:** Custom clients in `/app/brokers/` using direct HTTP calls. Migration to official SDKs requires authentication refactor.

**Specific differences observed:**
- TradeLocker: Custom uses `brand-api-key` header; official SDK uses JWT
- Tradovate: Custom stores credentials in config; OAuth requires redirect flow
- Alpaca: Custom uses `APCA-API-KEY-ID` header; SDK uses `AlpacaTradingClient`

**Prevention strategy:**
1. Run custom and SDK implementations in parallel during migration
2. Compare response formats between custom and SDK
3. Migrate one broker at a time, not all at once
4. Keep rollback path to custom implementation

**Phase mapping:** SDK Migration phase - per-broker implementation

**Severity:** HIGH - Breaking change to working system

---

#### P-SDK-02: Response Format Changes

**What goes wrong:** Custom clients parse responses one way. Official SDKs return different object structures, field names, or types. Code expecting old format crashes.

**Example Alpaca:**
- Old SDK (`alpaca-trade-api`): Returns dicts
- New SDK (`alpaca-py`): Returns typed objects with `_raw` property

**Prevention strategy:**
1. Create adapter layer between SDK and domain
2. Map SDK responses to internal domain objects
3. Unit test response mapping thoroughly
4. Use `_raw` property in alpaca-py if dict format needed

**Phase mapping:** SDK Migration phase - response mapping

**Severity:** HIGH - Runtime errors in production

**Sources:** [Alpaca-py GitHub](https://github.com/alpacahq/alpaca-py)

---

#### P-SDK-03: Multiple Client Classes (Alpaca)

**What goes wrong:** alpaca-py has many client classes (`StockHistoricalDataClient`, `CryptoDataStream`, `TradingClient`, etc.). Developers confuse which client for which operation, instantiate wrong client, get confusing errors.

**Prevention strategy:**
1. Document which Alpaca client class for each operation
2. Create wrapper that exposes only needed operations
3. Integration tests for each broker operation type

**Phase mapping:** SDK Migration phase - Alpaca implementation

**Severity:** MEDIUM - Developer confusion, runtime errors

**Sources:** [Alpaca SDKs Documentation](https://docs.alpaca.markets/docs/sdks-and-tools)

---

### Authentication Differences

#### P-SDK-04: Alpaca Paper vs Live URL

**What goes wrong:** Alpaca defaults to LIVE trading. Forgetting to specify paper URL results in real trades with real money during testing.

**Prevention strategy:**
```python
# ALWAYS explicit about environment
client = TradingClient(
    api_key,
    secret_key,
    paper=True  # EXPLICIT - never rely on default
)
```

**Phase mapping:** SDK Migration phase - environment configuration

**Severity:** CRITICAL - Unintended real trades

**Sources:** [Alpaca API Docs](https://docs.alpaca.markets/)

---

#### P-SDK-05: Rate Limit Differences

**What goes wrong:** Different brokers have vastly different rate limits. Code that works with high-limit broker fails with low-limit broker.

| Broker | Rate Limit |
|--------|-----------|
| Alpaca | 200/minute |
| Tradier | 120/minute |
| IBKR | 50 orders/second |

**Prevention strategy:**
1. Implement per-broker rate limiting
2. Use exponential backoff on 429 responses
3. Queue orders if rate limit approached
4. Log rate limit headers from responses

**Phase mapping:** SDK Migration phase - rate limit handling

**Severity:** MEDIUM - Trade delays or failures

**Sources:** [Alpaca Broker FAQs](https://docs.alpaca.markets/docs/broker-api-faq)

---

## Subscription Gating Pitfalls

### UX Issues

#### P-GATE-01: Scattered Billing Logic

**What goes wrong:** Subscription checks scattered throughout codebase: `if (user.plan === 'pro')` everywhere. Impossible to audit what's gated, test components in isolation, or change pricing tiers.

**Real-world impact:** Changing from "Pro $29/mo" to "Pro $39/mo + Growth $29/mo" requires finding and updating dozens of checks.

**Prevention strategy:**
1. Centralize gating in FeatureGate component/decorator
2. Define feature-to-tier mapping in single config file
3. Components should not know about billing
4. Use entitlement system, not plan string checks

```typescript
// BAD: Scattered checks
if (user.plan === 'pro') {
  showFeature();
}

// GOOD: Centralized gating
<FeatureGate feature="multi-broker">
  <MultiBrokerConfig />
</FeatureGate>
```

**Phase mapping:** Subscription Gating phase - architecture design

**Severity:** HIGH - Technical debt, maintenance nightmare

**Sources:** [Feature Gating SaaS Article](https://dev.to/aniefon_umanah_ac5f21311c/feature-gating-how-we-built-a-freemium-saas-without-duplicating-components-1lo6)

---

#### P-GATE-02: Breaking Existing Users

**What goes wrong:** Adding subscription gating to features that existing users already use. Without grandfathering, loyal users suddenly lose access.

**Warning signs:**
- Angry emails from beta users
- "Feature I was using is now locked" complaints
- Churn spike after monetization launch

**Prevention strategy:**
1. Identify all existing users before launching gating
2. Grandfather existing users on "Legacy" plan
3. Or: Give existing users time-limited Pro access
4. Communicate changes clearly before enforcement

**Phase mapping:** Subscription Gating phase - user migration

**Severity:** HIGH - User trust destruction

---

### Race Conditions

#### P-GATE-03: Subscription State Cache Staleness

**What goes wrong:** User upgrades subscription. Webhook processes. But cached subscription state in app still shows "free". User can't access features until cache expires.

**Warning signs:**
- Users reporting "I just paid but still can't access"
- Features unlock "eventually" (after cache TTL)
- Works after logout/login

**Prevention strategy:**
1. Invalidate subscription cache on any subscription webhook
2. Or: Always fetch fresh from Stripe for feature checks
3. Or: Use Stripe Customer Portal which handles this
4. WebSocket push subscription state updates to connected clients

**Phase mapping:** Subscription Gating phase - cache invalidation

**Severity:** MEDIUM - UX frustration after payment

---

#### P-GATE-04: Mid-Trade Subscription Expiry

**What goes wrong:** User's subscription expires exactly during trade execution. Signal received, validated against "pro" plan, execution starts, subscription expires, execution fails or partially completes.

**Specific to Tradeflow:** User has 5 brokers configured (Pro feature). Subscription expires. Signal comes in. Should it execute to all 5? Only 1? None?

**Prevention strategy:**
1. Subscription check at signal receipt, not during execution
2. Once signal accepted, execute regardless of subscription state
3. Grace period: Allow execution for 24 hours after expiry
4. Clear policy: "Signals in flight complete; new signals blocked"

**Phase mapping:** Subscription Gating phase - edge case handling

**Severity:** MEDIUM - Partial trade execution is dangerous

---

## Landing Page Pitfalls

### Conversion Killers

#### P-LANDING-01: Buzzword-Stuffed Copy

**What goes wrong:** Landing page filled with "AI-powered", "seamless", "revolutionary" without specific value. 95% of B2B landing pages suffer this. Zero differentiation, zero conversions.

**Warning signs:**
- High traffic, low signups
- Users can't explain what product does
- Copy sounds like every competitor

**Prevention strategy:**
1. Lead with specific problem: "Miss a signal, miss the trade"
2. Quantify value: "Execute TradingView alerts in <500ms"
3. Show, don't tell: Actual product screenshots, not stock photos
4. Social proof: Specific user testimonials with results

**Phase mapping:** Landing Page phase - copywriting

**Severity:** HIGH - Wasted marketing spend

**Sources:** [SaaS Landing Page Best Practices](https://www.grafit.agency/blog/saas-landing-page-best-practices), [B2B Landing Page Mistakes](https://www.exitfive.com/articles/8-reasons-your-b2b-landing-pages-arent-converting)

---

#### P-LANDING-02: Multiple CTAs Killing Conversions

**What goes wrong:** Landing page has "Start Free Trial", "Book Demo", "Contact Sales", "Download Whitepaper". User confused, takes no action. Adding more CTAs can decrease conversions by 266%.

**Prevention strategy:**
1. Single primary CTA: "Start Free Trial"
2. One secondary CTA max: "See Pricing"
3. Remove all other actions from landing page
4. A/B test CTA copy, not CTA count

**Phase mapping:** Landing Page phase - CTA design

**Severity:** HIGH - Conversion rate destruction

**Sources:** [Landing Page Mistakes 2025](https://moosend.com/blog/landing-page-mistakes/)

---

### Technical Issues

#### P-LANDING-03: Mobile Performance

**What goes wrong:** Landing page designed for desktop, force-fit to mobile. Heavy images, long load times on mobile networks. 50%+ of traffic is mobile, but page loads in 8 seconds.

**Warning signs:**
- High mobile bounce rate in analytics
- PageSpeed Insights mobile score <50
- Users complaining about slow page

**Prevention strategy:**
1. Mobile-first design, not desktop-down
2. Target <3 second load time on 3G
3. Lazy load images below fold
4. Use WebP/AVIF image formats
5. Test on real mobile devices, not just DevTools

**Phase mapping:** Landing Page phase - performance optimization

**Severity:** HIGH - Losing half your potential users

**Sources:** [Webstacks SaaS Conversions](https://www.webstacks.com/blog/website-conversions-for-saas-businesses)

---

#### P-LANDING-04: Homepage as Landing Page

**What goes wrong:** Driving paid traffic to homepage instead of dedicated landing page. Homepage has navigation, blog links, about page - a hundred ways to leave without converting.

**Prevention strategy:**
1. Create dedicated `/signup` landing page
2. Remove navigation from conversion pages
3. Match ad copy to landing page copy
4. Track conversions per traffic source

**Phase mapping:** Landing Page phase - page architecture

**Severity:** MEDIUM - Wasted ad spend

**Sources:** [B2B Landing Page Mistakes](https://www.exitfive.com/articles/8-reasons-your-b2b-landing-pages-arent-converting)

---

#### P-LANDING-05: No Interactive Demo

**What goes wrong:** Static screenshots feel outdated in 2025. Prospects expect to try product before signup. No demo = no differentiation from competitors.

**Prevention strategy:**
1. Embed interactive product tour on landing page
2. Show actual dashboard with demo data
3. Let users configure a sample signal routing rule
4. Video demo at minimum

**Phase mapping:** Landing Page phase - demo experience

**Severity:** MEDIUM - Lower conversion vs competitors

**Sources:** [KlientBoost SaaS Landing Pages](https://www.klientboost.com/landing-pages/saas-landing-page/)

---

## Prevention Checklist

### Stripe Integration Phase

- [ ] Design webhook handlers to fetch fresh state from Stripe, not trust event order
- [ ] Implement idempotency key generation strategy (new key after errors)
- [ ] Configure separate webhook secrets for test/live environments
- [ ] Set up webhook endpoint to receive raw body before JSON parsing
- [ ] Implement async webhook processing with queue (return 200 immediately)
- [ ] Add monitoring for webhook response times (<5 seconds)
- [ ] Handle `invoice.created` to prevent 72-hour finalization delay
- [ ] Implement `trial_will_end` handler for payment method check
- [ ] Review Stripe 2025-03-31 API changelog before SDK upgrade
- [ ] Test complete checkout flow in both test and live modes

### Broker OAuth Phase

- [ ] Document token lifetimes for each broker in code comments
- [ ] Implement proactive token refresh (before expiry, not on error)
- [ ] Add Schwab 7-day re-auth reminder system
- [ ] Handle IBKR daily reset with automatic reconnection
- [ ] Implement atomic token refresh with database locking
- [ ] Store token expiration timestamp, not just token value
- [ ] Create per-broker error handling for auth failures
- [ ] Alert users when refresh tokens approaching expiry

### SDK Migration Phase

- [ ] Run custom and SDK implementations in parallel during migration
- [ ] Migrate one broker at a time with rollback capability
- [ ] Create adapter layer between SDK and domain objects
- [ ] Unit test response mapping for each broker SDK
- [ ] Explicitly specify paper vs live environment (never rely on defaults)
- [ ] Implement per-broker rate limiting
- [ ] Document which SDK client class for each operation type
- [ ] Integration test each broker after SDK migration

### Subscription Gating Phase

- [ ] Design centralized FeatureGate component/decorator
- [ ] Create feature-to-tier mapping configuration
- [ ] Identify existing users for grandfathering
- [ ] Plan grace period policy for expired subscriptions
- [ ] Implement cache invalidation on subscription webhooks
- [ ] Define policy for in-flight signals during subscription changes
- [ ] Ensure signal pipeline isolated from subscription failures
- [ ] Test upgrade/downgrade flows end-to-end

### Landing Page Phase

- [ ] Write specific, benefit-focused copy (not buzzwords)
- [ ] Single primary CTA per page
- [ ] Target <3 second mobile load time
- [ ] Create dedicated landing page separate from homepage
- [ ] Include interactive demo or video walkthrough
- [ ] Mobile-first responsive design
- [ ] Set up conversion tracking per traffic source
- [ ] A/B test headline and CTA copy

---

## Sources

### Primary (HIGH confidence)
- [Stripe Webhooks Documentation](https://docs.stripe.com/webhooks)
- [Stripe Subscriptions Webhooks](https://docs.stripe.com/billing/subscriptions/webhooks)
- [Stripe Idempotent Requests](https://docs.stripe.com/api/idempotent_requests)
- [Stripe Go-Live Checklist](https://docs.stripe.com/get-started/checklist/go-live)
- [Stripe Migration Guide v18](https://github.com/stripe/stripe-node/wiki/Migration-guide-for-v18)
- [Alpaca-py GitHub](https://github.com/alpacahq/alpaca-py)
- [Alpaca SDKs Documentation](https://docs.alpaca.markets/docs/sdks-and-tools)
- [Schwab Developer Portal](https://developer.schwab.com/)

### Secondary (MEDIUM confidence)
- [Debugging Stripe Webhook Errors](https://dev.to/nerdincode/debugging-stripe-webhook-signature-verification-errors-in-production-1h7c)
- [Electronic Trading Hub - Brokerages](https://electronictradinghub.com/brokerages-suck-navigating-the-challenges-of-live-algo-trading/)
- [Questrade API Documentation](https://www.questrade.com/api)
- [OAuth 2.0 Token Revocation](https://curity.io/resources/learn/oauth-revoke/)
- [Feature Gating SaaS Article](https://dev.to/aniefon_umanah_ac5f21311c/feature-gating-how-we-built-a-freemium-saas-without-duplicating-components-1lo6)
- [SaaS Landing Page Best Practices](https://www.grafit.agency/blog/saas-landing-page-best-practices)
- [B2B Landing Page Mistakes](https://www.exitfive.com/articles/8-reasons-your-b2b-landing-pages-arent-converting)

### Tertiary (LOW confidence - needs validation)
- [TD Ameritrade API Status](https://blog.traderspost.io/article/does-td-ameritrade-have-api) - verify current Schwab API state
- [Stigg Best Practices](https://www.stigg.io/blog-posts/best-practices-i-wish-we-knew-when-integrating-stripe-webhooks) - unable to fetch, title-based reference

---

## Metadata

**Confidence breakdown:**
- Stripe pitfalls: HIGH - Official Stripe documentation extensively consulted
- OAuth pitfalls: MEDIUM-HIGH - Mix of official docs and developer experience reports
- SDK migration: MEDIUM - Based on SDK documentation and community reports
- Subscription gating: MEDIUM - General SaaS patterns, not trading-specific
- Landing page: MEDIUM - Marketing best practices, not technical verification

**Research date:** 2026-01-20
**Valid until:** 60 days for Stripe/OAuth (APIs stable), 30 days for landing page best practices
