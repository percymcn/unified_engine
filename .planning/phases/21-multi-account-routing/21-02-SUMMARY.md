---
phase: 21
plan: 02
type: feature
subsystem: signal-routing
tags: [routing, webhooks, multi-account, signals]

dependency-graph:
  requires: [21-01]
  provides: [signal-routing-engine, routing-api, routed-webhook-endpoint]
  affects: [21-03]

tech-stack:
  added: []
  patterns: [strategy-pattern, rule-engine]

key-files:
  created:
    - app/domain/services/routing_service.py
    - alembic/versions/010_add_routing_strategy.py
  modified:
    - app/routers/webhooks.py
    - app/routers/webhook_config.py
    - app/models/database_models.py
    - app/domain/services/signal_service.py
    - app/domain/services/__init__.py

decisions:
  - id: route-strategies
    summary: Four routing strategies (all_accounts, specific_accounts, rules_based, default_only)
    rationale: Covers all use cases from simple single-account to complex conditional routing
  - id: rule-priority
    summary: Higher priority rules evaluated first, all matching rules contribute accounts
    rationale: Allows fine-grained control while supporting multi-account targeting
  - id: fallback-default
    summary: Rules-based routing falls back to default account when no rules match
    rationale: Ensures signals are not lost due to configuration gaps
  - id: webhook-key-routing
    summary: New /signal/{webhook_key} endpoint for routed signal processing
    rationale: Clean URL structure, webhook config identified by key not auth

metrics:
  duration: ~8 minutes
  completed: 2026-01-22
---

# Phase 21 Plan 02: Signal Routing Configuration Summary

Flexible signal routing system allowing users to route TradingView signals to specific accounts, all accounts, or based on conditional rules.

## One-liner

Strategy-based signal routing engine with 4 strategies, rule evaluation, and dedicated webhook endpoint.

## What Was Built

### 1. Routing Engine (routing_service.py)

Core routing logic with four strategies:

- **ALL_ACCOUNTS**: Route signals to all active, signal-enabled accounts
- **SPECIFIC_ACCOUNTS**: Route only to explicitly listed account IDs
- **RULES_BASED**: Evaluate rules against signal data (symbol, action, source)
- **DEFAULT_ONLY**: Route only to the default account

Rule conditions support operators:
- `eq`, `neq`: Equality comparisons
- `contains`, `starts_with`, `ends_with`: String matching
- `in`, `not_in`: List membership
- `gt`, `lt`, `gte`, `lte`: Numeric comparisons
- `regex`: Pattern matching

### 2. Routed Webhook Endpoint

New endpoint: `POST /api/webhooks/signal/{webhook_key}`

Flow:
1. Look up WebhookConfig by webhook_key
2. Get user's active, signal-enabled accounts
3. Build signal data from payload
4. Apply routing rules to determine target accounts
5. Apply symbol/action filters
6. Execute signal on all target accounts
7. Track stats (total/successful/failed)

### 3. Enhanced WebhookConfig Model

New columns:
- `routing_strategy`: Strategy selector (default: "default_only")
- `specific_account_ids`: JSON array for specific_accounts strategy

### 4. Routing API Endpoints

- `GET /{config_id}/routing`: Get current routing config with available accounts
- `PUT /{config_id}/routing`: Update routing strategy and rules
- `POST /{config_id}/routing/test`: Dry-run routing with sample signal data

### 5. Routing-Aware Signal Execution

SignalService updated:
- Check `is_signal_enabled` before routing to account
- Sort accounts by `signal_priority` (higher first)
- Filter inactive/disconnected accounts

## Key Files

| File | Purpose |
|------|---------|
| `app/domain/services/routing_service.py` | RoutingEngine, RoutingConfig, RoutingRule classes |
| `app/routers/webhooks.py` | `/signal/{webhook_key}` endpoint |
| `app/routers/webhook_config.py` | Routing API endpoints |
| `app/models/database_models.py` | routing_strategy, specific_account_ids columns |
| `alembic/versions/010_add_routing_strategy.py` | Database migration |

## Commits

| Hash | Description |
|------|-------------|
| 87768fd | Add RoutingEngine with strategy-based signal routing |
| 0d62735 | Integrate routing engine with webhook processing |
| c76f638 | Add routing strategy to WebhookConfig model |
| f7ce7ee | Add routing-aware signal execution with account filters |
| 002f954 | Add routing rules API endpoints |

## Decisions Made

1. **Four routing strategies**: Covers all use cases from simple to complex
2. **Higher priority rules first**: Clear evaluation order
3. **All matching rules contribute accounts**: Supports multi-account targeting per signal
4. **Fallback to default**: Prevents signal loss when no rules match
5. **Webhook key in URL path**: Clean REST design, no auth header needed for TradingView

## API Usage Examples

### Create webhook with rules-based routing

```bash
curl -X POST http://localhost:8765/api/webhook-configs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Symbol Router",
    "source": "tradingview",
    "routing_strategy": "rules_based",
    "routing_rules": [
      {"condition": {"field": "symbol", "operator": "eq", "value": "US30"}, "target_account_id": 1, "priority": 10},
      {"condition": {"field": "symbol", "operator": "eq", "value": "NAS100"}, "target_account_id": 2, "priority": 10}
    ],
    "default_account_id": 1
  }'
```

### Send signal to routed webhook

```bash
curl -X POST http://localhost:8765/api/webhooks/signal/{webhook_key} \
  -H "Content-Type: application/json" \
  -d '{"ticker": "US30", "action": "buy", "quantity": 1}'
```

### Test routing configuration

```bash
curl -X POST http://localhost:8765/api/webhook-configs/1/routing/test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "US30", "action": "buy"}'
```

## Verification Results

All must-haves verified:

1. RoutingEngine correctly resolves accounts for all 4 strategies
2. Webhook processing uses routing engine
3. Multiple accounts can receive same signal
4. Rules-based routing matches on symbol/action
5. Default fallback works when no rules match

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Phase 21 Plan 03 (Multi-Account UI) can proceed. All backend routing infrastructure is in place:
- Routing engine ready for frontend consumption
- API endpoints documented and tested
- Database schema updated

## Success Criteria

| Criteria | Status |
|----------|--------|
| ACCT-03: Route signals to specific accounts or all accounts | COMPLETE |
