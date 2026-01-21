# Research Summary: v1.1 Production Ready with Monetization

**Researched:** 2026-01-21
**Domain:** Trading SaaS + Stripe Billing + Official Broker SDKs
**Milestone:** v1.1 (subsequent to shipped v1.0)

## Executive Summary

v1.1 adds Stripe subscription billing and migrates from custom broker implementations to official SDKs. The existing hexagonal architecture provides clean integration points: new `PaymentPort` for Stripe, updated broker adapters behind existing `BrokerPort`.

**Critical findings:**

1. **Stripe integration is straightforward** — Official Python SDK (14.2.0) and Stripe.js (8.6.1) provide everything needed. Webhook handling is the main complexity.

2. **4 of 5 brokers have official SDKs** — TradeLocker (0.56.2), ProjectX (3.5.9), MetaAPI (29.1.1) all have official Python SDKs. Only Tradovate requires custom OAuth implementation.

3. **Subscription gating belongs in application layer** — Domain defines `SubscriptionTier` on User entity; enforcement happens in use cases, not domain logic.

4. **Webhook race conditions are the #1 Stripe pitfall** — Events arrive out of order. Must treat webhooks as notifications and fetch fresh state from Stripe API.

5. **Each broker has different auth** — TradeLocker (JWT), Tradovate (OAuth 2.0), ProjectX (API key), MetaAPI (token). No unified pattern.

## Key Stack Additions

| Package | Version | Purpose |
|---------|---------|---------|
| stripe (Python) | 14.2.0 | Billing API |
| @stripe/stripe-js | 8.6.1 | Frontend |
| tradelocker | 0.56.2 | TradeLocker SDK |
| project-x-py | 3.5.9 | TopStep/ProjectX SDK |
| metaapi-cloud-sdk | 29.1.1 | MT4/MT5 via MetaAPI |

## Feature Categories

| Category | Table Stakes | Differentiators |
|----------|--------------|-----------------|
| Billing | Pricing page, checkout, portal | Trial period, usage metrics |
| Broker Auth | Connection status, credential input | OAuth flows, token refresh |
| Settings | Timezone, password change | Position sizing defaults |
| Dashboard | Signal status, broker health | Webhook debugging |

## Architecture Integration

```
┌──────────────────────────────────────────────────────────────┐
│                       FRONTEND                                │
│  Next.js 14 with Route Groups                                │
│  ├── (marketing)/ → Landing, Pricing                         │
│  └── (dashboard)/ → Protected app                            │
│      ├── /auth/tradovate/callback                            │
│      └── /auth/callback                                       │
└───────────────────────┬──────────────────────────────────────┘
                        │ BFF Pattern
┌───────────────────────▼──────────────────────────────────────┐
│                    APPLICATION LAYER                          │
│  ├── ManageSubscriptionUseCase (Stripe events → User state)  │
│  ├── LinkBrokerAccountUseCase (OAuth callback → credentials) │
│  └── FeatureGate (subscription tier → feature access)        │
└───────────────────────┬──────────────────────────────────────┘
                        │ Ports
┌───────────────────────▼──────────────────────────────────────┐
│                  INFRASTRUCTURE LAYER                         │
│  ├── StripeAdapter (implements PaymentPort)                  │
│  ├── TradeLockerAdapter → tradelocker SDK                    │
│  ├── TopStepAdapter → project-x-py SDK                       │
│  ├── MetaApiAdapter → metaapi-cloud-sdk                      │
│  └── TradovateAdapter → custom OAuth 2.0                     │
└──────────────────────────────────────────────────────────────┘
```

## Critical Pitfalls to Avoid

| Pitfall | Severity | Prevention |
|---------|----------|------------|
| Stripe webhook race conditions | CRITICAL | Fetch fresh state on every event |
| Test/Live key mismatch | CRITICAL | Verify webhook secret matches environment |
| Tradovate token expiry | HIGH | 1-hour limit, proactive renewal required |
| Scattered subscription checks | HIGH | Centralized FeatureGate component |
| Existing user lockout | HIGH | Grandfather existing users on billing launch |

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| Stripe integration | HIGH | Official SDK, comprehensive docs |
| TradeLocker SDK | HIGH | Official, PyPI verified |
| ProjectX SDK | HIGH | Official, PyPI verified |
| MetaAPI SDK | HIGH | Official, PyPI verified |
| Tradovate OAuth | MEDIUM | No official SDK, community patterns |
| Landing page conversion | LOW | Marketing best practices, needs A/B testing |

