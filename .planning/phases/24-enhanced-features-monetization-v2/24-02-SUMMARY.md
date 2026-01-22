---
phase: 24
plan: 02
type: execute
status: complete
subsystem: billing
tags: [stripe, pricing, tiers, monetization]

dependency-graph:
  requires:
    - Phase 13 (Stripe integration foundation)
  provides:
    - 4-tier pricing structure backend and frontend
    - Tier-based broker limits (1, 2, 3, 4)
    - Checkout with tier selection
    - Webhook tier processing
  affects:
    - 24-04 (Trial UI & Upgrade Prompts)
    - 24-05 (4-Tier Pricing UI)

tech-stack:
  added: []
  patterns:
    - Tiered pricing with broker limits
    - Metadata-driven webhook processing
    - Legacy compatibility mapping

key-files:
  created:
    - ui-next/src/lib/pricing.ts
  modified:
    - app/services/stripe_service.py
    - app/routers/billing.py
    - app/routers/stripe_webhooks.py
    - app/core/billing.py

decisions:
  - tier_id: "4-tier model uses tier_1, tier_2, tier_3, tier_4 identifiers"
  - legacy_mapping: "Legacy plan='pro' maps to tier_3 for backward compatibility"
  - broker_limits: "Paid tiers unlock 1, 2, 3, 4 brokers respectively"
  - error_code: "Broker limit exceeded returns 402 Payment Required"

metrics:
  duration: "11 minutes"
  completed: "2026-01-22"
---

# Phase 24 Plan 02: 4-Tier Pricing Backend Summary

4-tier pricing structure with tier-based broker limits and Stripe integration.

## Commits

| Hash    | Type | Description                                          |
| ------- | ---- | ---------------------------------------------------- |
| 5bfd6a9 | feat | Add frontend pricing constants (pricing.ts)          |
| 2b3c768 | feat | Update billing endpoints for 4-tier checkout         |
| bc1abcc | feat | Update webhook and broker gating for 4-tier pricing  |

## What Was Built

### Task 1: 4-Tier Pricing Structure

**Backend (`app/services/stripe_service.py`):**
- `PRICING_TIERS` dict with tier_1, tier_2, tier_3, tier_4
- Each tier has: name, price (cents), brokers limit, stripe_price_id, features
- Pricing: $19.99, $39.99, $69.99, $129.99 per month
- Broker limits: 1, 2, 3, 4 respectively
- Helper functions: `get_tier_by_broker_count()`, `get_broker_limit()`, `get_all_tiers()`

**Frontend (`ui-next/src/lib/pricing.ts`):**
- Matching `PRICING_TIERS` structure
- Helper functions: `formatPrice()`, `getTierFeatures()`, `getBrokerLimit()`
- Tier comparison: `isTierHigher()`, `getUpgradeTiers()`
- 235 lines with full TypeScript types

### Task 2: Billing Endpoints

**POST `/api/billing/checkout`:**
- Accepts `tier_id` parameter (tier_1, tier_2, tier_3, tier_4)
- Legacy `plan="pro"` mapped to tier_3
- Validates tier exists in PRICING_TIERS
- Includes tier_id in checkout metadata for webhook

**GET `/api/billing/plans`:**
- Returns all 5 tiers (free + 4 paid)
- Includes name, price, price_display, features, broker_limit
- Returns current user's tier for comparison

**GET `/api/billing/status`:**
- Returns tier, tier_name, broker_limit, brokers_used
- Calculates brokers_used from active accounts

### Task 3: Webhook and Broker Gating

**Stripe Webhook Handler:**
- `checkout.session.completed`: Reads tier_id from metadata
- `subscription.updated`: Preserves tier from metadata
- `subscription.deleted`: Sets tier back to "free"
- Legacy "pro" in metadata mapped to tier_3

**Broker Gating (`app/core/billing.py`):**
- TIER_LIMITS updated with tier_1=1, tier_2=2, tier_3=3, tier_4=4
- `require_broker_slot()` returns 402 Payment Required
- Error message includes tier name and upgrade suggestion

## Verification Results

- [x] PRICING_TIERS has all 4 tiers with correct prices
- [x] POST /api/billing/checkout accepts tier_id parameter
- [x] GET /api/billing/plans returns all 4 tiers
- [x] Webhook correctly sets subscription_tier from metadata
- [x] Broker limit enforced: tier_1=1, tier_2=2, tier_3=3, tier_4=4
- [x] Free tier limited to 1 broker
- [x] Frontend pricing.ts matches backend tiers (235 lines)

## Deviations from Plan

None - plan executed exactly as written.

## Files Changed

| File                             | Changes                                    |
| -------------------------------- | ------------------------------------------ |
| app/services/stripe_service.py   | Added PRICING_TIERS, helper functions      |
| app/routers/billing.py           | Updated checkout, plans, status endpoints  |
| app/routers/stripe_webhooks.py   | Tier-aware webhook processing              |
| app/core/billing.py              | 4-tier TIER_LIMITS, 402 error response     |
| ui-next/src/lib/pricing.ts       | New file with pricing constants            |

## Next Phase Readiness

Ready for:
- 24-04: Trial UI can use pricing.ts for tier display
- 24-05: 4-Tier Pricing UI has all backend APIs ready
- Frontend can call /api/billing/checkout with tier_id

Dependencies satisfied:
- Checkout creates correct Stripe session for selected tier
- Webhook updates user subscription_tier correctly
- Broker limits enforced by tier
