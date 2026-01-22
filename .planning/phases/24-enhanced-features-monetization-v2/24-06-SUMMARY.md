---
phase: 24-enhanced-features-monetization-v2
plan: 06
subsystem: accounts
tags: [multi-broker, account-selection, signal-routing, sdk]
requires:
  - phase-15 (TradeLocker SDK)
  - phase-16 (Tradovate OAuth)
  - phase-17 (ProjectX SDK)
  - phase-18 (MetaAPI SDK)
provides:
  - Multi-broker account fetching service
  - Account selection endpoints (available, select, sync)
  - Signal routing filtered by selected accounts
affects:
  - 24-07 (Broker Account Selection UI)
tech-stack:
  added: []
  patterns:
    - Multi-broker account aggregation
    - Selection-based signal routing
    - Credential extraction with encryption fallback
key-files:
  created:
    - app/services/account_fetcher_service.py
  modified:
    - app/routers/accounts.py
    - app/services/signal_processor.py
decisions:
  - id: broker-id-formats
    decision: "Handle different broker ID formats dynamically"
    rationale: "TradeLocker (numeric), ProjectX (alphanumeric), Tradovate (numeric), MetaAPI (UUID)"
  - id: selection-storage
    decision: "Use existing is_signal_enabled field for account selection"
    rationale: "TradingAccount model already has is_signal_enabled boolean field"
  - id: routing-modes
    decision: "Three routing modes: specific account, broker type, all selected"
    rationale: "Covers all use cases from single account to broadcast"
metrics:
  duration: 10 minutes
  completed: 2026-01-22
---

# Phase 24 Plan 06: Broker Account Selection Backend Summary

Multi-broker account fetcher service and selection-based signal routing.

## One-liner

Account fetcher service supporting 4 broker types with selection-based signal routing.

## What Was Built

### 1. AccountFetcherService (app/services/account_fetcher_service.py)

Created unified service to fetch available accounts from all supported broker SDKs:

- **BrokerAccountInfo dataclass**: Standardized account info (id, name, type, balance, currency, server, login, broker_type)
- **fetch_all_accounts()**: Routes to broker-specific fetcher based on type
- **fetch_tradelocker_accounts()**: Uses TradeLocker SDK wrapper, falls back to executor
- **fetch_projectx_accounts()**: Uses ProjectX SDK service, detects account types (live/evaluation/express)
- **fetch_tradovate_accounts()**: Uses Tradovate executor with OAuth token support
- **fetch_metaapi_accounts()**: Uses MetaAPI SDK or provisioning API for MT4/MT5

Broker ID format handling:
- TradeLocker: Numeric IDs (e.g., "12345678")
- ProjectX/TopStep: Alphanumeric IDs (e.g., "ABC-12345-XY")
- Tradovate: Numeric IDs (e.g., "987654")
- MetaAPI: UUID format (e.g., "a1b2c3d4-e5f6-7890-abcd-ef1234567890")

### 2. Account Selection Endpoints (app/routers/accounts.py)

Added three new endpoints:

**GET /api/accounts/available/{broker_type}**
- Fetches available accounts from broker SDK
- Cross-references with stored TradingAccounts
- Returns: id, name, type, balance, is_stored, is_selected, stored_account_id

**PUT /api/accounts/{account_id}/select**
- Toggles is_signal_enabled for account
- Request: `{ "selected": boolean }`
- Returns: Updated selection status

**POST /api/accounts/sync-all**
- Re-fetches accounts from all connected brokers
- Updates stored accounts with fresh balance/equity
- Identifies new accounts available on brokers

### 3. Signal Routing with Selection (app/services/signal_processor.py)

Updated signal processor to respect account selection:

**_execute_signal()** - Refactored for multi-account routing:
- Gets target accounts via _get_target_accounts()
- Logs routing decisions with account list
- Executes on all target accounts
- Aggregates results (successful/failed counts)

**_get_target_accounts()** - New method for selection filtering:
- Mode 1: Specific account_id - uses that account if selected
- Mode 2: Broker type - uses all selected accounts of that type
- Mode 3: No filter - uses all selected accounts
- Orders by signal_priority (higher first)
- Logs when skipping non-selected accounts

**_execute_on_account()** - New method for per-account execution:
- Includes deduplication check per account
- Calculates position size per account settings
- Returns detailed result with account_id, account_number

## Commits

| Commit | Description | Files |
|--------|-------------|-------|
| 572d3ad | feat(24-06): add account fetcher service for multi-broker support | app/services/account_fetcher_service.py |
| 8f3d021 | feat(24-06): add account selection endpoints | app/routers/accounts.py |
| 9844d81 | feat(24-06): update signal routing to respect account selection | app/services/signal_processor.py |

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- [x] AccountFetcherService fetches accounts from all 4 broker types (TradeLocker, ProjectX, Tradovate, MetaAPI)
- [x] GET /api/accounts/available/{broker_type} returns account list
- [x] Accounts include: id, name, type, balance (where available)
- [x] PUT /api/accounts/{id}/select toggles selection (is_signal_enabled)
- [x] Selected accounts stored in database (TradingAccount.is_signal_enabled)
- [x] Signal processor only routes to selected accounts (is_signal_enabled=True)
- [x] Different broker ID formats handled correctly

## Technical Notes

1. **Credential Extraction**: Endpoints decrypt stored credentials with graceful fallback for unencrypted values
2. **SDK Fallbacks**: Each broker has executor fallback when SDK not available
3. **Priority Ordering**: Selected accounts ordered by signal_priority (descending) for consistent routing
4. **Deduplication Integration**: Moved deduplication check into per-account execution to support multi-account signals

## Next Phase Readiness

Ready for 24-07 (Broker Account Selection UI):
- All backend endpoints available
- Selection status persisted in database
- Signal routing respects selection
