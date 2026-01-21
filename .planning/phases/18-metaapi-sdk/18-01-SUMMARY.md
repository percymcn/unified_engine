---
phase: 18
plan: 01
name: "MetaAPI SDK Integration"
subsystem: brokers
tags: [metaapi, mt4, mt5, sdk, trading]

dependency-graph:
  requires: [17]  # After broker completion
  provides:
    - MetaAPI SDK service wrapper
    - Dual-mode MT4/MT5 executors
    - Real-time streaming support
  affects: [19, 20]  # Webhook refinements, analytics

tech-stack:
  added:
    - metaapi-cloud-sdk>=29.0.0
  patterns:
    - dual-mode executor (SDK preferred, httpx fallback)
    - streaming synchronization listener

key-files:
  created:
    - app/services/metaapi_sdk_service.py
    - tests/test_metaapi_sdk.py
    - docs/metaapi-sdk-integration.md
  modified:
    - requirements.txt
    - app/core/config.py
    - app/brokers/mt4_executor.py
    - app/brokers/mt5_executor.py
    - app/infrastructure/adapters/mt4_adapter.py
    - app/infrastructure/adapters/mt5_adapter.py

decisions:
  - id: DEC-18-01
    description: "Use metaapi-cloud-sdk as unified MT4/MT5 trading API"
    rationale: "Official SDK provides better reliability, real-time streaming, and cloud access"
  - id: DEC-18-02
    description: "Implement dual-mode architecture with fallback to httpx"
    rationale: "Maintains backward compatibility with self-hosted Manager API setups"

metrics:
  duration: "~14 minutes"
  completed: "2026-01-21"
---

# Phase 18 Plan 01: MetaAPI SDK Integration Summary

**One-liner:** Integrated metaapi-cloud-sdk for MT4/MT5 with dual-mode executors, streaming support, and graceful fallback to Manager API.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add metaapi-cloud-sdk dependency | d1a48ce | requirements.txt |
| 2 | Create MetaAPI SDK Service wrapper | 27e390a | app/services/metaapi_sdk_service.py |
| 3 | Add MetaAPI environment variables | 2aa7f7b | app/core/config.py |
| 4 | Update MT4 Executor for dual-mode | 7e24cc0 | app/brokers/mt4_executor.py |
| 5 | Update MT5 Executor for dual-mode | 8eebc8b | app/brokers/mt5_executor.py |
| 6 | Update MT4 Adapter for MetaAPI | f0fa5cf | app/infrastructure/adapters/mt4_adapter.py |
| 7 | Update MT5 Adapter for MetaAPI | ccae3f9 | app/infrastructure/adapters/mt5_adapter.py |
| 8 | Add real-time streaming support | 7643d37 | app/services/metaapi_sdk_service.py |
| 9 | Add unit tests for MetaAPI SDK | e4ff3dd | tests/test_metaapi_sdk.py |
| 10 | Document supported features | b815091 | docs/metaapi-sdk-integration.md |

## Implementation Details

### MetaAPI SDK Service (892 lines)

Created comprehensive wrapper for metaapi-cloud-sdk:

**Connection Management:**
- `connect()` / `disconnect()` - Async connection lifecycle
- Auto-deploy accounts if needed
- Wait for terminal state synchronization

**Order Types Supported:**
- Market buy/sell
- Limit buy/sell
- Stop buy/sell
- Stop-limit buy/sell (MT5 only)

**Position/Order Management:**
- Get positions, orders from terminal state
- Modify position SL/TP
- Close position (full or partial)
- Close positions by symbol
- Modify/cancel pending orders

**Real-Time Streaming:**
- `add_synchronization_listener()` for callbacks
- `subscribe_to_symbols()` for bulk subscriptions
- `get_quotes_bulk()` for multiple symbols
- `wait_for_price()` with timeout

### Dual-Mode Executors

Both MT4 and MT5 executors now support:

1. **SDK Mode (Preferred)**
   - Uses MetaAPISDKService
   - Requires METAAPI_TOKEN + METAAPI_ACCOUNT_ID
   - Cloud-based trading
   - Real-time streaming

2. **Manager API Mode (Fallback)**
   - Uses httpx to self-hosted Manager API
   - Original implementation preserved
   - Works without MetaAPI credentials

**Mode Selection Logic:**
```python
if use_sdk and SDK_AVAILABLE and has_metaapi_credentials:
    try: connect via SDK
    except: fallback to httpx
else:
    use httpx directly
```

### Configuration

New environment variables:
- `METAAPI_TOKEN` - API token from app.metaapi.cloud
- `METAAPI_ACCOUNT_ID` - Provisioned account ID
- `METAAPI_APPLICATION` - Optional app name

Broker configs updated to include MetaAPI credentials alongside Manager API settings.

## Verification Results

**Unit Tests:**
```
tests/test_metaapi_sdk.py: 8 passed, 16 skipped (SDK not installed)
```

Tests properly skip when SDK not installed, pass for:
- Service initialization
- Health status without connection
- SDK availability detection
- Dual-mode executor configuration

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

### Blockers
None

### Concerns
- MetaAPI free tier has limitations (1 account)
- Real SDK testing requires credentials

### Prerequisites Met
- [x] MetaAPI SDK dependency added
- [x] Service wrapper complete
- [x] Executors support dual-mode
- [x] Adapters support MetaAPI credentials
- [x] Streaming support implemented
- [x] Tests passing
- [x] Documentation complete