---

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Critical Fixes & Infrastructure
**Rationale:** Fix broken functionality before adding features. Users can't test new features if basics don't work.
- Fix desktop sidebar, WebSocket, webhook URLs, dashboard data
- Configure public URLs (tradeflow.fluxeo.net)
- Bind backend to LAN IP
- **Addresses:** All "Critical Fixes" requirements
- **Avoids:** Users abandoning due to broken UI

### Phase 2: Branding
**Rationale:** Rename before marketing launch to avoid confusion.
- Rename "Unified Engine" → "Tradeflow" everywhere
- Update UI text, API responses, docs
- **Simple scope:** Low risk, quick win

### Phase 3: Stripe Foundation
**Rationale:** Must have billing infrastructure before landing page.
- Create `PaymentPort` and `StripeAdapter`
- Implement webhook handler with idempotency
- Add `stripe_customer_id` to User model
- **Addresses:** Billing infrastructure
- **Avoids:** Webhook race conditions (handle fresh state fetch)

### Phase 4: Landing Page
**Rationale:** Needs Stripe products configured first.
- Marketing landing page at "/"
- Pricing comparison table
- Call-to-action to signup
- **Addresses:** Marketing landing page requirement
- **Depends on:** Phase 3 (Stripe products exist)

### Phase 5: Subscription Gating
**Rationale:** Gate features after landing page so conversion flow works.
- FeatureGate component (centralized)
- Middleware for subscription status
- Checkout → Trial → Dashboard flow
- **Avoids:** Scattered subscription checks
- **Avoids:** Existing user lockout (grandfather existing)

### Phase 6: Broker SDK Migration
**Rationale:** High risk, do after monetization stabilizes.
- Update TradeLocker adapter to use official SDK
- Update TopStep adapter to use project-x-py
- Update MetaAPI adapter for MT4/MT5
- **Uses:** Official SDKs from STACK.md
- **Avoids:** Breaking existing signal execution

### Phase 7: Tradovate OAuth
**Rationale:** Custom implementation, needs dedicated focus.
- OAuth 2.0 redirect flow
- /auth/tradovate/callback page
- Token storage with Fernet encryption
- Token refresh (1-hour limit)
- **Lower confidence:** MEDIUM (no official SDK)
- **Likely needs:** Deeper research during implementation

### Phase 8: UI Enhancements
**Rationale:** Polish after core functionality complete.
- User Profile page
- Settings page (timezone, position sizing)
- Dashboard improvements
- **Deferred:** Can ship v1.1 without these if needed

### Phase ordering rationale:

1. **Fixes first** — Can't demo or test if sidebar doesn't click
2. **Branding second** — Clean slate before marketing
3. **Billing before landing** — Need Stripe products to show pricing
4. **Landing before gating** — Need somewhere to convert users
5. **Broker SDKs late** — High risk, existing functionality works
6. **OAuth last among brokers** — Lowest confidence, needs most research
7. **UI polish at end** — Nice-to-have, not blocking monetization

### Research flags for phases:

- **Phase 3 (Stripe):** Standard patterns, research complete
- **Phase 5 (Gating):** May need UX research for trial flow
- **Phase 7 (Tradovate):** NEEDS deeper research (no official SDK, conflicting community reports)
- **Phase 6 (Broker SDKs):** Research complete, but test each migration carefully

---

## Open Questions

1. **TopStep API pricing ($29/mo)** — Should Tradeflow absorb or pass through?
2. **MetaAPI quote limits** — Free tier: 1 tick/2.5s. Sufficient for signal routing?
3. **Existing user migration** — How to grandfather v1.0 users on billing launch?
4. **Tradovate token refresh** — Community reports conflicting info. Test actual behavior.

---

## Files in This Research

| File | Purpose |
|------|---------|
| STACK.md | SDKs, versions, integration patterns |
| FEATURES.md | Table stakes, differentiators, complexity |
| ARCHITECTURE.md | Component boundaries, data flow, build order |
| PITFALLS.md | Common mistakes, prevention strategies |
| SUMMARY.md | This file — executive summary + roadmap implications |
