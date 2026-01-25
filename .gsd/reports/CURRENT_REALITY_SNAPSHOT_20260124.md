# Current Reality Snapshot - v1.2

**Generated:** 2026-01-24 00:45
**Status:** ✅ All Systems Operational

## Stack Status

| Service       | URL                          | Status |
|--------------|------------------------------|--------|
| Backend API  | http://127.0.0.1:8765        | ✅ UP  |
| Frontend UI  | http://127.0.0.1:3456        | ✅ UP  |
| PostgreSQL   | localhost:5432               | ✅ UP  |

**LAN Access (iPhone/iPad):**
- UI: http://192.168.1.254:3456
- API: http://192.168.1.254:8765

## Database Stats

| Table            | Count |
|-----------------|-------|
| Users           | 15    |
| Trading Accounts| 4     |
| Signals         | 0     |
| Webhook Configs | 0     |

**Accounts by Broker:**
- ProjectX: 4 accounts

## Implemented API Routers (34 total)

### Core
- `auth.py` - Authentication (JWT, login, register)
- `users.py` - User management
- `accounts.py` - Trading account CRUD + discovery
- `health.py` - Health checks

### Trading
- `signals.py` - Signal ingestion and processing
- `trades.py` - Trade history
- `positions.py` - Position tracking
- `strategies.py` - Strategy definitions
- `strategy_execution.py` - Strategy execution

### Webhooks & Routing
- `webhooks.py` - Public webhook endpoints
- `webhooks_secure.py` - Authenticated webhooks
- `webhook_config.py` - Webhook configuration
- `signal_intelligence.py` - Signal analysis

### Broker-Specific
- `projectx_broker.py` - ProjectX/TopStep full SDK features
- `brokers_unified.py` - Unified broker interface
- `broker_contracts.py` - Credential schemas API
- `tradovate_oauth.py` - Tradovate OAuth flow

### Configuration
- `symbol_aliases.py` - Symbol mapping
- `account_groups.py` - Account grouping
- `risk.py` - Risk management
- `credential_router.py` - Credential management

### Billing & Admin
- `billing.py` - Plans and subscriptions
- `subscription.py` - Subscription management
- `stripe_webhooks.py` - Stripe integration
- `trial.py` - Trial management
- `admin.py` - Admin functions

### Other
- `dashboard.py` - Dashboard data
- `analytics.py` - Analytics
- `notifications.py` - Notifications
- `api_keys.py` - API key management
- `oauth.py` - OAuth flows
- `contracts.py` - Contract definitions
- `funnel_router.py` - Funnel routing
- `unified_router.py` - Unified routing

## Broker Executors (6 brokers)

| Broker      | Executor               | SDK Mode | Status      |
|-------------|------------------------|----------|-------------|
| TradeLocker | tradelocker_executor   | SDK only | ✅ Complete |
| ProjectX    | projectx_executor      | SDK      | ✅ Complete |
| Tradovate   | tradovate_executor     | OAuth    | ✅ Complete |
| MT4         | mt4_executor           | MetaAPI  | ✅ Complete |
| MT5         | mt5_executor           | MetaAPI  | ✅ Complete |
| TopStep     | (alias for ProjectX)   | SDK      | ✅ Complete |

## UI Pages (Dashboard)

### Main
- `/dashboard` - Overview dashboard
- `/dashboard/signals` - Signal list
- `/dashboard/trades` - Trade history

### Settings
- `/dashboard/settings/accounts` - Account management
- `/dashboard/settings/accounts/[id]/settings` - Account settings + broker selection
- `/dashboard/settings/webhooks` - Webhook configuration
- `/dashboard/settings/routing` - Signal routing rules
- `/dashboard/settings/groups` - Account groups
- `/dashboard/settings/symbols` - Symbol aliases
- `/dashboard/settings/risk` - Risk settings
- `/dashboard/settings/api-keys` - API keys
- `/dashboard/settings/profile` - User profile
- `/dashboard/settings/preferences` - Preferences
- `/dashboard/settings/billing` - Billing/subscription
- `/dashboard/settings/broker-tools` - Broker-specific tools

### Other
- `/dashboard/upgrade` - Upgrade flow

## Key Endpoints Verified

| Endpoint                      | Method | Auth   | Status |
|------------------------------|--------|--------|--------|
| `/health`                    | GET    | None   | ✅     |
| `/api/v1/brokers/contracts`  | GET    | None   | ✅     |
| `/api/billing/plans`         | GET    | None*  | ✅     |
| `/api/v1/accounts/test-connection` | POST | JWT | ✅ |
| `/api/v1/accounts/{id}/refresh-accounts` | POST | JWT | ✅ |
| `/api/v1/brokers/projectx/*` | *      | JWT    | ✅     |

*Optional auth - works with or without token

## Recent Completions (This Session)

### Bug Fixes
1. **SQLAlchemy Column description** - Removed invalid `description` parameter from Column() definitions
2. **Missing Dict import** - Added `Dict, Any` to accounts.py imports

### Database Schema
- ✅ `webhook_key` column exists
- ✅ `enabled_broker_account_ids` column exists (JSON)
- ✅ `default_broker_account_id` column exists
- ✅ `discovered_accounts_cache` column exists (JSON)

## v1.1 Milestone Complete Features

### TradeLocker
- SDK-only mode (Brand API removed)
- Account discovery
- Broker account selection UI
- Refresh accounts functionality

### ProjectX/TopStep
- Full SDK feature parity
- Platform API routes
- Orderbook, quotes, history
- Technical indicators
- Portfolio metrics
- Risk analysis

### Account Management
- Test & Validate flow
- Discovered accounts selection
- Default account setting
- Per-broker webhook keys

## Known Gaps for v1.2

1. **Webhook Routing** - Multi-user/strategy/account routing not implemented
2. **Account Onboarding UX** - Discovery step needs refinement
3. **Alembic Migrations** - Template file missing, manual SQL used
4. **Observability** - Logging/monitoring limited

## Canonical Ports

| Service  | Port | Enforced By                  |
|----------|------|------------------------------|
| API      | 8765 | local_up_postgres.sh         |
| UI       | 3456 | local_up_postgres.sh         |
| Postgres | 5432 | System PostgreSQL            |

## Files Changed This Session

- `app/models/database_models.py` - Fixed Column() description params
- `app/routers/accounts.py` - Added Dict, Any imports

## Next Steps → v1.2 Requirements

See: Requirements and Roadmap (to be created)
